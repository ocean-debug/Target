# TargetDiscovery Agent

面向生命科学科研场景的药物靶点发现 Agent。项目参考 OpenScience 的科研工作台形态，重点建设生命科学垂直能力：Best Practice 工作流、公开组学分析、实测与预测扰动、证据追溯、可靠性审查和 TargetCard 报告。

## 一句话目标

输入疾病问题、候选靶点、GWAS 变异或公开组学数据，Agent 自动完成任务拆解、证据检索、工具选择、组学/扰动分析、靶点排序，并输出可追溯研究报告。

## 本月交付边界

主工作流：

```text
疾病问题
  -> 证据检索
  -> 遗传与组学分析
  -> observed / predicted perturbation
  -> gene -> program -> trait 整合
  -> 候选靶点排序
  -> 药物与实验验证路线
  -> TargetCard + Trace
```

本月不建设独立评测平台、不开展湿实验、不从零训练通用细胞大模型。评测只作为 Agent 内部的质量门。

## 仓库结构

```text
agents/                     专业 Agent 定义和 Prompt
workflows/                  Best Practice 工作流
schemas/                    跨模块数据合同
configs/                    工具注册和运行配置
src/target_agent/
  agent/                    Planner、Router、State、Session
  tools/evidence/           文献与数据库检索
  tools/omics/              公开组学分析
  tools/perturbation/       实测与预测扰动
  tools/genetics/           GWAS 与变异解释
  tools/target/             靶点评分与因果整合
  tools/drug/               药物匹配
  provenance/               Evidence DAG 与 Trace
  reviewer/                 Best Practice 和可靠性审查
  reports/                  TargetCard 与研究报告
cases/main_demo/            主 Demo 输入、预期产物和答疑
data/                       仅保存 manifest；大数据不进入 Git
models/                     模型卡和权重获取方式；权重不进入 Git
tests/                      小型成功、失败和回归案例
docs/                       架构、分工、完成标准和冲刺计划
```

## 开始协作

1. 阅读 [PROJECT_CHARTER.md](PROJECT_CHARTER.md)、[docs/OWNERSHIP.md](docs/OWNERSHIP.md) 和 [CONTRIBUTING.md](CONTRIBUTING.md)。
2. 从最新 `main` 创建短分支，例如 `feat/omics-qc`。
3. 先确认相关 Schema，再实现工具；不要在个人 Notebook 中定义私有接口。
4. 每个 PR 必须包含运行方法、一个成功样例、一个失败/边界样例和 Trace 位置。
5. 科学内容由生命科学成员复核，Agent/接口由工程成员复核。

## 共同完成标准

- 主 Agent 能生成计划并调用真实工具，不是单次知识问答。
- 至少接通文献/数据库、公开组学和扰动预测三类真实能力。
- 关键结论可回链到 EvidenceItem 或 ToolResult。
- 输出区分文献事实、实测结果、模型预测和团队推断。
- 工具失败、证据冲突或上下文不匹配时能够降级、追问或拒绝。
- 非作者成员可根据 README 复现主 Demo。

## 项目负责人

王海洋。六位成员共同对整体架构、科学正确性、接口联调、可靠性和最终演示负责；个人分工仅表示模块主责。
