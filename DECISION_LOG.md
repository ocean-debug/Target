# Decision log

Cross-module contracts, workflow choices, model boundaries and scientific-safety decisions are recorded here. Accepted decisions must not be changed silently in a feature branch.

## 2026-08-08 - 论文模式语料管线与策略可见性（P1）

- **Status:** accepted
- 决策：候选语料只存元数据（PMID/标题/期刊/年份/DOI/PMCID/查询桶），不存摘要与全文；期刊白名单与查询桶是确定性常量，过滤规则可测试；append-only 按 PMID 去重并逐条 SHA-256。
- 决策：ResearchPlan 新增 `evidence_strategy_patterns` 字段，Planner few-shot 命中随计划持久化，项目快照与 Web 工作台展示“论文模式 → 策略 → 执行”链路，并明确标注为策略提示而非证据。
- 决策：语料刷新通过 NCBI E-utilities（esearch + esummary）完成，邮箱/API Key 只从环境或命令行注入，不进入仓库与日志。
- 验收：新增语料管线测试（过滤/去重/分桶/上限/append-only/digest/状态绑定）与 Planner 持久化测试；全量 pytest、benchmark、schema 导出与仓库策略检查在远程验收环境执行通过。

## 2026-08-08 - 修复策略可执行闭包门禁（P0.4）

- **Status:** accepted
- 决策：把修复策略从文档化约定升级为可执行闭包断言。`verify_domain_repair_policy()` 校验 finding 类别字面量 = 可修复类别 ∪ 显式拒绝类别、动作映射封闭、overlay payload 白名单与成功标准非空，并在 `ResearchProjectStore.assert_integrity()` 每次执行时先行校验，防止新增修复模式静默绕过持久化门禁。
- 决策：`RepairRequest` 增加 `candidate_lane_recompute_required` 并强制绑定 SWITCH_DATASET_SAME_CONTEXT：数据集切换必须显式声明候选绑定证据通道按新候选集重算，其它动作禁止携带；域修复请求必须保持 `no_scope_change=True`。
- 决策：修复决议快照绑定（before == trigger snapshot、最新决议 after == 当前项目快照）与“RESOLVED 时不得存在 active blocking 评估”写入 store 完整性门禁；ToolResult `supersedes_tool_run_id` 链加入引用完整性检查（禁止孤儿引用、自指与环），旧结果保留在 append-only ledger 中仅供审计。
- 验收：新增 10 项测试（8 项策略闭包/合同/ledger + 2 项 store 篡改门禁），全量 pytest、benchmark、schema 导出与仓库策略检查在远程验收环境执行通过。

## 2026-08-08 - 类型化候选绑定与证据失效（P0.3）
- **Status:** accepted
- 决策：把“证据依赖候选集合”从隐式约定升级为类型化合同。PlanStep 声明 candidate_bound + evidence_lane；候选绑定步骤的 ToolResult 记录 step_id + candidate_universe_digest（含合同版本与排序候选全集），恢复时 digest 不匹配即重取，并以 supersedes_tool_run_id 建立取代链。
- 决策：Reviewer 与 Ranking 只消费未被取代的 active 结果与证据；旧结果保留在 append-only ledger 中，确保“候选集变化后文献/药物/安全/扰动证据按新候选集重算”可被机器断言，而不是只依赖整体子图重跑。
- 决策：项目修复层把“数据集切换后所有候选绑定证据通道按新候选集重算”写入 SWITCH_DATASET_SAME_CONTEXT 成功标准；SPLIT_CONTEXT_SAME_SCOPE 明确保持候选绑定不变。
- 决策：对齐数据训练（Planner/Reviewer SFT 与偏好对）按用户要求延后到最终阶段，不进入本轮改造。
- 验收：新增候选绑定合同/Planner 校验/运行时重取与取代链测试，全套测试在远程验收环境执行。
## 2026-08-08 - 类型化领域修复：上下文拆分与 overlay 可执行断言

