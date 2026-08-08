# CNS 论文工作流提取与 Agent 证据策略增强方案（plan.md）

> 文档状态：草案 v0.1
> 关联仓库：`ocean-debug/Target`
> 目标：将近5年 CNS（Nature/Science/Cell）论文的分析流程与证据组合模式结构化提取，用于增强 Target 的 `evidence_strategy`、Planner、Reviewer 与对齐训练。

---

## 1. 背景与动机

### 1.1 导师反馈

- 监督/打分系统目前不够 agentic，需要让 Agent 真正理解问题、选择证据路径并自我审查。
- 当前 pipeline 是“疾病 → 组学 → 通路 → 遗传/文献/药物”的固定顺序，证据层次组合方式不够灵活。
- 应“从质量最好的数据开始”，让不同层面证据相互补充或验证，而不是固定先做单细胞/组学。

### 1.2 文献调研结论（2026-08-07）

已存在但方向不同的相关工作：

| 工作 | 内容 | 与本方案的差异 |
|---|---|---|
| BioWorkflow (2025, BIB) | 从论文抽取生物信息学工作流（步骤/工具/版本/参数），恢复率约80% | 只做抽取，不用于 Agent 策略或对齐 |
| SkillFoundry (CMU, 2026) | 从仓库/API/脚本/论文自动编译可验证 Skill 库 | 面向通用科研资源，不做疾病证据策略 |
| OriGene (bioRxiv 2025) | 自进化疾病靶点发现 Agent | 进化来自任务反馈，非论文工作流蒸馏 |
| Open-Rosalind (2026) | Tool-First 生物医学 Agent + 过程感知评测 | 侧重评测，不提炼论文模式 |
| K-Dense scientific-agent-skills | 158 个静态策展 Skill | 非自进化，非论文驱动 |

**空白**：尚无“CNS 论文证据组合模式 → 证据策略 → Agent 对齐训练 → 盲测靶点排名验证”的完整闭环。

### 1.3 本方案定位

不做通用工作流抽取，不做通用 Skill 库。聚焦：

```text
疾病机制/靶点发现类 CNS 论文
→ 提取“证据起点选择 + 层次组合 + 交叉验证 + 结论边界”
→ 沉淀为 Evidence Strategy Pattern
→ 增强 Target 的 evidence_strategy / Planner / Reviewer
→ 生成对齐数据，LoRA 训练 Reviewer/Planner 辅助模型
→ 用盲测靶点排名 + 专家审核验证
```

---

## 2. 目标与成功标准

### 2.1 目标

1. 建成 200+ 篇论文的结构化 `WorkflowPattern` 库（首版 50 篇）。
2. `evidence_strategy` 能按疾病检索论文模式，输出“质量优先的证据路径建议”。
3. Planner 在 few-shot 模式下能参考论文模式选择起点与验证链。
4. 生成 ≥180 条对齐数据（120 SFT + 60 preference），完成 Reviewer LoRA 最小实验。
5. 盲测靶点排名验证：新增论文模式后，已知参考靶点恢复率与证据链完整性不下降，并有可测量提升。

### 2.2 成功标准（可验收）

| 指标 | 目标 |
|---|---|
| WorkflowPattern 结构化完整率 | ≥80%（自动一致性检查通过） |
| 专家复核通过率 | ≥90%（抽样 20%） |
| evidence_strategy 模式检索命中率 | 20 个测试疾病中 ≥16 个能返回相关模式 |
| 盲测参考靶点 Top-10 恢复率 | 相比基线不下降，目标提升 ≥10% |
| 对齐数据 | 120 SFT + 60 preference + 30 holdout |
| Reviewer LoRA 实验 | 完成一次训练/评估，错误分类率不高于基线 |
| 可复现性 | 论文清单、版本、校验和、Prompt、参数全部落盘 |

### 2.3 非目标

- 不做湿实验执行。
- 不追求自动复现论文全部结果。
- 不存储论文全文（只存结构化摘要 + 引用）。
- 不把 CNS 论文当作金标准，只作为“专家流程模式”参考。
- 不训练通用科学大模型。

---

## 3. 数据语料

### 3.1 来源与检索

