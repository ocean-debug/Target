# TargetDiscovery Agent 研究报告

- 任务：Two studies report opposite directions for a candidate gene in non-alcoholic steatohepatitis; resolve by context
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
- 支持证据：ev-ff4644c6f3dd, ev-c1466eb647a4, ev-1f1ea4785917, ev-f16f6099393f, ev-2ced037b8f94, ev-362533a5759d, ev-8207e482a478, ev-b84b8a7daee3
- 反方或混合证据：ev-0704e065c513, ev-3017bf2db4aa
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing PNPLA3 activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PNPLA3 in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. LEPROT — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 9.97；组学 0.00；扰动 0.00；机制 0.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-59fa80e0cbfe
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing LEPROT activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of LEPROT in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. GCGR — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-e35f98814941, ev-5aac95f97aba, ev-a7449b279148, ev-611ec1a4380c, ev-d3bafe712a93, ev-402eaab59535, ev-ac1801630ce0, ev-b89569fff28c, ev-6f4bfe41399b, ev-c7229cc7d4aa
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GCGR activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GCGR in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. GLP1R — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-052e171e01fe, ev-1e49374c1597, ev-b4fb12dada2a, ev-41a9dcef19ce, ev-a8dfbbcb1861, ev-ce3bcc527c85, ev-08bf4924cfa2, ev-89aa26083039, ev-6555118cc51f, ev-3544a691942d, ev-620591800df6
- 反方或混合证据：ev-044d55d8ed30, ev-e5265f930336
- 证据缺口：No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GLP1R activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GLP1R in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. PPARA — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-c06b08b72ba9, ev-bf8abe2a1bb6, ev-5bee2f149685, ev-a4902ff992df, ev-0816b4da0a39
- 反方或混合证据：ev-b391d1224748, ev-0ea3cb73e458, ev-2be8dad58227, ev-a81b7ce5f836
- 证据缺口：No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing PPARA activity in hepatocyte will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PPARA in hepatocyte with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `major` / `causal_overreach`：Evidence ev-3544a691942d uses causal language beyond its evidence class. 处理：Downgrade language or add a valid causal design.
- `major` / `causal_overreach`：Evidence ev-620591800df6 uses causal language beyond its evidence class. 处理：Downgrade language or add a valid causal design.
- `major` / `causal_overreach`：Evidence ev-6f4bfe41399b uses causal language beyond its evidence class. 处理：Downgrade language or add a valid causal design.
- `major` / `causal_overreach`：Evidence ev-c7229cc7d4aa uses causal language beyond its evidence class. 处理：Downgrade language or add a valid causal design.
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
- `major` / `causal_overreach`：LoRA reviewer confirmed causal_overreach: downgrade to OBSERVED and request causal validation 处理：downgrade to OBSERVED and request causal validation
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
