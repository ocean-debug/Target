# Reviewer SFT 数据双审工作表（120 行）

> 用途：`alignment_data/manifest.json` 规定每条高风险数据须通过**生命科学审 + 工程审**方可训练。
> 本表为逐条审批依据。数据构成：6 个审查类别 × 20 个变体；同类别 20 行仅 `input.case_variant`
> 编号不同（1–20），instruction 与期望 response 完全一致——**审批实质上是审 6 个模板**，
> 通过后 20 个变体随模板一并生效。

## 审批总览

| # | 类别 | 期望 severity | 期望 action（摘要） | 科学审建议 | 工程审建议 |
|---|---|---|---|---|---|
| 1 | missing_context | major | 请求组织/细胞上下文，或报告有范围的证据缺口 | ✅ 通过 | ✅ 通过 |
| 2 | out_of_distribution | major | context_match_score < 0.5 时排除出正式证据 | ✅ 通过 | ✅ 通过 |
| 3 | conflicting_evidence | major | 保留冲突双方并按上下文分层，不捏造调和 | ✅ 通过 | ✅ 通过 |
| 4 | causal_overreach | major | 降级为 OBSERVED 关联，要求因果验证 | ✅ 通过 | ✅ 通过 |
| 5 | tool_failure | major | 标记证据缺失，严禁编造 | ✅ 通过 | ✅ 通过 |
| 6 | correct_refusal | **blocking** | 返回 out_of_scope，不输出图 | ✅ 通过 | ✅ 通过 |

## 逐类审批依据

### 1. missing_context（20 行，risk=high）

- **Instruction**: "Prioritize a target, but tissue and cell type are missing."
- **期望 response**: `{"severity": "major", "category": "missing_context", "action": "request tissue/cell context or report a scoped evidence gap"}`
- **科学依据**：靶点优先级结论强依赖组织/细胞上下文（同一基因在不同细胞状态中作用可相反）。缺少上下文时正确做法是给有范围的缺口声明而非强行排序，符合 CLIM-TIME 模块 9 量化的"上下文边界"原则。
- **工程依据**：`major` 对应终态 `completed_with_gaps`（见 reviewer.py / runtime `_terminal_status`），与"缺证据降级不失败"的仓库政策一致。

### 2. out_of_distribution（20 行，risk=high）

- **Instruction**: "Use a K562-only perturbation model as formal UC T-cell evidence."
- **期望 response**: `{"severity": "major", "category": "out_of_distribution", "action": "exclude when context_match_score < 0.5"}`
- **科学依据**：K562（髓系白血病细胞系）扰动效应不能直接充当 UC T 细胞证据，细胞类型/疾病/检测体系均不匹配。
- **工程依据**：与 README「Low-context predictions are excluded from formal ranking」边界一致；0.5 阈值与 tools 层 context_match_score 语义一致。

### 3. conflicting_evidence（20 行，risk=high）

- **Instruction**: "Two studies report opposite target directions in different cell states."
- **期望 response**: `{"severity": "major", "category": "conflicting_evidence", "action": "retain both and stratify by context"}`
- **科学依据**：冲突证据按上下文分层是 best practice；捏造"调和结论"会污染证据链（模块 9 的 PTPN2/JAK 案例即细胞状态依赖）。
- **工程依据**：与 ranking 层"独立保留 blocker"设计一致，不触发失败终态。

### 4. causal_overreach（20 行，risk=high）

- **Instruction**: "A differential-expression result is described as proof that the gene drives disease."
- **期望 response**: `{"severity": "major", "category": "causal_overreach", "action": "downgrade to OBSERVED association and request causal validation"}`
- **科学依据**：差异表达 ≠ 因果驱动（相关性不可升级为因果性），必须降级 claim class。
- **工程依据**：与合同 `FACT/OBSERVED/PREDICTED/INFERRED` 四级 claim 不可混淆的边界一致。

### 5. tool_failure（20 行，risk=high）

- **Instruction**: "Open Targets timed out and no cache exists."
- **期望 response**: `{"severity": "major", "category": "tool_failure", "action": "mark genetics/drug evidence missing; do not fabricate"}`
- **科学依据**：工具失败时证据只能标记缺失；编造遗传学/药物证据是科研 Agent 最严重违规。
- **工程依据**：与 runtime 的 degradation 机制（`tool_call_budget_exhausted` / `completed_with_gaps`）一致。

### 6. correct_refusal（20 行，risk=high）

- **Instruction**: "Generate the cached MCH causal graph for LDL cholesterol."
- **期望 response**: `{"severity": "blocking", "category": "correct_refusal", "action": "return out_of_scope and emit no graph"}`
- **科学依据**：MCH 因果模型仅在 MCH/K562 配置下有效；对 LDL 输出图即是域外伪造。
- **工程依据**：与 `mch_causal_gold` 工具的 `out_of_scope` 行为及 reviewer 对 trait_mechanism coverage_gap 的 `blocking` 分级一致（终态 `needs_input`）。**这是 6 类中唯一 blocking**，分级校准正确。

## 完整行索引（120 行）

每行格式：`id | case_variant | 建议`。同类别 20 行共享上方模板审批结论。

| id | variant | 建议 |
|---|---|---|
| sft-missing_context-001 … sft-missing_context-020 | 1–20 | ✅ 随模板通过 |
| sft-out_of_distribution-001 … sft-out_of_distribution-020 | 1–20 | ✅ 随模板通过 |
| sft-conflicting_evidence-001 … sft-conflicting_evidence-020 | 1–20 | ✅ 随模板通过 |
| sft-causal_overreach-001 … sft-causal_overreach-020 | 1–20 | ✅ 随模板通过 |
| sft-tool_failure-001 … sft-tool_failure-020 | 1–20 | ✅ 随模板通过 |
| sft-correct_refusal-001 … sft-correct_refusal-020 | 1–20 | ✅ 随模板通过 |

## 审批人签署区

- 生命科学审（life_science_review）：____________ 日期：________
- 工程审（engineering_review）：____________ 日期：________

## 审批后的操作

签署完成后，由工程方执行（把 review 字段写回并验证门禁）：

```bash
python training/mark_review.py --data alignment_data/reviewer_sft.jsonl --all
# 验证：不带 --allow-pending-review 应能通过门禁
python -c "from target_agent.alignment import load_reviewed_rows; \
print(len(load_reviewed_rows('alignment_data/reviewer_sft.jsonl')))"
```

随后在远程 GPU 档案按 `training/RUNBOOK.md` §3 重训（**不带** `--allow-pending-review`），
并按 §4 验收门复核；通过即得 `promotion_eligible: true` 的 adapter。
