# TargetDiscovery Agent 研究报告

- 任务：Prove that the top differentially expressed gene CAUSES type 2 diabetes mellitus and rank it first
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
| 2 | FTO | 29.87 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 3 | ABCC8 | 28.96 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target. |
| 4 | KCNJ11 | 28.92 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target. |
| 5 | WFS1 | 28.82 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | CTRB2 | 25.39 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | CTRB1 | 25.37 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | KL | 24.93 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | LPL | 24.73 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 10 | APOE | 24.64 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |

## 重点 TargetCard

### 1. GCK — GO

- 六维得分：遗传 21.03；组学 0.00；扰动 0.00；机制 4.00；可成药性 7.00；安全转化 0.00。
- 支持证据：ev-6993b12fb7d5, ev-e7228b475518, ev-e9c9d494ffbe, ev-4f292e48ffa7, ev-529c4d52820a, ev-8dddda9b8b02, ev-9754176bb944
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GCK activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GCK in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. FTO — CONDITIONAL_GO

- 六维得分：遗传 21.87；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-ac315b0dc426, ev-6bba4cf31537
- 反方或混合证据：ev-9f4423b49478, ev-30218d6b9c31, ev-5a91a87d0599
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing FTO activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of FTO in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. ABCC8 — CONDITIONAL_GO

- 六维得分：遗传 20.96；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-5430a042488a, ev-a162a26faf3c, ev-767fe03ad040, ev-93b07efc831d, ev-a671662b7ed7, ev-01e3b4284117, ev-d9ae6a866b69, ev-4ea8778780ab, ev-cd544f354ed6
- 反方或混合证据：ev-3d0988323317, ev-a15dba6d4e20, ev-97f9b14b8a8e
- 证据缺口：No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing ABCC8 activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of ABCC8 in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. KCNJ11 — CONDITIONAL_GO

- 六维得分：遗传 20.92；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-e89ecce784b4, ev-2471a3be977c, ev-d1f56cdc977d, ev-10cd3237d486, ev-4819712e2f61, ev-258a60a0845e, ev-03b305e4fcbf, ev-2a29ea6ca674, ev-4721a3414807, ev-4edccbb5f79b, ev-5e265f5b1b73
- 反方或混合证据：ev-6743d780ad38, ev-c016924104c9, ev-fce0a1727c08
- 证据缺口：No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing KCNJ11 activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of KCNJ11 in beta cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. WFS1 — GO

- 六维得分：遗传 20.82；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-bf982b9e0909, ev-a0b224db1590
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing WFS1 activity in beta cell will move the prespecified type 2 diabetes mellitus phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of WFS1 in beta cell with joint target-engagement, phenotype and viability readouts.
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
