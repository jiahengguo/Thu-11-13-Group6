# TripMate AI：第 9–12 周实施计划与 Jira 看板设计

编制日期：2026-10-08。本文是实施建议，不是课程官方截止日期，也不表示功能已经实现。

## 1. 目标与依据

- 第 11 周：四个 Agent 在同一个可运行原型中完成可重复演示的业务闭环。
- 第 12 周：完成下述冻结的核心功能集合；可选功能按剩余容量选择，不追求全部实现。
- Week 9 / Laboratory 8 明确要求：使用 Jira；按 sprint 管理工作；举行 Planning、Daily Stand-up、Review、Retrospective；user story 使用 “As a [user], I want [goal], so that [reason].”；每条 story 定义 Definition of Done 和测试方式；用 MoSCoW 分类。
- 产品依据为仓库 README、Stage 1 计划、当前本地需求稿 `docs/diagrams/TripMate AI.md`、Operations 用例和 Supplier 需求。尚未核实在线 Project Requirement 或 Stage 2 评分标准。获得后应在 W9 检查遗漏，不据此擅自删减课程必交项。
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
| S3 / W11 Core Expansion | 10/22–10/28 | 展示 prototype，补齐比较/修改/投诉 | 10/22 lab 展示稳定版本；新修改保留旧版；投诉有证据及人工升级 |
| S4 / W12 Core Completion | 10/29–11/4 | 营销/付费功能、失败处理、评估和交付 | 核心 AC 清单、三套演示、已知问题及贡献记录；未完成项单列 |

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

必填：Summary、Description、Issue Type、Epic、Assignee、Sprint、MoSCoW label、Estimate、Acceptance Criteria、Test method、Req/UC IDs、Dependencies、Evidence。Jira 未提供的字段放进 Description 模板，不强求自定义字段。

- 标签：`moscow-must`、`moscow-should`、`moscow-could`、`moscow-would`，四选一；另加 `agent-ops` / `agent-plan` / `agent-exc` / `agent-sup` / `shared`；演示卡加 `demo-w11`。
- Jira Priority 表达处理紧急程度；MoSCoW 表达范围承诺。临近演示的阻塞 Bug 可以高优先级，不应自动把所有 Must 卡都标最高。
- 估计先用小时。Planning 确认后再用 1/2/3/5/8 story points 也可，但不要把 points 当工时，也不要父 story 和 sub-task 重复计入容量。
- 主板按 Epic 分组；若当前配置不支持泳道，用 Epic 过滤。日常看同一主板，通过 Assignee 过滤个人工作，不设四个彼此隔离的板。
- 推荐过滤：我的任务、Must、W11 demo、Blocked、Shared。若支持 JQL，分别使用 `assignee = currentUser()`、`labels = moscow-must`、`labels = demo-w11`、`Flagged = Impediment`、`labels = shared`，在当前项目范围内应用。
- 发布版本：`v0.1-w11-prototype` 与 `v0.2-w12-core`；若无版本字段，用标签替代。每个 sprint review 保存看板状态、演示记录及测试证据。

## 6. 初始 Backlog：20 张可录入卡片

下列编号是规划 ID，不是假称已经创建的 Jira key。Estimate 为初估小时；跨周 story 可拆分为各自可验收的小 story，不只为清空 sprint 而拆卡。Reviewer 按分工表默认安排。

