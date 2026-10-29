# 文档索引

当前版本从这里开始浏览。带日期的审计、测试和交接说明保留其原始范围，不代表最新功能状态；最新安装步骤以根目录 README 为准。Stage 1 工作草稿和独立 UML 已清理，仅保留最终报告。

## 常用入口

- [中文安装与启动](../README.zh-CN.md)
- [English setup guide](../README.md)
- [集成流程、演示顺序与当前限制](stage2/LIVE_WORKFLOW.zh-CN.md)
- [演示账户与供应数据](stage2/DEMO_ACCOUNTS.zh-CN.md)
- [启动和配置检查](stage2/STARTUP_READINESS.zh-CN.md)
- [Stage 1 最终报告](TripMate_AI_stage1_report.pdf)

## 根目录

- [TripMate AI 当前架构](ARCHITECTURE.zh-CN.md)
- [Project Description.pdf](Project%20Description.pdf)
- [TripMate_AI_stage1_report.pdf](TripMate_AI_stage1_report.pdf)

## contracts/v1

- [B01 acceptance and review record](contracts/v1/B01_ACCEPTANCE.md)
- [TripMate AI shared contracts v1.0.0](contracts/v1/CONTRACTS.md)
- [Requirement and ownership mapping — B01 v1.0.0](contracts/v1/REQUIREMENT_MAPPING.md)

## contracts/v1/examples

- [AgentResult.exception.approval-pending.json](contracts/v1/examples/AgentResult.exception.approval-pending.json)
- [AgentResult.exception.failure.json](contracts/v1/examples/AgentResult.exception.failure.json)
- [AgentResult.exception.success.json](contracts/v1/examples/AgentResult.exception.success.json)
- [AgentResult.operations.approval-pending.json](contracts/v1/examples/AgentResult.operations.approval-pending.json)
- [AgentResult.operations.failure.json](contracts/v1/examples/AgentResult.operations.failure.json)
- [AgentResult.operations.success.json](contracts/v1/examples/AgentResult.operations.success.json)
- [AgentResult.planning.approval-pending.json](contracts/v1/examples/AgentResult.planning.approval-pending.json)
- [AgentResult.planning.failure.json](contracts/v1/examples/AgentResult.planning.failure.json)
- [AgentResult.planning.success.json](contracts/v1/examples/AgentResult.planning.success.json)
- [AgentResult.supplier.approval-pending.json](contracts/v1/examples/AgentResult.supplier.approval-pending.json)
- [AgentResult.supplier.failure.json](contracts/v1/examples/AgentResult.supplier.failure.json)
- [AgentResult.supplier.success.json](contracts/v1/examples/AgentResult.supplier.success.json)
- [Approval.approved.json](contracts/v1/examples/Approval.approved.json)
- [Approval.pending.json](contracts/v1/examples/Approval.pending.json)
- [Case.confirmed.json](contracts/v1/examples/Case.confirmed.json)
- [ItineraryVersion.draft.json](contracts/v1/examples/ItineraryVersion.draft.json)
- [PriceBreakdown.base.json](contracts/v1/examples/PriceBreakdown.base.json)
- [SupplierOffer.draft.json](contracts/v1/examples/SupplierOffer.draft.json)
- [TraceEvent.approval-requested.json](contracts/v1/examples/TraceEvent.approval-requested.json)
- [TravelRequest.confirmed.json](contracts/v1/examples/TravelRequest.confirmed.json)

## exception

- [Customer Exception: Operations integration](exception/INTEGRATION.md)
- [Exception integration acceptance evidence](exception/INTEGRATION_ACCEPTANCE.md)
- [Customer Exception Agent delivery backlog](exception/JIRA_BACKLOG.md)
- [Main compatibility validation — 15 October 2026](exception/MERGE_VALIDATION.md)
- [默认认证门户 Exception 接入](exception/PORTAL_INTEGRATION.zh-CN.md)
- [Customer Exception Agent prototype](exception/README.md)
- [Customer Exception prototype validation](exception/TEST_RESULTS.md)
- [integration-evidence.json](exception/integration-evidence.json)

