# V2 架构与边界

```text
TaskSpec 2.0
  → Planner（Step JSON / deterministic fallback）
  → 白名单 Router
  → Europe PMC / Open Targets / UC Omics / observed perturbation / DeltaFactor / MCH gold
  → append-only Evidence Store + Trace + checkpoints
  → deterministic Reviewer（最多2轮）
  → 六维排名 + 独立阻断项
  → mechanistic evidence graph（UC）或 causal model（MCH only）
  → 5 TargetCards + falsifiable experiments + report
```

## 为什么不使用复杂 Agent 框架

三周交付的核心风险是科学边界、合同漂移和可追溯性，不是编排功能不足。当前状态机以 Pydantic 合同和落盘检查点为中心，路径可审计、可恢复，且更适合现场演示。

## 证据层级

- `FACT`：文献/数据库明确陈述，必须带逐字来源跨度。
- `OBSERVED`：本项目从公开数据重算或迁移的实测结果。
- `PREDICTED`：模型输出，必须带训练与验证范围。
- `INFERRED`：Agent 综合判断，必须引用底层 EvidenceItem。

Reviewer 无权把低上下文预测升级成实验事实。前端只渲染 `report.json`、`ranked_targets.json` 和图合同，不执行科学计算。

## 双场景

UC 输出 mechanistic evidence graph：遗传、组学、实测扰动、预测扰动和 Agent 推断的边类型分别保留，不称为 UC 因果图。

MCH 输出 causal model：只接受 `desired_phenotype=MCH`；论文 43/59 与扩展 94/147 分开。任何其他性状返回 `out_of_scope`。
