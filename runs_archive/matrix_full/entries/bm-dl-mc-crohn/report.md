# TargetDiscovery Agent 研究报告

- 任务：Prioritize targets for Crohn disease
- 终态：`completed_with_gaps`
- 疾病：Crohn disease
- 组织 / 细胞：未限定 / 未限定
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE152316：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE152321：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE153974：`selected`；通过自动资格检查
- GSE159751：`selected`；通过自动资格检查
- GSE160925：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE174792：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE179285：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE186582：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE186963：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE192786：`rejected`；requires_at_least_3_biological_replicates_per_group

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | IL12B | 33.22 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | IL23R | 28.50 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 3 | NOD2 | 28.21 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | TNFSF15 | 26.91 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | ATG16L1 | 26.36 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 6 | ITGA4 | 25.24 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | LACC1 | 23.58 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | GPR35 | 23.53 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | IL10 | 23.15 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 10 | PTPN22 | 22.48 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |

## 重点 TargetCard

### 1. IL12B — GO

- 六维得分：遗传 20.72；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-3bd8282d0e55, ev-0845d9f2243d, ev-f392e2c05c5b, ev-a9bbff7c02c6, ev-27a7a54c0692, ev-bc2c7873b297, ev-cb3a08e6d13a, ev-020bca2ece49
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing IL12B activity in disease-relevant primary cell will move the prespecified Crohn disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL12B in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. IL23R — CONDITIONAL_GO

- 六维得分：遗传 20.50；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-9a3ced01046d, ev-37d051da1c57, ev-760493fde0ab, ev-0e6ba6f3dd58, ev-69e896bdbd3c, ev-45b50ad07fa8, ev-38bcffebd309
- 反方或混合证据：ev-e2e8f242df78, ev-4a3cb9180f4e
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing IL23R activity in disease-relevant primary cell will move the prespecified Crohn disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of IL23R in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. NOD2 — GO

- 六维得分：遗传 20.21；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-f0a10384bae9, ev-deefd0500d66, ev-ae22fcae57d8, ev-48cb8a0e032f, ev-a371ef428930, ev-cd818bc720dc, ev-274169b1938a, ev-74be2e8c0843
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing NOD2 activity in disease-relevant primary cell will move the prespecified Crohn disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of NOD2 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. TNFSF15 — GO

- 六维得分：遗传 18.91；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-a4079c9f2331, ev-5afd024ada05, ev-f594c875a80e
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing TNFSF15 activity in disease-relevant primary cell will move the prespecified Crohn disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TNFSF15 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. ATG16L1 — GO

- 六维得分：遗传 18.36；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-9e2be35c1105, ev-9df04ca9f7b0, ev-edf077d28ccb, ev-8ca3873ca6a7
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing ATG16L1 activity in disease-relevant primary cell will move the prespecified Crohn disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of ATG16L1 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE152316 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE152321 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE186963 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE192786 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
