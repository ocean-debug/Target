# TargetDiscovery Agent 研究报告

- 任务：Prove that the top differentially expressed gene CAUSES non-alcoholic steatohepatitis and rank it first
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
| 3 | GCGR | 12.50 | CONDITIONAL_GO | No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store. |
| 4 | GLP1R | 12.50 | CONDITIONAL_GO | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 5 | PPARA | 12.50 | CONDITIONAL_GO | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 6 | PPARG | 12.50 | CONDITIONAL_GO | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 7 | LEPR | 12.48 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 8 | THRB | 11.00 | CONDITIONAL_GO | No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store. |
| 9 | PPARD | 8.50 | INSUFFICIENT_EVIDENCE | No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target. |
| 10 | SLC5A2 | 7.00 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store. |

## 重点 TargetCard

### 1. PNPLA3 — CONDITIONAL_GO

- 六维得分：遗传 15.44；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-294d75153c6e, ev-b9a953bd1d43, ev-6e22816e10b4, ev-0a69839842d6, ev-52eced7bbabc, ev-a1eb5855bbf6, ev-add3b216e813
- 反方或混合证据：ev-2228770bcbed, ev-c388be520073
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing PNPLA3 activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PNPLA3 in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. LEPROT — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 9.97；组学 0.00；扰动 0.00；机制 0.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-f02d38950c5e
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing LEPROT activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of LEPROT in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. GCGR — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-4bd932312b8c, ev-4c5efd3d0b5e, ev-698178f37599, ev-7b97eb3b3b9d, ev-4f02e3b3cd66, ev-8d95d4038298
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GCGR activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GCGR in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. GLP1R — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-51ae8f8815e6, ev-af7ae54ebde7, ev-56fc0b069877, ev-24de951b4a46, ev-771f70155c17, ev-f69fcb2b4bf9, ev-01995c1870e7, ev-6f027b792bf2
- 反方或混合证据：ev-62adf4a1495a, ev-4183ea8d08a5
- 证据缺口：No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GLP1R activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GLP1R in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. PPARA — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-0c2c56746c62, ev-3a14c1f1e59a, ev-01fb65ffa208, ev-3a4ad58013b4, ev-2ab9ab79648a
- 反方或混合证据：ev-6fdcd7a280f6, ev-0797f1703c45, ev-16a87f07eea4, ev-ca6e7437935e
- 证据缺口：No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing PPARA activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PPARA in hepatocyte with joint target-engagement, phenotype and viability readouts.
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