| 来源 | 用途 | 接口 |
|---|---|---|
| PubMed / NCBI E-utilities | 文献元数据、摘要 | esearch/esummary/efetch |
| Europe PMC | 开放全文、方法部分 | REST API |
| PMC OA | 开放全文 XML | FTP/API |
| NCBI GEO / ArrayExpress（关联数据） | 论文引用的组学数据集 | 现有 Target GEO 工具 |

### 3.2 纳入标准

- 期刊：Nature、Science、Cell（以及 Nature 子刊高影响力工作，可选）。
- 时间：2021-01 至 2026-08（近5年）。
- 主题（任选其一）：
  - 疾病机制与靶点发现；
  - GWAS/eQTL/coloc/遗传学定位；
  - 单细胞/空间组学疾病研究；
  - 扰动（CRISPR、药物）与因果验证；
  - 多组学整合；
  - 药物靶点/临床转化。
- 排除：纯方法学（无疾病应用）、综述（除非含系统性流程）、动物模型无关疾病、无法获得 Methods 的论文。

### 3.3 语料规模

| 阶段 | 规模 | 用途 |
|---|---|---|
| 候选池 | 1000-2000 篇 | PubMed 检索 |
| 全文候选 | 300-500 篇 | 有开放全文/Methods |
| 首版入库 | 50 篇 | 跑通流程 |
| 目标库 | 200 篇 | 完成闭环 |

---

## 4. 系统设计

### 4.1 总体架构

```text
PubMed/Europe PMC
   │ 检索与筛选
   ▼
CorpusManager（论文清单、去重、纳入/排除原因）
   │ 全文获取
   ▼
PaperParser（PMC XML / PDF → Methods 文本 + 表格 + 图注）
   │ LLM 结构化抽取
   ▼
PatternExtractor（→ WorkflowPattern JSONL）
   │ 自动一致性检查
   ▼
PatternValidator（结构检查 + 证据回链 + 专家复核）
   │ 入库
   ▼
PatternStore（SQLite/FTS5 + JSONL 快照）
   │
   ├──→ evidence_strategy RAG 检索（新增）
   ├──→ Planner few-shot 模板（新增）
   ├──→ evidence_synthesis 跨层验证（新增）
   ├──→ 对齐数据生成器（training/data）
   └──→ 盲测靶点排名评估（benchmark）
```

### 4.2 核心合同：WorkflowPattern

```json
{
  "pattern_id": "wp-pmid-35860525",
  "pmid": "35860525",
  "journal": "Nature",
  "year": 2022,
  "disease": "lung adenocarcinoma",
  "research_question": "…",
  "data_layers": [
    {
      "layer": "genetics",
      "data_type": "gwas",
      "cohort": "population",
      "sample_size": "…",
      "accession": "…"
    },
    {
      "layer": "bulk_omics",
      "data_type": "rna_seq",
      "cohort": "patient_tumor_vs_normal",
      "sample_size": "…",
      "accession": "GSE…"
    }
  ],
  "analysis_workflow": [
    {
      "step": "fine-mapping",
      "tool": "SuSiE",
      "order": 1,
      "input": "gwas_summary",
      "output": "credible_sets"
    }
  ],
  "data_integration": [
    {
      "from_layer": "genetics",
      "to_layer": "bulk_omics",
      "method": "coloc",
      "anchor": "variant_gene",
      "evidence_link_type": "colocalization"
    }
  ],
  "validation": ["independent_cohort", "perturbation", "mouse_model"],
  "evidence_roles": {
    "primary_lane": "genetics",
    "validation_lanes": ["bulk_omics", "single_cell", "perturbation"],
    "rationale": "…"
  },
  "claims": [
    {"claim": "…", "claim_class": "OBSERVED", "support": "…"}
  ],
  "sources": {
    "fulltext": "https://pmc.ncbi.nlm.nih.gov/articles/PMC…",
    "methods_section": "sec-…",
    "extraction_prompt": "prompt-v3",
    "extractor_model": "step-3.7-flash",
    "checksums": {"pdf": "sha256:…", "xml": "sha256:…"}
  }
}
```

### 4.3 数据组合（Evidence Link）建模

沿用 Target `EvidenceItem` 体系，新增论文级连接模式：

