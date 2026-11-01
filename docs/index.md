# 文档索引

更新日期：2026-11-01（Australia/Sydney）。本索引按用途分类；[完整文件目录](catalog.md)保留所有版本控制文档的入口。

## 开始运行与演示

- [中文安装与启动](../README.zh-CN.md) · [English setup](../README.md)
- [演示账户与供应数据](stage2/DEMO_ACCOUNTS.zh-CN.md)
- [启动和配置检查](stage2/STARTUP_READINESS.zh-CN.md)
- [Demo 操作路径](stage2/DEMO_SCENARIOS.zh-CN.md)：操作指引，历史截图不能替代新版本复验。
- [演示模型统一配置](stage2/DEMO_MODEL_KEYS.zh-CN.md)
- [CI 与发布](stage2/CI_RELEASE.zh-CN.md)

## 测试与验收

- **[2026-11-01 真实云端浏览器验收与停止时状态](testing/2026-11-01-browser-acceptance.zh-CN.md)**：营销正常闭环通过；投诉部分分支通过，退款人工审核未完成。
- [测试记录分类与判定规则](testing/README.md)
- [本轮结构化记录与截图校验值](testing/2026-11-01-browser-evidence.json)
- [Stage 2 历史验收和修复记录](stage2/README.md)：按日期、代码基线和测试方式阅读，不能汇总为当前版本全部通过。

- [多城市模拟数据与逐日规划操作](stage2/MULTI_CITY_DEMO.zh-CN.md)：十项供应资源、实际 offerId 草稿及现有审核流程。

## 当前接口与领域说明

| 领域 | 文档 |
| --- | --- |
| 总体架构 | [架构说明](ARCHITECTURE.zh-CN.md) |
| 最新门户接入 | [接口与模拟数据](stage2/INTERFACE_INTEGRATION.zh-CN.md)、[规划及恢复状态机](stage2/LIFECYCLE_IMPLEMENTATION.md) |
| 身份与门户 | [认证与角色入口](portal/PORTAL_HANDOFF.md)、[React 队列](stage2/REACT_PORTAL.zh-CN.md) |
| Operations | [协调与交接](operations/OPERATIONS_HANDOFF.md) |
| Planning | [门户接入](planning/Authenticated_Portal_Integration.zh-CN.md)、[逐日因素](planning/Daily_Planning_Factors.zh-CN.md)、[行程激活](planning/Trip_Activation.zh-CN.md)、[课程模型](planning/Campus_Model_Connection.zh-CN.md) |
| Exception | [门户接入](exception/PORTAL_INTEGRATION.zh-CN.md)、[投诉政策输入](stage2/UC04_COMPLAINTS.md)、[Operations 集成](exception/INTEGRATION.md) |
| Supplier | [供应报价交接](stage2/B08_SUPPLIER_HANDOFF.zh-CN.md) |
| Campaign / Membership | [营销活动](stage2/UC08_CAMPAIGN_HANDOFF.zh-CN.md)、[会员权益](stage2/UC07_MEMBERSHIP.md)、[地图](uc07-trip-map.md) |
| 云端排错 | [按需读取](stage2/SCOPED_CLOUD_READS.zh-CN.md)、[读取性能实测](stage2/CLOUD_READ_PERFORMANCE_2026-11-01.zh-CN.md)、[本轮仍观察到的超时与冲突](testing/2026-11-01-browser-acceptance.zh-CN.md#云端问题与恢复情况) |

## 合同、需求与原始材料

- [Stage 2 小组贡献声明](../Stage%202%20Group%20Contribution%20Statement.md)

- [共享合同 v1](contracts/v1/CONTRACTS.md)、[需求与负责人映射](contracts/v1/REQUIREMENT_MAPPING.md)
- [B01 验收](contracts/v1/B01_ACCEPTANCE.md)、[Campaign 合同](contracts/v1/Campaign_Prototype.md)
- [合同 JSON 示例目录](catalog.md#contract-examples)
- [Project Description](Project%20Description.pdf)、[Stage 1 最终报告](TripMate_AI_stage1_report.pdf)
- [Planning Jira 卡](planning/Jira_Cards_B01-B20.en.md)、[实施计划](planning/Stage2_Week9-12_Plan_and_Jira.zh-CN.md)

## 文档维护

`testing/` 放验收结论、结构化记录和对应截图；`stage2/` 保留集成说明、日期审计和原始交接；各领域目录保留接口、实现与专项记录。保留原有路径，避免破坏 README、Jira 和历史链接。

历史文档中的“尚未实现”只适用于其当时代码；实现更新不等于真实环境验收通过。账户密码、密钥、本机配置、原始认证响应和临时个人材料不属于交付文档。未完成的流程不得改写成通过，不自动改变 Jira 或小组签收状态。
