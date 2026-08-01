# Architecture

## 设计原则

项目参考 OpenScience 的“Agent Runtime + Tool Layer + Skills + Workspace + Provenance”结构，但只实现靶点发现所需的垂直切片。

```text
User / Demo UI
      |
      v
TargetDiscovery Agent
  Intake -> Planner -> Router -> Critic -> Report
      |         |         |
      |         |         +-- Target / Drug tools
      |         +------------ Evidence / Omics / Perturbation / Genetics tools
      +---------------------- Workflow Pack + Best Practice rules
                                |
                                v
                       Evidence DAG + Run Trace
```

## 关键对象

- `TaskSpec`：用户问题、疾病上下文、约束和预期输出。
- `EvidenceItem`：一条支持或反对某个 claim 的来源化证据。
- `ToolResult`：任何工具的统一运行结果。
- `PerturbationResult`：observed 或 predicted 扰动的标准结果。
- `TargetCard`：候选靶点的完整证据包和 Go/No-Go 建议。

## 模块边界

### Agent Runtime

维护任务状态、计划、工具路由、重试、缓存、停止条件和报告状态。它不实现具体生物学算法。

### Evidence Layer

负责文献和数据库连接、EvidenceItem标准化、去重以及claim-source回链。

### Omics Layer

负责数据可用性判断、QC、差异、通路、细胞状态和program分析。重计算结果必须物化为ToolResult。

### Perturbation Layer

负责实测Perturb-seq、scGen/GEARS等预测工具、上下文/OOD检查和observed-predicted比较。

### Target Reasoning

将遗传、组学、扰动、可药性和安全性整合为可拆解排序，不用单一黑箱总分隐藏冲突。

### Reviewer

检查引用、数字、图表、细胞上下文、疾病阶段、扰动方向、模型适用范围和因果措辞。Reviewer只给出结构化发现，不静默修改原结果。

### Reports/UI

展示Plan、工具调用、TargetCard、Evidence Graph和Trace。页面不得生成后端不存在的新数字。

## 可靠性状态

每个结论必须标记为 `FACT`、`OBSERVED`、`PREDICTED` 或 `INFERRED`。当出现以下情况时，Agent必须追问、降级或拒绝：

- 组织、细胞类型或疾病阶段不匹配；
- 模型未覆盖目标基因或扰动类型；
- 工具失败、数据质量不足或来源不可用；
- 多类证据方向冲突；
- 缺少能够支持关键因果措辞的证据。
