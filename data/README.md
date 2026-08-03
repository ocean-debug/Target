# 数据与重算边界

`data/derived/` 只包含三个可审查的小型快照，来源和上游资产记录在 `MANIFEST.json`：

- `uc_candidates_v2.json`：GSE125527 donor-pseudobulk edgeR 的20个初始候选。
- `uc_observed_perturbation_v2.json`：GSE190604 原代 T 细胞 CRISPRa 中与候选重叠的实测结果，以及对 UC 签名的有限样本相关。
- `mch_gold_v2.json`：论文 MCH 配置与项目扩展复现的分离指标。

重算要求：保留公开数据 accession、下载校验和、样本/细胞过滤、软件版本、随机种子、完整参数、输出校验和和 session info。大原始矩阵、模型权重和中间缓存留在远程 `/home/hywang/codex/deecamp/`，不进 Git。

UC 组学是观察性证据；GSE190604 的 CRISPRa 是激活而非抑制；71 靶点的疾病签名相关是有限样本机制支持，均不得自动表述为疾病因果。
