# TargetDiscovery Agent 研究报告

- 任务：Two studies report opposite directions for a candidate gene in psoriasis; resolve by context
- 终态：`completed_with_gaps`
- 疾病：psoriasis
- 组织 / 细胞：skin / keratinocyte
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE154200：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE171012：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE173706：`rejected`；single_cell_series_not_supported_by_bulk_template
- GSE176509：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold；single_cell_series_not_supported_by_bulk_template
- GSE183047：`rejected`；single_cell_series_not_supported_by_bulk_template
- GSE186063：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE192867：`selected`；通过自动资格检查
- GSE200977：`selected`；通过自动资格检查
- GSE201397：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE203415：`rejected`；requires_at_least_3_biological_replicates_per_group

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | IL12B | 34.36 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | TYK2 | 33.55 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | TRAF3IP2 | 29.08 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 4 | CARD14 | 28.75 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | IL23R | 28.33 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 6 | IL36RN | 28.15 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | TNFAIP3 | 27.96 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | EGFL8 | 25.19 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | SH2B3 | 24.12 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | IL13 | 23.53 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |

## 重点 TargetCard

### 1. IL12B — GO

- 六维得分：遗传 21.86；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-71a8a6c9f4ed, ev-6cd3eeaf04ba, ev-ed7d0e20a7ea, ev-981697f11c89, ev-d157e90193f0, ev-a45907aa9ee3, ev-8e4df089df99, ev-76581b97888b, ev-ebc038732547, ev-d4cbba58c648, ev-2732885732a1
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing IL12B activity in keratinocyte will move the prespecified psoriasis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL12B in keratinocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. TYK2 — GO

- 六维得分：遗传 21.05；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-be83910a7201, ev-f03ddcf7125d, ev-e578d203e8b5, ev-516feb029205, ev-605dc580dc04, ev-2fc445d5c0da, ev-ada25fb40109, ev-418653f811e5, ev-4903e51c692d, ev-a0e651244056, ev-3fb3c0b343fd
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing TYK2 activity in keratinocyte will move the prespecified psoriasis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TYK2 in keratinocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. TRAF3IP2 — CONDITIONAL_GO

- 六维得分：遗传 21.08；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-6e173ff4b983, ev-ca8a3bdfcba9, ev-937735215b2b, ev-518caea950f7
- 反方或混合证据：ev-42ab5cb108fd
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing TRAF3IP2 activity in keratinocyte will move the prespecified psoriasis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TRAF3IP2 in keratinocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. CARD14 — GO

- 六维得分：遗传 20.75；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-0751026d358b, ev-c35ec4f310ae, ev-e3af07fd67f5, ev-da43a27485a0, ev-7805ad351b51, ev-8b2c86e81383, ev-60eb5bc53060, ev-023fd2c7ba07
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing CARD14 activity in keratinocyte will move the prespecified psoriasis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CARD14 in keratinocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. IL23R — CONDITIONAL_GO

- 六维得分：遗传 20.33；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-e7cb3af0efc5, ev-55295aec6782, ev-74679e76f028, ev-69e84185dc23, ev-4c0f4f90e34e
- 反方或混合证据：ev-9358d1c25743, ev-d83f81e5a6df
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing IL23R activity in keratinocyte will move the prespecified psoriasis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL23R in keratinocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE154200 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE171012 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE173706 was rejected: single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE176509 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE183047 was rejected: single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE186063 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE201397 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE203415 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
