# TargetDiscovery Agent 研究报告

- 任务：Discover traceable targets for colorectal cancer in colon epithelial cell
- 终态：`completed_with_gaps`
- 疾病：colorectal cancer
- 组织 / 细胞：colon / epithelial cell
- 科学表达：FACT / OBSERVED / PREDICTED / INFERRED 全程分离；总分仅用于排序。

## 数据集选择

- GSE151911：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE288724：`selected`；通过自动资格检查
- GSE319878：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE308712：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE316624：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE310401：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE290123：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE271043：`rejected`；requires_at_least_3_biological_replicates_per_group
- GSE298631：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold
- GSE326923：`rejected`；requires_at_least_3_biological_replicates_per_group；metadata_confidence_below_threshold

## 候选靶点排名

| 排名 | 靶点 | 总分 | 决策 | 关键缺口 |
|---:|---|---:|---|---|
| 1 | TP53 | 33.48 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target. |
| 2 | MSH2 | 29.93 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 3 | MSH6 | 29.77 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 4 | MLH1 | 29.17 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 5 | FGFR3 | 28.85 | CONDITIONAL_GO | No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target. |
| 6 | MLH3 | 28.32 | GO | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 7 | FBXO11 | 25.82 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 8 | PMS2 | 25.12 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 9 | SMAD7 | 24.51 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |
| 10 | FLCN | 24.28 | INSUFFICIENT_EVIDENCE | No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target. |

## 重点 TargetCard

### 1. TP53 — CONDITIONAL_GO

- 六维得分：遗传 20.98；组学 0.00；扰动 0.00；机制 4.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-1b6471c4e6ae, ev-21208b5e55d1, ev-892b38a8678b, ev-8d869df4182b, ev-44eba6907996
- 反方或混合证据：ev-325fa69d9138, ev-e8e25425373d, ev-fc28b20f087d
- 证据缺口：No matched-context measured perturbation evidence for this target.
- 可证伪假设：Changing TP53 activity in epithelial cell will move the prespecified colorectal cancer phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of TP53 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 2. MSH2 — GO

- 六维得分：遗传 21.93；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-20a553483e37, ev-564782fa6a3e
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing MSH2 activity in epithelial cell will move the prespecified colorectal cancer phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of MSH2 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 3. MSH6 — GO

- 六维得分：遗传 21.77；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-131ef2f66936, ev-dfc1a60c1330
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing MSH6 activity in epithelial cell will move the prespecified colorectal cancer phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of MSH6 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 4. MLH1 — GO

- 六维得分：遗传 21.17；组学 0.00；扰动 0.00；机制 4.00；可成药性 4.00；安全转化 0.00。
- 支持证据：ev-bc428e861bf0, ev-4f1ed529d9ed
- 反方或混合证据：无
- 证据缺口：No matched, source-grounded safety evidence was retrieved.；No matched-context measured perturbation evidence for this target.；No known drug was returned in the current Open Targets result.
- 可证伪假设：Changing MLH1 activity in epithelial cell will move the prespecified colorectal cancer phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of MLH1 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

### 5. FGFR3 — CONDITIONAL_GO

- 六维得分：遗传 20.35；组学 0.00；扰动 0.00；机制 0.00；可成药性 8.50；安全转化 0.00。
- 支持证据：ev-029242a0e6ea, ev-e500f910f9e8, ev-97b9b510e791, ev-ea1d23dea259, ev-c07357f40dd5, ev-4471281e681a
- 反方或混合证据：ev-975510a9ee27
- 证据缺口：No matched-context measured perturbation evidence for this target.；No span-validated literature claim for this target.
- 可证伪假设：Changing FGFR3 activity in epithelial cell will move the prespecified colorectal cancer phenotype in the desired direction without a prohibitive viability effect.
- 信息价值最高的下一实验：A direction-resolved, donor-replicated perturbation of FGFR3 in epithelial cell with joint target-engagement, phenotype and viability readouts.
- 停止条件：no target engagement with two validated reagents；reproducible toxicity at the minimum effective exposure；no primary-endpoint effect at adequate power

## Reviewer 结论

- `minor` / `dataset_ineligibility`：GEO dataset GSE151911 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE319878 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE308712 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE316624 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE310401 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE290123 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE271043 was rejected: requires_at_least_3_biological_replicates_per_group 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE298631 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
- `minor` / `dataset_ineligibility`：GEO dataset GSE326923 was rejected: requires_at_least_3_biological_replicates_per_group, metadata_confidence_below_threshold 处理：Select the next eligible dataset or retain the omics dimension as a documented gap.
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
