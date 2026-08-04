# TargetDiscovery Agent 研究报告

- 任务：Two studies report opposite directions for a candidate gene in breast carcinoma; resolve by context
- 终态：`completed_with_gaps`
- 疾病：breast carcinoma
- 组织 / 细胞：breast / epithelial cell
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE253036：`selected`；通过自动资格检查
- GSE261033：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE276755：`selected`；通过自动资格检查
- GSE276760：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE284956：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE295336：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE300130：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE303026：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE308114：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE310291：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | BRIP1 | 29.37 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | CDH1 | 29.14 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | BRCA1 | 28.91 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | BRCA2 | 28.90 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | PALB2 | 28.88 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | CHEK2 | 28.69 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | MSH2 | 28.38 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | MLH1 | 28.35 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | MSH6 | 24.40 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | FBXO11 | 24.38 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |

## 重点 TargetCard

### 1. BRIP1 — GO

- 六维得分：遗传 21.37；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-b82dd4177ed7, ev-63a76919df32, ev-f9ca1815aef8, ev-069a22b8e560, ev-274cc8c1e59b, ev-f2f78e3884fc
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing BRIP1 activity in epithelial cell will move the prespecified breast carcinoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of BRIP1 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. CDH1 — GO

- 六维得分：遗传 21.14；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-e08449ef57b9, ev-4281697fbf7a, ev-f60897b556d1, ev-0b0f7bad72bc, ev-ef3a8f546688, ev-6d45505c8fa3, ev-33e2a9857b3c
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing CDH1 activity in epithelial cell will move the prespecified breast carcinoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CDH1 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. BRCA1 — GO

- 六维得分：遗传 20.91；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-61cb16a7b58f, ev-96bd15720c31, ev-0b14a1fa0a44, ev-d78115e506e5
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing BRCA1 activity in epithelial cell will move the prespecified breast carcinoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of BRCA1 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. BRCA2 — GO

- 六维得分：遗传 20.90；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-25572d5c5cfb, ev-b921fc24bcaf, ev-967919590980
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing BRCA2 activity in epithelial cell will move the prespecified breast carcinoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of BRCA2 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. PALB2 — GO

- 六维得分：遗传 20.88；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-5a2c25a279ce, ev-85bd856cbe79, ev-166d92049425, ev-ae7cedaaa889, ev-dd7fbcc117bf, ev-296a0f18a1dd
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing PALB2 activity in epithelial cell will move the prespecified breast carcinoma phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PALB2 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE261033 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE284956 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE295336 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE300130 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE303026 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE310291 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
