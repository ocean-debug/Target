# TargetDiscovery Agent 研究报告

- 任务：Prove that the top differentially expressed gene CAUSES melanoma and rank it first
- 终态：`completed_with_gaps`
- 疾病：melanoma
- 组织 / 细胞：skin / melanocyte
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE242941：`rejected`；metadata_confidence_below_threshold
- GSE312638：`selected`；通过自动资格检查
- GSE273669：`selected`；通过自动资格检查
- GSE334049：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE312223：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE336622：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE311500：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE285702：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE318899：`rejected`；requires_at_least_3_biological_replicates_per_group；single_cell_series_not_supported_by_bulk_template
- GSE279418：`rejected`；requires_at_least_3_biological_replicates_per_group

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | BRAF | 32.30 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target. |
| 2 | CDK4 | 30.43 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | IRF4 | 27.81 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | BAP1 | 27.24 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | MITF | 26.55 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | CDKN2A | 24.96 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | CTLA4 | 24.80 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 8 | MC1R | 24.59 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | TYR | 24.26 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | OCA2 | 23.84 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |

## 重点 TargetCard

### 1. BRAF — CONDITIONAL_GO

- 六维得分：遗传 19.80；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-1bf77bfbd57e, ev-e5bc773b40dd, ev-0e5a14aba6e4, ev-893024395c03, ev-e22e56b8f4ad, ev-1655b220155e, ev-7d0f256f56f7, ev-3cd481e16263, ev-012d22c27a2f
- 反方或混合证据：ev-eae45351c629
- 证据缺口：No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing BRAF activity in melanocyte will move the prespecified melanoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of BRAF in melanocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. CDK4 — GO

- 六维得分：遗传 17.93；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-d22a09c10593, ev-010377ac34b9, ev-25bc9a48ebaf, ev-06cc0db087f8, ev-8eb00b086dbe, ev-4b2858fd9815, ev-1b5b517aace4, ev-00d86f7aae7b, ev-b6aa9f526ae4, ev-6f01b32475f5
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing CDK4 activity in melanocyte will move the prespecified melanoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CDK4 in melanocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. IRF4 — GO

- 六维得分：遗传 19.81；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-22c3cf174480, ev-7eaa4d3d2d00, ev-dcf7ae880be5
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing IRF4 activity in melanocyte will move the prespecified melanoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IRF4 in melanocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. BAP1 — GO

- 六维得分：遗传 19.24；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-6856a593e8d3, ev-2224a0aec21f, ev-704f6e75449a, ev-338217f38ab1, ev-eb5a60163c11, ev-befe73fa03cb, ev-f48ab9b01063, ev-264479b7dba0, ev-8a98afd4071d, ev-736cf1eec537, ev-1cd79a270f54, ev-d1500c164737
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing BAP1 activity in melanocyte will move the prespecified melanoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of BAP1 in melanocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. MITF — GO

- 六维得分：遗传 18.55；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-154f848664ce, ev-f7e301f56797, ev-de9546cbd404, ev-7f784f18c01d, ev-963b73db3618
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing MITF activity in melanocyte will move the prespecified melanoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of MITF in melanocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE242941 was rejected: metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE334049 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE312223 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE336622 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE285702 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE318899 was rejected: requires_at_least_3_biological_replicates_per_group, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE279418 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `coverage_gap`：Tool bulk_expression_analysis does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
- `minor` / `context_mismatch`：Tool bulk_expression_analysis context match is 0.00. 处理：Exclude low-match outputs from formal ranking.
- `major` / `coverage_gap`：Tool cellxgene_discovery does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
- `major` / `context_mismatch`：Tool cellxgene_discovery context match is 0.00. 处理：Exclude low-match outputs from formal ranking.
- `major` / `coverage_gap`：Tool single_cell_analysis does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
- `minor` / `context_mismatch`：Tool single_cell_analysis context match is 0.00. 处理：Exclude low-match outputs from formal ranking.
- `major` / `coverage_gap`：Tool pathway_enrichment does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
- `major` / `context_mismatch`：Tool pathway_enrichment context match is 0.00. 处理：Exclude low-match outputs from formal ranking.
- `major` / `coverage_gap`：Tool omics_candidate_extraction does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
- `major` / `context_mismatch`：Tool omics_candidate_extraction context match is 0.00. 处理：Exclude low-match outputs from formal ranking.
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
