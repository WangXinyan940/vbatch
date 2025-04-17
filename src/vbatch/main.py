import argparse
from .build import run


def main():
    parser = argparse.ArgumentParser(
        description="Job submit tool for volc ML platform."
    )
    parser.add_argument("input", type=str, help="Bash script file you want to submit.")
    parser.add_argument(
        "--priority",
        type=int,
        default=None,
        help="Priority of the job. Default is 4. (Only 2, 4, 6 are supported)",
    )
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)
