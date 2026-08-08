# Target 已完成能力与证据边界

> 状态日期：2026-08-08  
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

### 1.5 产品级缓存与热重跑

- 分析缓存 key 与任务上下文解耦（数据集 + recipe + 源校验和 + 工具/合同版本）；旧含上下文的 key 保留一次性迁移回退，同一数据集/recipe 可在不同任务间复用数值结果，证据仍按当前任务上下文生成；
- Europe PMC 检索/全文持久缓存；LLM 重排与跨度抽取结果按“语料快照 + 模型 + 提示版本”缓存，回放时仍执行原文 span 校验；
- Reviewer 使用归一化载荷缓存：运行内 ID 归一为位置 token，缓存命中后映射回当前 ID 并重新校验；单条非法 finding 只被跳过，不再丢弃整轮有效结果；
- Reviewer 专属超时 240s、重试 1 次，避免 90s×3 无效等待后落入确定性回退；
- 远程验收（UC）：冷启动约 28 分钟 → 工具层全缓存后阶段二 55s；冷、暖、热三次独立运行的 Top10 排序完全一致，终态均为 completed_with_gaps、0 blocking、2 gaps。

### 1.6 机制证据图与证据合成（P2.5）

- 证据合成将持久化 Evidence Store 投影为机制证据图：disease / locus / variant / gene / cell_state（组织或细胞类型）/ drug 实体节点，外加 genetics / omics / perturbation / drug / literature / safety 证据层节点；
- 跨层模式链接：只有当基因在两条独立证据层都有达标证据（context_match ≥ 0.5）且匹配论文模式 EvidenceLink 时才生成 pattern_evidence_link 边，claim_class 固定为 INFERRED，并携带 pattern_id、link_type、decision_rule 与 why_this_link，明确标注“策略假设而非当前疾病证据”；
- 确定性质量门：方向冲突基因（同上下文 increase+decrease）拦截其全部模式链接；两条层共享 source lineage 或同一 tool run 时视为非独立证据，模式链接被拦截并写入 evidence_dependence finding；低上下文证据不参与模式链接但保留在图上供审计；
- 图语义边界：边权重仅为上下文匹配系数（排序用途），不表示因果或临床成功概率；安全性阻断以独立 safety_liability 边保留，不被加权平均隐藏；
- 接口：GET /api/projects/<id>/mechanism-graph 返回 graph + synthesis_findings + reviewer_findings + lane_coverage + pattern_links；Web 工作台证据图区改为“工作流 DAG / 机制证据图”双面板，支持模式链接、预测/推断边、证据层节点筛选，前端不创造任何后端不存在的数字；
- 合同：GraphNode 新增 lane 类型，GraphEdge 新增 attributes，schemas/causal_graph.schema.json 同步更新（兼容读取旧图）。

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

自动修复必须同时满足：模块 side-effect-free、replay-safe、声明 `same_input_retry`、输入 digest 不变且仍在预算内。checkpointed/supervised 模式要求对精确 trigger snapshot 批准；过期 digest 被拒绝。旧 result/assessment/artifact 不删除；当前 runtime 的 finalize 与 release digest 使用逻辑 active item 集，API ledger 仍返回全部历史记录并额外给出 active item IDs 与 active artifact IDs；WorkItemHead/ArtifactHead 是 active 视图的权威指针（见 2.5）。

已实现同上下文数据集切换修复：Reviewer 对首选数据集给出 blocking FAIL 时，确定性策略生成类型化 SWITCH_DATASET_SAME_CONTEXT 指令（不改变冻结 TaskSpec，仅替换 preferred/excluded accession），重建受影响子图并强制重新评审，具备端到端验收测试。

已实现类型化领域 finding 驱动的完整修复策略（R0–R3）：

- R0 声明降级（causal_overreach）：Reviewer 判定某条派生 Claim 因果越界时，自动生成 DOWNGRADE_CLAIM overlay，将 claim_class 降为 INFERRED 并写入 `causal_interpretation_removed`，无需人工审批；
- R1 同范围补证（coverage_gap）：证据引用缺失但证据集内存在候选时，自动生成 SUPPLEMENT_EVIDENCE overlay，只追加已存在的证据引用，不新造证据；
- R2 证据排除（context_mismatch）：上下文不匹配或冲突证据必须经 checkpoint 审批后生成 EXCLUDE_EVIDENCE overlay，仅从引用层移除、不删除来源证据；
- R3 越界拒绝：`unsupported_claim`、真值/阈值/范围改动等类别不在 FINDING_TO_ACTION 白名单内，策略层永不提议，只能由人类决策处理；
- overlay 全部由确定性 `DomainOverlayModule` 在派生层执行：保留源结果、只写 `domain_overlay.json` 审计文件，并将已解决的 finding 标记为 `finding_status=resolved`，Reviewer 不再重复触发；
- 多个 finding 形成链式 overlay 时，早期 repair 的 Resolution 会跟随最终 active 链升级为 RESOLVED，仓库完整性校验按链末 active 项复核，避免“修好了但永远显示 unresolved”。

