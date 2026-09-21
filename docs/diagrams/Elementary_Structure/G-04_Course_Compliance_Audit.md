# G-04 课程与项目需求核对记录

日期：2026-09-17。结论：当前模型的主要职责及 UML 关系可作为修订稿使用；仍有需求自身冲突和跨图命名待统一，不能宣称无条件全部通过。

## 1. 实际使用的依据

- 项目功能基线：`docs/TripMate AI.md`，重点核对 2.2–2.7、OPS-02/03、TP-01/02、EXC-01/02、SUP-01/02/03、UC-01–08。
- `docs/Project Description.pdf`：设计应支持未来实现，说明关键组件职责、关系和设计假设。
- `docs/ELEC5620_Project_Stage_1_Marking_Criteria.pdf` 第 1 页：Elementary Structure 为 3 分，要求详细设计时类图、generalization、composition、aggregation、interfaces、multiplicity。
- 课程根目录：`/Volumes/jiaheng/Data Memory/学校/USYD/研究生/2026sem2/5620`。
- Week 6 `5 Modeling Structure part 1.pdf`：第 19–22 页关联端角色与多重性；23–25 页泛化；28 页组合的删除语义；29 页共享聚合语义；32 页成员表示；34–35 页接口实现与使用；38 页约束；39–42 页 Agent 抽象、能力、协作与执行记录。检查了相关页的原图。
- Week 6 `ELEC5620-TUT-05.pdf`：第 19–25 页继承、组合/聚合、依赖、关系名、角色、可导航性、可见性；检查了相关关系示例原图。
- Week 6 `ELEC5620-Lab-Note-5.pdf`：以系统主要类、属性、方法及类间关系构建设计时模型。
- Week 7 `5 Modeling Structure part 2.pdf` 第 10–14 页、`ELEC5620-TUT-06.pdf` 第 12 页及 Laboratory 6：类图与运行时对象快照区别；本次不混入带具体值的对象实例。
- 已核对 SD-04 和 SM-04 的可编辑原件。其余成员的 sequence/state 原件不在当前目录，未作全组跨图通过的结论。
- 用户提供的学长截图用于学习三栏、黑白线条、清晰箭头、多重性与分层方式；其 Booking/Payment/Authentication 业务不能直接移入当前项目。
- 用户提供的 ChatGPT 分享链接本次读取失败；没有声称已读到分享记录。

## 2. 已实施的修正