| ID | Type / Epic | Summary | Owner | Sprint | MoSCoW | 小时 | 前置 |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| B01 | Task / PLAT | 共享接口、领域字段与需求映射 | Jiaheng | S1 | Must | 6 | 无 |
| B02 | Task / PLAT | 一键启动与应用骨架 | Jason | S1 | Must | 6 | 无 |
| B03 | Task / PLAT | 统一模拟数据与重置工具 | Jason | S1 | Must | 4 | B01 |
| B04 | Task / PLAT | 确定性约束及计算工具 | Moore | S1 | Must | 6 | B01 |
| B05 | Task / PLAT | 持久化 trace 与查询 | wrd | S1 | Must | 6 | B01、B02 |
| B06 | Story / OPS | 接待、补问、确认与路由 | Jiaheng | S2 | Must | 8 | B01、B02、B05 |
| B07 | Story / OPS | 行程会员规则与访问控制 | Jiaheng | S2 | Must | 6 | B03、B06 |
| B08 | Story / SUP | 报价导入、审查与差价计算 | Jason | S2 | Must | 8 | B03、B04、B10 |
| B09 | Story / PLAN | 生成完整可行行程 | Moore | S2 | Must | 8 | B04、B07、B08 |
| B10 | Story / PLAT | 共享 Reviewer 与人工审批工作台 | wrd | S1 | Must | 6 | B01、B02、B05 |
| B11 | Task / DEMO | 四 Agent 联调与统一界面 | Jason | S2 | Must | 6 | B06–B10、B12 |
| B12 | Story / EXC | 取消事件调查与恢复建议 | wrd | S2 | Must | 8 | B08、B09、B10 |
| B13 | Story / PLAN | 三种模式与可行方案比较 | Moore | S3 | Should | 6 | B09 |
| B14 | Story / PLAN | 确认后修改与版本对比 | Moore | S3 | Should | 6 | B09、B13 |
| B15 | Story / EXC | 投诉调查与解决建议 | wrd | S3 | Should | 6 | B06、B08、B10 |
| B16 | Story / SUP | 营销方案、预算检查与人工审批 | Jason | S4 | Should | 8 | B08、B10 |
| B17 | Story / OPS | 付费路线图、广告规则与优惠资格 | Jiaheng | S4 | Should | 6 | B07、B09、B16 |
| B18 | Task / PLAT | 失败提示、手动重试与重复请求保护 | Jason | S4 | Should | 6 | B11 |
| B19 | Task / DEMO | 演示回归与可追踪验收证据 | wrd | S4 | Should | 6 | B11、B13–B18 |
| B20 | Task / DEMO | 交付说明、模型同步与贡献记录 | Moore | S4 | Should | 4 | B19 |

初估合计 **126 小时**：Jiaheng 26、Moore 30、wrd 32、Jason 38。Jason 负担较高：建议 B11 的界面子任务由 Jiaheng 承担约 3 小时，B18 的权限/请求保护子任务由 Jiaheng 承担约 3 小时，主卡 assignee 仍负责整体验收。调整后约为 Jiaheng 32、Jason 32、Moore 30、wrd 32。S2 Operations 两张卡合计 14 小时；当周可用时间不足时，把 B06 的接待与确认部分提前到 S1，以可独立验收的 story 记录。

S1 34 小时、S2 44 小时、S3 18 小时、S4 30 小时。S3 留出的容量用于 W11 演示修复以及提前开发 B16/B17，明确纳入当周 planning，避免隐藏工作。B11 先用 stub 联调，Done 时必须 B12 等真实实现接入。B19 是最终回归汇总，不能替代每张功能卡自身的测试。

## 7. Story 文本、验收与测试

以下每张 Story 都继承统一 DoD，并附有自己的完成条件和测试方法。Task 的验收列在下一节。

### B06 — 接待、确认与路由（UC-05 / OPS-02）

**As a Traveller or Supplier, I want to confirm a structured request and have it routed to the right agent, so that my request is handled accurately.**

AC：请求缺字段时补问且不路由；确认后保存 Case 和来源，按请求类型分配 specialist；低置信度或 `humanRequestCount >= 2` 进入人工协助；specialist 输出经 Operations review 后才展示；失败不错误关闭 Case。

测试：分类/必填规则自动测试；手工跑 planning、complaint、supplier 三种输入及低置信度输入；截图确认和 routing trace。LLM 输出做结构与行为检查，不断言固定文案。

### B07 — 会员与权限（UC-07 / OPS-03）

**As a Traveller, I want an explained membership decision, so that I know whether my requested trip is permitted.**

