#!/usr/bin/env bash
#PBS -q gpu
#PBS -N target-v2-workbench
#PBS -l nodes=gpu03:ppn=50
#PBS -j oe

set -eo pipefail
source /home/hywang/anaconda3/etc/profile.d/conda.sh
conda activate agenttest
set -u
export CUDA_VISIBLE_DEVICES=0
cd /home/hywang/codex/deecamp/Target
python -m target_agent serve --host 0.0.0.0 --port 8000
