# TargetDiscovery Agent 研究报告

- 任务：Two studies report opposite directions for a candidate gene in type 2 diabetes mellitus; resolve by context
- 终态：`completed_with_gaps`
- 疾病：type 2 diabetes mellitus
- 组织 / 细胞：pancreatic islet / beta cell
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE198906：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE221156：`rejected`；single_cell_series_not_supported_by_bulk_template
- GSE277551：`selected`；通过自动资格检查
- GSE282850：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE196797：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE282230：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold；single_cell_series_not_supported_by_bulk_template
- GSE153855：`rejected`；single_cell_series_not_supported_by_bulk_template
- GSE251911：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE251913：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE281600：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | GCK | 32.03 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | ABCC8 | 28.96 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target. |
| 3 | KCNJ11 | 28.92 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target. |
| 4 | FTO | 25.87 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 5 | CTRB2 | 25.39 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | CTRB1 | 25.37 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | KL | 24.93 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | WFS1 | 24.82 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | LPL | 24.73 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 10 | APOE | 24.64 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |

## 重点 TargetCard

### 1. GCK — GO

- 六维得分：遗传 21.03；组学 0.00；扰动 0.00；机制 4.00；可成药性 7.00；安全转化 0.00。
- 支持证据：ev-1532637d97db, ev-9b9db7645c24, ev-7bf9d05931e4, ev-22524e4a5a9c, ev-05b192c4e06c, ev-2cb030fa0887, ev-6a35be14a9af
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GCK activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GCK in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. ABCC8 — CONDITIONAL_GO

- 六维得分：遗传 20.96；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-84db149c2660, ev-f96cc372f7ef, ev-836587e63075, ev-6170019c0c5e, ev-f4a07c95c4bb, ev-e49c0a596ecd, ev-b969389a2dc0, ev-bf63a62d968d, ev-2533c2568eda, ev-e489a1ed2240
- 反方或混合证据：ev-706f4cda1a67, ev-26b8f371dddc, ev-09cc43f5c5c9
- 证据缺口：No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing ABCC8 activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of ABCC8 in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. KCNJ11 — CONDITIONAL_GO

- 六维得分：遗传 20.92；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-0fb724e96f88, ev-b99825a83435, ev-1cdf6999f12e, ev-d4f67ce47c2e, ev-d0f5ade22c3e, ev-e35cbf4564c7, ev-f7e7bbbc6b21, ev-c63f625799ea, ev-097229575cee, ev-ccdc991e144e, ev-9e47e2a4a227
- 反方或混合证据：ev-95baf84357ba, ev-488e32deba31, ev-3f9d3b0816c5
- 证据缺口：No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing KCNJ11 activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of KCNJ11 in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. FTO — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 21.87；组学 0.00；扰动 0.00；机制 0.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-c7103f803066
- 反方或混合证据：ev-0f8e19d157af, ev-2b5833e24b9b, ev-0f0c6d23fe25
- 证据缺口：No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing FTO activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of FTO in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. CTRB2 — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 21.39；组学 0.00；扰动 0.00；机制 0.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-301906db8630
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing CTRB2 activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CTRB2 in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE198906 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE221156 was rejected: single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE282850 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE196797 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE282230 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE153855 was rejected: single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE251911 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE251913 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE281600 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
