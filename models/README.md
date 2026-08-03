# Reviewer LoRA

运行时默认使用 Step API 或确定性 Reviewer。LoRA 是可选、离线且人工批准的 Reviewer 后端展示，不控制完整 Agent。

- 默认候选基座：`Qwen/Qwen3-8B`（仅当第二周末仍未选择模型）。
- 训练入口：`training/reviewer_lora.py`。
- 数据必须通过生命科学和工程双重批准；待审数据默认拒绝训练。
- 权重不进 Git；这里只提交模型卡、训练参数、数据 manifest、保留集结果和限制。
- 使用 `--allow-pending-review` 只能做技术 smoke test，产物不得晋升或用于正式演示结论。
