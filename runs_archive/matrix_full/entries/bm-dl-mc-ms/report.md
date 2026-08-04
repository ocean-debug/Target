# TargetDiscovery Agent 研究报告

- 任务：Prioritize targets for multiple sclerosis
- 终态：`completed_with_gaps`
- 疾病：multiple sclerosis
- 组织 / 细胞：未限定 / 未限定
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE120375：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE194078：`selected`；通过自动资格检查
- GSE203241：`selected`；通过自动资格检查
- GSE205763：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE208747：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE209596：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE211358：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE214625：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE216026：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE216028：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | CD58 | 27.40 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | TNFRSF1A | 26.30 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 3 | IL7R | 26.09 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | CD86 | 25.92 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | IL2RA | 23.09 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | RRP15 | 12.19 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | KEAP1 | 9.58 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | KCNH8 | 9.03 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | CDK4 | 8.73 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | S1PR5 | 7.98 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |

## 重点 TargetCard

### 1. CD58 — GO

- 六维得分：遗传 19.40；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-5c27d2b3815f, ev-01ad6d4f38d9, ev-37cc9139d318
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing CD58 activity in disease-relevant primary cell will move the prespecified multiple sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CD58 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. TNFRSF1A — CONDITIONAL_GO

- 六维得分：遗传 18.30；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-b65aae3e5333, ev-905f2b92b162, ev-6cbacc80280f
- 反方或混合证据：ev-f7a73584c1e9, ev-b30ea4a1d6a8, ev-b1b5d5c6ff40
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing TNFRSF1A activity in disease-relevant primary cell will move the prespecified multiple sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TNFRSF1A in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. IL7R — GO

- 六维得分：遗传 18.09；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-229119c5bc7f, ev-e65da28f208c
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing IL7R activity in disease-relevant primary cell will move the prespecified multiple sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL7R in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. CD86 — GO

- 六维得分：遗传 17.92；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-38000e4b9acc, ev-03208b88e715, ev-b4f345799dfb
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing CD86 activity in disease-relevant primary cell will move the prespecified multiple sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CD86 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. IL2RA — GO

- 六维得分：遗传 15.09；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-b7ad1934e38a, ev-597e64c016c9, ev-c12d07df60b2, ev-0ed8865a13a1, ev-c6655e520847
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing IL2RA activity in disease-relevant primary cell will move the prespecified multiple sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL2RA in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE120375 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE205763 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE211358 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE214625 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE216026 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE216028 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
- `major` / `coverage_gap`：LoRA reviewer confirmed missing_context: request tissue/cell context or report scoped evidence 处理：request tissue/cell context or report scoped evidence
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