- 确定性证据门禁（来自子运行 claims/evidence，而不是 LLM 文本）：
  - 方向一致性：同一基因同时出现 increase 与 decrease 证据时，生成 blocking `conflicting_evidence` finding，映射到 R2 证据排除（需 checkpoint 审批）；
  - 证据独立性：一条 Claim 的多条证据共享同一 source/dataset/study/tool-run 谱系时，生成 blocking `evidence_dependence` finding，映射到 R0 声明降级（自动降为 INFERRED），防止把同一研究的重复引用当作独立支持；
  - 与子运行 Reviewer finding 按 finding_id 去重合并，确定性门禁不覆盖人工/LLM finding。

- 尚未完成：从自由 Reviewer 文本直接生成修复（当前只接受类型化 finding）；步骤级回退与跨模块候选依赖超集链的完整自动修复（上下文拆分见 2.6，候选绑定证据失效见 2.7）。

### 2.3 Review 与发布

- 结构完整性评审和领域 Reviewer 分离；
- finding 可分 blocking/major/minor，结果绑定 target digest；
- 修复后必须重新 Review；
- release decision marker 绑定当前 active project snapshot SHA-256，而不是只绑定 plan ID；
- 输入或修复导致快照变化时，旧 marker 不再适用；当前尚无独立 `ReleaseRecord`、专家签名或认证发布包。

### 2.4 持久 Python/R 分析内核（借鉴 OpenAI4S/Wisp）

- 显式创建/停止的持久会话，Python（默认）与 R（Rscript + jsonlite，可选）双后端，状态跨执行保留；
- 换行 JSON 协议，stdout/stderr/traceback 截断标记，超时终止会话并保留 FAILED 原因；空闲会话按策略回收；
- 本地守护进程自动拉起（日志在 cache/kernel-daemon.log）；CLI 提供 kernel start/exec/status/stop/stop-all/serve；
- Web API：GET/POST /api/kernels、GET/DELETE /api/kernels/<id>、POST /api/kernels/<id>/exec；工作台第 08 节内核控制台（启动/运行/停止，能力栏显示内核开/关）；
- 明确边界：LLM 不自动执行代码，仅人工或注册工具使用；doctor 区分必需依赖与可选分析后端；
- 9 项内核测试：状态持久、错误恢复、超时杀死、输出截断、默认目录自动创建、禁用、R 未装、空闲回收、Web API 生命周期。

### 2.5 工作尝试、产物版本与 CAS 头

- WorkAttempt 永久不可变（append-only，结果快照按 digest 绑定）；WorkItemHead 以 CAS 更新并记录 attempt/result digest，重放同一提交是幂等 no-op；
- 每条工作项执行顺序固定为：不可变结果快照 -> attempt 行 -> head CAS -> result.json 镜像；中断恢复以 head 为权威，不通过 Trace 猜测业务状态；
- 产物注册同时写入 artifact_versions.jsonl（不可变版本行）与 artifact_heads.jsonl（CAS active 指针），旧版本内容寻址保留、可审计可读取；
- Reviewer 只接收当前 active artifact 集；每次评审提交生成 ReviewTarget，绑定评审时刻的输入闭包 snapshot digest、result digest 与 active artifact 逻辑 ID；
- worker lease 支持 heartbeat 续期与过期回收；孤儿/过期 lease（含 RUNNING attempt 行）恢复时被回收并重试，中断的 attempt 行保留为审计记录；
- 中断边界验收：attempt/head/review 任一边界模拟中断后恢复，已完成步骤不重复执行、旧版本不丢失，缺失的 ReviewTarget 由恢复逻辑幂等重建。

### 2.6 类型化领域修复：同范围上下文拆分与 overlay 断言

