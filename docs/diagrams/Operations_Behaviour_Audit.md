# Operations behavioural diagrams — review and corrections

Reviewed: 2026-09-22. Owner: Jiaheng Guo.

## Scope and conclusion

SD-01 and SM-01 model the **single confirmed travel-planning CustomerCase** explicitly selected in AD-01. SD-01 shows collaboration during a handling attempt, including alternatives that suspend that attempt. SM-01 shows the Case lifecycle across waiting, recovery, revision, human handling and closure. Ending an interaction attempt does not mean closing the Case.

The original diagrams needed corrections to UML notation, alternative-flow control and recovery paths. The revised diagrams follow the relevant Tutorial 7 conventions and the UC-05/UC-07 requirements **within this declared scenario**. They are not a claim to depict every external-request type or every standalone entitlement use case.

Sources:

- ELEC5620-TUT-07.pdf, pages 22–32: objects, lifelines, message kinds, creation, focus of control and combined fragments; pages 37–44: object lifecycle, transitions, state actions and compound states.
- [TripMate AI.md](TripMate%20AI.md), UC-05 and UC-07, including business rules and acceptance criteria.
- [AD-01](Activity_diagrams/AD-01_Operations_Customer_Request.drawio), including its scope and explanatory constraints.
- [Current class model](Elementary_Structure/G-04_Current_Model.md): ExternalRequest, CustomerCase / Case, OperationsAgent, Agent, TravelPlanningAgent, EntitlementService, ReviewerGuardrail and HumanFounderOperator.

## Corrections to the original diagrams

| Finding | Correction | Basis |
|---|---|---|
| Ordinary synchronous calls used open arrowheads, indistinguishable from signals. | Operation calls use solid lines with filled arrowheads; returns use dashed lines with open arrowheads; descriptive external communications use signal notation. | Tutorial 7 pp. 25–27 |
| ExternalRequest and CustomerCase headers appeared at the top despite later creation messages. | Each new object's header and lifeline start at its creation message. CustomerCase is created only after confirmation. | Tutorial 7 p. 28; UC-05 steps 3, 8–9; class relationship R009 |
| Object names were not explicitly underlined. | Instance labels use underlining and `instance: Class` notation. | Tutorial 7 pp. 22–24 |
| Focus of control was represented mainly by one long Operations bar. | Service-call activations align with calls and corresponding returns; the planning activation spans its collaborative work. | Tutorial 7 p. 30 |
| Denied / VerificationFailed alternatives could fall through to specialist processing or review. | Explicit break paths suspend the current attempt, preserving the Case. Only Allowed permits the protected continuation. | UC-07 main flow and A1–A4 |
| Human edit, rejection or takeover could be followed by automatic delivery. | Non-approval paths suspend automatic release; the final delivery fragment requires passed checks, unchanged response and scoped approval when required. | UC-05 A9–A10 and AC-UC05-05; AD-01 |
| Specialist unavailability was followed by an assumed immediate valid assignment. | Record coordination failure and request human assistance; do not assert resolution has already occurred. | UC-05 A8 |
| Mandatory escalation was expressed too vaguely. | Show the `humanRequestCount >= 2` condition, unresolved uncertainty and conflicting evidence; SM-01 applies escalation to the actual automated composite state. | UC-05 BR12 / AC-04; UC-07 A7 |
| Waiting-state return paths did not clearly identify the required recheck. | Retain initial/post-planning phase; evidence recovery returns to the relevant entitlement check. Changes to plan facts return to planning, while an unchanged version can be rechecked directly. | UC-05 A6–A7; UC-07 A1–A4 |
| A broad initial transition mixed request confirmation with an event-triggered transition from an initial pseudostate. | Treat confirmed ExternalRequest as creation context; use an untriggered initial transition into Confirmed. | Tutorial 7 initial-state and lifecycle notation |
| Open CustomerCase was a visual enclosure, with its states stored as unrelated root cells. | Use real Draw.io nesting for Open CustomerCase and Automated coordination; global transitions attach to these composites. | Tutorial 7 p. 44 |
| Several drawn paths / labels differed from their XML-connected endpoints or obscured other elements. | Rebuild connections with explicit ports, individual routes, separately placed labels and visible non-junction bridges. Render PNG from the actual decoded Draw.io model. | Diagram integrity and requested layout constraints |

