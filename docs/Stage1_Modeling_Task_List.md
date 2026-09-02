# TripMate AI - Stage 1 计划

本文档是 Stage 1 的唯一执行计划，只说明分工、评分项、完成顺序和检查标准。项目介绍见 [README](../README.zh-CN.md)，详细功能描述以[当前 Project Requirement](https://unisydneyedu-my.sharepoint.com/:w:/r/personal/jguo9172_uni_sydney_edu_au/_layouts/15/doc.aspx?sourcedoc=%7Bdb7e1c58-8a31-419c-a0cf-9058e8145514%7D&action=edit)为准。

## 1. Stage 1 目标

- **截止日期：** 2026 年 9 月 24 日
- **评分：** Report 15 分、Video Presentation 5 分、Individual Interview 10 分

最终提交需要形成一条一致的主线：Project Requirement → Use Case → Architecture → Model。所有材料都应说明一名 Human Founder/Operator 如何监督四个协作式 AI Agent 运营旅行服务。

Stage 1 提交包包括：

- Project Requirement Documentation。
- 必交的小组模型和个人模型。
- Requirement-to-Model Traceability。
- 不超过 8 分钟的视频。
- 清晰的个人贡献记录。
- 每位成员的 Interview 准备。

## 2. 信息来源与维护方式

内容不一致时按以下顺序处理：

1. [当前 Project Requirement](https://unisydneyedu-my.sharepoint.com/:w:/r/personal/jguo9172_uni_sydney_edu_au/_layouts/15/doc.aspx?sourcedoc=%7Bdb7e1c58-8a31-419c-a0cf-9058e8145514%7D&action=edit)定义产品、角色、Core Features 和 Optional Features。
2. [Stage 1 Marking Criteria](ELEC5620_Project_Stage_1_Marking_Criteria.pdf)定义评分项以及个人/小组任务规则。
3. 本计划把前两项转化为具体工作。
4. README 只负责项目总览，不重复本计划。

Project Requirement 发生变化时，应同时更新对应的 Requirement ID、Use Case、模型和 Traceability 记录。

## 3. 四个 Agent 的分工

小组共四人，每人端到端负责一个业务 Agent，同时参与所有小组模型。

| 方向 | 负责范围 | Use Cases | 个人模型主线 |
| --- | --- | --- | --- |
| Operations Agent | 获客、前台、意图收集、会员校验和分流 | UC-05、UC-07 | UC-05 |
| Travel Planning Agent | 完整行程、约束、比较和修改 | UC-01、UC-02 | UC-01 |
| Customer Exception Agent | 异常恢复、投诉、证据和升级 | UC-03、UC-04 | UC-03 |
| Supplier Partnership Agent | 供应商资源、库存条款、价格和差价 | UC-06 | UC-06 |

“个人模型主线”把同一成员的 Ad hoc Requirement、Use Case Specification、Activity Diagram、Interaction Diagram 和 State Machine 串在一起。额外的 Use Case Specification 仍由对应 Agent 负责人完成。

最终确认后补全四人姓名：

| Member | Agent | 小组模型贡献 |
| --- | --- | --- |
| Jiaheng | Operations Agent | 按模型记录 |
| Moore | Travel Planning Agent | 按模型记录 |
| 待补充 | Customer Exception Agent | 按模型记录 |
| 待补充 | Supplier Partnership Agent | 按模型记录 |

## 4. 按 Agent 组织的需求基线

每位成员至少负责两个 Core Features 和一个 Optional Feature。下列 ID 只用于连接 Requirement 与模型，不另写一套重复的需求文档。

| Agent | Core Features | Optional Feature 候选 |
| --- | --- | --- |
| Operations | OPS-01 Campaign 与 Lead；OPS-02 前台接待与分流；OPS-03 Membership 校验 | OPS-O1 Campaign 实验或留存分析 |
| Travel Planning | PLAN-01 请求与约束收集；PLAN-02 完整行程生成；PLAN-03 方案比较与修改 | PLAN-O1 目的地/政策 RAG 或更多实时数据 |
| Customer Exception | EXC-01 异常恢复；EXC-02 投诉调查与解决 | EXC-O1 主动异常预测或通知 |
| Supplier Partnership | SUP-01 Supplier Offer 导入与校验；SUP-02 定价与差价计算 | SUP-O1 Supplier Reliability Scorecard 或需求驱动的合作建议 |

四个方向共用以下控制：

- Reviewer/Guardrail 检查约束、证据、计算、时间冲突、会员规则、价格、差价和政策。
- Human Founder/Operator 审批重要的财务、合同、法律、安全、外部发布和低置信度操作。
- Trace 连接请求、Agent 决策、Tool Result、Plan Version、Approval 和最终结果。

## 5. Use Case 基线

小组采用 7 个 Use Cases，符合总数 5-10 个的要求。

| ID | Use Case | Owner | 主要结果 |
| --- | --- | --- | --- |
| UC-01 | Create and Compare a Travel Plan | Travel Planning | 合格的完整行程选项 |
| UC-02 | Revise Preferences and Compare Versions | Travel Planning | 校验后的新行程版本 |
| UC-03 | Recheck an Active Trip and Recover from Disruption | Customer Exception | 校验后的恢复方案 |
| UC-04 | Investigate and Resolve a Complaint | Customer Exception | 解决方案或人工升级 |
| UC-05 | Acquire, Receive, and Route a Customer | Operations | 合格 Lead 或正确分流的 Case |
| UC-06 | Source Supplier Inventory and Validate Margin | Supplier Partnership | 通过审核的 Offer 和 Price Breakdown |
| UC-07 | Enforce Membership and Premium Access | Operations | 允许请求或解释会员限制 |

每份 Use Case Specification 包含 Goal、Actors、Trigger、Preconditions、Main Flow、Alternative/Error Flows、Postconditions、Business Rules、Tools/Data、Approval Conditions、Acceptance Criteria，以及关联的 Requirement/Diagram ID。

## 6. 评分交付物

### 6.1 小组任务

四名成员都要参与每项小组任务，并在提交中写明各自完成的部分或贡献比例。

| ID | Deliverable | 完成标准 | 分值 |
| --- | --- | --- | ---: |
| G-01 | Project Requirement Documentation | 包含当前 Agent、用户、Core/Optional Features 和成员分工 | 必交 |
| G-02 | Feature Diagram | 一张完整 Feature Model，包含适合的 Non-functional Requirements | 1 |
| G-03 | Overall Use Case Diagram | Actors、7 个 Use Cases、System Boundary 和正确的 include/extend | 1 |
| G-04 | Class Diagram | 正确使用 Generalisation、Composition、Aggregation、Interface、Multiplicity 和 Role Name | 3 |
| G-05 | Complex Structure Models | 用 Object、Collaboration/Communication 和 Structured/Composite Class 表达运行时结构 | 3 |
| G-06 | Traceability Matrix | Requirement 连接到 Feature、Use Case、Diagram、Acceptance Evidence 和 Owner | 支持材料 |
| G-07 | Contribution Record | 小组贡献和个人所有权清晰 | 必交 |

Ad hoc Overall Design、Architecture Analysis/Design、Package 和 Deployment Diagram 均为可选；只有在确实能解释设计时再加入。

### 6.2 个人任务

每位成员围绕自己 Agent 的个人模型主线独立完成：

| ID | Deliverable | 最低要求 |
| --- | --- | --- |
| I-01 | Ad hoc Requirement | 1 项，与负责的 Agent 相关 |
| I-02 | Use Case Specification | 至少 1 份；小组总数保持 5-10 |
| I-03 | Activity Diagram | 1 张行为模型 |
| I-04 | Interaction Diagram | 1 张，优先使用 Sequence Diagram |
| I-05 | State Machine Diagram | 1 张生命周期模型 |

这五项必须描述同一业务行为。例如，Operations 负责人不能用 Campaign 分流作为 Ad hoc Requirement，却提交 Supplier Offer 的 State Machine。

## 7. 个人图分配

| Agent | Activity Diagram | Interaction Diagram | State Machine |
| --- | --- | --- | --- |
| Operations | AD-01 获客、接待、会员校验与分流 | SD-01 客户接待与分流 | SM-01 Lead/Customer Case 生命周期 |
| Travel Planning | AD-02 生成、校验、排序和修改方案 | SD-02 行程生成与 Review | SM-02 ItineraryVersion 生命周期 |
| Customer Exception | AD-03 发现、调查、恢复或升级 | SD-03 异常/投诉处理 | SM-03 ExceptionCase 生命周期 |
| Supplier Partnership | AD-04 导入、校验、定价和审批 Offer | SD-04 Supplier Offer 与差价 Review | SM-04 SupplierOffer 生命周期 |

图表要求：

- Activity Diagram 使用 Swimlanes，包含正常流程、一个有意义的失败和 Human Escalation。
- Sequence Diagram 的 Message 要表达输入和输出，仅在场景需要时使用 `alt`、`opt` 或 `loop`。
- State Machine 使用业务状态和事件，不描述页面跳转。
- 每张图标明 Diagram ID、Author、Requirement ID 和 Use Case ID。

## 8. 小组模型范围

### Feature Diagram

采用七个顶层区域：Operations and Customer Service、Membership and Monetisation、Supplier Partnerships、Travel Planning、Customer Exception Handling、Human Oversight and Guardrails、Platform/Data/Audit。表达 Mandatory、Optional 和 Alternative Feature，避免把长段文字塞进图中。

### Overall Use Case Diagram

Actors 包括 Free Traveller、Paid Traveller、Human Founder/Operator、Tourism Supplier、Travel/Weather/Map Data Provider 和 Advertising Channel。使用 7 个基线 Use Cases，并复用少量 include 行为，例如 Validate Membership、Retrieve Offers、Validate Constraints、Review Proposal、Request Approval 和 Record Trace。

### Class Diagram

覆盖 Use Cases 实际使用的领域对象：

- Customer、MembershipPlan、Subscription 和 Entitlement。
- 四个 Agent、Reviewer/Guardrail、HumanApproval 和 AgentExecutionLog。
- TravelRequest、ItineraryVersion、TripLeg、Accommodation、Activity 和 PriceBreakdown。
- Supplier、SupplierAgreement、SupplierOffer 和 TravelProduct。
- DisruptionEvent、ExceptionCase、Evidence、Policy、Campaign、Lead 和 Feedback。

### Complex Structure Models

三个运行时视图统一使用 Sydney-to-Melbourne 场景：

- Object Diagram：具体的 Customer、Membership、Request、Offers、ItineraryVersion、PriceBreakdown 和 Exception/Approval 实例。
- Collaboration/Communication Diagram：UI、Orchestrator、Agents、Tools、Reviewer 和 Operator 的协作。
- Structured/Composite Class Diagram：运行时部件、Ports/Interfaces、Repositories、Trace Store 和 Approval Queue。

## 9. 完成顺序

| 目标日期 | 结果 |
| --- | --- |
| 9 月 2-5 日 | 确认四个 Agent 负责人，冻结 Requirement IDs 和 7 个 Use Cases |
| 9 月 6-11 日 | 完成各 Agent 的 Ad hoc Requirement、Specifications 和三张个人图 |
| 9 月 12-16 日 | 完成 Feature、Overall Use Case、Class 和 Complex Structure Models |
| 9 月 17-20 日 | 整合 Report 与 Traceability Matrix，完成跨模型检查 |
| 9 月 21-23 日 | 录制并检查 Video，准备 Interview，核对贡献记录 |
| 9 月 24 日 | 提交 Stage 1 |

依赖顺序：

1. 确认 Agent 边界和 Requirement IDs。
2. 定稿 Use Case Specifications。
3. 按每人的主线完成个人行为模型。
4. 汇总小组结构模型和运行时模型。
5. 基于最终模型制作 Traceability 和 Presentation。

## 10. 一致性检查

提交前由全组统一检查：

- Requirement、7 个 Use Cases、Diagrams 和 Video 使用相同的四个 Agent 名称和职责。
- 每位成员至少负责两个 Core Features 和一个 Optional Feature。
- 每位成员的 Ad hoc Requirement、Use Case Specification、Activity、Interaction 和 State Machine 围绕同一业务行为。
- Class Diagram 包含行为图中使用的重要对象。
- Sequence Diagram 的 Message 能对应到设计中的 Operation、Tool 或 Responsibility。
- State 与 Use Case 的 Preconditions/Postconditions 一致。
- Membership 限制、Comfort/Value/Budget、Supplier Price/Margin、Reviewer 和 Human Approval 出现在相关位置。
- 每项评分材料标明 Author 或 Contribution Split。
- Video 不超过 8 分钟，每位成员都能解释自己的 Agent 和共享架构。

## 11. 提交清单

- [ ] 已包含当前 Project Requirement。
- [ ] G-02 至 G-05 完成且可读。
- [ ] 四套个人模型完整。
- [ ] Use Case Specifications 总数为 5-10。
- [ ] Traceability Matrix 中没有孤立的 Requirement 或 Diagram。
- [ ] Contribution Record 与仓库记录一致。
- [ ] Report/PDF 已完成视觉检查。
- [ ] Video 已上传 Canvas，并按需附 YouTube Link。
- [ ] 每位成员已准备 Interview。