| link_type | 示例 | 说明 |
|---|---|---|
| `colocalization` | GWAS SNP → eQTL | 变异-基因 |
| `differential_expression` | 基因 → 疾病组学 | 基因-表型 |
| `cell_type_localization` | 基因 → scRNA | 基因-细胞类型 |
| `perturbation_response` | 基因 → 敲除/激活 | 因果-功能 |
| `drug_target` | 基因 → 药物 | 可干预性 |
| `cohort_replication` | 数据集 A → 数据集 B | 独立验证 |

Pattern 中的 `data_integration` 将被转换为 `EvidenceLink` 建议，供 `evidence_synthesis` 使用。

### 4.4 Pattern 检索与策略注入

#### 4.4.1 evidence_strategy 增强

新增输入：`TaskSpec + 疾病可得性快照（数据源可用性）`。

流程：

```text
1. 疾病标准化
2. 检索 PatternStore（disease_category + data_layers 过滤）
3. 汇总 Top-K 论文的 evidence_roles（primary_lane 统计）
4. 结合本任务实际可用数据，输出：
   - primary_lane（质量优先起点）
   - validation_lanes（验证链）
   - rationale（引用论文 + 数据可得性）
5. Reviewer 对策略进行审查（是否 OOD、是否证据不足、是否忽略可用数据）
```

#### 4.4.2 Planner few-shot

- 从 PatternStore 选择 2-3 个与当前疾病类别相似的高质量 Pattern；
- 作为 few-shot 示例注入 Planner prompt；
- 明确标注：示例来自论文模式，不是金标准，必须根据实际数据可得性调整。

#### 4.4.3 质量优先规则

`evidence_strategy` 输出按以下优先级排序（可被论文模式修正）：

1. 遗传学定位（GWAS/fine-mapping/coloc）——人群规模、因果性；
2. 疾病上下文组学（bulk）——患者队列；
3. 单细胞/空间——分辨率高但队列小，用于定位验证；
4. 扰动——因果强但覆盖窄，用于验证；
5. 文献/药物——支撑与转化。

每条建议附带理由与风险，禁止输出无依据的固定顺序。

### 4.5 对齐数据生成

#### 4.5.1 SFT 数据（120 条）

| 类别 | 数量 | 示例 |
|---|---|---|
| evidence_strategy 选择 | 30 | 给定疾病与数据可得性，输出合理起点与验证链 |
| Planner 路径规划 | 30 | 参考论文模式生成执行计划 |
| Reviewer 策略审查 | 30 | 识别起点选择错误、证据缺口、过度因果 |
| 可靠拒绝/降级 | 30 | 无合格数据时输出 completed_with_gaps |

#### 4.5.2 Preference 数据（60 对）

- 证据组合完整 vs 证据组合残缺；
- 遗传学优先（有GWAS时）vs 盲目组学优先；
- 跨层验证 vs 单一证据链；
- 明确证据等级 vs 混淆 FACT/OBSERVED/PREDICTED/INFERRED；
- 正确拒绝 vs 伪造结果。

#### 4.5.3 Holdout（30 条）

- 论文模式外的 30 个疾病任务；
- 用于评估 LoRA 泛化，不参与训练。

#### 4.5.4 训练

- 默认基座：Qwen3-8B-Instruct（或按现有 training 配置）；
- 目标：Reviewer LoRA 优先（结构化的策略审查与矛盾检测）；
- Planner 增强以 few-shot/RAG 为主，LoRA 为可选；
- 训练、评估全部走现有 `training/` 流程与外部 GPU Profile。

### 4.6 评测

#### 4.6.1 模式质量评测

- 自动：JSON Schema、必填字段、回链存在性、claim_class 合法性；
- 半自动：LLM 一致性检查（同一论文两次抽取的 pattern 相似度）；
- 人工：专家复核 20%（科研方向 + 工程方向各 1 人）。

#### 4.6.2 Agent 能力评测（盲测）

- 使用 Target `benchmark/` 盲测靶点排名；
- 对 18 个疾病库 + 新增疾病：
  - 基线（无 Pattern）vs 增强（有 Pattern）；
  - 指标：参考靶点 Top-10 恢复率、证据链独立数、Reviewer 问题数、终态正确性；
- 禁止把盲测恢复率表述为生物学成功率。

#### 4.6.3 回归

- 现有 72 任务 / 270 断言矩阵必须全绿；
- 现有 AD/LUAD/UC 三次缓存一致性必须保持。

---

## 5. 执行计划（4 周）

### 第 1 周：语料与抽取管线

