# TargetDiscovery Agent V2

面向生命科学科研场景的 Best Practice 对齐与长程可靠性 Agent。主 Demo 聚焦溃疡性结肠炎（UC）疾病靶点发现；MCH/K562 作为独立科学金样板，展示“基因→程序→性状”的因果建模及其适用边界。

本仓库的产品是科研 Agent。Rubric、对齐案例和测试只是系统质量门，不建设独立评测平台。

## 可交付能力

- 类型化、可恢复的状态机：`Intake → Planner → Router → Tool → Evidence Store → Reviewer → Ranking → TargetCard → Report`。
- Step API 可用时参与规划和证据解释；不可用或 JSON 校验失败时自动切换到确定性 UC/MCH 工作流。
- Europe PMC 真检索、稳定 chunk、SQLite FTS5 召回、逐字跨度校验；检索命中本身不算证据。
- Open Targets 疾病关联、遗传证据和已知药物连接器。
- GSE125527 UC 组学快照与 GSE190604 原代 T 细胞 CRISPRa 实测扰动。
- DeltaFactor 明确标为 `PREDICTED`；K562→UC 上下文匹配低于 0.5 时不得进入正式排序。
- MCH 严格区分论文 `43/59` 与项目扩展 `94/147`；非 MCH 输入返回 `out_of_scope`，不生成固定图。
- 输出前10名、5张 TargetCard、重点3个、可证伪实验方案、Reviewer 问题和完整 Trace。

## 可靠性合同

公共合同版本为 `2.0.0`，唯一源是 [contracts.py](src/target_agent/contracts.py)。`schemas/` 由 Pydantic 自动导出，不手工维护第二份定义。

- 结论必须区分 `FACT / OBSERVED / PREDICTED / INFERRED`。
- 每条 EvidenceItem 必须关联 `tool_run_id`、来源定位、原文/结果跨度、上下文、立场与不确定性。
- `coverage_status=not_covered` 不得写成成功；低上下文、冲突或工具失败触发降级、补证或拒绝。
- 最多2轮 Reviewer、30次工具调用和20个初始候选。
- 终态只有：`completed`、`completed_with_gaps`、`needs_input`、`refused`、`failed`。
- 报告只读取结构化 Evidence Store；前端不计算或新增科学数字。

## 远程复现（唯一验收方式）

所有测试、构建和 Demo 均在指定远程环境运行；本地只读、编辑和 Git 操作。

```bash
ssh hywang@192.168.79.84
cd /home/hywang/codex/deecamp/
git clone --branch integration/v2-demo git@github.com:ocean-debug/Target.git Target
cd Target
qsub scripts/pbs_validate.sh
```

验收作业固定使用 `gpu` 队列、`gpu03`、50 核、`agenttest` 环境和 GPU 0。成功日志应包含：

```text
MCH_GOLD_BOUNDARY=OK
REPO_POLICY=OK
REMOTE_HOST=gpu03
PYTHON_VERSION=3.11.13
V2_VALIDATION=OK
```

运行三个边界场景：

```bash
python -m target_agent run --input cases/main_demo/input.uc_demo.yaml --run-id run-uc-demo
python -m target_agent run --input cases/main_demo/input.mch_gold.yaml --run-id run-mch-gold
python -m target_agent run --input cases/main_demo/input.ood_crohn.yaml --run-id run-crohn-ood
python scripts/validate_run.py runs/run-uc-demo
```

配置 Step API 时复制 `.env.example` 到不入 Git 的环境变量文件，并设置 `STEP_API_KEY` 与当前可用的 `STEP_MODEL` 部署名。缺失时会使用确定性工作流，不影响结构化主链。

## 单页工作台

```bash
qsub scripts/pbs_demo_server.sh
ssh -L 8000:gpu03:8000 hywang@192.168.79.84
```

浏览器打开 `http://127.0.0.1:8000`。API：

- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/events`
- `GET /api/runs/{run_id}/report`
- `GET /api/runs/{run_id}/artifacts/{name}`

## 对齐与安全进化

```bash
python -m target_agent generate-alignment --output alignment_data
```

生成 120 条 Reviewer/Planner SFT、60 组偏好对和 30 条内部保留案例。所有高风险条目默认处于双人复核 `pending`，未经生命科学与工程双重批准时，LoRA 训练入口会拒绝运行。Agent 不自动改代码、训练、发布或晋升经验。

训练模型暂不锁定；若第二周末仍未选择，脚本默认 `Qwen/Qwen3-8B`。该 LoRA 仅作为可切换 Reviewer 后端，不控制完整 Agent。

## 数据边界

Git 只保存 manifest、小型派生快照、参数和复现方法；原始组学数据、缓存、模型权重、运行目录和密钥均不入库。详见 [data/README.md](data/README.md) 与 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

最终远程作业、真实服务结果、边界条件和未开放闸门见 [验收报告](docs/VALIDATION_REPORT.md)。
