#!/bin/bash
# VBATCH --image vemlp-cn-beijing.cr.volces.com/preset-images/python:3.10
# VBATCH --partition your-own-queue
# VBATCH --flavor ml.g3a.xlarge
# VBATCH --vepfs-id your-vepfs-id
# VBATCH --vepfs-path /Your_Path
# VBATCH --vepfs-mount-path /vepfs
# VBATCH --tags example1,example2
# VBATCH --task-name vbatch-submit
# VBATCH --description tool_test
# VBATCH --priority 4
# VBATCH --preemptible true
# VBATCH --activedeadlineseconds 1h
# VBATCH --delayexittimeseconds 0s
# VBATCH --accesstype Public

source ~/.bashrc
source activate
conda deactivate 
conda activate /vepfs/conda-envs/your-env-name

which python
echo "success"
pwd
ls -l ../*