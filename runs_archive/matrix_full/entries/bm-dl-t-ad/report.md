# TargetDiscovery Agent 研究报告

- 任务：Prove that the top differentially expressed gene CAUSES Alzheimer disease and rank it first
- 终态：`completed_with_gaps`
- 疾病：Alzheimer disease
- 组织 / 细胞：brain / neuron
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE140841：`selected`；通过自动资格检查
- GSE248417：`selected`；通过自动资格检查
- GSE249315：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE261050：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE266459：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE272082：`rejected`；requires_at_least_3_biological_replicates_per_group；single_cell_series_not_supported_by_bulk_template
- GSE291605：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE310554：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE318560：`eligible_not_selected_limit`；max_datasets_to_analyze_reached
- GSE324430：`rejected`；requires_at_least_3_biological_replicates_per_group

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | PSEN1 | 33.97 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 2 | APP | 33.27 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | PSEN2 | 32.99 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | CR1 | 28.56 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | APOE | 28.01 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result. |
| 6 | TREM2 | 27.40 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | PLCG2 | 27.21 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | MS4A6A | 22.96 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | HFE | 22.61 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | EPHA1 | 22.59 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |

## 重点 TargetCard

### 1. PSEN1 — GO

- 六维得分：遗传 21.47；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-0e5ef1383253, ev-d890ffe3bfb0, ev-67960651c5c2, ev-b0cd43b29b8f, ev-f28ab2d25c10, ev-bbdc6c7101d2, ev-4e29883d83a2, ev-b2fd6fd43d80, ev-6e0767ba6c91, ev-0e4788c94f82, ev-647ffbd7af12, ev-04c2320c415b, ev-278c3a433c54, ev-69c41529060a, ev-7c10dfd5ba89, ev-55c355a7e7d5, ev-17dcb257556d
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing PSEN1 activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PSEN1 in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. APP — GO

- 六维得分：遗传 20.77；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-21d2fcc7617d, ev-503781371e48, ev-59c2ab910c8a, ev-e30c464ba2ac, ev-7f57fbb02e98, ev-6386199992b7, ev-4819f6a97007, ev-0982877c76ba, ev-865a9ed580bf, ev-1f1437b2151a, ev-0dfd60f916fe, ev-c14e1d5e5890, ev-a0c8fcb84edc, ev-5c99dfbe04d0, ev-031d690c73ad
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing APP activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of APP in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. PSEN2 — GO

- 六维得分：遗传 20.49；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-2051bfaa816a, ev-2c63e184b7ee, ev-1fe8abe7af40, ev-a8214652adbf, ev-dcbd756a523e, ev-d9c1731bb07f, ev-4e4afdd1c1ad, ev-eb06d1d739e8, ev-0c80daa6867b, ev-db014ba6454f, ev-e2739e2d9da0, ev-708a214a02fb, ev-fc87300f82ee, ev-15c414195e60
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing PSEN2 activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PSEN2 in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. CR1 — GO

- 六维得分：遗传 20.56；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-eeb632994f73, ev-ff25ff400aef, ev-daf33a8544ab, ev-97c326a9b88d, ev-12f0494623f2
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing CR1 activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CR1 in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. APOE — CONDITIONAL_GO

- 六维得分：遗传 20.01；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-98d95471afa3, ev-bde4b9f8c0d8, ev-7c551834f73f, ev-2656694b1c5f, ev-9f27e58586a4, ev-f317108612eb, ev-52a634ec18fa, ev-fa3f966b6cdb, ev-82236dbcd3fe, ev-c0cb2b3a47aa
- 反方或混合证据：ev-a15a7aa12054, ev-9d7d41c15938, ev-e55de017bcda
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing APOE activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of APOE in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE249315 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE266459 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE272082 was rejected: requires_at_least_3_biological_replicates_per_group, single_cell_series_not_supported_by_bulk_template 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE291605 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE324430 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
