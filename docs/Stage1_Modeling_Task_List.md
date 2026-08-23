# TripMate AI - Stage 1 图表与模型任务清单

## 1. 文档用途

本文档只用于管理 Stage 1 的设计图表和系统模型任务。

四页左右的 Project Requirement 大纲见：

- [Project Requirement Four-Page Outline](Project_Requirement_4_Page_Outline.md)

评分依据：

- [ELEC5620 Project Stage 1 Marking Criteria](ELEC5620_Project_Stage_1_Marking_Criteria.pdf)
- [Project Requirement Example](Project_Requirement_Example.pdf)
- [ELEC5620 Project Description](Project%20Description.pdf)

## 2. 四人小组必须遵守的规则

### 2.1 小组共同任务

四名成员都必须参与小组模型，并在报告中注明各自完成的部分或贡献比例。

### 2.2 个人任务

评分标准中带星号的项目属于个人任务。四名成员每人至少完成：

- 1 项 Ad hoc Requirement。
- 1 份 Use Case Specification。
- 1 张 Activity Diagram。
- 1 张 Interaction Diagram。
- 1 张 State Machine Diagram。

每个人的 Activity、Interaction 和 State Machine Diagram 必须基于其本人负责的 Ad hoc Requirement 和对应 Use Case Specification。

### 2.3 四人小组最低数量

| 个人成果 | 最低总数 | 分配方式 |
| --- | ---: | --- |
| Ad hoc Requirement | 4 | 每人 1 项 |
| Use Case Specification | 5-10 | 项目采用 7 个，每人至少负责 1 个 |
| Activity Diagram | 4 | 每人 1 张 |
| Interaction Diagram | 4 | 每人 1 张 |
| State Machine Diagram | 4 | 每人 1 张 |

## 3. 需要建模的业务范围

| 业务编号 | 业务范围 | 主要角色 | 对应用例 |
| --- | --- | --- | --- |
| BIZ-01 | 获客、营销、Lead 与客服前台 | Operations Agent | UC-05 |
| BIZ-02 | 免费/付费会员、行程限制、广告与高级功能 | Operations Agent | UC-07 |
| BIZ-03 | 供应商资源、协议价格、条款和差价 | Supplier Partnership Agent | UC-06 |
| BIZ-04 | 交通、住宿、活动组合和旅行方案比较 | Travel Planning Agent | UC-01、UC-02 |
| BIZ-05 | 行中复查和旅行异常恢复 | Customer Exception Agent | UC-03 |
| BIZ-06 | 投诉调查、解决和重新开启 | Customer Exception Agent | UC-04 |
| BIZ-07 | Reviewer 检查和人工审批 | Reviewer/Guardrail、Operator | 支持全部用例 |
| BIZ-08 | Trace、审计、反馈、成本和收入复盘 | Operator、Platform | 支持全部用例 |

## 4. 总任务清单

| ID | 成果 | 要求 | 分值 | 负责人 | 状态 |
| --- | --- | --- | ---: | --- | --- |
| M-01 | Project Requirement Documentation | 必须纳入 Stage 1 | - | 小组 | [ ] |
| M-02 | Ad hoc Requirements | 每人至少 1 项 | 0.5 | 个人 | [ ] |
| M-03 | Feature Diagram | 1 张完整小组图 | 1 | 小组 | [ ] |
| M-04 | Overall Use Case Diagram | 1 张完整小组图 | 1 | 小组 | [ ] |
| M-05 | Use Case Specifications | 总数 5-10，每人至少 1 份 | 2 | 个人后合并 | [ ] |
| M-06 | Elementary Structure Modeling | 详细 Class Diagram | 3 | 小组 | [ ] |
| M-07 | Complex Structure Modeling | Object、Collaboration、Structured Class | 3 | 小组 | [ ] |
| M-08 | Activity Diagrams | 四人各 1 张 | 1.5 | 个人 | [ ] |
| M-09 | Interaction Diagrams | 四人各 1 张 | 1.5 | 个人 | [ ] |
| M-10 | State Machine Diagrams | 四人各 1 张 | 1.5 | 个人 | [ ] |
| M-11 | Ad hoc Overall Design Diagram | 可选 | Optional | 小组 | [ ] |
| M-12 | Architecture Analysis and Design | 可选 | Optional | 小组 | [ ] |
| M-13 | Package Diagram | 可选 | Optional | 小组 | [ ] |
| M-14 | Deployment Diagram | 可选 | Optional | 小组 | [ ] |
| M-15 | Requirement-Model Traceability Matrix | 强烈建议 | - | 小组 | [ ] |
| M-16 | Contribution Record | 必须提供贡献证据 | - | 小组 | [ ] |

