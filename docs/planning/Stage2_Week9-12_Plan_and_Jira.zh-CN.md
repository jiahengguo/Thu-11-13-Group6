# TripMate AI：第 9–12 周实施计划与 Jira 看板设计

编制日期：2026-10-08。本文是实施建议，不是课程官方截止日期，也不表示功能已经实现。

## 1. 目标与依据

- 第 11 周：四个 Agent 在同一个可运行原型中完成可重复演示的业务闭环。
- 第 12 周：完成下述冻结的核心功能集合；可选功能按剩余容量选择，不追求全部实现。
- Week 9 / Laboratory 8 明确要求：使用 Jira；按 sprint 管理工作；举行 Planning、Daily Stand-up、Review、Retrospective；user story 使用 “As a [user], I want [goal], so that [reason].”；每条 story 定义 Definition of Done 和测试方式；用 MoSCoW 分类。
- 产品依据为仓库 README、保留的 `docs/TripMate_AI_stage1_report.pdf` 和现有模块需求。尚未核实在线 Project Requirement 或 Stage 2 评分标准。获得后应在 W9 检查遗漏，不据此擅自删减课程必交项。
- 仓库当前主要包含模型和文档，未发现应用源码或构建配置；因此按从基础原型开始估算。若已有其他分支或独立代码库，可缩短基础工作。

**执行原则：先交付跨 Agent 的完整流程，再扩展场景；从第 9 周起持续集成。**

## 2. 范围与可行性

### W11 原型演示范围

固定悉尼至墨尔本、AUD、模拟供应商/预订/支付/异常数据：

1. Traveller 输入请求，Operations 提取信息、补问并取得确认；验证模拟身份及访问权限。
2. 会员规则允许或拒绝请求；免费会员最多两条 Planned/Active 行程、每条最多五个日历日。
3. Supplier 导入并验证报价，确定性计算售价和差价；Planning 只能使用 Approved 且未过期的报价。
4. Planning 生成包含交通、住宿、活动的完整行程；先检查硬约束，再按 Comfort/Value/Budget 排序并解释。
5. 操作员注入一条模拟取消事件，Exception 调用 Supplier 与 Planning 形成恢复建议。
6. Reviewer 检查证据、计算和审批条件；受限建议进入人工审批；由 Operations 统一展示最终结果。
7. 页面展示 case、四个 Agent 的处理记录、验证结果和审批记录，能够定位失败发生在哪里。

演示可以提前准备数据和输入，但业务处理必须由应用执行；模拟数据应标注。LLM 用于提取、分析和解释，会员/价格/时间/库存/审批决定由确定性规则执行。Reviewer 是共享控制能力，不另设第五位负责人或强制第五个 LLM Agent。

### W12 核心功能冻结集合

以 UC-01 至 UC-08 为业务覆盖骨架，包含：完整行程与比较、确认后的版本修改、异常恢复、投诉调查、统一接待与回复、供应商验证和定价、会员/付费权益、营销方案评估与人工审批；加上共享 trace、校验、保存、重试和演示界面。

每个 UC 至少一条成功路径和一条有意义的失败/等待路径。完成数量以验收通过的 story 为准，不能用页面数量或代码量判断“大部分完成”。未通过 AC 的 story 留在 Testing 或 Backlog，明确剩余工作。

| MoSCoW | 本阶段含义 | 范围 |
| --- | --- | --- |
| Must-have | W11 演示与系统基础不可缺 | 接待/确认/会员、报价验证和差价、行程生成、共享校验/审批/trace、一次取消恢复、跨 Agent 集成 |
| Should-have | W12 核心目标；延后须记录缺口 | 版本修改、投诉、营销审批、会员完整 UI 与路线地图、失败恢复、完整评估和交付说明 |
| Could-have | 核心全部验收后，最多挑一个 | Supplier reliability summary、少量目的地 RAG、模拟主动异常通知、获客分析 |
| Would-like-to-have | 本阶段不承诺 | 实时供应商/支付/广告平台、复杂预测、生产级部署、多城市大规模扩展 |