## Requirement coverage and deliberate boundaries

| Requirement | Representation in the revised pair |
|---|---|
| UC-05 intake, requester/source identification and verification | SD-01: ExternalRequest creation with requester kind, source and optional campaign reference; verification gate before protected work. |
| Missing fields, uncertainty and clarification | SD-01: deterministic missing-field check, clarification loop and intake assistance; incomplete/unresolved intake cannot create a Case. |
| Confirmation and proposed intent split | SD-01: explicit summary/split confirmation before `confirm()` and `intake(request)`. The diagram follows one resulting CustomerCase. |
| Initial UC-07 decision | SD-01 evaluation and terminal alternatives for Denied / VerificationFailed; SM-01 Confirmed and its three outcome transitions. |
| Routing, hand-off, unavailability and tracking | SD-01 `route(case)`, specialist call and recorded assistance; SM-01 Assigned / In Progress / Human Assistance. |
| Confirmed changes and additional facts | Compact SD-01 requests additional facts and pauses the attempt; SM-01 covers confirmation and recovery through its global amendment transition, Awaiting Requester and guarded return paths. Full summary is reconfirmed when category, routing, risk or approval changes. |
| Returned Plan Version and post-planning UC-07 | SD-01 returns status, dates, inclusive duration and evidence; SM-01 Awaiting Plan Access Decision prevents review from bypassing the final entitlement result. This is a processing condition, not a new entitlement outcome. |
| Free / Paid rules | Record Free count limit of two Planned/Active trips, five inclusive calendar days and `endDate - startDate + 1`; active Paid members are exempt from these Free-tier limits. |
| Membership changes and trace | Use latest verified membership for the post-planning check and retain both snapshots when changed. Trace includes Case, version where applicable, count, decision, rule, reason and timestamp. |
| Denial and protected-action blocking | Denied preserves existing trips and explains permitted recovery; VerificationFailed blocks the action, retains the open Case and escalates when required. UC-07 does not alter an itinerary, subscription or discount. |
| Review, revision and human decision | Failed review returns revision reasons; authorised edits repeat affected checks; rejection/takeover pauses release. RequestRevision and recorded human closure are retained because AD-01 explicitly contains them. |
| Delivery and retries | SD-01 delivery loop and successful-delivery closure; SM-01 retains Ready to Respond for transient retry and persistent-failure assistance. Referral alone does not close the Case. |
| Withdrawal and closure | SD-01 distinguishes withdrawal before Case creation from withdrawal afterwards; SM-01 Open-to-Closed transition applies throughout the Case lifecycle. Recorded human closure is distinct from successful delivery. |
| All-stage escalation | SM-01 Automated-to-Human transition; SD-01 constraint and applicable assistance messages. An explanatory note supplements the sequence; it does not substitute for the lifecycle transition. |

The following are **outside the selected AD-01 scenario**, rather than accidentally omitted branches:

- UC-05 A1 routine enquiries, SupplierCase processing, complaint/disruption investigation and their specialist internals.
- Coordination of all Cases created from a multi-intent split. Confirmation of the split is shown, but this scenario follows only the selected planning Case.
- UC-07 A5 standalone Premium Feature access and A6 standalone advertising/member-offer eligibility. The planning check still checks applicable feature/member-offer entitlements. No standalone advertising workflow, discount calculation or quotation is added.
- UC-01's planning algorithms, supplier search, ranking and itinerary construction; UC-06 pricing; UC-08 campaign design; payment or subscription execution.