## 5. 用例基线

项目采用 7 个 Use Cases，符合评分标准要求的 5-10 个范围。

| ID | Use Case | 主要参与者 | 建议负责人 |
| --- | --- | --- | --- |
| UC-01 | Create and Compare a Travel Plan | Traveller、Operations Agent、Travel Planning Agent | Member B |
| UC-02 | Revise Preferences and Compare Versions | Traveller、Travel Planning Agent | Member B |
| UC-03 | Recheck Active Trip and Recover from Disruption | Traveller、Customer Exception Agent、Operator | Member C |
| UC-04 | Investigate and Resolve a Complaint | Traveller、Customer Exception Agent、Operator | Member C |
| UC-05 | Plan and Evaluate an Acquisition Campaign | Operator、Operations Agent、Reviewer | Member A |
| UC-06 | Source Supplier Inventory and Validate Margin | Operator、Supplier Partnership Agent、Travel Planning Agent | Member D |
| UC-07 | Enforce Membership and Premium Access | Traveller、Operations Agent | Member A |

每份 Use Case Specification 应包含：

1. ID、名称和作者。
2. Goal。
3. Primary Actor 和 Supporting Actors。
4. Preconditions。
5. Trigger。
6. Main Success Scenario。
7. Alternative Flows。
8. Error/Exception Flows。
9. Postconditions。
10. Business Rules。
11. 使用的数据和工具。
12. Human Approval 条件。
13. Acceptance Criteria。
14. 关联 Requirement 和 Diagram ID。

## 6. 小组共同模型

### 6.1 M-03 Feature Diagram

绘制 1 张覆盖整个 TripMate AI 的 Feature Diagram。

顶层 Feature 建议包括：

1. Operations and Customer Service。
2. Membership and Monetisation。
3. Supplier Partnerships。
4. Travel Planning。
5. Customer Exception Handling。
6. Human Oversight and Guardrails。
7. Platform, Data, and Audit。

必须表达：

- Mandatory、Optional 和 Alternative Features。
- Comfort、Value 和 Budget 三种旅行模式。
- 免费会员最多同时两条行程、每条最多五天。
- 付费会员去广告、不受免费版限制并拥有地图路线功能。
- 供应商差价、会员订阅和免费用户广告三种收入来源。
- 适合附着在 Feature 上的 Non-functional Requirements。

完成标准：

- [ ] 一张图覆盖完整产品。
- [ ] 每个 Feature 能追踪到 Requirement ID。
- [ ] 四名成员的贡献均有记录。

### 6.2 M-04 Overall Use Case Diagram

外部 Actors：

- Free Traveller。
- Paid Traveller。
- Human Founder/Operator。
- Large Tourism Supplier。
- Travel/Weather/Map Data Provider。
- Advertising Channel。

主要 Use Cases：UC-01 至 UC-07。

支持型 Use Cases：

- Validate Membership。
- Retrieve Supplier Offers。
- Validate Constraints and Budget。
- Calculate Price and Margin。
- Review Proposal。
- Request Human Approval。
- Record Trace。

完成标准：

- [ ] 有清楚的 System Boundary。
- [ ] 所有主要用户和外部系统均已出现。
- [ ] `include` 和 `extend` 使用正确。
- [ ] 图中用例与 7 份文字规格一致。

### 6.3 M-06 Elementary Structure Modeling - Class Diagram