| 原问题 | 当前处理 | 依据与影响 |
|---|---|---|
| drawio 将所有 HTML 内容作为泳道标题，文字离开类框；SVG 另画一套，掩盖错误 | 类名只放标题；属性、操作为原生子单元；分隔线独立；移动类框时成员随之移动 | Week 6 p32；Tutorial 类图规范 |
| 合并总览/详图后重复 createPlan、handleCase 等操作，很多无参数或返回类型 | 从详细候选清单恢复有类型的成员，每个操作单独一项，接口与实现签名一致 | Week 6 p34–35；Tutorial 可见性规范 |
| 多重性写成中部的“1 • 0..*” | 中部只显示关系名，数量标在两个关联端；不为泛化/实现标数量 | Week 6 p19–22 |
| 每个请求必须同时关联一个 Traveller 和一个 Supplier | 两个请求者端均改为 0..1，直接请求加 xor；活动反馈保留 sourceCampaignId | OPS-02、UC-05；避免错误的双请求者约束 |
| humanRequestCount 在 Traveller 上成为终身累计 | 移到 ExternalRequest，按本次请求统计 | OPS-02 的重复人工请求升级条件；计数范围是明确的设计解释 |
| 每个 CaseAssignment 同时强制关联 Agent 和 OperationsAgent | 删除重复协调关联，保留 Agent 关联，以 COORDINATOR 角色约束指定 OperationsAgent | 支持 coordinator / primary / supporting 三类分工 |
| 免费规则写成 active <= 2 | 明确 PLANNED + ACTIVE <= 2，旅行时长为含首尾日期的 5 天 | OPS-03、UC-07 |
| PlanComparison 只连“两个版本”，无法区分角色 | 分开 baseline 和 revision 两条关联，每端恰好一个版本；要求同一计划且两个版本不同 | TP-02、UC-02；关系名明确区分两种用途 |
| 一个 TravelPlan 只允许一个 CustomerCase 涉及 | CustomerCase 端改为 0..*，使创建、修订、异常等后续 Case 可涉及同一计划 | UC-01/02/03 |
| Draft 记录创建时即被要求有价格/验证/轨迹子项 | 相关历史/草稿下界设为 0；可行版本至少有一项等成熟状态要求用约束补充 | UC-06、SM-04 的 Draft 与失败路径；静态基数须容纳完整生命周期 |
| 省略确认请求、约束、验证记录后无法解释规划结果 | 恢复 TravelRequest、ConstraintSet、ValidationResult，并连接请求及版本 | TP-01/02、UC-01/02 |
| 省略营销 brief 和会员优惠规则 | 恢复 CampaignBrief、MemberOfferRule；保留会员层级、折扣、有效期、适用 offers | SUP-03、UC-08 与 UC-06/07 的折扣职责边界 |
| 三个抽象领域根类没有任何保留的具体子类 | ItineraryItem、TravelProduct、ExceptionIssue 改为带 kind/type 的具体类 | 明确选择简化模型；不假装省略的子类仍在实图中。Agent/Case 保持抽象和泛化 |
| 清空旧审核/批准可能被解释成删除历史 | 操作命名为 invalidateCurrentDecisions，明确保留旧记录 | UC-06 修订后重检、Agent Trace 历史要求 |
| 确定性服务没有供供应商校验使用的操作 | IConstraintValidationService/实现类补 validateOffer | SUP-01、UC-06；不能只提供 validatePlan |
| SVG 与 PNG 陈旧 | 同步重新生成 | PNG 为浏览预览，drawio 为可编辑交付 |

当前共 **48 个分类器、69 条关系**。具体成员及每条关联见 [当前模型清单](G-04_Current_Model.md)。

## 3. 保留的合理设计

- 四个业务 Agent 继承共同的 Agent，共享执行、审查、追踪能力；不把四个角色写成单独运行时对象。
- 五组接口/实现保留实线或虚线空心三角的正确方向：子类指向父类，实现类指向接口；使用者以虚线依赖接口。
- CaseAssignment 保存有状态、有时间的分配记录，适合普通关联实体；无需为了展示 association class 而强行改成虚线挂接的关联类。
- TravelPlan–ItineraryVersion、Version–Item、Request–ConstraintSet、Case–Assignment、Run–TraceEntry 等组合保留。其删除语义是假设只在允许删除整个聚合时级联删除；正常业务关闭、取消、失效不等同于物理删除审计记录。
- CampaignProposal–SupplierOffer 使用白菱形表达共享选择集；Offer 独立存在，不随 Campaign 删除。Week 6 p29 明确普通 UML 共享聚合没有额外强生命周期语义，不能把它解释成组合。
- Reviewer/Guardrail 的 review 与 HumanApproval 的授权分开。通过审查不意味着获得支出、合同或发布授权。
- 不加入学长图中的真实 Booking、Payment 执行服务，因为本项目 UC-06/08 明确将真实预订、支付、发布和支出排除在基础原型之外。

## 4. 明确的简化与补充类型

这是主要设计类图，不是全部代码类型清单。未展开的类型必须仍有明确含义：

