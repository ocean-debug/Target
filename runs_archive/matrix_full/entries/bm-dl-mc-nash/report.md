# TargetDiscovery Agent 研究报告

- 任务：Prioritize targets for non-alcoholic steatohepatitis
- 终态：`completed_with_gaps`
- 疾病：non-alcoholic steatohepatitis
- 组织 / 细胞：未限定 / 未限定
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE106737：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE126848：`selected`；通过自动资格检查
- GSE143319：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE148849：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE150734：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE151158：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE159676：`selected`；通过自动资格检查
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
- 支持证据：ev-9fe18995a218, ev-07586723a36d, ev-3a7e9c876982, ev-0ba16a86d34e, ev-79246119053d, ev-1f819ca53eaf, ev-5643ae95d86b
- 反方或混合证据：ev-555cf13e8fa2, ev-9e0cde8a5be4
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing PNPLA3 activity in disease-relevant primary cell will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PNPLA3 in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. LEPROT — INSUFFICIENT_EVIDENCE

- 六维得分：遗传 9.97；组学 0.00；扰动 0.00；机制 0.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-52ca59435b05
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing LEPROT activity in disease-relevant primary cell will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of LEPROT in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. GCGR — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-3563a6703034, ev-eb2e29b6a7cf, ev-fb643125b505, ev-639cc9d5d897, ev-a5cb5fae79af, ev-da165f8e8039, ev-f00ceb0bf31c, ev-91ccb771652b
- 反方或混合证据：ev-6646332fb600
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GCGR activity in disease-relevant primary cell will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GCGR in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. GLP1R — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-194267a4d1e3, ev-b95c1d1627cc, ev-aaff01e05664, ev-eff2e08c9122, ev-4db6523892fd, ev-f2b0c9a042a9, ev-552d849969f5, ev-fd426c9b9fc3
- 反方或混合证据：ev-ff03a4e59eed, ev-4a3c5e854710
- 证据缺口：No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing GLP1R activity in disease-relevant primary cell will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of GLP1R in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. PPARA — CONDITIONAL_GO

- 六维得分：遗传 0.00；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-78474e1b2250, ev-dfab5d4fac75, ev-4bc39540dbe1, ev-d61c68cfa0f7, ev-144458a5a509
- 反方或混合证据：ev-a5ea4e2a1fe8, ev-eb9f2d74388d, ev-7e69c49d9ee9, ev-0a921536cd34
- 证据缺口：No qualifying human-genetic evidence in the current store.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing PPARA activity in disease-relevant primary cell will move the prespecified non-alcoholic steatohepatitis phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PPARA in disease-relevant primary cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE106737 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE143319 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE148849 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE150734 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE151158 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
- `major` / `coverage_gap`：LoRA reviewer confirmed missing_context: request tissue/cell context or report scoped evidence 处理：request tissue/cell context or report scoped evidence
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