建议按以下领域组织类：

**用户与会员**

- Customer。
- MembershipPlan。
- Subscription。
- Entitlement。
- Advertisement。

**Agent 与控制**

- Agent Interface/Base Class。
- OperationsAgent。
- TravelPlanningAgent。
- CustomerExceptionAgent。
- SupplierPartnershipAgent。
- Reviewer/Guardrail。
- HumanApproval。
- AgentExecutionLog。

**供应商与商业**

- Supplier。
- SupplierAgreement。
- SupplierOffer。
- TravelProduct/Resource。
- PriceBreakdown。
- MarginRecord。

**旅行规划**

- TravelRequest。
- ItineraryVersion。
- TripLeg/TransportOption。
- AccommodationOption。
- Activity。
- SimulatedOrder。

**异常与运营**

- DisruptionEvent。
- ExceptionCase。
- CompanyPolicy。
- MarketingCampaign。
- Lead。
- CustomerFeedback。
- CostRecord。

Class Diagram 必须正确使用：

- Generalisation。
- Composition。
- Aggregation。
- Interface/Realisation。
- Association 和 Role Name。
- Multiplicity。

重点关系：

- Customer 拥有 Membership/Subscription，并可创建多个 TravelRequests。
- TravelRequest 拥有一个或多个 ItineraryVersions。
- ItineraryVersion 组合 TripLeg、Accommodation 和 Activity。
- Supplier 通过 SupplierAgreement 提供多个 SupplierOffers。
- PriceBreakdown 分别记录 Supplier Cost、Customer Price、Fees 和 Margin。
- ExceptionCase 关联到受影响的 Itinerary/Order、Evidence、Policy 和 Approval。

### 6.4 M-07 Complex Structure Modeling

为降低 3 分结构建模部分的失分风险，建议完成以下三张图。

#### M-07A Object Diagram

使用具体的 Sydney-to-Melbourne 场景，展示：

- Customer 实例。
- MembershipPlan 实例。
- TravelRequest 实例。
- SupplierOffer 实例。
- ItineraryVersion 实例。
- PriceBreakdown 实例。
- ExceptionCase 和 HumanApproval 实例。

实例值应包含预算、供应商成本、客户售价、差价和状态。

#### M-07B Collaboration/Communication Diagram

展示旅行方案生成中的对象协作：

- Customer Web UI。
- Operations Agent。
- Membership Tool。
- Travel Planning Agent。
- Supplier Partnership Agent。
- Search/Validation Tools。
- Reviewer/Guardrail。
- Human Operator。

#### M-07C Structured Class/Composite Structure Diagram

展示运行时内部结构和接口：

- Application API/Orchestrator。
- 四个 Business Agents。
- Reviewer/Guardrail。
- Tool Adapters。
- Data Repositories。
- Trace Store。
- Human Approval Queue。

## 7. 四人个人模型分工

### 7.1 Activity Diagrams

| ID | 业务流程 | 负责人 | 必须出现的流程 |
| --- | --- | --- | --- |
| AD-01 | 获客、客户接待与会员校验 | Member A | Campaign/Lead、请求、免费/付费判断、两条/五天限制、澄清或分流 |
| AD-02 | 完整旅行规划与比较 | Member B | 收集限制、获取资源、过滤、评分、验证、Review、展示、修改/确认 |
| AD-03 | 异常恢复与投诉处理 | Member C | 事件/投诉、证据、严重度、恢复/解决、审批/升级、关闭/重开 |
| AD-04 | 供应商资源与差价验证 | Member D | 导入、标准化、库存/条款、差价、Review、批准/拒绝 |

每张 Activity Diagram 必须：

- [ ] 对应负责人自己的 Ad hoc Requirement 和 Use Case。
- [ ] 使用 Initial/Final Node、Action、Decision、Merge 和 Guard。
- [ ] 使用 Swimlanes 区分 User、Agent、Tool 和 Operator。
- [ ] 包含正常、失败和人工升级流程。

### 7.2 Interaction Diagrams

优先使用 Sequence Diagram。

