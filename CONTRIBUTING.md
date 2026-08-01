# Contributing

## 1. 开始任务前

1. 在 GitHub Issue 中写清目的、输入、输出、负责人、依赖和验收条件。
2. 确认是否会修改 `schemas/` 或 `workflows/`；接口变更必须先讨论。
3. 从最新 `main` 创建分支。

分支命名：

```text
feat/<module>-<short-name>
fix/<module>-<short-name>
docs/<short-name>
experiment/<short-name>
```

示例：`feat/omics-qc`、`feat/gears-tool`、`fix/evidence-dedup`。

## 2. 提交规范

一次提交只完成一个可解释的小步骤。推荐格式：

```text
feat(omics): add dataset quality result schema
fix(agent): stop retrying on unsupported cell type
docs(workflow): define disease-to-target stopping rules
```

不要提交：API Key、患者信息、模型权重、绝对路径、原始大数据、运行缓存和未清理的 Notebook 输出。

## 3. Pull Request 必须包含

- 改了什么，以及为什么改。
- 输入和输出示例。
- 运行命令或调用方式。
- 一个成功案例。
- 一个失败、OOD 或拒绝案例。
- 产生的 Trace、报告或图表位置。
- 对上游和下游模块的影响。

涉及科学结论的 PR 需要生命科学成员复核；涉及 Schema、Agent 或工具接口的 PR 需要工程成员复核。

## 4. Schema 与工具合同

- 不在工具代码中创建只有自己知道的私有字段。
- 公共字段先进入 `schemas/`，再由工具实现。
- 删除或重命名字段属于破坏性变更，必须在 `DECISION_LOG.md` 记录迁移方案。
- 每个工具必须返回明确的 `status`、`provenance`、`warnings` 和 `limitations`。

## 5. 完成定义

请遵循 [docs/DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md)。代码存在于仓库不等于完成；只有被主 Agent 调用、留下 Trace，并由非作者复现，才算完成。
