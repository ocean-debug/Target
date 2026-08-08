---
id: genetics-audit
name: 人类遗传学证据审计
description: 受控 GWAS summary statistics、预计算 SuSiE credible set 与 coloc 审计；禁止 nearest-gene 映射。
version: 1.0.0
evidence_lanes: ["genetics"]
scopes: ["disease_target_discovery", "genetics"]
---

# Genetics Audit Best Practice

## 适用
把人类遗传学证据纳入靶点决策的所有任务。

## 硬性规则
1. GWAS summary statistics 必须通过候选宇宙冻结、变异校验与 provenance 检查。
2. 用户提供的 SuSiE credible set / coloc 输出必须经过 checksum 绑定的 variant-level harmonization 审计。
3. 禁止 nearest-gene 映射；GWAS-only locus 保持 unresolved。
4. 统计后验一律标 INFERRED；Open Targets 聚合证据只是数据库上下文，不能进入正式遗传学维度。
5. 体细胞突变不与遗传易感性混为一谈。
