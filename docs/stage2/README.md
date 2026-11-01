# Stage 2 集成说明与历史记录

这里保留原有文件名和链接。安装以根目录 README 为准；最新逐项验收以[真实云端浏览器记录](../testing/2026-11-01-browser-acceptance.zh-CN.md)为准。

## 当前实现与演示入口

- [门户接口接入](INTERFACE_INTEGRATION.zh-CN.md)、[规划／恢复状态机](LIFECYCLE_IMPLEMENTATION.md)
- [统一模型配置](DEMO_MODEL_KEYS.zh-CN.md)、[模型规划接线](MODEL_PLANNING.zh-CN.md)
- [启动检查](STARTUP_READINESS.zh-CN.md)、[演示账户](DEMO_ACCOUNTS.zh-CN.md)、[Demo 操作路径](DEMO_SCENARIOS.zh-CN.md)
- [投诉](UC04_COMPLAINTS.md)、[会员](UC07_MEMBERSHIP.md)、[营销](UC08_CAMPAIGN_HANDOFF.zh-CN.md)、[CI 与发布](CI_RELEASE.zh-CN.md)

- [旅客逐日编辑器](CUSTOMER_DAILY.md)、[多城市模拟数据与操作](MULTI_CITY_DEMO.zh-CN.md)

## 日期验收与排错记录

| 日期 / 记录 | 阅读边界 |
| --- | --- |
| [2026-11-01 本轮浏览器验收](../testing/2026-11-01-browser-acceptance.zh-CN.md) | main edab5e0；真实云端；按验收点区分通过与未完成 |
| [云端读取性能](CLOUD_READ_PERFORMANCE_2026-11-01.zh-CN.md) | 旧、新代码只读接口对比；不能据此宣称后续所有写入均无超时 |
| [云端流程修复](CLOUD_WORKFLOW_FIX_2026-11-01.zh-CN.md) | 当时复现的会员写冲突与任务超时，保留原始验证范围 |
| [11/13/45 隔离验收](ACCEPTANCE_11_13_45_2026-11-01.zh-CN.md)、[五卡验收](FIVE_CARD_ACCEPTANCE_2026-11-01.zh-CN.md)、[20/49 签收范围](RELEASE_20_49_CLOSEOUT.zh-CN.md) | 隔离自动化与既定签收范围，不替代真实云端或同伴复核 |
| [2026-10-31 Supplier / UC-08](SUPPLIER_ACCEPTANCE_2026-10-31.zh-CN.md) | 实际浏览器，但认证、云存储和模型为隔离替身 |
| [2026-10-27 集成演练](LIVE_WORKFLOW.zh-CN.md)、[PR 审计](PR_VALIDATION_AUDIT_2026-10-27.zh-CN.md)、[项目清单](PROJECT_LIST_2026-10-27.zh-CN.md) | 当时基线与待办，不能当作最新功能缺口清单 |

## 保留的交接与证据

- [B02/B03 交接](B02_B03_HANDOFF.md)、[合并说明](B02_B03_MERGE_NOTES.md)、[测试](B02_B03_TEST_RESULTS.md)
- [B08 交接](B08_SUPPLIER_HANDOFF.zh-CN.md)、[测试](B08_TEST_RESULTS.md)、[Supabase 适配](SUPABASE_ADAPTATION.md)
- [快照修复](SNAPSHOT_TIMEOUT_FIX.zh-CN.md)、[按需读取](SCOPED_CLOUD_READS.zh-CN.md)、[React 门户](REACT_PORTAL.zh-CN.md)
- 原始 JSON、截图及其余文件见[完整目录](../catalog.md)。

新增验收结果优先放 `docs/testing/`，在本页或总索引添加入口；不覆盖旧记录的日期、代码基线和原始结果。