Should-have 仍属于 W12 核心目标，不能因为标签就宣称无需实现。Optional 是否必须个人展示，需依据 Stage 2 评分标准确认。

### 容量假设与技术选择

- 假设每人每周投入约 12–14 小时，含会议、实现、review 和测试。四周总容量 192–224 人小时。
- 初始 backlog 估计 126 人小时，余量 66–98 小时用于会议、未知技术问题、返工和准备；估计不是交付保证。W9 Planning 必须用真实可用时间重新校准。
- 若实际每人少于 10 小时/周，或 W9 基础任务未完成，应保留 W11 演示闭环，先推迟 Could/Would；再把 Should 的未完成部分明确列为 W12 缺口，及时向 tutor 解释。
- 推荐单仓库、单后端、单数据库、四个模块式 Agent，共享一套接口；无需四个独立服务。优先使用团队熟悉的 Web 框架，SQLite/本地存储和一个 LLM 提供者足够。W9 第一天定技术栈，之后不因个人偏好重换。
- UI 采用统一接待入口、行程/版本页、Operator 工作台（报价、异常、审批、trace）。四位成员在同一个应用里交付功能。

## 3. 四人分工与共同责任

姓名沿用本地需求稿，正式 Jira assignee 应映射到实际账号。

| 成员 | 业务端到端所有权 | 公共责任 | 常规交叉 reviewer |
| --- | --- | --- | --- |
| Jiaheng | Operations；UC-05、UC-07 | 共享接口约定、请求入口、Case 状态和权限边界 | wrd |
| Moore | Travel Planning；UC-01、UC-02 | 约束校验、行程与版本数据结构、交付说明整合 | Jason |
| wrd | Customer Exception；UC-03、UC-04 | Reviewer、人工审批队列、trace、演示验收 | Jiaheng |
| Jason | Supplier；UC-06、UC-08 | 项目启动、模拟数据、集成检查与重试机制 | Moore |

公共工作也创建 Jira Task，有一位 assignee 和一位 reviewer。每人负责自己功能的页面、服务逻辑、测试和证据，不把 UI/测试集中留给另一人。演示与报告应体现四人的实际贡献。

## 4. 四个一周 sprint

以下按用户确认的“10 月 8 日为第 9 周”连续推算，以周四 lab 为检查点；如课程安排不同，调整日期而保留顺序。

| Sprint | 建议日期 | 目标 | Review 必须展示 |
| --- | --- | --- | --- |
| S1 / W9 Foundation | 10/8–10/14 | 可启动应用、共享数据和接口、基础规则 | 固定请求能沿接口走通至结果；允许 specialist stub，明确标注；trace 和审批基础可用 |
| S2 / W10 Demo Flow | 10/15–10/21 | 接入真实 Agent 逻辑，打通四 Agent 闭环 | 新请求→会员→报价→完整行程→模拟取消→恢复建议→受控回复；不依赖手工编辑数据库 |
| S3 / W11 Core Expansion | 10/22–10/28 | 展示 prototype，补齐比较/修改/投诉/营销/付费权益 | 10/22 lab 展示稳定版本；10/28 前完成核心功能扩展 |
| S4 / W12 Core Completion | 10/29–11/4 | 失败处理、回归评估和交付 | 核心 AC 清单、三套演示、已知问题及贡献记录；未完成项单列 |

**W11 可演示版本应在 10/21 晚前准备好，10/22 展示。W12 大部分核心功能应在 10/29 Review 可见，11/4 前完成该 sprint 的验收和修复。** 营销和付费功能需在 W11 就开始接口/数据准备，避免把 S4 全变成新开发。若要求 W12 lab 当天全部完成，将 S4 功能实现提前到 S3，S4 只做验收；按实际容量重新排期。