- DomainFinding.category 与 FINDING_TO_ACTION 对齐为同一封闭集合（新增 gene_mapping_overreach、evidence_dependence、missing_provenance、context_split_needed），合同层不再允许策略映射之外的 finding 类别进入修复流程；
- 新增 SPLIT_CONTEXT_SAME_SCOPE 修复（R2、checkpoint 审批）：当冲突证据可确定性映射到冻结 TaskSpec 内的不同子上下文时，overlay 将每条证据重新绑定到其子上下文（context 合并 + context_split_by/reason 审计标记），证据保持 active，不删除任何一侧；子上下文必须等于或收窄冻结值，更宽泛值被拒绝；
- 冲突检测器优先尝试上下文拆分：同一基因 opposing-direction 证据带不同 tissue/cell_type 子上下文时输出 context_split_needed（替代直接排除）；无可用子上下文时仍走 conflicting_evidence 到 EXCLUDE；
- overlay 可执行断言：EXCLUDE 只能隔离已存在于派生证据集的证据（missing row 拒绝应用，isolated_only/retained_in_source 写入审计），SUPPLEMENT 必须携带非空 reason 且只能引用已存在证据，DOWNGRADE 只允许降至 INFERRED、拒绝任何升级与已 INFERRED 的 no-op；
- 自主性契约：AUTONOMOUS 项目不再提出 checkpoint 必须审批的 R2 修复（dataset switch / exclusion / context split），避免“提出后暂停、恢复时校验失败”的死锁；这类 finding 保留为文档化阻塞缺口并以 completed_with_gaps 收尾，CHECKPOINTED/SUPERVISED 项目行为不变。

### 2.7 类型化候选绑定与证据失效（P0.3）

- `PlanStep` 声明 `candidate_bound` 与 `evidence_lane`（literature / genetics / drug_safety / perturbation / trials），evidence_lane 必须与 candidate_bound 同时出现，Planner 拒绝没有候选产生依赖的证据步骤；
- 每个候选绑定步骤的 ToolResult 写入 `_candidate_bound` 元数据（step_id + candidate_universe_digest + evidence_lane），digest 包含合同版本与排序后的候选基因全集；
- 恢复时以 ToolResult ledger 重建候选全集，比对每个已完成候选绑定步骤的 digest；不一致则从 completed_steps 移除并重取，同时写入 `replan/resume` 与 `evidence_superseded` trace，新结果通过 `supersedes_tool_run_id` 显式取代旧结果；
- Reviewer/Ranking 只消费未被取代的 active ToolResult 及其 EvidenceItem，旧证据保留在 append-only ledger 中但不再参与评分与报告；
- 项目修复策略明确要求数据集切换后所有候选绑定证据通道按新候选集重算，上下文拆分时保持候选绑定不变。

### 2.8 修复策略可执行闭包门禁（P0.4）

- `verify_domain_repair_policy()` 作为唯一可执行策略闭包断言：DomainFinding.category 字面量必须等于“可修复类别 ∪ 显式拒绝类别”，FINDING_TO_ACTION 键必须与可修复类别一致且每个动作都存在于 DOMAIN_REPAIR_POLICY，overlay 动作必须与 payload 白名单一一对应且每个动作都有非空成功标准；`ResearchProjectStore.assert_integrity()` 每次持久化完整性检查都先执行该断言，任何新增修复模式都无法静默绕过；
- `RepairRequest` 新增 `candidate_lane_recompute_required` 合同字段并绑定到 SWITCH_DATASET_SAME_CONTEXT：数据集切换修复必须声明候选绑定证据通道按新候选集重算，其它动作禁止携带该标记；store 层同时校验域修复请求 `no_scope_change` 恒为 True；
- 快照绑定：修复决议的 `before_snapshot_digest` 必须等于触发请求的 `trigger_snapshot_digest`，最新决议的 `after_snapshot_digest` 必须等于当前项目快照；RESOLVED 决议不允许存在任何未消除的 active blocking 评估；
- ToolResult 超链成为引用完整性的一部分：`supersedes_tool_run_id` 必须指向 append-only ledger 中真实存在的旧结果、不允许自指或成环，旧结果与旧证据保留在 ledger 中仅供审计，Reviewer/Ranking 只消费 active 结果。
## 3. 已完成的产品接口

