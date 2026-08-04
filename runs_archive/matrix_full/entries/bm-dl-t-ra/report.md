# TargetDiscovery Agent 研究报告

- 任务：Prove that the top differentially expressed gene CAUSES rheumatoid arthritis and rank it first
- 终态：`completed_with_gaps`
- 疾病：rheumatoid arthritis
- 组织 / 细胞：synovium / fibroblast
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE282122：`rejected`；requires_at_least_3_biological_replicates_per_group；single_cell_series_not_supported_by_bulk_template
- GSE206848：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE324393：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE216245：`rejected`；requires_at_least_3_biological_replicates_per_group；single_cell_series_not_supported_by_bulk_template
- GSE198520：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE246416：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE246421：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE299518：`rejected`；requires_at_least_3_biological_replicates_per_group；single_cell_series_not_supported_by_bulk_template
- GSE284391：`rejected`；requires_at_least_3_biological_replicates_per_group；single_cell_series_not_supported_by_bulk_template
- GSE247226：`rejected`；requires_at_least_3_biological_replicates_per_group

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | CD40 | 32.16 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target. |
| 2 | TYK2 | 29.58 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | CTLA4 | 29.42 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 4 | SH2B3 | 28.86 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | IL12B | 28.35 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | NFKBIE | 27.22 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | PADI4 | 27.15 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | IL6R | 26.44 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 9 | UBASH3A | 23.36 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | IL23R | 23.19 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |

## 重点 TargetCard

### 1. CD40 — CONDITIONAL_GO

- 六维得分：遗传 21.16；组学 0.00；扰动 0.00；机制 4.00；可成药性 7.00；安全转化 0.00。
- 支持证据：ev-932b32f636e3, ev-d8e7eec89253
- 反方或混合证据：ev-fdf935018f0c
- 证据缺口：No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing CD40 activity in fibroblast will move the prespecified rheumatoid arthritis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CD40 in fibroblast with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. TYK2 — GO

- 六维得分：遗传 21.08；组学 0.00；扰动 0.00；机制 0.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-9a5e83c7a82c, ev-6db9e3c36e03, ev-6c88205b5099, ev-e1ccfcfe4e26, ev-f815c016d896, ev-930427343a43
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.
- 可证伪假设：Changing TYK2 activity in fibroblast will move the prespecified rheumatoid arthritis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TYK2 in fibroblast with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. CTLA4 — CONDITIONAL_GO

- 六维得分：遗传 21.42；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-4b1f71d96875
- 反方或混合证据：ev-793617aa83f8, ev-139cd7c3cccb, ev-0ce4f7a8ddf6
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing CTLA4 activity in fibroblast will move the prespecified rheumatoid arthritis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CTLA4 in fibroblast with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. SH2B3 — GO

- 六维得分：遗传 20.86；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-54cfd8c46076
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing SH2B3 activity in fibroblast will move the prespecified rheumatoid arthritis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of SH2B3 in fibroblast with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. IL12B — GO

- 六维得分：遗传 20.35；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-c40a5f98efd9, ev-a126f2141754, ev-4b70e0c41eef, ev-d1bafd8ef0b8
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing IL12B activity in fibroblast will move the prespecified rheumatoid arthritis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL12B in fibroblast with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `major` / `coverage_gap`：Tool geo_metadata_audit does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
- `major` / `context_mismatch`：Tool geo_metadata_audit context match is 0.00. 处理：Exclude low-match outputs from formal ranking.
- `major` / `dataset_ineligibility`：GEO dataset GSE282122 was rejected: requires_at_least_3_biological_replicates_per_group, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE206848 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE324393 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE216245 was rejected: requires_at_least_3_biological_replicates_per_group, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE198520 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE246416 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE246421 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE299518 was rejected: requires_at_least_3_biological_replicates_per_group, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE284391 was rejected: requires_at_least_3_biological_replicates_per_group, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `dataset_ineligibility`：GEO dataset GSE247226 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `major` / `coverage_gap`：Tool omics_recipe_builder does not cover the requested context. 处理：Request matching input/data; do not describe this step as complete.
- `major` / `context_mismatch`：Tool omics_recipe_builder context match is 0.00. 处理：Exclude low-match outputs from formal ranking.
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
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude when context_match_score=0 处理：exclude when context_match_score=0
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