- D1-D2：PubMed/Europe PMC 检索脚本，生成 1000+ 候选池，完成纳入/排除标注。
- D3-D4：定义 WorkflowPattern Schema；实现 PaperParser（PMC XML）与 PatternExtractor。
- D5-D7：抽取 30-50 篇，自动一致性检查 + 专家复核 10 篇；交付 Pattern JSONL 首批。

验收：

- 检索脚本可复现，清单含 PMID、期刊、年份、主题、纳入/排除原因；
- 30-50 篇 pattern 通过 Schema 校验；
- 人工复核 10 篇，≥9 篇通过。

### 第 2 周：PatternStore 与 evidence_strategy 集成

- 实现 PatternStore（SQLite/FTS5 + JSONL 快照 + 校验和）。
- 实现 `evidence_strategy` 工具：检索 → 统计 primary_lane → 输出策略。
- 实现 Planner few-shot 注入（按疾病类别检索 2-3 篇）。
- 为 18 个疾病库预跑策略输出，人工审查合理性。

验收：

- 20 个测试疾病 ≥16 个能返回相关 Pattern；
- evidence_strategy 输出包含 primary_lane、validation_lanes、rationale、风险；
- 预跑结果全部记录，无明显疾病-起点错配。

### 第 3 周：证据合成与对齐数据

- 实现 `evidence_synthesis`（跨层 EvidenceLink 构建 + 方向一致性 + 独立链计数）。
- 生成 120 SFT + 60 preference + 30 holdout。
- 运行 Reviewer LoRA 训练与评估（外部 GPU Profile）。
- 完成盲测靶点排名基线 vs 增强对比。

验收：

- 对齐数据全部经过双人复核（科研 + 工程）；
- LoRA 评估报告输出：holdout 错误分类率不高于基线；
- 盲测结果记录完整，参考靶点恢复率不下降。

### 第 4 周：集成、回归与交付

- 将 evidence_strategy 接入 Web UI 与报告（展示“论文模式 → 策略 → 执行”）。
- 运行完整回归：72/270 矩阵、AD/LUAD/UC 三次一致性、schema 导出、repo policy。
- 生成 README、数据清单、模型卡、决策日志、Demo 路径。
- 非作者按 README 复现一次。

验收：

- 全部回归通过；
- 演示 3 分钟主链路 + 2 分钟模式增强对比；
- 论文清单、Pattern、数据、模型、参数全部可溯源。

---

## 6. 角色分工

| 角色 | 负责内容 |
|---|---|
| 科学评审（组学/疾病背景成员） | 纳入标准、抽取质量复核、evidence_roles 合理性、盲测结果解读 |
| 工程（Agent/后端） | 检索管线、PatternStore、evidence_strategy、Planner few-shot |
| 工程（训练） | 对齐数据生成、LoRA 训练与评估、数据版本管理 |
| 产品/演示 | Web 展示、Demo 脚本、讲解稿、答辩材料 |
| 队长（集成） | 分支管理、回归验收、PR 评审、对外汇报 |

规则：

- 每个高风险抽取样本由科学 + 工程各 1 人复核；
- 数据、Prompt、模型版本变更必须留痕；
- 不允许自动修改代码/自动训练/自动发布；全部走 PR 与人工批准。

---

## 7. 交付物清单

| 交付物 | 位置（建议） |
|---|---|
| 论文清单与筛选记录 | `paper_workflow/corpus/corpus.jsonl` |
| WorkflowPattern 库 | `paper_workflow/patterns/patterns.jsonl` |
| Pattern Schema | `paper_workflow/schemas/workflow_pattern.schema.json` |
| PatternStore 实现 | `src/target_agent/tools/paper_patterns.py` |
| evidence_strategy 工具 | `src/target_agent/tools/evidence_strategy.py` |
| evidence_synthesis 工具 | `src/target_agent/tools/evidence_synthesis.py` |
| Planner few-shot 模板 | `configs/planner_fewshot/*.yaml` |
| 对齐数据 | `training/data/paper_patterns/` |
| LoRA 评估报告 | `training/reports/reviewer_lora_patterns_*.md` |
| 盲测报告 | `benchmark/reports/pattern_ablation_*.md` |
| README/模型卡 | `paper_workflow/README.md` |

---

## 8. 风险与对策

