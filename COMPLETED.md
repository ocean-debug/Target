# Target 已完成能力与证据边界

> 状态日期：2026-08-05  
> 本文只记录仓库中已经实现且有检查路径的能力；未完成项不会写成产品能力。具体远程验收事实见 [docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md)。

## 1. 已完成的科学主链

### 1.1 通用任务与上下文合同

- `TaskSpec` 记录疾病、亚型、组织、细胞类型、阶段、物种、目标表型和数据集限制；
- 任务支持疾病到靶点与受控遗传学/机制输入；
- 缺少上下文时保留缺口，不从自然语言中静默虚构；
- 关键科学对象以 Pydantic 为单一源并导出 JSON Schema。

### 1.2 动态公开组学流程

- 疾病标准化、GEO 动态检索、候选数据集评分与元数据资格审查；
- 整数 count 矩阵走 PyDESeq2，非整数/连续矩阵会被拒绝；
- 单细胞正式差异证据要求 donor、condition、cell type，并采用 donor-level pseudobulk；
- 支持 QC、差异结果、通路富集、候选基因提取和来源校验和；
- 没有合格数据时，其他证据链继续，终态降级为 `completed_with_gaps`。

### 1.3 遗传学与多证据融合

- 受控 GWAS summary-statistics 候选宇宙冻结、变异校验与 provenance；
- 审查用户提供的 SuSiE credible set 与 coloc 输出；
- 遗传学、组学、扰动、机制、可成药性和安全性分维度记录；
- 上下文匹配系数、预测扰动上限、反方证据和安全阻断项独立保留；
- 分数仅作为优先级，不表述为临床成功概率。

当前边界：尚未在主链中重算 fine-mapping/coloc；Open Targets 聚合证据不替代正式遗传统计；上下文错配的 K562/DeltaFactor 结果不得进入疾病正式得分。

### 1.4 研究交付物

- 候选排序、重点 TargetCard、证据缺口、Go/Conditional Go/Insufficient Evidence；
- 可证伪实验计划，明确干预、模型、对照、终点和不同结果对应结论；
- Evidence Store、Trace、工具版本/参数与报告回链；
- 报告从结构化存储生成，不能新造后端不存在的数字。

## 2. 已完成的可靠性控制面

### 2.1 持久项目模型

- 项目、目标、计划、work item、result、artifact、assessment、decision 和 event 为类型化记录；
- 项目 spec 与基础 plan 冻结；事件、评审和决定追加记录；
- artifact 内容寻址并校验 SHA-256；
- 项目目录是恢复单元，跨进程执行锁避免同一项目被并发运行；
- 终态、依赖失败、预算和缺口具有显式状态。

### 2.2 项目执行/完整性评审触发的有界修复

已实现的真实边界是：

```text
typed transient failure
-> digest-bound independent FAIL assessment
-> immutable RepairRequest
-> deterministic policy eligibility
-> append-only ResearchPlanRevision overlay
-> same-input affected-subgraph rerun
-> re-review + RepairResolution
-> new release snapshot digest
```

自动修复必须同时满足：模块 side-effect-free、replay-safe、声明 `same_input_retry`、输入 digest 不变且仍在预算内。checkpointed/supervised 模式要求对精确 trigger snapshot 批准；过期 digest 被拒绝。旧 result/assessment/artifact 不删除；当前 runtime 的 finalize 与 release digest 使用逻辑 active item 集，API ledger 仍返回全部历史记录并额外给出 active item IDs，尚无 WorkItemHead/ArtifactHead。

尚未完成：领域科学 Reviewer finding 驱动的补证、通用 GEO 数据集切换、科学方法改变、跨证据补证、上下文拆分和从自由 Reviewer 文本直接生成修复。系统明确不执行这些动作。

### 2.3 Review 与发布

- 结构完整性评审和领域 Reviewer 分离；
- finding 可分 blocking/major/minor，结果绑定 target digest；
- 修复后必须重新 Review；
- release decision marker 绑定当前 active project snapshot SHA-256，而不是只绑定 plan ID；
- 输入或修复导致快照变化时，旧 marker 不再适用；当前尚无独立 `ReleaseRecord`、专家签名或认证发布包。

## 3. 已完成的产品接口

- CLI：创建、运行、状态、事件、活动、checkpoint、repair queue 和 repair decision；
- HTTP：项目创建/运行/状态、事件、领域活动、artifact、repair queue 与 snapshot-bound 决策；
- stdio MCP：十一项类型化工具，全部调用同一 `ResearchProjectService`；
- Web 与 MCP 不建立第二套状态语义；
- 决策已持久化但后台队列已满时，接口区分“决定已接受”和“是否成功排队”。

## 4. 已完成的 benchmark 与对齐资产

- 内部 fake/unit benchmark 覆盖合同、恢复、拒绝、确定性和引擎一致性；
- 参考 blind-ranking scorer 能在载入私有标签前冻结任务、排名和状态 digest，并计算 disease-macro 指标及 trap/safety gate；
- Planner/Reviewer SFT、偏好和 held-out 资产具有角色字段与 promotion gate；现有 120 条 SFT 是 6 个模板各 20 个索引变体，科学与工程角色由同一负责人完成，不是独立双人审核；
- benchmark runner 已读取权威 `reviewer_findings.jsonl`，并支持显式 `finding_category` 断言。

重要限定：历史 18 疾病 `conflicting_evidence` 桶的 54/54 仅验证终态、provenance 和报告存在；当时 `expectation.reviewer_categories` 未作为可执行断言，因此不能证明冲突识别或修复。公共疾病库也不能作为最终盲测集。当前没有外部 evaluator 控制、独立专家标注的生物学性能结果。

## 5. 已验证但不应夸大的事实

- 动态 AD、LUAD、UC 流程曾在远程环境运行；无合格 UC 组学时可靠降级；
- Step 结构化 Planner、Waitress 服务、stdio MCP、Schema 导出与仓库策略均有远程验收记录；
- Reviewer LoRA 在模板一致的 30 条 held-out 集上通过合同测试，但这不代表开放世界 Reviewer 水平；
- 当前项目修复的远程完整验收已经覆盖自动相同输入重跑、checkpointed 精确快照批准、逻辑 active item 集、release decision marker 重绑定、HTTP/MCP 和 benchmark ledger 修正；最终精确提交的验收结果以验证报告最后一节为准。

## 6. 仍未完成

- WorkAttempt/Head、worker lease/heartbeat 和所有中断边界恢复；
- ArtifactVersion/ReviewTarget 的完整 active-head 模型；
- 类型化领域修复、同上下文数据集替换和科学依赖失效；
- 真实 fine-mapping/coloc 重算和广泛适用的扰动 Oracle；
- 大规模、多疾病、独立专家审核的 alignment 数据；
- 外部隐藏疾病盲测与独立专家仲裁；
- 生产级多用户认证、租户隔离和 Streamable HTTP MCP；
- 自动湿实验、临床决策或自修改系统。

后续优先级与验收标准见 [PRD.md](PRD.md)，可视化状态页见 [product_status.html](product_status.html)。
