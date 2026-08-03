#!/usr/bin/env bash
#PBS -q gpu
#PBS -N target-v2-demo-accept
#PBS -l nodes=gpu03:ppn=50
#PBS -j oe

set -eo pipefail
source /home/hywang/anaconda3/etc/profile.d/conda.sh
conda activate agenttest
set -u
export CUDA_VISIBLE_DEVICES=0
cd /home/hywang/codex/deecamp/Target
prefix="accept-${PBS_JOBID%%.*}"
python scripts/demo_acceptance.py --prefix "$prefix"

