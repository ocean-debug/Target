---
id: target-card-review
name: TargetCard 证据门控与 Reviewer
description: 证据先乘上下文匹配系数；反证与安全阻断项独立保留；GO 必须有至少两类独立证据。
version: 1.0.0
evidence_lanes: ["integration", "safety"]
scopes: ["disease_target_discovery"]
---

# TargetCard Review Gates

## 适用
候选靶点排名、TargetCard 生成与最终 Reviewer 评审。

## 门控规则
1. 排名维度固定：人类遗传学 25%、疾病上下文组学 20%、实测/预测扰动 20%、机制收敛 15%、可成药性 10%、安全与转化 10%。
2. 每条证据先乘上下文匹配系数；context_match_score < 0.5 完全排除。
3. 预测扰动最多获得扰动维度一半分值。
4. 反方证据与安全阻断项独立保留，不通过加权平均隐藏。
5. 总分只用于排序，不表述为临床成功概率。
6. GO 必须有至少两类独立证据且包含人类遗传学或匹配上下文的实测扰动；否则只能 CONDITIONAL_GO 或 INSUFFICIENT_EVIDENCE。
