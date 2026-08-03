# 远程验收矩阵

固定配置：`hywang@192.168.79.84`、`/home/hywang/codex/deecamp/`、`agenttest`、PBS `gpu` 队列、`gpu03`、50 核、默认 GPU 0。

| 验收项 | 命令/测试 | 通过信号 |
|---|---|---|
| Schema/迁移/版本 | `tests/test_contracts.py` | 2.0 schema 导出，混用版本拒绝 |
| 工具成功与 OOD | `tests/test_science_tools.py` | UC 成功、Crohn/MCH OOD 正确 |
| Evidence/Trace 回链 | `tests/test_runtime.py` | source span、tool_run_id 无空链 |
| covered=false | `tests/test_review_and_web.py` | blocking/needs_input，不写 completed |
| UC 三次一致 | `test_cached_style_uc_three_runs_are_consistent_and_fast` | 排名、分数、决策完全一致且单次<120秒 |
| MCH 数字 | `scripts/validate_mch_gold.py` | 43/59 与 94/147 分离、Fig.3a 检查通过 |
| DeltaFactor 边界 | `test_deltafactor_uc_is_excluded` | context<0.5、formal_score_eligible=false |
| Step 回退 | UC 测试使用 `Planner(None)` | 确定性工作流完成 |
| 前端数字 | `test_api_artifact_matches_backend_without_new_numbers` | report 与后端 ranking 完全相同 |
| 仓库策略 | `scripts/repo_policy_check.py` | 无密钥、本地绝对路径、>5MB 文件 |

