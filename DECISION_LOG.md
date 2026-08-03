# Decision Log

跨模块接口、工作流、模型选择和科学边界的决定记录在这里。已经冻结的决定不得在个人分支中静默修改。

## 模板

### YYYY-MM-DD — 决策标题

- **状态**：proposed / accepted / superseded
- **提出工作流**：
- **参与工作流**：
- **问题**：
- **候选方案**：
- **最终决定**：
- **理由**：
- **影响模块**：
- **迁移或回滚方法**：
- **相关 Issue/PR**：

---

## 2026-08-01 — 采用共享 Schema 作为模块边界

- **状态**：accepted
- **提出工作流**：A（评测协议与协调）
- **参与工作流**：A–F
- **问题**：多个工作流并行开发时，组学、扰动、证据和报告模块容易产生不兼容字段。
- **最终决定**：跨模块对象必须以 `schemas/` 中的版本化 JSON Schema 为准；工作流通过这些对象交接。
- **理由**：减少口头约定和后期集中联调成本。
- **影响模块**：全部模块。
- **迁移或回滚方法**：破坏性变更创建新版本并保留旧字段的迁移说明。
- **相关 Issue/PR**：项目初始化 PR。
# V2 decisions — 2026-08-03

- This Target repository is the only maintained repository; handover assets are read-only inputs.
- Public contracts move to 2.0.0 and are generated from Pydantic; legacy data is accepted only through an explicit one-way adapter.
- UC is the primary target-discovery demo; MCH/K562 is an isolated causal-modelling gold sample.
- Low-context DeltaFactor predictions are exploratory and excluded from UC formal ranking.
- Reports and the UI may only render structured Evidence Store values.
- Experience promotion and LoRA training are offline, auditable and human-approved; no automatic code, training or publishing mutation is allowed.
