#!/usr/bin/env bash
#PBS -q gpu
#PBS -N target-v2-validate
#PBS -l nodes=gpu03:ppn=50
#PBS -j oe

set -eo pipefail
source /home/hywang/anaconda3/etc/profile.d/conda.sh
conda activate agenttest
set -u
export CUDA_VISIBLE_DEVICES=0
cd /home/hywang/codex/deecamp/Target

python -m pip install -e '.[test]'
python -m target_agent export-schemas --output schemas
python -m target_agent generate-alignment --output alignment_data
python scripts/validate_mch_gold.py
python scripts/repo_policy_check.py
pytest
python scripts/environment_witness.py
