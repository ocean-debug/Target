# Ownership

六位成员共同对完整 Agent 负责。下表中的“主责”表示交付接口人，不表示单独开发。

| 成员 | 主责目录/模块 | 最终交付 | 主要协作 |
| --- | --- | --- | --- |
| 王海洋 | `agents/`、`workflows/`、组学与扰动科学规则、靶点评分规范 | TargetDiscovery Agent定义、Disease→Target工作流、组学/扰动科学方案、评分规则、最终科学审核 | 张炜民、陈锦钰、陈政翰 |
| 张炜民 | `src/target_agent/agent/`、`schemas/`、`configs/` | AgentState、Planner、Router、工具注册、重试/缓存/恢复、一键启动 | 全员 |
| 陈锦钰 | `tools/omics/`、observed perturbation、`data/` | Dataset Card、QC、差异/通路/细胞状态、cNMF/program、Perturb-seq实测工具 | 王海洋、陈政翰 |
| 钱可 | `tools/drug/`、TargetCard内容、实验路线、`cases/` | Disease Brief、Go/No-Go、药物证据、实验方案、Demo科学叙事 | 王海洋、纪家灏、陈政翰 |
| 纪家灏 | `tools/evidence/`、`tools/genetics/`、`provenance/`、报告/UI | 文献数据库连接、Evidence Store、Chorus/AlphaGenome工具、回链、报告生成和展示 | 张炜民、钱可 |
| 陈政翰 | predicted perturbation、`tools/target/`、`models/` | scGen/GEARS、OOD Gate、gene→program→trait、可解释靶点排序和模型卡 | 王海洋、陈锦钰、钱可 |

## 交叉责任

- **组学计算**：王海洋、陈锦钰共同负责。
- **扰动预测**：王海洋、陈政翰共同负责，陈锦钰提供实测比较。
- **Agent联调**：全员负责，张炜民管理发布版本。
- **Evidence与报告**：纪家灏、钱可共同负责，全员审核。
- **最终Demo**：钱可负责叙事，纪家灏负责页面，张炜民负责运行，王海洋负责科学审核，全员参与答疑。

## GitHub账号

目前仅确认仓库管理员为 `@ocean-debug`。其他成员加入仓库后，请在这里补充GitHub账号，并更新 `.github/CODEOWNERS`；不要猜测或使用未经确认的账号。
