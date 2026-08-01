# Perturbation Tools

共同主责：王海洋、陈政翰；陈锦钰负责实测扰动输入与比较。

本目录同时容纳：

- observed Perturb-seq分析；
- scGen/GEARS等预测工具；
- observed与predicted比较；
- 细胞、基因、物种和扰动类型的Context/OOD Gate。

统一返回`PerturbationResult`。模型可运行不等于适用于当前问题；任何外推都必须标记限制。