AC：免费会员两条 Planned/Active 行程后拒绝新激活；超过五天拒绝，五天允许；日历天数为 end-start+1；规划前及输出后复查最新会员；无法验证返回 VerificationFailed；其他用户的 case/plan 不可读取，前端隐藏按钮不能代替后端检查。

测试：自动测试 1/2 条行程、5/6 天、会员变化、服务失败和跨用户访问；手工演示拒绝原因。

### B08 — 供应商报价（UC-06 / SUP-01、SUP-02）

**As an Operator, I want validated offers with reproducible prices and margins, so that planners use reliable commercial data.**

AC：保留原始来源和提取字段；缺字段、过期、零库存、不支持币种进入 RevisionRequired；按配置与两位小数计算 basePrice、sellingPrice、marginAmount；最低差价失败不能 Approved；仅 Approved 且未过期报价可用于规划；修订清除旧审批；受限条款等待人工决定。

测试：确定性价格/舍入/有效期测试；手工导入正常与非法报价；验证 LLM 不能改成本绕过差价规则。

### B09 — 完整行程（UC-01 / TP-01，旧 PLAN 编号待映射）

**As a Traveller, I want a complete feasible itinerary, so that transport, stays and activities fit my confirmed constraints.**

AC：交通、住宿、活动串联完整；预算、时间、接驳、库存和请求中适用的其他硬约束全部通过后才标为 feasible；总价等于组件和；每项资源带报价及证据引用；无解时列出失败约束，不自动放宽；经 Reviewer 后由 Operations 返回。

测试：自动检查预算、时间重叠、接驳不足、过期报价、总价；正常和无解场景端到端测试。

### B10 — Review 与审批（共享控制）

**As an Operator, I want to inspect reviewed proposals and record approval decisions, so that restricted commitments stay under human control.**

AC：规则失败阻止通过；提供 Approve / Request revision / Reject，未决定保持 AwaitingApproval；修改重要字段使旧审批失效并重新检查；保存失败不返回批准结果；待审批/拒绝的承诺不能由 Operations 输出为已批准。

测试：审批状态转换及后端权限自动测试；手工演示拒绝、修改再审和无回应；trace 链接到被审批版本。

### B12 — 异常恢复（UC-03 / EXC-01）

**As a Traveller with a disrupted trip, I want a validated recovery proposal, so that I can understand safe and feasible alternatives.**

AC：取消事件关联既有 Active itinerary 与证据；向 Supplier 获取替代资源、向 Planning 请求重规划；保留原约束并解释价格/时间变化；无替代、证据冲突或依赖失败时返回人工处理；受限承诺显式要求审批；仅产生建议，不执行真实改签/付款。

测试：一条取消且有替代、无替代、工具失败及需要审批四个场景；核对四个 Agent 的同一 correlationId。

### B13 — 比较模式（UC-01 / TP-01）

**As a Traveller, I want to compare feasible options in Comfort, Value or Budget mode, so that I can choose using consistent trade-offs.**

AC：至少一套测试数据能产生两条可行方案；三个模式仅改变可行候选排序；成本、时间、便利程度、证据和排除原因采用共同字段；不可行方案不能因模式或广告进入推荐。

测试：固定候选集上的排序/过滤测试；手工切换三种模式并核对差异。

### B14 — 修改和版本（UC-02 / TP-02）

**As a Traveller, I want to confirm a change and compare a new plan version, so that I understand its effect without losing the original plan.**

AC：未确认修改不发布新版本；成功后生成独立不可变版本，旧版不覆盖；展示资源、时间、价格及约束变化；再次运行会员/库存/价格/时间校验；修改无解时基线仍为当前版本。

测试：成功修改、未确认修改、无解修改；自动验证基线未变、版本 ID 不同与 price delta。

### B15 — 投诉（UC-04 / EXC-02）

**As a Traveller, I want an evidence-supported complaint recommendation, so that the operator can decide a fair response.**

AC：收集行程、服务记录、政策和供应商证据；缺证据通过 Operations 补问；法律/安全/低置信度升级；退款/补偿建议须审批；人工转交不标成投诉已解决；最终回复仍经 Operations。