| ID | 运行场景 | 负责人 | 主要 Lifelines |
| --- | --- | --- | --- |
| SD-01 | 获客、接待和会员校验 | Member A | Customer、Operations Agent、Entitlement Service、Lead Service、Travel Planning Agent |
| SD-02 | 方案生成、供应商资源和确认 | Member B | Customer、Operations Agent、Travel Planning Agent、Supplier Partnership Agent、Tools、Reviewer |
| SD-03 | 异常恢复或投诉解决 | Member C | Customer/Event Source、Customer Exception Agent、Order/Policy Tools、Travel Planning Agent、Reviewer、Operator |
| SD-04 | Supplier Offer 导入和差价审批 | Member D | Supplier、Supplier Partnership Agent、Inventory Adapter、Margin Tool、Reviewer、Operator、Repository |

每张 Interaction Diagram 必须：

- [ ] Message 名称表达明确输入和输出。
- [ ] 适当使用 `alt`、`opt` 和 `loop`。
- [ ] 包含工具失败、Review 拒绝或 Human Approval 分支。
- [ ] 对应本人的 Ad hoc Requirement 和 Use Case。

### 7.3 State Machine Diagrams

| ID | Stateful Entity | 负责人 | 建议 States |
| --- | --- | --- | --- |
| SM-01 | Subscription/Membership | Member A | Free、UpgradePending、PaidActive、GracePeriod、Expired、Cancelled |
| SM-02 | TravelRequest/ItineraryVersion | Member B | Draft、InformationRequired、Planning、UnderReview、Proposed、Confirmed、Active、Superseded、Completed、Cancelled |
| SM-03 | ExceptionCase | Member C | Received、InformationRequired、Investigating、RecoveryProposed、ResolutionProposed、AwaitingApproval、AwaitingCustomer、Resolved、Reopened、Escalated |
| SM-04 | SupplierOffer | Member D | Imported、Normalising、UnderReview、Approved、Active、Stale、Suspended、Rejected、Expired |

每张 State Machine Diagram 必须：

- [ ] 每个 Transition 有明确 Event/Trigger。
- [ ] 需要时使用 Guard 和 Action。
- [ ] 包含失败、到期、取消、重开或重试路径。
- [ ] 不允许出现业务上不可能的状态转换。
- [ ] 对应本人的 Ad hoc Requirement 和 Use Case。

## 8. 可选模型

### 8.1 Ad hoc Overall Design Diagram

绘制一张方便 Tutor 快速理解的总体图，包含：

- Customer Web Interface。
- Operator Dashboard。
- 四个 Business Agents。
- Reviewer/Guardrail。
- Supplier/Data/Tool Integrations。
- Membership and Advertising Rules。
- Database and Trace Store。
- Human Approval Queue。

该图用于高层说明，不能替代正式 UML。

### 8.2 Architecture Analysis and Design

建议覆盖：

- Business Viewpoint。
- Logical Viewpoint。
- Process Viewpoint。
- Development Viewpoint。
- Deployment Viewpoint。

同时解释选择和放弃的方案，例如：

- 四个宽职责 Agent 与多个功能重叠 Agent。
- Deterministic Rules 与 LLM-only Calculation。
- Web/Streamlit Prototype 与完整移动应用。
- Simulated Supplier/Payment Flow 与真实系统集成。

### 8.3 Package Diagram

建议 Packages：

- `ui`
- `api`
- `agents.operations`
- `agents.travel_planning`
- `agents.customer_exception`
- `agents.supplier_partnership`
- `orchestration`
- `tools.travel`
- `tools.membership`
- `tools.commercial`
- `tools.exception`
- `guardrails`
- `domain`
- `data`
- `tracing`
- `tests`

### 8.4 Deployment Diagram

按照可能的 Stage 2 网页原型绘制：

- Customer/Operator Browser。
- Streamlit 或 Web Frontend。
- FastAPI/Application Service。
- Agent Orchestration Runtime。
- LLM API。
- SQLite Prototype Database。
- Simulated Supplier/Travel/Weather Services。
- Map Component。
- Trace/Log Store。