- CLI：创建、运行、状态、事件、活动、checkpoint、repair queue 和 repair decision；
- HTTP：项目创建/运行/状态、事件、领域活动、artifact、repair queue 与 snapshot-bound 决策；
- HTTP 工作台：`/api/projects` 项目列表、`/api/projects/<id>/resume` 手动继续、checkpoint 审批（plan/release）、repair/fork 审批、redo/restore 回退与 branches 查询；
- Web 单页工作台（UTF-8 中文）：新建项目、计划/结果/分支/事件/产物渲染，所有数字只来自后端 API；
- MCP fork 工具：`target_propose_fork`、`target_decide_fork`、`target_get_branches`；
- 产品外壳：`target-agent init` 脚手架（project.yaml + README + .env.example）、`project-export`/`project-import` 可移植项目包（MANIFEST + SHA-256 校验、拒绝覆盖、拒绝密钥文件）、`project-package-inspect` 与 Web `GET /api/projects/<id>/export`；
- 模型供应商抽象：`LLM_PROVIDER=step|openai`，openai 模式走任意 OpenAI 兼容 Chat Completions 端点；
- 科研工作区：`GET /api/projects/<id>/graph` 证据图（工作项依赖 + 产物溯源 DAG）、`GET /api/projects/<id>/files` 项目文件树、`GET /api/projects/<id>/files/preview` 文本预览（路径越界/密钥文件/超大文件拒绝），Web 工作台新增证据图与文件预览面板；
- 技能库：skills/ 下 6 个 SKILL.md（文献证据抽取、bulk RNA 受控分析、单细胞 pseudobulk、遗传审计、TargetCard Review、可证伪实验设计），SkillCatalog 扫描并以 SHA-256 校验、确定性检索；CLI `skills list/search/show`、Web `GET /api/skills` 与 `GET /api/skills/<id>`、`/api/capabilities.skills`；Planner 只接收 id/name/description/evidence_lanes 渐进提示，完整正文按需加载且不作为任务证据；
- 持久分析内核：CLI kernel 子命令、Web /api/kernels 生命周期接口与工作台内核控制台（能力栏显示内核开关）；
- stdio MCP：十一项类型化工具，全部调用同一 `ResearchProjectService`；
- Web 与 MCP 不建立第二套状态语义；
- 决策已持久化但后台队列已满时，接口区分“决定已接受”和“是否成功排队”。

## 4. 已完成的 benchmark 与对齐资产

- 内部 fake/unit benchmark 覆盖合同、恢复、拒绝、确定性和引擎一致性；
- 参考 blind-ranking scorer 能在载入私有标签前冻结任务、排名和状态 digest，并计算 disease-macro 指标及 trap/safety gate；
- Planner/Reviewer SFT、偏好和 held-out 资产具有角色字段与 promotion gate；现有 120 条 SFT 是 6 个模板各 20 个索引变体，科学与工程角色由同一负责人完成，不是独立双人审核；
- benchmark runner 已读取权威 `reviewer_findings.jsonl`，并支持显式 `finding_category` 断言；
- 论文策略 P0/P1：`paper_strategy.py` 的 ObservedWorkflow/StrategyPattern/BestPracticePattern 合同、append-only 确定性 PatternStore 与 Planner few-shot；种子库 10 条 discovery patterns 与 checksum manifest；
- 论文语料管线（P1）：`paper_corpus.py` 通过 NCBI E-utilities 按 4 个查询桶 × 期刊白名单检索近 5 年 CNS/高影响力论文，esummary 批量取元数据，确定性过滤（期刊/年份/标题排除 review 与 methods-only），append-only `CorpusStore` 按 PMID 去重并逐条 SHA-256；CLI `pattern corpus refresh|status` 与 `scripts/build_paper_corpus.py`；
- 证据策略可见性（P1）：ResearchPlan 持久化 `evidence_strategy_patterns`（few-shot 命中），项目快照与 Web 工作台展示“论文模式 → 策略 → 执行”链路，前端明确标注“策略提示非证据”；
- P3 对齐数据生成与 Planner/Reviewer LoRA 训练按团队决定延后至最后阶段，以论文策略沉淀为数据来源。

重要限定：历史 18 疾病 `conflicting_evidence` 桶的 54/54 仅验证终态、provenance 和报告存在；当时 `expectation.reviewer_categories` 未作为可执行断言，因此不能证明冲突识别或修复。公共疾病库也不能作为最终盲测集。当前没有外部 evaluator 控制、独立专家标注的生物学性能结果。

## 5. 已验证但不应夸大的事实