每个 sprint 前半段优先完成可集成的小增量，后半段测试和修复。10/20 前停止给 demo 增加新能力；10/21 只修复演示阻塞问题。保存稳定标签 `w11-prototype`，后续扩展不覆盖演示基线。

### W9 当天的执行顺序

1. 全组核对 Stage 2 评分要求、四人的实际可用时间和现有代码位置。
2. 冻结演示输入、需求 ID 映射和最低 AC。旧稿 PLAN-01/02/03 与当前稿 TP-01/02 并存；只建立确认过的映射，不随意更改已有 ID。
3. 约定 Case、TravelRequest、SupplierOffer、PriceBreakdown、ItineraryVersion、AgentResult、Approval、TraceEvent 的字段和状态；用一份 JSON 示例检验大家的理解。
4. 定义 Agent 调用输入/输出、`caseId`、`correlationId`、证据引用、校验结果、错误和 `requiresApproval`；明确 Operations 是对外出口。
5. 建 Jira、录入 backlog、开 S1，完成第一次 stand-up。
6. 四人基于同一模拟数据开始；基础接口定稿后立即用 stub 联调，随后逐项替换成实际模块。

### 依赖关系

接口/启动/数据 → 接待及权限、供应商和共享校验 → 行程生成 → 四 Agent 集成 → 恢复/修改/投诉/营销。

恢复依赖 Supplier、Planning、审批和 trace；营销依赖 Approved offers 与审批；会员优惠联动依赖 UC-08 规则、UC-07 资格和 UC-06 最终价格。不要让各人到 W10 末才交换输出格式。

## 5. Jira 板设计

