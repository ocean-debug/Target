---
id: literature-evidence-extraction
name: 文献证据抽取与溯源
description: 从 Europe PMC 召回片段中抽取可核对 claim，强制原文跨度、上下文、立场与不确定性标注；检索命中本身不是证据。
version: 1.0.0
evidence_lanes: ["literature"]
scopes: ["disease_target_discovery", "literature_review"]
---

# Literature Evidence Extraction

## 适用
任何需要把文献检索变成可审计证据的任务。

## 最佳实践
1. 只从稳定 chunk（固定 chunk ID）召回片段；全文/摘要版本在 EvidenceItem 中显式记录。
2. LLM 抽取 Claim 时必须给出可核对的原文跨度；检索命中本身不得自动算作支持证据。
3. 每条证据记录 stance（支持/反对/中性）、效应方向与不确定性。
4. 区分 FACT（原始记录）、OBSERVED（实验观察）、PREDICTED（模型预测）、INFERRED（Agent 综合推断）。
5. 上下文不匹配、证据冲突或片段缺失时降级、拒绝或标记缺口，不用流畅文字补全。

## 验收
- 每条 Claim 可回链到 source id + 片段 + 工具运行 id。
- 报告中没有数据库里不存在的数字或新引用。