- **Status:** accepted
- 决策：把“上下文错误”细化为两种确定性处置——子上下文仍在冻结 TaskSpec 内时走 SPLIT_CONTEXT_SAME_SCOPE（R2/checkpoint，重新绑定证据上下文，不删除），完全在范围外时走 EXCLUDE_EVIDENCE（隔离引用、保留源证据）。
- 子上下文门控为字符串级收窄关系（等于或包含于冻结值），是保守启发式；不接受更宽泛或跨维度值，宁可不修复也不猜。
- 决策：AUTONOMOUS 项目不提出任何 CHECKPOINT_REQUIRED 修复；之前“R2 提议 → WAITING_REVIEW → resume 校验失败”的组合视为缺陷，本次以策略层门控消除。
- 决策：overlay 不允许删除证据记录；EXCLUDE 仅从 active 引用移除并写 isolated_only/retained_in_source，SUPPLEMENT 必须带 reason，DOWNGRADE 固定目标 INFERRED 且拒绝 no-op/升级。
- 验收：新增 6 项策略/overlay 测试（原因与来源校验、自主性门控、同范围拆分提议与执行、升级/缺失/no-op 拒绝、冲突拆分检测、checkpointed 拆分端到端），全套测试需在远程验收环境通过。

## 2026-08-08 - WorkItemHead/ArtifactHead CAS 与确定性恢复

- **Status:** accepted
- WorkItemHead 是工作项当前已提交结果的权威指针（attempt + result digest + CAS version），result.json 只是镜像；执行顺序固定为“不可变结果快照 → attempt 行 → head CAS → 镜像”，中断恢复从 durable head 重建，不依赖 Trace 猜测。
- 产物注册同时写 ArtifactVersion 不可变版本行与 ArtifactHead（CAS active 指针）；旧版本保留且可读，Reviewer 只读取 active artifact 集。
- 每次评审提交写 ReviewTarget，snapshot digest 只包含评审项输入闭包（结果/评审/产物），下游报告完成后 digest 不漂移，恢复可幂等重建缺失 target。
- Worker lease 增加 heartbeat 续期与过期回收；孤儿/过期 lease（含 RUNNING attempt 行）恢复时回收并重试，中断 attempt 保留审计。
- 验收（远程验收环境）：新增 6 项测试覆盖 CAS 冲突、幂等重放、版本台账、heartbeat、镜像修复不重跑、过期 lease 回收、ReviewTarget 重建；全套测试通过。

## 2026-08-08 - Product-speed cache layers

- **Status:** accepted
- Analysis cache keys are task-context-free (dataset + recipe + source checksum + tool/contract versions); legacy task-context keys remain as a one-time migration fallback.
- Literature LLM rerank/extract results persist under corpus-snapshot + model + prompt-version keys; replay still requires exact source spans.
- Reviewer LLM findings cache uses a normalized payload (per-run ids become positional tokens); replay maps tokens back to current ids and re-validates. A single invalid finding is skipped instead of discarding the whole review round.
- Reviewer uses a dedicated 240s read timeout with one retry; the previous 90s x 3 budget wasted ~4 minutes before deterministic fallback.
- Acceptance (remote acceptance environment): fresh UC project warm stage-2 run is 55s; cold/warm/hot runs produce identical Top-10 rankings with completed_with_gaps, 0 blocking, 2 gaps.

## 2026-08-01 - Versioned schemas are module boundaries

- **Status:** accepted
- Cross-module objects use the versioned JSON Schemas generated from the canonical Pydantic models.
- Breaking changes require a new contract version and an explicit one-way adapter.
- The goal is to prevent omics, perturbation, evidence and reporting modules from drifting into incompatible field conventions.

## 2026-08-03 - V2 auditable Agent boundaries