建议一个 Scrum board，项目名 `TripMate AI Stage 2`，项目 key 可用 `TMA`（实际以 Jira 创建结果为准），四个 sprint，共享 backlog。Scrum backlog 支持把待办分配到 sprint，见 [Atlassian 官方说明](https://support.atlassian.com/jira-software-cloud/docs/use-your-scrum-backlog/)。具体字段及视图能力取决于团队所用 Jira 项目配置，不要求购买额外插件。

### Epic 和 issue 层级

| Epic | 对应职责 |
| --- | --- |
| E-OPS Operations & Membership | UC-05、UC-07 |
| E-PLAN Planning & Versions | UC-01、UC-02 |
| E-EXC Exception & Complaints | UC-03、UC-04 |
| E-SUP Supplier & Campaigns | UC-06、UC-08 |
| E-PLAT Platform & Human Oversight | 接口、数据、校验、审批、trace、稳定性 |
| E-DEMO Integration & Delivery | 联调、演示、验收、贡献与模型一致性 |

Epic 下放用户可验收的 Story，公共工程工作用 Task，实际缺陷用 Bug；大 story 的实现步骤用 Sub-task，尽量控制在半天至一天内。一条 story 只选一个主 Epic，跨 Agent 关系用 dependency link 和标签表达。不能把“实现某个 Agent”作为持续四周的大卡片。

### Workflow

`To Do → In Progress → Review → Testing → Done`

| 位置 | 进入/离开条件 | 建议工作量上限 |
| --- | --- | --- |
| Backlog | 尚未进入当前 sprint；并非开发列 | 排序即可 |
| To Do | 已达到 Ready 标准；进入当前 sprint | 不设置硬上限 |
| In Progress | assignee 正在实现 | 每人最多 1 个主项，全组最多 4 个 |
| Review | 可运行、已有提交/PR 和初步测试 | 全组最多 2 个，优先清理 |
| Testing | review 已通过，待功能与集成验收 | 全组最多 2 个 |
| Done | 满足该卡 AC 和统一 DoD | 完成列必须位于最右侧 |

这些 WIP 上限是团队约定；项目支持列限制时可配置，否则在每日会议执行。列与状态的映射参见 [Atlassian 官方说明](https://support.atlassian.com/jira-software-cloud/docs/configure-columns/)。

Blocked 用 flag 保留原列，同时评论原因、依赖卡、解阻负责人和下次检查时间；超过一个工作日未解除就缩小任务或两人协作。Jira 支持用 flag 标记阻塞，见 [官方说明](https://support.atlassian.com/jira-software-cloud/docs/flag-an-issue/)。审批等待是应用的业务状态，不意味着实现该审批功能的 Jira story 必须一直 Blocked。

### 卡片字段、标签与视图

必填：Summary、Description、Due Date、User Story、Issue Type、Epic、Assignee、Sprint、MoSCoW label、Estimate、Acceptance Criteria、Test method、Req/UC IDs、Dependencies、Evidence。Jira 未提供的字段放进 Description 模板，不强求自定义字段。

- 标签：`moscow-must`、`moscow-should`、`moscow-could`、`moscow-would`，四选一；另加 `agent-ops` / `agent-plan` / `agent-exc` / `agent-sup` / `shared`；演示卡加 `demo-w11`。
- Jira Priority 表达处理紧急程度；MoSCoW 表达范围承诺。临近演示的阻塞 Bug 可以高优先级，不应自动把所有 Must 卡都标最高。
- 估计先用小时。Planning 确认后再用 1/2/3/5/8 story points 也可，但不要把 points 当工时，也不要父 story 和 sub-task 重复计入容量。
- 主板按 Epic 分组；若当前配置不支持泳道，用 Epic 过滤。日常看同一主板，通过 Assignee 过滤个人工作，不设四个彼此隔离的板。
- 推荐过滤：我的任务、Must、W11 demo、Blocked、Shared。若支持 JQL，分别使用 `assignee = currentUser()`、`labels = moscow-must`、`labels = demo-w11`、`Flagged = Impediment`、`labels = shared`，在当前项目范围内应用。
- 发布版本：`v0.1-w11-prototype` 与 `v0.2-w12-core`；若无版本字段，用标签替代。每个 sprint review 保存看板状态、演示记录及测试证据。

## 6. Updated backlog — English cards

Updated on 2026-10-09. The authoritative card descriptions, user stories, deadlines, assignees, prerequisites, acceptance criteria, and test methods are in [Jira Cards B01–B20](Jira_Cards_B01-B20.en.md). The [CSV](Jira_Starter_Backlog.csv) contains matching content for import.

| ID | Title | Assignee | Deadline | Sprint | Prerequisites |
| --- | --- | --- | --- | --- | --- |
| B01 | Define shared agent contracts, domain schemas, and requirement mappings | Jiaheng | 2026-10-10 | S1 | None |
| B02 | Set up the runnable web application and local database | Jason | 2026-10-10 | S1 | None |
| B03 | Create resettable supplier, traveller, and disruption fixtures | Jason | 2026-10-11 | S1 | B01, B02 |
| B04 | Implement deterministic pricing and itinerary constraint validators | Moore | 2026-10-12 | S1 | B01, B03 |
| B05 | Persist and display linked agent execution traces | wrd | 2026-10-12 | S1 | B01, B02 |
| B06 | Capture, confirm, and route traveller and supplier requests | Jiaheng | 2026-10-15 | S2 | B01, B02, B03, B05 |
| B07 | Enforce membership limits and protected case access | Jiaheng | 2026-10-16 | S2 | B03, B04, B06 |
| B08 | Validate supplier offers and calculate approved selling prices | Jason | 2026-10-16 | S2 | B03, B04, B05, B10 |
| B09 | Generate a complete itinerary from approved supplier offers | Moore | 2026-10-18 | S2 | B04, B05, B07, B08, B10 |
| B10 | Build proposal review and human approval controls | wrd | 2026-10-14 | S1 | B01, B02, B04, B05 |
| B11 | Integrate the four-agent workflow and freeze the Week 11 demo | Jason | 2026-10-21 | S2 | B06, B07, B08, B09, B10, B12 |
| B12 | Investigate a cancellation and propose a validated recovery | wrd | 2026-10-20 | S2 | B06, B08, B09, B10 |
| B13 | Compare feasible itineraries in Comfort, Value, and Budget modes | Moore | 2026-10-23 | S3 | B09 |
| B14 | Create confirmed plan revisions and compare immutable versions | Moore | 2026-10-25 | S3 | B06, B07, B09, B13 |
| B15 | Investigate complaints and prepare reviewed resolution recommendations | wrd | 2026-10-26 | S3 | B06, B08, B09, B10 |
| B16 | Evaluate supplier-based campaigns and record human approval | Jason | 2026-10-27 | S3 | B08, B10 |
| B17 | Apply paid route-map access, advertising rules, and member-offer eligibility | Jiaheng | 2026-10-28 | S3 | B07, B08, B09, B16 |
| B18 | Handle dependency failures and make manual retries safe | Jason | 2026-10-30 | S4 | B11 |
| B19 | Run release regression scenarios and record acceptance evidence | wrd | 2026-11-02 | S4 | B11, B13, B14, B15, B16, B17, B18 |
| B20 | Finalize setup instructions, model alignment, and contribution records | Moore | 2026-11-04 | S4 | B19 |

## 7. Acceptance and user stories

All 20 cards, including engineering Tasks, now include an English user story and explicit acceptance criteria. See the detailed card document rather than maintaining duplicate descriptions here.

## 8. Revised schedule and capacity

B16 and B17 move from S4 to S3 and finish on 27 and 28 October, respectively. S4 focuses on reliability, regression, and delivery. Estimates remain 126 hours: S1 34, S2 44, S3 32, S4 16. Assignee totals remain Jiaheng 26, Moore 30, wrd 32, Jason 38 before the existing six-hour support allocation to Jiaheng; effective totals are 32, 30, 32, and 32 hours. B06 intake preparation starts during S1. Prerequisites are explicit planning IDs, not actual Jira keys.

## 9. Ready、Done 与卡片模板

**Definition of Ready：**角色和价值清楚；AC 可验证；有测试数据；owner/reviewer、估计、依赖、MoSCoW 和 UC/Req 已填写；没有未解决的关键接口问题。大任务先拆小，再进 sprint。

**统一 Definition of Done：**

1. 该卡所有 AC 达成，成功与相关失败路径已检查。
2. 功能已集成到共享应用，并由另一成员 review。
3. 相关自动/手工测试有结果及证据；LLM 文案不要求逐字固定。
4. 该卡涉及的 trace、错误、审批与权限遵循共享规则。
5. 需求/模型或接口变更已同步；PR/commit、截图或 trace 关联 Jira。
6. 可在共享演示环境复现，没有该卡引入的阻塞缺陷。

单项写完代码只能进入 Review。全组系统可演示是 release 验收条件，不替代单卡 DoD。

```text
Summary:
Story: As a [user], I want [goal], so that [reason].
Req / UC:
Scope / exclusions:
Acceptance criteria:
- Given ... When ... Then ...
Definition of Done: 统一 DoD + 本卡具体完成条件
Test method / fixtures:
Assignee / Reviewer:
Epic / Sprint / MoSCoW / Estimate:
Dependencies:
Evidence: PR / commit / test result / screenshot / trace
```

## 10. Lab 会议和日常节奏

| Ceremony | 节奏/时长 | 具体产出 |
| --- | --- | --- |
| Sprint Planning | 每周四，25–30 分钟 | sprint goal、实际容量、Ready stories、依赖和 assignee |
| Daily Stand-up | 每个工作日 5–10 分钟，可异步 | 已完成、今天做什么、阻碍；更新 Jira；不在会上长时间调试 |
| Sprint Review | 每周三 20–30 分钟，周四 lab 给 tutor 展示 | 从可运行软件出发检查 AC，记录反馈和 backlog 调整 |
| Retrospective | Review 后 10–15 分钟 | 一件继续、一件停止、一件改进；下一 sprint 验证改进是否奏效 |

首次 stand-up 可以说“Stage 1 已完成哪些模型；今天准备实现什么；接口/LLM/数据有什么阻碍”。不要预先编造已完成工作。每周轮换会议主持人；功能范围和验收由全组确认。

## 11. 演示脚本与风险处置

### W11 建议演示（约 6–8 分钟，课程要求优先）

1. 30 秒说明四 Agent 及模拟范围。
2. 2 分钟输入一条已准备但真实处理的 Free Member 请求，展示确认、会员、报价和完整行程。
3. 1 分钟展示超预算/会员超限的规则拒绝及原因。
4. 2 分钟注入交通取消，展示 Exception→Supplier→Planning 的恢复建议。
5. 1 分钟展示受限建议等待人工决定；批准/拒绝后由 Operations 处理回复。
6. 30 秒展示同一 case 的 trace；各成员解释自己模块和一项测试。

### W12 回归三套场景

- A 正常规划：Free/Paid、Comfort/Value/Budget、修改与版本、路线图/广告权限。
- B 异常/投诉：取消有替代、无解升级、投诉缺证据、补偿等待审批。
- C 供应商/营销：非法或过期报价、最低差价失败、活动超预算、修改后重新审批、带来源的模拟响应。

| 风险/触发条件 | 处理 |
| --- | --- |
| W9 接口尚未稳定 | 暂停新增业务字段，四人用同一 JSON fixture 联调；先解阻公共接口 |
| LLM 配置/联网不稳定 | W9 先验证一次真实调用；固定输入和结构化输出；离线 fixture 模式明确标注；真实 Agent 路径也保存证据 |
| W10 中期还没有一条完整规划 | 暂停 Should/Could，缩减 UI 和数据量；两人合力处理主要阻塞，保持共享审批和硬约束 |
| W10 末恢复链仍未接通 | 只保留一种取消和一种恢复；不能把尚未实现的第四个 Agent 说成可演示 |
| 实际投入不足/新增评分项 | 调整容量和 backlog；保留 Must，先延后 Optional，再透明报告 Should 缺口 |
| 演示前出现破坏性修改 | 使用稳定标签和重置数据；新功能在独立分支 review 后合入 |

## 12. 本周 Jira 设置清单

- [ ] 创建一个 Scrum board、六个 Epic、S1–S4。
- [ ] 录入 B01–B20，设置 owner、label、估计、依赖和 AC。
- [ ] 把 S1 Ready 卡放入 sprint；未清楚的卡留在 backlog。
- [ ] 设置五列、Done 最右侧、blocked flag 处理规则和个人过滤。
- [ ] 定义统一 DoD，给每张 story 附测试方法。
- [ ] 完成首次 stand-up；记录实际阻碍。
- [ ] W9 Review 展示集成骨架；记录 tutor 反馈。
- [ ] W11 稳定原型和 W12 核心验收分别保存证据。

## CSV import notes

All 20 CSV cards are now written in English. Fields include Summary (title), Description, User Story, Due Date, Assignee, Reviewer, and Dependencies. Due dates use `yyyy-MM-dd` in Australia/Sydney. Map displayed assignee names to verified Jira accounts; map planning IDs to actual issue keys before creating dependency links. The CSV includes user stories and prerequisites in Description as well as separate columns. It does not indicate that any Jira issues have been created. See the English card document for full mapping guidance.

## Sources

- 本周 lab：`/Volumes/jiaheng/Data Memory/学校/USYD/研究生/2026sem2/5620/week9/ELEC5620-Lab-Note-8.pdf`（两页）。
- 本地项目基线：`README.zh-CN.md`、`docs/TripMate_AI_stage1_report.pdf`。
- 详细规则：保留报告中的 UC-05、UC-06、UC-07、UC-08。
- Jira 产品能力：上文链接的 Atlassian 官方文档（2026-10-08 核对）。
