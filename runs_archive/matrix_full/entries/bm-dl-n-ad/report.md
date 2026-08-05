# TargetDiscovery Agent 研究报告

- 任务：Discover traceable targets for Alzheimer disease in brain neuron
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
| 8 | MS4A6A | 26.96 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | HFE | 22.61 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | EPHA1 | 22.59 | INSUFFICIENT_EVIDENCE | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |

## 重点 TargetCard

### 1. PSEN1 — GO

- 六维得分：遗传 21.47；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-94203066538c, ev-9dd306aee5bd, ev-356d8d21e4e8, ev-e0e63f7358c3, ev-703fb106045f, ev-6f0349b457f6, ev-02c74a547792, ev-3fe96c3cf371, ev-edee0a479cf8, ev-9cc17097971e, ev-9ec79124ffa8, ev-6b19c0a0e966, ev-20c20e058832, ev-544ec003e822, ev-240ca12b3f23
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing PSEN1 activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PSEN1 in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. APP — GO

- 六维得分：遗传 20.77；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-92c424332b4d, ev-b7383d44f232, ev-08443f2fcb2f, ev-7459666bf975, ev-cff79f06792d, ev-bbfadc809d96, ev-8806f0e02197, ev-d58e58b668a4, ev-07ec063fa110, ev-85d333ed966d, ev-babac8a4f4a2, ev-1069dec64808
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing APP activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of APP in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. PSEN2 — GO

- 六维得分：遗传 20.49；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-d878919af5f2, ev-914a7b24b78d, ev-b1f1c839270e, ev-dc5635324c43, ev-3d3ab3c0a109, ev-7c889f6fb816, ev-39ab099ec9c0, ev-3a4f3959f680, ev-b9485120d1af, ev-6d17d62f4e51, ev-5d9742b81759, ev-16ef67547d9e, ev-a2c9e57da0af
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing PSEN2 activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of PSEN2 in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. CR1 — GO

- 六维得分：遗传 20.56；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-e5c46fd8df51, ev-0de46fd7e958, ev-e161b242f122, ev-0a13f8790c8e
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing CR1 activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of CR1 in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. APOE — CONDITIONAL_GO

- 六维得分：遗传 20.01；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-8e6e3862a043, ev-40ee277746bc, ev-979809e08512, ev-ccaf1b8f47e3, ev-b94021caea9a, ev-c560d5acba16, ev-211bf7c4f359, ev-1560935cfee6, ev-ea0c46176441
- 反方或混合证据：ev-321de989f296, ev-7a7e7152fcbd, ev-a91a78005de6
- 证据缺口：No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing APOE activity in neuron will move the prespecified Alzheimer disease phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of APOE in neuron with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `major` / `causal_overreach`：Evidence ev-d58e58b668a4 uses causal language beyond its evidence class. 处理：Downgrade language or add a valid causal design.
- `major` / `causal_overreach`：Evidence ev-9cc17097971e uses causal language beyond its evidence class. 处理：Downgrade language or add a valid causal design.
- `major` / `causal_overreach`：Evidence ev-3a4f3959f680 uses causal language beyond its evidence class. 处理：Downgrade language or add a valid causal design.
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
- `major` / `causal_overreach`：LoRA reviewer confirmed causal_overreach: downgrade to OBSERVED and request causal validation 处理：downgrade to OBSERVED and request causal validation
- `major` / `context_mismatch`：LoRA reviewer confirmed out_of_distribution: exclude and do not emit 处理：exclude and do not emit

## 使用边界

- 组学差异、数据库关联和扰动相关均不能单独证明疾病因果。
- 低上下文匹配的预测不得进入正式得分。
- 实验方案是可证伪的研究建议，不替代伦理、临床或药物安全决策。