必须标明订票、支付、退款和供应商合同均为模拟流程。

## 9. 四人总分工表

| 成员 | Ad hoc Requirement | Use Cases | Activity | Interaction | State Machine | 主要小组模型职责 |
| --- | --- | --- | --- | --- | --- | --- |
| Member A | 获客、客户接待和会员 | UC-05、UC-07 | AD-01 | SD-01 | SM-01 | Feature Diagram 的运营/会员分支；Use Case Actors |
| Member B | 完整旅行规划 | UC-01、UC-02 | AD-02 | SD-02 | SM-02 | Class Diagram 的旅行领域；旅行规划 Collaboration |
| Member C | 客户异常处理 | UC-03、UC-04 | AD-03 | SD-03 | SM-03 | Exception Domain、Approval Flow、Edge Cases |
| Member D | 供应商资源和盈利 | UC-06 | AD-04 | SD-04 | SM-04 | Supplier/Commercial Domain、Object Diagram、Margin Evidence |

将 Member A-D 替换为真实姓名，并记录每人在所有小组模型中的具体部分或贡献比例。

## 10. 建议完成顺序

1. 确认四页 Project Requirement 和统一术语。
2. 完成四项 Ad hoc Requirements 和 UC-01 至 UC-07。
3. 完成 Feature Diagram 和 Overall Use Case Diagram。
4. 完成综合 Class Diagram。
5. 四名成员分别完成 Activity、Interaction 和 State Machine Diagram。
6. 基于同一套 Classes 和 Operations 完成 Object、Collaboration 和 Structured Class Diagram。
7. 有时间再完成 Architecture、Package 和 Deployment Diagram。
8. 完成 Requirement-Model Traceability Matrix。
9. 完成个人贡献记录和跨模型一致性检查。

## 11. 一致性检查清单

- [ ] 所有文档统一使用四个 Business Agent 名称。
- [ ] Reviewer/Guardrail 被视为横向控制组件，而不是重叠的客服 Agent。
- [ ] 每个 Use Case 都出现在 Overall Use Case Diagram 中。
- [ ] 每位成员的三类个人图均能追踪到本人的 Ad hoc Requirement 和 Use Case。
- [ ] Sequence/Collaboration Messages 与 Class Operations 一致。
- [ ] State 名称与领域类中的状态字段一致。
- [ ] 免费会员限制始终为同时两条行程、每条最多五天。
- [ ] 付费会员无广告并包含地图路线。
- [ ] 广告不会影响硬性限制和推荐排序。
- [ ] Supplier Cost、Customer Price 和 Margin 始终分开表示。
- [ ] 真实订票、支付、退款、赔偿和供应商合同保持在原型范围之外。
- [ ] 高风险、法律、安全、供应商和较大金额操作均有 Human Approval。
- [ ] 每张图包含 ID、标题、作者、版本和关联 Requirement/Use Case ID。
- [ ] 每张小组图记录四名成员的工作部分或贡献比例。

## 12. 最终提交检查

- [ ] 四页 Project Requirement Documentation 已完成。
- [ ] 4 项个人 Ad hoc Requirements 已完成。
- [ ] 1 张完整 Feature Diagram 已完成。
- [ ] 1 张完整 Overall Use Case Diagram 已完成。
- [ ] 7 份 Use Case Specifications 已完成，每人至少负责 1 份。
- [ ] 详细 Class Diagram 已完成。
- [ ] Object、Collaboration 和 Structured Class Diagrams 已完成。
- [ ] 4 张 Activity Diagrams 已完成，每人 1 张。
- [ ] 4 张 Interaction Diagrams 已完成，每人 1 张。
- [ ] 4 张 State Machine Diagrams 已完成，每人 1 张。
- [ ] Optional Models 已根据时间决定是否完成。
- [ ] Requirement-Model Traceability Matrix 已完成。
- [ ] 四人贡献表已完成。
- [ ] 图表术语、Requirement IDs 和 Use Case IDs 已统一。
