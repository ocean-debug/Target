---
id: single-cell-pseudobulk
name: 单细胞正式差异（pseudobulk）
description: 单细胞正式疾病差异采用 供体×细胞类型×条件 pseudobulk，至少 3 位独立供体；per-cell marker 只能做探索。
version: 1.0.0
evidence_lanes: ["omics", "single_cell"]
scopes: ["disease_target_discovery", "single_cell"]
---

# Single-cell Pseudobulk Best Practice

## 适用
CELLxGENE Census、标准 .h5ad、标准 10x 矩阵的正式差异分析。

## 硬性规则
1. Census 固定版本 2025-11-08；先查规模并只用 is_primary_data == True。
2. 单次自动分析最多 10 万细胞、下载不超过 2 GB；保留原始 count 层，不覆盖。
3. 正式差异采用 donor × cell_type × condition 的 pseudobulk；每组至少 3 位独立供体。
4. per-cell marker 只作探索结果，不作正式疾病差异证据。
5. 用户 H5AD 缺少可靠 cell_type/donor/condition 字段时返回缺口，不自动虚构注释。
