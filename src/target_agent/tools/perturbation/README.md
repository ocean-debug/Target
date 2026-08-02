# Perturbation Tools

主责：工作流 F；工作流 C 负责实测扰动输入、上下文和科学比较，工作流 B 负责工具接入。

本目录同时容纳：

- observed Perturb-seq分析；
- scGen/GEARS等预测工具；
- observed与predicted比较；
- 细胞、基因、物种和扰动类型的Context/OOD Gate。

统一返回`PerturbationResult`。模型可运行不等于适用于当前问题；任何外推都必须标记限制。