- **Status:** superseded in part by V2.1
- This repository is the only maintained implementation; handover assets remain read-only inputs.
- MCH/K562 is an isolated causal-modelling gold sample and must not be presented as disease-context causal evidence.
- Low-context DeltaFactor predictions are exploratory and excluded from formal ranking.
- Reports and the UI render structured Evidence Store values only.
- Experience promotion and LoRA training are offline, auditable and human-approved; automatic code, training or publishing mutation is prohibited.

## 2026-08-03 - V2.1 generic public-omics workflow

- **Status:** accepted
- The public contract is `2.1.0`, with an explicit one-way adapter from TaskSpec `2.0.0`.
- The default disease workflow discovers GEO and CELLxGENE data dynamically; UC snapshots and fixed perturbation tools are disabled compatibility plugins.
- LLMs select only tools exposed by the live typed registry. Matrix type, biological replication, metadata confidence and context remain deterministic gates.
- Cache identity binds source checksums, scientific recipe content, tool and contract versions, and biological context; per-run trace IDs are excluded.
- Infrastructure configuration and secrets are external to Git. The production web command uses Waitress; Flask development mode is explicit.
- Scientific workflow references are pinned to `scientific-agent-skills` v2.62.0 at commit `ad21a3868923628330734375dddbf7b86ea84222`.

## 2026-08-04 - Disease library as a first-class asset

- **Status:** accepted
- `configs/disease_library.yaml` holds 18 curated diseases (autoimmune, neurodegenerative, cancer, metabolic, respiratory); every ontology identifier was verified against live EBI OLS search before entry, and new identifiers must pass the same live check.
- Reference targets are evidence-graded (`approved_drug > gwas > mendelian > clinical_trial > mechanistic`) and serve as ranking sanity anchors, not as ground truth for scoring novelty.
- Task templates encode the project 50/20/15/15 composition (normal / missing_context / conflicting_evidence / trap) with machine-checkable `expectation` blocks consumed by the benchmark layer.
- The disease resolver merges library aliases at runtime; hard-coded legacy aliases win on conflict so existing behaviour never regresses.

## 2026-08-04 - Stable demo replay and live workbench share one backend

- **Status:** accepted
- The main workbench supports both validated stored-run replay and new live Agent runs; replay is never represented as live execution.
- The replay bundle is derived only from persisted status, Plan, Trace, ToolResult, EvidenceItem, ranking and TargetCard artifacts.
- Internal tool/event identifiers, absolute server paths and secrets are excluded from the public bundle.
- Frontend code performs presentation only and does not create new scientific scores, claims or database results.

## 2026-08-05 - V3 project control plane serves the vertical Target product

- **Status:** accepted
- Target remains a disease-driven drug-target-discovery Agent; the project/run/artifact model is internal reliability infrastructure, not a general-purpose scientific-workbench claim.
- The project contract is `3.0.0` and wraps, rather than replaces, the target-specific `TaskSpec 2.1.0`, evidence contracts, ranking rules, Reviewer gates and TargetCards.
- Accepted plans use allowlisted typed modules. Artifact snapshots are content-addressed; project events, assessments and decisions are append-only.
- The vertical project plan invokes the existing disease-target workflow as one bounded module instead of duplicating its literature, omics and evidence-fusion stages at project level.
- Phase-one HTTP project endpoints are shipped for embedding. MCP, external blind target-ranking evaluation, GWAS/eQTL ingestion and broad perturbation Oracles remain roadmap work and must not be represented as completed.

## 2026-08-05 - Reviewer repair is bounded to transient read-only failures

- **Status:** accepted
- Automatic repair may retry only allowlisted read-only connectors and must remain within both tool-call and review-round budgets.
- The append-only ToolResult ledger retains failed attempts. Review and terminal status use the latest effective attempt for each tool after repair.
- Matrix eligibility, replication, biological context, model scope, causal boundaries and safety blockers cannot be cleared by retry.
- If repair is unavailable or still fails, the system preserves the corresponding evidence gap and degraded terminal status.

## 2026-08-05 - V2.2 controlled human-genetics evidence boundary

