# TargetDiscovery Agent 研究报告

- 任务：Prioritize targets for amyotrophic lateral sclerosis
- 终态：`completed_with_gaps`
- 疾病：amyotrophic lateral sclerosis
- 组织 / 细胞：未限定 / 未限定
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE183204：`selected`；通过自动资格检查
- GSE205718：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE209696：`selected`；通过自动资格检查
- GSE212131：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE212134：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE212630：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE213125：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE214017：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE217625：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE219278：`rejected`；requires_at_least_3_biological_replicates_per_group

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | FUS | 29.28 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | SOD1 | 29.24 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | TARDBP | 29.14 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | SQSTM1 | 29.02 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | TBK1 | 28.75 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 6 | UBQLN2 | 28.27 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | SETX | 27.93 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | MASP2 | 25.04 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | ANG | 24.63 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | TUBA4A | 23.94 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |

## 重点 TargetCard

### 1. FUS — GO

- 六维得分：遗传 21.28；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-db7d6f57c4f4, ev-7bca637ffb85, ev-bb43d9f769ed, ev-a2c12b11ab21, ev-6247917e956b, ev-f17c067c8112, ev-5f84ef8eea05, ev-e079b4660998, ev-3ee42bfbb55a, ev-ce3747d619a5, ev-93fcd0aa0c27, ev-9e532f8831a1
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing FUS activity in disease-relevant primary cell will move the prespecified amyotrophic lateral sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of FUS in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. SOD1 — GO

- 六维得分：遗传 21.24；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-c3fd20f29412, ev-349ce55d24cf, ev-5b6fec8610f8, ev-6b34b27d2d09, ev-2cd8a7060a25, ev-4e1429d8f05a, ev-a4da8ddd96e9, ev-247f9a45dc37, ev-e24e5ea4fa22, ev-aedb98d45db4, ev-1449f62da9fc
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing SOD1 activity in disease-relevant primary cell will move the prespecified amyotrophic lateral sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of SOD1 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. TARDBP — GO

- 六维得分：遗传 21.14；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-600e52bfe17e, ev-be20b50ae79c, ev-247fe128ee50, ev-ae5bbea8ed03, ev-8740de5a5ae5, ev-13a7d6098f20, ev-c4be61aaee6b
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing TARDBP activity in disease-relevant primary cell will move the prespecified amyotrophic lateral sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TARDBP in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. SQSTM1 — GO

- 六维得分：遗传 21.02；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-cd99ad5a2526, ev-b6c9618079da, ev-e44b6db223f3, ev-4f293b992e46, ev-9cd86901b001, ev-f1e2e4400d48
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing SQSTM1 activity in disease-relevant primary cell will move the prespecified amyotrophic lateral sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of SQSTM1 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. TBK1 — CONDITIONAL_GO

- 六维得分：遗传 20.75；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-135c3b839fb1, ev-3c820ba28b3d, ev-bc1362a83a58, ev-4363bb5281da, ev-31936257c30e, ev-35dcdd2dfb16, ev-88364a5e24fd
- 反方或混合证据：ev-583333043709
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing TBK1 activity in disease-relevant primary cell will move the prespecified amyotrophic lateral sclerosis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TBK1 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE205718 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE212131 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE212134 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE213125 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE219278 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
- `major` / `coverage_gap`：LoRA reviewer confirmed missing_context: request tissue/cell context or report scoped evidence 处理：request tissue/cell context or report scoped evidence
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