Tutorial 7 describes collaboration scenarios and the lifecycle of a selected object; it does not require every alternative of every related use case to be expanded into each diagram, or every notation (history, concurrency, entry/exit points) to be used. If full UC-05/UC-07 coverage is later required by a separate assessment rubric, the current explicitly scoped pair alone would not establish that coverage.

## Remaining inconsistency in the source document

UC-05 A2 still says **“The Case remains in Draft.”** This conflicts with UC-05 main steps 3 and 8–9, AC-UC05-01/02, the current class relationship “ExternalRequest produces Case after confirmation”, and the updated AD-01.

The diagrams consistently retain **ExternalRequest before confirmation and create CustomerCase after confirmation**. This review does not silently change the use-case source. Suggested replacement for A2: “The ExternalRequest remains pending verification. Protected Case, membership or supplier information is processed only after identity and access verification succeeds. Case records are created after the structured request is confirmed.”

## Layout and verification

- Exactly one `<diagram>` in each `.drawio`; one PNG per diagram. No auxiliary diagram images are added to the project.
- White, black and grey only; canvas size follows the complete diagram rather than a paper-size limit.
- PNGs are captured from a local browser rendering the decoded XML with mxGraph, the graph-model renderer underlying Draw.io. They are not separately redrawn approximations. Draw.io-specific application editing has not been manually smoke-tested in the desktop application.
- Check unique IDs, valid parent/terminal references, text bounds, text-to-text intersections, state/label separation, state-route penetration, and collinear business-edge overlap using the rendered model.
- Final checks passed: one page per file, valid IDs/references and connected state edges; 93 SD text boxes and 46 SM text boxes with no text overflow or text-to-text intersections; no state overlap, label-to-state overlap, state-route penetration, collinear transition overlap or transition-through-label intersections. SD message captions also do not intersect message lines. Complete PNG dimensions: SD 3611 × 6390; SM 5166 × 7676.
- Crossings use explicit non-junction bridge graphics present in both XML and PNG. Normal UML lifeline/message intersections, nested frames, activation bars on lifelines, composite containment and final-state concentric circles are intentional notation, not accidental overlap.

Outputs: [SD-01 editable](Interaction_diagrams/SD-01_Operations_Sequence.drawio), [SD-01 PNG](Interaction_diagrams/SD-01_Operations_Sequence.png), [SM-01 editable](State_machine_diagrams/SM-01_CustomerCase_StateMachine.drawio), [SM-01 PNG](State_machine_diagrams/SM-01_CustomerCase_StateMachine.png).

## 交互图精简说明（2026-09-22）

上一版把用例说明、等待状态及恢复细节重复放进时序图，导致图长达到 13828 像素。本次调整保持原来的参与对象和正文字号，将高度降至 6390 像素，缩短约 54%；只更新 SD-01，SM-01 保持不变。

- 保留 43 条必要消息，以及创建、同步调用、返回、激活条、loop / opt / alt / break 等相关 UML 表达。
- 保留接收与确认、初始 UC-07、路由与专员协作、计划后 UC-07、审核与批准、交付与关闭的顺序。
- 把分散的长篇规则说明合并为图首约束和图尾规则摘要；省略不提供额外信息的简单返回消息。
- 对等待补充事实、审核修改和人工处理，保留请求及中止本轮的分支；后续确认、恢复和重新检查沿用 SM-01，避免在两张图中重复展开。
- 资料不足本身只导致等待；分类不确定仍未解决或两次明确请求人工帮助才触发相应人工升级。初始／最终资格检查失败、拒绝或修改均不能继续自动交付。
- 最终交付仍由明确的 opt 条件约束：审核通过、需要的批准覆盖当前回复、没有待处理的升级。成功交付与持续失败仍为互斥分支。

这次压缩调整的是表达层次和留白，没有新增业务范围，也没有通过缩小文字或拆成多张图片来缩短图长。
