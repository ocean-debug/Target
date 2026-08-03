#!/usr/bin/env bash
#PBS -q gpu
#PBS -N target-ot-probe
#PBS -l nodes=gpu03:ppn=50
#PBS -j oe

set -eo pipefail
source /home/hywang/anaconda3/etc/profile.d/conda.sh
conda activate agenttest
set -u
cd /home/hywang/codex/deecamp/Target
python scripts/opentargets_probe.py