## exception/screenshots

- [english-demo.png](exception/screenshots/english-demo.png)

## operations

- [Operations Agent implementation and handoff](operations/OPERATIONS_HANDOFF.md)
- [Operations acceptance evidence](operations/TEST_RESULTS.md)

## planning

- [Sprint 2：认证门户 Planning 接入](planning/Authenticated_Portal_Integration.zh-CN.md)
- [Planning 课程模型接入](planning/Campus_Model_Connection.zh-CN.md)
- [逐日规划与旅游影响因素后端](planning/Daily_Planning_Factors.zh-CN.md)
- [TripMate AI — Jira Cards B01–B20](planning/Jira_Cards_B01-B20.en.md)
- [Jira_Starter_Backlog.csv](planning/Jira_Starter_Backlog.csv)
- [Planning 与 main 联调说明](planning/Main_Integration.zh-CN.md)
- [Moore — Travel Planning 实现与交接](planning/Moore_Travel_Planning_Implementation.zh-CN.md)
- [TripMate AI：第 9–12 周实施计划与 Jira 看板设计](planning/Stage2_Week9-12_Plan_and_Jira.zh-CN.md)
- [Travel Planning API 交接与调用说明](planning/Travel_Planning_API_Handoff.zh-CN.md)
- [Sprint 2：旅客明确开始行程](planning/Trip_Activation.zh-CN.md)

## planning/evidence

- [live_model_smoke.json](planning/evidence/live_model_smoke.json)
- [main_integration_smoke.json](planning/evidence/main_integration_smoke.json)

## portal

- [TripMate portal and Supabase delivery](portal/DELIVERY_REPORT.md)
- [Portal and Supabase Jira Backlog](portal/JIRA_BACKLOG.md)
- [Supabase authentication and role portals](portal/PORTAL_HANDOFF.md)
- [Portal acceptance evidence — 13 October 2026](portal/TEST_RESULTS.md)

## stage2

- [B02 + B03: Local workbench and deterministic fixture handoff](stage2/B02_B03_HANDOFF.md)
- [B02/B03 branch and integration notes](stage2/B02_B03_MERGE_NOTES.md)
- [B02/B03 verification record (2026-10-13, Windows)](stage2/B02_B03_TEST_RESULTS.md)
- [B08：供应商报价评估与定价交接](stage2/B08_SUPPLIER_HANDOFF.zh-CN.md)
- [B08 Windows verification — 2026-10-13](stage2/B08_TEST_RESULTS.md)
- [默认演示账户和供应数据](stage2/DEMO_ACCOUNTS.zh-CN.md)
- [真实账户集成演练与下一步](stage2/LIVE_WORKFLOW.zh-CN.md)
- [默认门户的课程模型规划接线](stage2/MODEL_PLANNING.zh-CN.md)
- [TripMate AI 项目功能与 Bug 清单](stage2/PROJECT_LIST_2026-10-27.zh-CN.md)
- [PR 验证与 Sprint 2 剩余工作审计](stage2/PR_VALIDATION_AUDIT_2026-10-27.zh-CN.md)
- [初始化入口与课程模型就绪检查](stage2/STARTUP_READINESS.zh-CN.md)
- [Supabase 快照读取超时修复与验证](stage2/SNAPSHOT_TIMEOUT_FIX.zh-CN.md)
- [Supplier B02/B03/B08 adaptation — 13 October 2026](stage2/SUPABASE_ADAPTATION.md)
- [cloud-demo-init-evidence-2026-10-27.json](stage2/cloud-demo-init-evidence-2026-10-27.json)

本索引覆盖版本控制中的文档与示例；本机临时交接、账户密码、未提交的个人材料不属于交付文档。