| 风险 | 等级 | 对策 |
|---|---|---|
| Cell/Nature 全文开放率低 | 高 | 放宽到 Nature 子刊与 PMC OA；Methods 不足则剔除 |
| 论文选择性发表偏差 | 中 | 明确标注“论文模式”非金标准；模式只作建议 |
| 抽取质量不稳定 | 高 | Schema + 自动一致性 + 双人复核 + 同文重抽相似度 |
| 论文流程与数据可得性不匹配 | 中 | evidence_strategy 必须结合任务实际数据，禁止照搬 |
| 版权问题 | 中 | 只存结构化字段与引用，不存大段原文 |
| LoRA 训练过拟合论文模式 | 中 | 30 条跨论文 holdout + 盲测靶点回归 |
| 时间不足 | 高 | 首版 50 篇；证据策略 RAG 优先于训练 |

---

## 9. 决策记录（ADR 建议）

| ADR | 决策 | 日期 |
|---|---|---|
| ADR-P1 | 抽取范围 = 疾病机制/靶点类 CNS + 高影响子刊，不抽通用方法论文 | TBD |
| ADR-P2 | 模式库以 JSONL + SQLite/FTS5 存储，不存全文 | TBD |
| ADR-P3 | evidence_strategy 输出必须结合论文模式与任务数据可得性，二者冲突时以任务数据为准 | TBD |
| ADR-P4 | 对齐训练默认 Reviewer LoRA，Planner 以 few-shot/RAG 为主 | TBD |
| ADR-P5 | 盲测恢复率只作为内部质量门，不对外表述为生物学成功率 | TBD |

---

## 10. 下一步（立即执行）

1. 冻结语料纳入/排除标准（PR 评审）。
2. 实现 PubMed/Europe PMC 检索脚本，产出 1000+ 候选池清单。
3. 定义 WorkflowPattern Schema v0.1 并评审。
4. 人工挑选 10 篇代表性论文，手工标注 pattern，作为抽取质量基线。
5. 启动 evidence_strategy 最小原型（先离线读 JSONL，不接 Web）。

## 附录 A：与现有 Target 模块的映射

| 本方案组件 | 现有模块 | 关系 |
|---|---|---|
| WorkflowPattern | `contracts.py` / `schemas/` | 新增合同 |
| PatternStore | `tools/literature.py`（Europe PMC RAG） | 复用 FTS5 基础设施 |
| evidence_strategy | 新工具（Planner 前） | 新增 |
| evidence_synthesis | 新工具（Reviewer 前） | 新增 |
| EvidenceLink | `contracts.py` `EvidenceItem` | 扩展 |
| 对齐数据 | `training/data/` | 新增子目录 |
| LoRA | `training/reviewer_lora.py` | 复用 |
| 盲测 | `benchmark/` | 复用 |
| Web 展示 | `src/target_agent/webapp.py` | 扩展 |


---

## 当前实现状态（2026-08-08）

### 已完成（P0/P1/P2）

