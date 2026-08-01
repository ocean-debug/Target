# Agent Runtime

主责：张炜民；全员参与接口设计和联调。

本目录实现TaskSpec接收、Planner、Router、AgentState、重试、缓存、断点恢复和停止条件。Runtime只负责编排，不应把具体组学或扰动算法复制到这里。

首批交付建议：

- `state.py`：任务、计划、证据、工具结果和报告状态。
- `planner.py`：根据Workflow生成可检查步骤。
- `router.py`：根据tool registry选择工具。
- `session.py`：保存run_id、恢复点和运行产物。
- 一个成功链路和一个工具失败降级链路。
