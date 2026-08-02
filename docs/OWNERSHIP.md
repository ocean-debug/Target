# Workstream Ownership（匿名）

团队共同对完整 Agent 负责。仓库只记录工作流及交付接口，不记录成员姓名或个人对应关系；“主责”表示交付边界，不表示单独开发。

| 工作流 | 主责范围 | 本周交付 | 月度交付接口 |
| --- | --- | --- | --- |
| A｜评测协议与协调 | Evidence Schema、Rubric、指标、Judge 校准、跨工作流节奏 | 评测协议 v1、5 题端到端试跑 | 可靠性质量门、版本冻结清单、整体验收记录 |
| B｜Agent 系统与基线 | Agent 主链、Planner/Router/State、Trace、复跑、缓存、模型路由 | 3 个 Baseline 及完整运行记录 | 可恢复的 Agent Runtime、一键运行入口、模型与工具路由 |
| C｜Gold Set 与科学证据 | 湿实验 Gold Set、证据等级、阴性/冲突题、组学与实测扰动科学审核 | 20 题骨架、5 题 Gold | Gold Set、证据分级规范、科学证据与组学分析资产 |
| D｜Demo 与临床产品 | Demo 叙事、药物安全、Go/No-Go、实验验证路线 | Demo Brief、代表案例复核 | 可演示疾病案例、TargetCard 内容、临床前验证建议 |
| E｜证据存储与前端 | 数据库连接器、Evidence Store、Provenance、Evidence Card 与 Trace 回放 | 数据模型、Trace UI | 可追溯证据存储、报告生成、Demo 前端 |
| F｜Benchmark 与消融 | Benchmark Runner、消融、错误分类、实验 Rubric、预测扰动可靠性 | 指标设计、错误标签 | 自动化 Benchmark、消融报告、错误分析与风险门控 |

## 协作接口

- **A ↔ B/F**：A 冻结协议与 Rubric；B 提供运行 Trace；F 实现自动计算、消融和错误归因。
- **B ↔ C/E**：B 统一工具合同与运行状态；C 提供科学证据和组学资产；E 保存 Evidence 与 Trace。
- **C ↔ D/F**：C 复核证据等级、组学和实测扰动；D 将其转为案例叙事与实验路线；F 检查可靠性边界。
- **D ↔ E**：D 定义 Demo 与 TargetCard 展示需求；E 提供可回放前端和可追溯报告。
- **共同责任**：整体架构、科学正确性、接口联调、最终 Demo 与答疑由所有工作流共同承担。

## 隐私约定

个人姓名、联系方式及工作流与个人的对应关系不进入仓库、Issue 或 PR。仓库权限和人员安排通过 GitHub 设置及线下协作渠道维护。