1. 冻结 Paper-to-Strategy 合同：`ObservedWorkflow` / `EvidenceLink` / `StrategyPattern` / `BestPracticePattern`，位于 `src/target_agent/paper_strategy.py`。
2. 建成 PatternStore：append-only JSONL、不可变 digest、确定性词法检索，支持按疾病/数据可得性过滤，不依赖模型或网络。
3. 完成 Planner Few-shot 增强：`PlannerFewShotBuilder` 检索 top-k 模式，把 `why_this_order`、起始证据层、证据顺序、停止/降级规则注入 Step Planner；无命中或未配置时自动退化为原确定性流程。
4. 种子模式库：`paper_strategy/patterns.jsonl` 首批 10 条 discovery patterns（T2D/IBD/RA/CAD/AD/PD/Asthma/MCH trait-mechanism/Perturb-seq/sc-eQTL），`MANIFEST.json` 含逐条校验和。
5. CLI：`target-agent pattern search|list|add`；`scripts/build_seed_patterns.py` 可在远程校验并重建语料。
6. 新增 `tests/test_paper_strategy.py`（合同校验、store 不可变、检索排序、数据可得性惩罚、few-shot 输出）。
7. 候选语料管线：`paper_corpus.py` + `scripts/build_paper_corpus.py`，通过 NCBI E-utilities 按 4 个查询桶 × 10 个期刊白名单检索，确定性过滤（期刊归一化/年份/标题排除 review 与 methods-only），append-only `CorpusStore` 按 PMID 去重并逐条 SHA-256；远程真实刷新得到 200 条候选池（含 Science/Cell/Nature 及子刊），CLI `pattern corpus refresh|status`。
8. 证据策略可见性：ResearchPlan 持久化 `evidence_strategy_patterns`，项目快照与 Web 工作台展示“论文模式 → 策略 → 执行”链路，前端明确标注“策略提示非证据”。
9. 抽取工具链（P2）：`src/target_agent/pattern_extraction.py` 提供 append-only Gold 标注台账（`pattern curate`）、Europe PMC 摘要/Methods 有界提取、StrategyPattern 严格校验与 append-only 抽取审计（`pattern extract`），全程不存全文；专家评审以 `pattern review` 追加式台账完成，模式记录保持不可变。
10. 垂直子工作流注入：LangGraphRuntime 的域内 Planner 现在从配置的模式库构建 few-shot 提示并持久化命中 trace（`planner_pattern_hints`）；项目级 Planner 沿用原注入路径。
11. 消融回归：`benchmark/pattern_ablation.py` 在公开疾病金标准上离线度量模式覆盖率与确定性计划有效性，并支持 `--llm` 对比真实 Step Planner 在有/无模式提示下的计划形状；新增 benchmark 单元检查 BM-12。
12. 证据合成与机制证据图（P2.5）：确定性投影 Evidence Store 为实体/证据层/模式链接三层图；方向冲突与证据依赖质量门拦截模式链接；Web 工作台新增“机制证据图”面板与 `GET /api/projects/<id>/mechanism-graph` 接口。
13. 论文摘要 RAG（P2.6）：PaperRagStore 存储有界摘要分块（paper_strategy/rag/chunks.jsonl + MANIFEST），确定性词法检索（疾病/查询/数据可得性/年份/期刊），PlannerFewShotBuilder.build_paper_evidence 注入两端 Planner，ResearchPlan.paper_evidence 持久化，planner_paper_evidence trace，Web 新增“论文证据（RAG）”面板；仅存摘要、不存全文。
14. 论文RAG入图与盲测RAG覆盖率（P2.7）：机制证据图新增 strategy_paper 节点与 paper_strategy_hint 边（strategy_only/not_evidence、weight=0、不进入 lane_coverage/pattern_links/排名）；pattern_ablation 新增 --rag 离线分析；runner 新增 paper_rag_graph_projection 单元检查；队友 PR 12 上下文关系基准（145 例）经审查并入产品分支。

### 延后（P3，按团队决定最后再做）

- 把 Pattern 转成 Planner SFT / Reviewer 偏好数据并训练小型 Reviewer/Planner 模型。
- 在此之前先用 RAG + few-shot + 确定性规则验证策略价值，再做对齐训练。

### 下一步

0. 论文 RAG 已落地并接入机制证据图（P2.7）：`target-agent pattern rag refresh|search|status` + `benchmark/pattern_ablation.py --rag`；下一步扩充摘要分库（建议 30-50 篇 gold 论文优先），在真实 AD/肺腺癌/UC 运行上回归机制证据图，并重跑盲测 RAG 覆盖率。
1. 机制证据图回归：在真实 AD / 肺腺癌 / UC 运行上检查实体节点、证据层覆盖、模式链接与 synthesis findings，确认 UI 展示与后端数据一致。
2. 人工挑选 30-50 篇 Gold 论文：`target-agent pattern curate --pmid <PMID> --status gold --rationale "..." --role life_science|engineering`，科学+工程双人标注。
2. 批量抽取：`target-agent pattern extract`（需配置 Step 提供商），随后 `target-agent pattern review` 完成双人复核；每条抽取失败记录进入 `paper_strategy/extractions.jsonl` 供复盘。
3. 盲测回归：`python benchmark/pattern_ablation.py` 建立当前覆盖率基线（10 条种子：14/18 疾病命中、18/18 计划有效；SLE/银屑病/ALS/黑色素瘤尚无模式），模式库扩充后重跑，确保计划有效性不下降；可选 `--llm --limit N` 对比真实规划形状。
4. 对齐数据生成与 Planner/Reviewer 小模型训练：按团队决定最后再做，来源为已复核的 Pattern 库。
