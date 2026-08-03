# TargetDiscovery Agent V2 验收报告

验收日期：2026-08-03

## 验收环境

- SSH：`hywang@192.168.79.84`
- 工作目录：`/home/hywang/codex/deecamp/Target`
- Conda 环境：`agenttest`
- PBS：`gpu` 队列，`gpu03` 节点，50 CPU 核，`CUDA_VISIBLE_DEVICES=0`
- Python：3.11.13
- 实际 GPU 见证：`NVIDIA A100-PCIE-40GB`

说明：此前提供的资源描述为 H100，但本次指定节点 `gpu03` 实际暴露的是 A100。本文只记录运行时可验证事实；若最终验收必须使用 H100，需要另行指定 H100 节点。

## 最终代码验收

PBS 作业 `73414` 在指定环境完成：

```text
16 passed in 0.29s
MCH_GOLD_BOUNDARY=OK
PAPER_DIRECTION=43/59
PROJECT_EXTENSION=94/147
FIG3A_NUMERIC_CHECK=OK
REPO_POLICY=OK
REMOTE_HOST=gpu03
PYTHON_VERSION=3.11.13
GPU0=NVIDIA A100-PCIE-40GB
V2_VALIDATION=OK
```

覆盖范围包括：合同 2.0.0、旧合同单向迁移、混合版本拒绝、工具成功与失败/OOD、Evidence—ToolRun—Trace 回链、覆盖不足降级、DeltaFactor 上下文排除、MCH 边界、报告数字一致性和仓库策略。

## 真实服务与端到端验收

PBS 作业 `73415` 使用真实 Open Targets、Europe PMC 和本地可复现数据资产完成：

- UC 首次运行：5.640 秒，终态 `completed_with_gaps`。
- UC 缓存连续三次：0.985、0.541、1.047 秒，科学结论一致。
- MCH 金样板：0.034 秒，终态 `completed`。
- Crohn 上下文错配案例：0.066 秒，终态 `needs_input`。
- 最终见证：`REAL_DEMO_ACCEPTANCE=OK`。

UC 的 `completed_with_gaps` 是预期的可靠性行为，而非执行失败：实测扰动只覆盖 71 个筛选靶点中的有限交集，同时存在安全性信号和证据冲突，系统保留缺口而不宣称完整覆盖。

### Open Targets 实际结果

- 疾病解析：溃疡性结肠炎 `MONDO_0005101`
- 人类遗传关联：10 条进入候选融合
- 已知药物/临床候选链接：15 条
- 具有可成药性信息的候选：9 个
- 安全性事件：7 条，作为独立 blocker 保留
- 最高遗传学候选包括：IL23R、IL12B、IL10、FCGR2A、GPR35、JAK2、MST1、CXCR2、TNFSF15、IRF5

### Europe PMC 实际结果

- 检索命中：25 篇
- FTS5 召回片段：24 个
- 通过精确原文跨度校验的 Claim：11 条
- 检索命中本身未被计作支持证据。

### UC 缓存运行前十名

| 排名 | 靶点 | 决策 | 分数 | 独立 blocker |
|---:|---|---|---:|---:|
| 1 | CD27 | GO | 33.2446 | 0 |
| 2 | IL12B | GO | 32.3692 | 0 |
| 3 | JAK2 | CONDITIONAL_GO | 30.9028 | 3 |
| 4 | GATA3 | CONDITIONAL_GO | 29.8996 | 1 |
| 5 | IL2 | GO | 27.8526 | 0 |
| 6 | GPR35 | GO | 27.4515 | 0 |
| 7 | FOSB | CONDITIONAL_GO | 26.7213 | 1 |
| 8 | CXCR2 | GO | 24.9691 | 0 |
| 9 | IL23R | INSUFFICIENT_EVIDENCE | 24.3367 | 3 |
| 10 | TAGAP | GO | 23.8926 | 0 |

分数仅用于候选排序，不表示成功概率；blocker 不通过加权平均隐藏。

## 有意保留的上线门

- Step API：未在本次执行上下文提供 `STEP_API_KEY` 和部署模型名，因此没有发起真实 Step 请求；结构化失败后的确定性 UC/MCH 回退链已验证。
- Reviewer LoRA：120 条 SFT、60 组偏好对和 30 条保留案例已生成，但高风险案例仍处于生命科学与工程双重复核 `pending`。训练入口会拒绝未经批准的数据，因此本次未训练或发布权重。
- 自主进化：只实现离线、可审计、人工批准的 CaseRecord 晋升机制；Agent 不自动修改代码、训练或发布。

以上限制是可靠性护栏，不应在答辩中描述为已经完成的在线模型训练或自动进化。