- **Status:** accepted; narrows the V3 phase-one statement that no controlled human-genetics input existed. General eQTL ingestion and statistical fine-mapping/colocalization recomputation remain roadmap work.
- The target-discovery contract advances to `2.2.0`; homogeneous `2.0.0` and `2.1.0` payloads use explicit one-way adapters, while mixed contract trees are rejected.
- The current genetics lane audits pre-staged, checksum-bound GWAS summary statistics, SuSiE per-signal posterior credible sets and coloc results. It does not recompute fine-mapping or colocalization and does not execute arbitrary analysis code.
- A locus-to-gene result enters the strict human-genetics score only after study, phenotype, build, ancestry, LD, signal, regional variant manifest, allele harmonization, overlap, posterior, sensitivity and biological-context gates pass. GWAS-only loci remain unresolved; nearest-gene assignment is forbidden.
- Colocalization supports a shared association signal under the supplied model and priors. It remains `INFERRED`, does not establish the causal gene or variant and does not determine therapeutic direction.
- Open Targets aggregate genetic association is retained as non-formal database context; somatic-mutation evidence is represented separately. Neither can independently satisfy the strict genetics `GO` gate.
- For `gwas_locus_to_target`, the rankable candidate universe is restricted to checksum- and provenance-validated formal candidates emitted by the genetics extraction chain. Disease-level aggregate sources may annotate those candidates but may not expand the locus-specific universe.
- Non-terminal runs created under an older contract cannot resume in place under `2.2.0`; callers must start a derived current-contract run. Terminal legacy runs remain readable without mutation.
- Public bundles expose the stored run's source contract as `contract_version`/`source_contract_version` and the current renderer separately as `rendered_contract_version`.
- Genetics report provenance is additive across retries. Each selected stage records its exact ToolRun plus artifact checksums; earlier attempts remain available for audit.

## 2026-08-05 - Target is a vertical domain service, not a replacement workbench

- **Status:** accepted; supersedes only the MCP-roadmap portion of the earlier V3 phase-one decision.
- Architecture review of SciForge, OpenScience, OpenAI4S and Wisp showed that chat, general code execution, persistent kernels, remote compute and desktop workspace concerns belong to a mature host runtime.
- Target continues to own disease-target task contracts, evidence semantics, project state, allowlisted scientific execution, Reviewer gates, immutable artifacts and release decisions.
- `ResearchProjectService` is the product-facing application boundary. CLI, HTTP and MCP adapters must operate on the same durable store and may not create a parallel conversation-only state.
- The phase-one MCP surface uses the official Python SDK over local stdio and exposes project creation, bounded execution, status, event replay, checkpoint acceptance and verified text artifacts.
- MCP does not expose arbitrary shell or model-generated code execution and cannot waive frozen plans, evidence gates, artifact integrity or missing-context outcomes.
- Streamable HTTP MCP, registry publication, remote authentication policy and host-specific installation remain explicit roadmap work.

## 2026-08-05 - Child workflow activity is a projection, not a second evidence store

- **Status:** accepted
- The authoritative disease-target Trace, ToolResult, EvidenceItem, ReviewerFinding and Claim records remain in the child Evidence Store.
- The project store indexes a strict, append-only activity projection with its own cursor and an exact `child_run_id + source_trace_id` backlink.
- This is an additive `3.0.0` record and optional ledger: existing projects with no activity file remain readable as an empty activity stream; no persisted 3.0 object changes meaning.
- Only operational fields are projected: domain stage, tool name, status, coverage, context-match metadata and source IDs. Candidate genes, ranking values, evidence text and Reviewer prose are not copied.
- Projection is reconciled before resume and after execution. Projection failure may degrade the project work item but cannot alter the child scientific terminal status.
- Child `reviewer_repair` records a real bounded connector retry. It is not a project `DecisionEvent.REPLAN`; project-level evidence supplementation still requires a future immutable plan-revision contract.