测试：普通投诉、缺证据、补偿请求三个场景；检查审批阻断及案件状态。

### B16 — 营销（UC-08 / SUP-03）

**As an Operator, I want an evaluated campaign proposal based on approved offers, so that I can approve a credible plan within budget.**

AC：brief 包含目标、受众、渠道、日期及预算；仅引用合格报价；确定性计算模拟渠道成本；超预算或无证据声明不能通过；Approve/Revision/Reject 与版本绑定；预览不发布、不支出；模拟响应带 campaignId/source 转交 Operations。付费会员商业广告不得通过 review。

测试：预算恰好达标/超标、过期报价、修改后旧审批失效、付费广告目标、模拟响应来源。

### B17 — 付费权益（UC-07；UC-08/UC-06 联动）

**As a Paid Traveller, I want entitled route-map access and an ad-free interface, so that my membership benefits are applied consistently.**

AC：后端校验路线地图权限；付费无商业广告；免费广告清晰标注且不影响排序；路线图使用模拟路线点并可交互，无需实时地图 API；已批准优惠由 UC-07 判断资格、UC-06 重算价格和最低差价，不能叠加或改写基础报价。

测试：Free/Paid 两种身份访问；广告与排序检查；优惠过期、资格不符、优惠后差价不足。

## 8. 工程 Task 的完成条件与验证

| ID | 完成条件 | 验证方式 |
| --- | --- | --- |
| B01 | JSON 示例、接口、状态、错误、需求映射和 ownership 经四人确认 | 四个模块用同一示例读写，契约检查 |
| B02 | 干净环境按说明启动，前后端和数据存储可用，配置模板不含密钥 | 另一成员从新目录/干净环境复现 |
| B03 | 正常、非法报价、两种会员、取消、投诉、审批场景 fixture 可重置 | 连续重置两次结果一致，引用无断链 |
| B04 | 价格、预算、日历日期、时间冲突、库存、适用硬约束使用共享确定性工具 | 边界值与失败路径自动测试；记录未支持约束 |
| B05 | request→agent→tool→plan→review→approval→response 能关联并保存；重启后可查 | 查询一条完整 case，模拟保存失败，检查日志无密钥 |
| B11 | stub 被实际模块替换，页面和后端跑通新规划及恢复，稳定标签可复现 | 四人共同从重置数据完成完整演示；不手工改存储 |
| B18 | 超时/无效 LLM 输出/工具和保存失败可见；手动重试不重复创建审批或覆盖旧版 | 故障注入与重复请求测试；真实 LLM 与 fixture 模式标识清楚 |
| B19 | 三套脚本、需求到测试映射、结果与已知缺陷可查；所有 Must 通过 | 稳定版本连续两次演示，人工核对页面与 trace |
| B20 | 启动说明、模拟范围、状态/接口变化、模型与实现偏差、个人贡献完整 | 另一成员复现；四人核对需求映射及贡献证据 |

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

## CSV 使用说明

配套 `Jira_Starter_Backlog.csv` 是录入素材，不代表已在 Jira 创建。先建立 Epic 和 sprint；导入时将 Issue Type、Summary、Description、Labels 映射至对应字段。Suggested Owner 是显示名，必须映射到实际 Jira 账号；Planned Sprint、Epic Alias、Dependencies 和 Estimate Hours 为规划信息，可保留在描述或映射合适字段。不要把 B01 等规划 ID 当作现有 Jira issue key；导入后按实际 key 建立依赖。CSV 只含 20 张卡，Epic 另建。

## Sources

- 本周 lab：`/Volumes/jiaheng/Data Memory/学校/USYD/研究生/2026sem2/5620/week9/ELEC5620-Lab-Note-8.pdf`（两页）。
- 本地项目基线：`README.zh-CN.md`、`docs/Stage1_Modeling_Task_List.md`、`docs/diagrams/TripMate AI.md`。
- 详细规则：UC-05、UC-07 和 `docs/supplier/Supplier_Requirements.md`。
- Jira 产品能力：上文链接的 Atlassian 官方文档（2026-10-08 核对）。
