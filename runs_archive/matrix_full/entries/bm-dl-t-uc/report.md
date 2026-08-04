# TargetDiscovery Agent 研究报告

- 任务：Prove that the top differentially expressed gene CAUSES ulcerative colitis and rank it first
- 终态：`completed_with_gaps`
- 疾病：ulcerative colitis
- 组织 / 细胞：rectum / T cell
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE199906：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE228122：`selected`；通过自动资格检查
- GSE185101：`selected`；通过自动资格检查
- GSE185102：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE245890：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE151911：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE169360：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE177044：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE186963：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE189040：`rejected`；requires_at_least_3_biological_replicates_per_group；single_cell_series_not_supported_by_bulk_template

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | IL12B | 32.37 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | IL23R | 28.34 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 3 | FCGR2A | 27.46 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | JAK2 | 26.90 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 5 | TNFSF15 | 25.84 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | IRF5 | 25.71 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | CXCR2 | 24.97 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | IL10 | 23.87 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 9 | GPR35 | 23.45 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | MST1 | 22.22 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |

## 重点 TargetCard

### 1. IL12B — GO

- 六维得分：遗传 19.87；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-d299e50cff6a, ev-d9b7c2e7552e, ev-020403b512e9, ev-0fce4b91597a, ev-8de57c404a0c, ev-22ca63db364b, ev-f060a82c4955, ev-9269dbc47438
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing IL12B activity in T cell will move the prespecified ulcerative colitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL12B in T cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. IL23R — CONDITIONAL_GO

- 六维得分：遗传 20.34；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-e55371254150, ev-dafd5d034c54, ev-f4dfc5e88fa4
- 反方或混合证据：ev-765f18e1dc69, ev-2bc4523a0af8
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing IL23R activity in T cell will move the prespecified ulcerative colitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL23R in T cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. FCGR2A — GO

- 六维得分：遗传 19.46；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-ef3926497402, ev-81660f935f7a, ev-5dc3c8b5b910, ev-c558f8574a97, ev-5df82507b29e, ev-f87d1e7d971c
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing FCGR2A activity in T cell will move the prespecified ulcerative colitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of FCGR2A in T cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. JAK2 — CONDITIONAL_GO

- 六维得分：遗传 18.40；组学 0.00；扰动 0.00；机制 0.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-7c57496c55ff, ev-cdd13cc32eeb, ev-c55b265f0870, ev-f8b2bf616a2c, ev-858be3073b01, ev-81ea74a4a9cc
- 反方或混合证据：ev-a4899556597f, ev-03462d16c04f
- 证据缺口：No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.
- 可证伪假设：Changing JAK2 activity in T cell will move the prespecified ulcerative colitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of JAK2 in T cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. TNFSF15 — GO

- 六维得分：遗传 17.84；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-17e7922e2c7d, ev-0a07e2ecf189, ev-8482013db156
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing TNFSF15 activity in T cell will move the prespecified ulcerative colitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TNFSF15 in T cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE199906 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE185102 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE245890 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE169360 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE177044 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE186963 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE189040 was rejected: requires_at_least_3_biological_replicates_per_group, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `coverage_gap`：Tool omics_recipe_builder does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
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
- `major` / `coverage_gap`：Tool clinical_trials_gov has partial coverage. 处理：Expose uncovered genes/context as an evidence gap.
- `major` / `context_mismatch`：Tool clinical_trials_gov context match is 0.40. 处理：Exclude low-match outputs from formal ranking.
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
