import yaml
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import argparse
import time

exclude_envs = [
    "NVIDIA_VISIBLE_DEVICES",
    "SUPERVISOR_GROUP_NAME",
    "COLORTERM",
    "TERM_PROGRAM_VERSION",
    "SUPERVISOR_SERVER_URL",
    "VSCODE_PROXY_URI",
    "MLP_CODE_SERVER_PATH",
    "NVIDIA_DRIVER_CAPABILITIES",
    "MLP_CONSOLE_HOST",
    "VSCODE_GIT_ASKPASS_EXTRA_ARGS",
    "VSCODE_GIT_IPC_HANDLE",
    "NODE_EXEC_PATH",
    "VSCODE_GIT_ASKPASS_NODE",
    "MLP_INNER_CONTAINER",
    "MLP_INNER_JWT_PUBLIC_KEY_BASE64",
    "GIT_ASKPASS",
    "PROMPT_COMMAND",
    "MLP_DEVINSTANCE_ID",
    "MLP_IS_CANARY",
    "MLP_TRACKING_ENDPOINT",
    "MLP_ACCOUNT_ID",
    "VSCODE_GIT_ASKPASS_MAIN",
    "BROWSER",
    "MLP_TLS_INSECURE_SKIP_VERIFY",
    "MLP_IS_STRESS",
    "MLP_REGION",
    "VSCODE_IPC_HOOK_CLI",
]

template = {
    "TaskName": "vbatch-submit",
    "Description": "",
    "Framework": "Custom",
    "TaskRoleSpecs": [
        {"RoleName": "worker", "RoleReplicas": 1, "Flavor": "ml.xni3cl.28xlarge"}
    ],
    "Storages": [],
    "Envs": [],
    "RemoteMountCodePath": "/root/code",
    "Priority": 4,
    "Preemptible": False,
    "ActiveDeadlineSeconds": "1h",
    "DelayExitTimeSeconds": "0h",
    "AccessType": "Public",
}


def load_vscript(path: Path):
    with open(path, "r") as f:
        text = f.readlines()
    script_line, conf_line = [], []
    for line in text:
        if line.strip():
            if line.startswith("# VBATCH"):
                conf_line.append(line)
            else:
                script_line.append(line)

    # load config
    config_info = {}
    for line in conf_line:
        val = line.strip().split()[-1]
        if line.startswith("# VBATCH --image"):
            config_info["ImageUrl"] = val
        elif line.startswith("# VBATCH --partition"):
            config_info["ResourceQueueID"] = val
        elif line.startswith("# VBATCH --flavor"):
            config_info["Flavor"] = val
        elif line.startswith("# VBATCH --vepfs-id"):
            config_info["VepfsId"] = val
        elif line.startswith("# VBATCH --vepfs-path"):
            config_info["SubPath"] = val
        elif line.startswith("# VBATCH --vepfs-mount-path"):
            config_info["MountPath"] = val
        elif line.startswith("# VBATCH --tags"):
            tags = val.strip().split(",")
            config_info["Tags"] = tags
        elif line.startswith("# VBATCH --task-name"):
            config_info["TaskName"] = val
        elif line.startswith("# VBATCH --description"):
            config_info["Description"] = val
        elif line.startswith("# VBATCH --priority"):
            config_info["Priority"] = val
        elif line.startswith("# VBATCH --preemptible"):
            config_info["Preemptible"] = (val.lower() == 'true')
        elif line.startswith("# VBATCH --activedeadlineseconds"):
            config_info["ActiveDeadlineSeconds"] = f"{val}"
        elif line.startswith("# VBATCH --delayexittimeseconds"):
            config_info["DelayExitTimeSeconds"] = f"{val}"
        elif line.startswith("# VBATCH --accesstype"):
            config_info["AccessType"] = f"{val}"
    return script_line, config_info


def build_script(script_lines, path):
    script_inners = "\n".join([line.rstrip() for line in script_lines[1:]])
    return f"""{script_lines[0]}

cd \"{path}\"

{script_inners}

"""


def submit_job(base_bash: Path, priority: int = None):
    for key, val in os.environ.items():
        if key.upper() in exclude_envs:
            continue
        template["Envs"].append({"Name": key, "Value": val, "IsPrivate": True})

    script, config = load_vscript(base_bash)

    if "ImageUrl" in config:
        template["ImageUrl"] = config["ImageUrl"]
    if "ResourceQueueID" in config:
        template["ResourceQueueID"] = config["ResourceQueueID"]
    if "Flavor" in config:
        template["TaskRoleSpecs"][0]["Flavor"] = config["Flavor"]
    if "VepfsId" in config:
        template["Storages"].append(
            {
                "MountPath": config["MountPath"],
                "ReadOnly": False,
                "SubPath": config["SubPath"],
                "Type": "Vepfs",
                "VepfsId": config["VepfsId"],
            }
        )
    if "Tags" in config:
        template["Tags"] = config["Tags"]
    if "TaskName" in config:
        template["TaskName"] = config["TaskName"]
    if "Description" in config:
        template["Description"] = config["Description"]
    priority_to_use = 4
    if "Priority" in config:
        priority_to_use = int(config["Priority"])
    if priority is not None:
        priority_to_use = priority
    if priority_to_use not in [2, 4, 6]:
        raise ValueError("Priority must be 2, 4, or 6 or remain None.")
    template["Priority"] = priority_to_use
    if 'Preemptible' in config:
        template["Preemptible"] = config['Preemptible']
    if 'ActiveDeadlineSeconds' in config:
        template["ActiveDeadlineSeconds"] = config['ActiveDeadlineSeconds']
    if 'DelayExitTimeSeconds' in config:
        template["DelayExitTimeSeconds"] = config['DelayExitTimeSeconds']
    if 'AccessType' in config:
        template["AccessType"] = config['AccessType']

    log_name = str(Path(base_bash).with_suffix(".log").absolute())
    current_path = str(Path("./").absolute())
    template["Entrypoint"] = f'cd /root/code && bash run.sh >& \"{log_name}\"'
    script_text = build_script(script, current_path)

    with TemporaryDirectory() as tempdir:
        run_script_path = f"{tempdir}/run.sh"
        with open(run_script_path, "w") as f:
            f.write(script_text)
        template["UserCodePath"] = run_script_path

        yaml_path = f"{tempdir}/job.yaml"
        with open(yaml_path, "w") as f:
            yaml.safe_dump(template, f)

        try:
            subprocess.run(
                ["volc", "ml_task", "submit", "--conf", yaml_path], check=True
            )
        except subprocess.CalledProcessError:
            time.sleep(1.0)
            subprocess.run(
                ["volc", "ml_task", "submit", "--conf", yaml_path], check=True
            )


def run(args: argparse.ArgumentParser):
    input = args.input
    priority = args.priority
    if not os.path.exists(input):
        print(f"File {input} does not exist.")
        return
    submit_job(input, priority)