- 动态 AD、LUAD、UC 流程曾在远程环境运行；无合格 UC 组学时可靠降级；
- Step 结构化 Planner、Waitress 服务、stdio MCP、Schema 导出与仓库策略均有远程验收记录；
- Reviewer LoRA 在模板一致的 30 条 held-out 集上通过合同测试，但这不代表开放世界 Reviewer 水平；
- 当前项目修复的远程完整验收已经覆盖自动相同输入重跑、checkpointed 精确快照批准、逻辑 active item 集、release decision marker 重绑定、HTTP/MCP 和 benchmark ledger 修正；最终精确提交的验收结果以验证报告最后一节为准；
- 远程 HTTP 端到端冒烟通过：创建项目 → 审批计划 → 真实工具执行（GEO 检索、组学分析、Europe PMC、Open Targets、ClinicalTrials）→ 终态 `completed_with_gaps` → 事件/产物/项目列表完整；
- 2026-08-08 实时产品链路验证（Step 3.7 Flash + 冷缓存真实运行）：`init` → `project-run` → 计划 checkpoint → `project-approve --resume` → GEO 动态检索（10 候选、资格审核、拒绝理由可追溯）→ GSE197698/GSE206171 差异/通路/QC 分析 → 遗传/试验/文献 RAG → 10 个排名靶点 + 5 张 TargetCard + 11 条 Reviewer finding → 项目评审终态 `completed_with_gaps`（0 blocking）→ `project-export`（66 文件/1.67 MB zip）→ `project-package-inspect` → 全新目录 `project-import` 后状态与产物一致，重复导入拒绝覆盖；
- 全量回归 289 passed / 2 skipped（含 9 项持久内核测试与 6 项领域 finding 修复策略测试：自动 R0/R1、checkpointed R2、越界拒绝、overlay revision、链式 resolution、方向一致性与证据独立性门禁）；远程内核守护进程冒烟通过：start → exec → status → stop。

## 6. 仍未完成

- WorkItemHead/ArtifactVersion/ReviewTarget 的完整 active-head 模型；
- 所有中断边界恢复（WorkerLease 与 WorkAttempt 台账已实现，尚缺 heartbeat 与跨进程 CAS 全场景）；
- 从自由 Reviewer 文本直接生成修复（当前只接受类型化 finding）；上下文拆分与科学依赖失效的自动修复；
- 真实 fine-mapping/coloc 重算和广泛适用的扰动 Oracle；
- 大规模、多疾病、独立专家审核的 alignment 数据；
- 外部隐藏疾病盲测与独立专家仲裁；
- 生产级多用户认证、租户隔离和 Streamable HTTP MCP；
- 自动湿实验、临床决策或自修改系统。

后续优先级与验收标准见 [PRD.md](PRD.md)，可视化状态页见 [product_status.html](product_status.html)。


## 7. 论文策略模式：Gold 标注、抽取、评审与消融回归（P2，2026-08-08）

### 7.1 已完成

- **Gold 标注台账**：`CurationStore` append-only，记录 gold/rejected、理由、标注角色与 digest；CLI `target-agent pattern curate`。
- **抽取工具链**：`pattern_extraction.py` 提供 Europe PMC 元数据 + 摘要/Methods 有界文本（`EuropePmcMetaFetcher`），LLM 结构化输出必须通过 StrategyPattern 完整合同校验并含至少一条 observed_workflows；每次尝试写入 append-only 审计 `extractions.jsonl`（状态、来源材料级别、提示版本、错误），全程不落盘全文；CLI `target-agent pattern extract`。
- **专家评审台账**：`ReviewLedger` 追加式记录 life_science/engineering 双人评审，`PatternStore.corpus_card` 汇总有效评审状态；模式记录保持不可变；CLI `target-agent pattern review`。
- **垂直子工作流注入**：LangGraphRuntime 域内 Planner 自动从配置模式库构建 few-shot 提示，命中以 `planner_pattern_hints` trace 持久化；项目级 Planner 保持原有注入。
- **消融回归**：`benchmark/pattern_ablation.py` 离线度量 18 个公开疾病（normal 桶）的模式覆盖率与确定性计划有效性，支持 `--llm` 真实 Step 对比；benchmark 新增 BM-12 单元检查。当前基线：10 条种子模式命中 14/18 疾病（77.8%）、计划有效性 18/18；SLE/银屑病/ALS/黑色素瘤暂无命中，是 Gold 标注的优先补位方向。检索打分已过滤“disease/cell/type”等泛化词并要求实质性匹配，避免一个微胶质模式命中全部疾病。
- **配置**：settings 新增 `TARGET_AGENT_PATTERN_CURATION`、`TARGET_AGENT_PATTERN_REVIEW_LEDGER`、`TARGET_AGENT_PATTERN_EXTRACTION_AUDIT`。

### 7.2 已确认边界

- 当前种子模式库（10 条）覆盖率低，属于预期状态；覆盖率提升依赖人工 Gold 标注与批量抽取，不做虚高门槛。
- 抽取采用摘要或 Methods 有界文本，不保证覆盖论文全部细节；`source_material` 与提示版本留痕。
- 对齐数据生成与 Planner/Reviewer 小模型训练按团队决定延后，模式库作为其未来数据来源。