- `Money`：`amount: Decimal, currency: String`；当前原型金额为 AUD，同一 quoted quantity，按 UC-06 两位小数四舍五入。
- `DateRange`：`startDate: Date, endDate: Date`，含首尾天数。
- `SubjectRef`：不可变值类型 `subjectType: String, subjectId: String, revisionId: String`。引用具体被审核/批准的实体及版本；不是遗漏的接口。ReviewResult、HumanApproval 保存该值。约束：引用必须能解析，批准只适用于记录的版本及 scope；重要修改使当前批准失效而保留历史。
- `RequestedAction`：操作种类、目标计划/版本及可选 approved member-offer rule 的请求值；UC-07 判断资格，不创造折扣规则。
- `Constraint/Preference`：有名称、值、来源、确认状态的约束值。ConstraintSet 为确认快照，新修改生成新快照。
- `AgentResult/ExtractionResult`：内部操作结果值；`SupplierReliabilitySummary` 是可选汇总结果值，本图不扩展其生命周期。
- `ItineraryItemKind/ProductType`：Transport / Accommodation / Activity；`ExceptionIssueKind`：Disruption / Complaint；`RequesterKind`：Traveller / Supplier / CampaignResponse。
- `OfferStatus` 与 SM-04 一致：Draft、RevisionRequired、UnderReview、AwaitingApproval、Approved、Rejected、Expired。
- 图中其他 Status/Outcome/Role 类型为枚举词汇；其全套取值仍需结合其余成员尚未提供的状态图完成最终统一。没有把这项写成已经完成。

## 5. 仍待统一的内容

### 5.1 项目需求自身的 Case 创建时机冲突（提交前必须决定）

`TripMate AI.md` §2.2、§3.2、OPS-AH-01 表达“确认后创建 Case”，但 UC-05 主流程第 3 步、A 分支与 Acceptance Criteria 又描述提前创建 Draft CustomerCase/SupplierCase。

本图暂时延续此前模型的解释：未确认内容存 ExternalRequest，确认后产生 Case，允许一个请求拆成多个 Case。此处是**临时设计选择**，并不意味着需求冲突已解决。没有擅自改写需求文档。若团队选择 Draft Case，需一起调整 CaseStatus、confirmedAt 的可选性和生命周期表述；若选择当前方案，需同步修改 UC-05 所有 Draft Case 相关段落，而非只改第 3 步。

### 5.2 SD-04 命名与操作尚非一一对应

| SD-04 | 当前类图 | 核对结果 |
|---|---|---|
| OperationsAgent / SupplierPartnershipAgent | 同名类 | 职责一致；assessOffer 使用 SupplierCase + Evidence[*] |
| extractor: LLM / extractFields(source) | LLMAdapter 实现 ILLMService.extract(input, schema) | 需要统一 lifeline 类型与消息名 |
| rules: ValidationPricing / validateAndPrice | ConstraintValidationService.validateOffer + PricingService.calculate/checkMargin | 类图采用两个确定性职责；序列图需拆分调用或另行定义 facade，不应声称类型完全匹配 |
| ReviewerGuardrail.review(fields, source, breakdown) | review(subject: SubjectRef, evidence: Evidence[*]) | 需统一参数抽象层次；subject 可解析到 offer 与价格历史 |
| HumanFounder / requestApproval | HumanFounderOperator.decide | 人工请求和最终决定不是同一个操作，须在 sequence 中明确边界 |
| saveOfferAndTrace | 领域状态更新 + Agent.recordTrace | SD-04 明说是本地实现细节，无需为此强加持久化服务类 |

SM-04 的七种状态及“修订后重检、批准且未过期才可选”的规则一致。未改动 SD-04/SM-04 原文件，以便组员分别统一自己的行为模型。

### 5.3 选修能力与组员贡献

48 类覆盖主要核心业务。OPS-O1 acquisition metrics、EXC-O1 自动监测、知识检索等选修能力没有展开全部类；若这些是已承诺实现或评分的选修范围，仍应补相应设计视图，而不能将其一律称作不需要。最终报告还需按评分表注明各组员贡献。

## 6. 验证范围

- 已在 app.diagrams.net 导入真实 drawio，检查正常字号下的 Agent 类标题与成员归属；不是仅查看自制 SVG。
- XML 检查：每个类有原生属性/操作子单元，关系端点存在；结构关联均有两端多重性；操作含类型且无重复简写；接口实现操作一致。
- 几何检查：无类框重叠、无连接线穿过类框内部；主干之间仍存在交叉，不宣称零交叉。drawio 启用跳线。
- SVG/PNG 与 drawio 共用成员内容、换行与尺寸。SVG 是静态预览，不保留 drawio 的编辑行为及全部跳线呈现。
- 完整图适合大画布缩放浏览。插入报告时应采用矢量图并配主要区域说明，不能把整图压缩到普通 A4 页面后仍宣称正文可读。
