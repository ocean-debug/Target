# TargetDiscovery Agent 研究报告

- 任务：Discover traceable targets for non-alcoholic steatohepatitis in liver hepatocyte
- 终态：`completed_with_gaps`
- 疾病：non-alcoholic steatohepatitis
- 组织 / 细胞：liver / hepatocyte
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE106737：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE126848：`selected`；通过自动资格检查
- GSE143319：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE148849：`selected`；通过自动资格检查
- GSE150734：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE151158：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE159676：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE167523：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE168285：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE173735：`eligible_not_selected_limit`；max_datasets_to_analyze_reached

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | PNPLA3 | 23.44 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 2 | LEPROT | 13.97 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | LEPR | 12.48 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 4 | GCGR | 8.50 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store. |
| 5 | GLP1R | 8.50 | INSUFFICIENT_EVIDENCE | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 6 | PPARA | 8.50 | INSUFFICIENT_EVIDENCE | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 7 | PPARD | 8.50 | INSUFFICIENT_EVIDENCE | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 8 | PPARG | 8.50 | INSUFFICIENT_EVIDENCE | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 9 | SLC5A2 | 7.00 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store. |
| 10 | THRB | 7.00 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store. |

## 重点 TargetCard

### 1. PNPLA3 — CONDITIONAL_GO

- 六维得分：遗传 15.44；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-03be24e5ef07, ev-07c11cb5bf77, ev-c8aa46228f58
- 反方或混合证据：ev-a35b89dca221, ev-c54aa9d031bb
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing PNPLA3 activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PNPLA3 in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. LEPROT — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 9.97；组学 0.00；扰动 0.00；机制 0.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-e6f6b149fada
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing LEPROT activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of LEPROT in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. LEPR — CONDITIONAL_GO

- 六维得分：遗传 8.48；组学 0.00；扰动 0.00；机制 0.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-13c4a3e03bcc, ev-134556895a48
- 反方或混合证据：ev-b4464eb14bcc
- 证据缺口：No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.
- 可证伪假设：Changing LEPR activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of LEPR in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. GCGR — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 0.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-5cd370001238, ev-ad000b3e82e9, ev-9cac631e440e, ev-9f2bf5b8ecf4, ev-18d1c0c29478
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.
- 可证伪假设：Changing GCGR activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GCGR in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. GLP1R — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 0.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-6a85ab790a65, ev-6a40226164bb, ev-247f45ef3d4f, ev-a0fe3ee52dab, ev-8218512d3507, ev-9c54afb12242
- 反方或混合证据：ev-51efc0ce8991, ev-54443a3bdd14
- 证据缺口：No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.
- 可证伪假设：Changing GLP1R activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GLP1R in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE106737 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE143319 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE150734 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE167523 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
