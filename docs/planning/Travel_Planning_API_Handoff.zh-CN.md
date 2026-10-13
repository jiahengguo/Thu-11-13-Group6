# Travel Planning API 交接与调用说明

日期：2026-10-13（Australia/Sydney）。负责人 Moore；业务范围 UC-01 / UC-02、B04/B09/B13/B14。
依据：[共享 v1 契约](../contracts/v1/CONTRACTS.md)、[分工计划](Stage2_Week9-12_Plan_and_Jira.zh-CN.md)。
本文件描述本分支的实际代码，不表示其他成员服务或全组验收已经完成。

**main 合并更新**：已对接主分支 `a1605f4` 的 Operations 与 B03 数据库，见 [main 联调说明](Main_Integration.zh-CN.md)。
原文未集成状态以此更新为准：Operations 实际服务已接通；B03 是共享模拟数据；正式 Supplier/Reviewer/Exception 仍待对接。

## 1. 接口形式与当前状态

四个 Agent 在同一 Python 应用内调用，以下主要是 **Python API**，没有已经部署的 `/planning/*` HTTP 路由。
现已通过 main 的 `/api/operations/*` HTTP 路由联调规划/审核/交付/采用，具体认证与请求参数见 main 联调说明；
没有独立公开的 `/planning/*` 路由。模型代理是外部 HTTP 服务，不要让浏览器持有模型密钥。

| 能力 | 状态 |
| --- | --- |
| 价格计算、行程校验、确定性生成与模式排序 | 已实现 |
| 确认后修改、比较、保存不可变版本、明确接受 | 已实现 |
| campus-qwen 提出候选、工具校验、失败反馈修正 | 已实现并有真实模型运行证据；旅行数据仍为模拟 |
| `LLMService.extract/draft/explain` 原有占位 | `CampusLLMService` 已实现；结构化输出本地验证 |
| Operations/会员服务 | 已通过 main connect_planning 接入实际实现；开发账户仍为 fixture |
| Supplier/Reviewer 服务 | B03 数据库报价适配器已接入；正式 Supplier/Reviewer 仍待注入 |
| 统一四 Agent `build_agents()` | 支持注入 Operations；无依赖时仍为 STUB；开发联调须显式开启 |
| Exception 专门恢复接口、人工审批队列、会员折扣联调 | 尚未实现，见第 9 节 |

## 2. 共用数据规则

- 完整对象 schema：`src/tripmate/contracts/v1/schemas.json`；调用 `tripmate.contracts.validate(name, payload)`。
- 公共对象必须有 `schemaVersion/caseId/correlationId/sourceReferences/validationResults/errors/requiresApproval`。
- 不在严格 v1 对象里添加未知字段；PlanningSpec、PlanningProduct 和内部 record 是独立适配器数据。
- 金额：`{"amount":"450.00","currency":"AUD"}`，使用字符串和 Decimal，不用浮点数算钱。
- 日期 `YYYY-MM-DD`；时间带时区；日数按悉尼日历含首尾。
- 来源记录含 `sourceId/sourceType/sourceReference/capturedAt/freshness/simulated`。
- FIXTURE 表示业务数据模拟；即使调用真实模型，fixture 演示也保持 FIXTURE。
- Source、报价、版本 ID 必须真实对应输入快照，不能让模型捏造。

## 3. Planning 需要调用的 API

### 3.1 Jiaheng：需求上下文

注入 `PlanningRuntime.load_context`：

```python
get_planning_context(case_id: str) -> dict
# 返回 {"request": TravelRequest, "spec": PlanningSpec}
```

函数名可自定，注入的参数和返回值必须一致。Planning 首先收到已确认的 Case，再按 caseId 取上下文。

TravelRequest 关键字段：

| 字段 | 含义 |
| --- | --- |
| requestId / travellerId / caseId / correlationId | 请求、用户、Case 与全链路关联身份 |
| origin / destination / partySize | 出发地、目的地、正整数人数 |
| budgetCeiling / travelDates | 完整总预算和 startDate/endDate |
| rankingMode | COMFORT、VALUE 或 BUDGET |
| confirmedAt | 明确需求确认时间 |
| constraintSetId / constraintSetVersion | 确认后的约束快照及版本 |
| hardConstraints | constraintId、kind、description、confirmed |
| preferences | 自由文字偏好；不等于确定性保证 |
| baselineVersionId | 首次为 null；修改时指向已有不可变版本 |
| confirmedChangedFields | 首次为空；修改时精确列出已确认变化的字段 |

最小 PlanningSpec 例子（配合 constraintId 为 budget 的请求）：

```json
{
  "roundTrip": false,
  "constraintBindings": {
    "budget": {
      "description": "Use the confirmed total AUD budget",
      "value": {"amount": "450.00", "currency": "AUD"}
    }
  }
}
```

每个绑定 ID/description 必须与已确认 hardConstraints 对应。支持：

| kind | value |
| --- | --- |
| BUDGET | 与 budgetCeiling 一致的 Money |
| DATES | 与 travelDates 一致的对象 |
| ACCESSIBILITY | bool，是否必须无障碍 |
| BAGGAGE | 非负整数 kg |
| ARRIVAL_TIME | 最晚到达的带时区时间戳 |
| TRANSFER_LIMIT | 非负整数；当前每个方向仅支持直达 |

不支持的条件不能被忽略。Case 必须是 CUSTOMER，类型 TRAVEL_PLANNING 或 PLAN_REVISION，
状态 CONFIRMED/ASSIGNED/IN_PROGRESS；无 unresolvedQuestions/errors；身份关联必须匹配。
`requiresApproval` 或两次请求人工会阻止当前模块继续，交回 Operations。

### 3.2 Jiaheng：权限和会员

对应 `src/tripmate/services/ports.py`：

```python
access.authorise(requester_id: str, action: str, subject: dict) -> bool
entitlement.evaluate(traveller_id: str, action: str, dates: dict) -> dict
```

| 服务 | 当前 Planning 调用动作 | subject / dates |
| --- | --- | --- |
| access | CREATE_PLAN / REVISE_PLAN | TravelRequest |
| access | READ_PLAN | 修改基线的 ItineraryVersion |
| access | ADOPT_PLAN | 待采用的 ItineraryVersion |
| entitlement | CREATE_PLAN / REVISE_PLAN / PRESENT_PLAN / ADOPT_PLAN | TravelRequest.travelDates |

权益最小通过返回例子：

```json
{"travellerId":"demo-traveller","action":"CREATE_PLAN","outcome":"ALLOWED","reason":"Verified entitlement"}
```

必须精确匹配 travellerId/action 且 outcome=ALLOWED。DENIED、VERIFICATION_FAILED 或不匹配均阻止执行。
当前包装层将非允许结果归为 ENTITLEMENT_DENIED；完整会员计数/证据和策略由 Jiaheng 维护。
采用时重新检查，不沿用创建时授权。用户身份应来自后端认证会话，不直接信任网页提交的 travellerId。

### 3.3 Jason：已审核报价及产品数据

对应 `ApprovedOfferLookup.find_selectable`：

```python
offers.find_selectable(criteria: dict, at: str) -> list
# criteria 是完整确认后的 TravelRequest；at 是带时区当前时间
# 每个返回条目只能包含：
# {"offer": SupplierOffer, "price": PriceBreakdown, "product": PlanningProduct}
```

SupplierOffer 提供 offerId/materialVersion/supplierId/productId/productType、availableQuantity、
quotedQuantity/unitBasis、supplierCost、mandatoryChargesIncluded、validFrom/validUntil、
cancellationTerms/commercialTerms、status、priceBreakdownId、review/approvalId，以及公共 envelope。
必须是已审核、当前有效的 APPROVED 基础报价；审核 subject 对应精确报价版本。

PriceBreakdown 提供成本、markupRate、basePrice、discountAmount、sellingPrice、marginAmount、
minimumMargin、报价绑定、数量基准、配置版本、计算时间、来源和可空优惠 ID。
价格是报价数量对应的完整包价，Planning 不再次乘人数。人数改变需重新报价。

PlanningProduct **全部字段**如下，不允许多余字段：

| 字段 | 格式/含义 |
| --- | --- |
| productId | 与 offer.productId 一致 |
| role | OUTBOUND / RETURN / STAY / ACTIVITY |
| startAt / endAt | 服务起止时间，带时区 |
| origin / destination | 可衔接地点；当前不推断机场接驳 |
| partySize | 报价对应人数，与请求一致 |
| accessible / baggageKg | bool / 非负整数 kg |
| comfort / reliability | 0–1 十进制字符串，用于排序 |
| minConnectionMinutes | 非负整数衔接缓冲 |
| openingStart / openingEnd | ACTIVITY 营业时间，其他 role 为 null |
| sourceIds | 能在 offer.sourceReferences 中解析的来源 ID |

完整可运行示例：`tripmate.planning.fixtures.fixture_quotes()`。
结构损坏会中止调用；结构有效但过期、超预算或库存不满足的组合会被校验排除。
当前规划入口拒绝会员折扣报价，待 B17 接入实时资格复核；不能只凭一个 entitlementDecisionId 认定有效。

### 3.4 wrd：Reviewer

```python
reviewer.review(subject: dict, evidence: list, policies: list) -> dict
# subject 是完整 ItineraryVersion，evidence 是 sourceReferences
# policies 例如 ["planning-1.0", "planning-demo-1.0"]
```

返回完整 ReviewResult：

```json
{
  "reviewId": "review-123",
  "subject": {"subjectType": "ItineraryVersion", "subjectId": "version-123", "materialVersion": 1},
  "outcome": "PASS",
  "reasons": ["Evidence and deterministic checks verified"],
  "reviewedAt": "2026-10-13T10:00:00+11:00",
  "policyVersion": "review-policy-1",
  "sourceIds": ["source-123"]
}
```

上面仅为形状示例，ID 和时间必须绑定真实本次对象。生成及采用均要求 PASS、精确版本和有效时间。
非 PASS 返回 REVIEW_FAILED；当前不自动创建人工审批单，受限请求返回共享流程处理。

## 4. Planning 提供给组员的 API

### 4.1 生成/修改：Operations 调用

```python
from tripmate.agents.planning import TravelPlanningAgent
agent = TravelPlanningAgent(runtime)
result = agent.handle_case(confirmed_case)  # -> AgentResult
```

输入区别：TRAVEL_PLANNING 为首次生成；PLAN_REVISION 配合基线 ID、新 constraintSetVersion
及 confirmedChangedFields 创建新版本。原版本不覆盖；修改需求确认不等于接受新方案。
对当前不支持的隐藏 roundTrip 变化会拒绝，不能通过改内部 spec 绕过确认。

返回可以获得：

| AgentResult 字段 | 数据/含义 |
| --- | --- |
| status / executionMode | 结果状态和 STUB/FIXTURE/REAL 标记 |
| runId / caseId / correlationId | 运行记录与关联 |
| subjects | 已保存行程版本的 subjectType/subjectId/materialVersion 引用 |
| findings | 已评估组合、排除原因等 |
| validationResults / errors | 结构化校验和失败信息 |
| proposedResponse | 确定性建议摘要，不是已送达用户的消息 |
| review / approvalIds / requiresApproval | 审核与审批信息 |
| nextAction / sourceReferences | 后续动作与证据 |

当前实现成功返回 SUCCESS，业务或依赖失败返回 FAILURE；其他共享枚举不代表本模块已实现其流程。
入口 Case 结构校验失败可直接抛 ContractError；正常业务失败在 AgentResult.errors 中。
保存失败不会返回可发布 subjects。Operations 仍负责发布授权、用户展示、Case 状态与关闭。

### 4.2 读取详情、比较和生命周期（内部 repository API）

```python
record = runtime.repository.get_version(version_id)
selected_id = runtime.repository.selected(plan_id)  # str 或 None
state = runtime.repository.lifecycle(plan_id)
events = runtime.repository.find_by_case(case_id)
```

`get_version` 返回内部 record，含：

| 字段 | 可获得的数据 |
| --- | --- |
| version | ItineraryVersion；时间、交通/住宿/活动项目、报价引用、总价、来源与审核 |
| request / spec | 生成时的确认需求与硬约束绑定 |
| quotes | 当时完整 offer/price/product 快照，含内部供应商成本 |
| metrics | cost、journeyMinutes、transfers、comfort、reliability、terms、activities、accommodation |
| ranking | mode、configVersion、weights、score |
| comparison（修改时） | 原/新版本、changedRequirements、added/removed/changed/unchangedOffers、costDelta、journeyMinutesDelta、前后 metrics/sources、scopeChanged、dataRefresh 等 |
| modelPlanning（模型路径） | model、attempts、工具反馈、explanationDraft、rankingScope |
| llmDraftForReview（可选） | 另行注入 llm.explain 时的待审核草稿 |

`subjects` 不携带完整行程，要通过版本引用读取。解释草稿不能直接作为已审核事实发布。
`lifecycle` 当前返回 `{planId, selectedVersionId, planStatus}`，仅实现 DRAFT/PLANNED；ACTIVE/COMPLETED 后续联调。
采用状态单独保存，历史 version.planStatus 仍可为 DRAFT，会员计数不能只读历史快照。
`find_by_case` 返回 Planning 的 TraceEvent 列表，不代表实现共享 TraceRepository.append。

这些是内部存储 API，**不自带访问鉴权和字段脱敏**。Operations/wrd 需先 authorise 并按使用场景筛选字段，
不得把 record（尤其 quotes 中的成本）整体返回旅客浏览器。不要直接改 planning_* 表。

### 4.3 明确采用：Operations 调用

```python
from tripmate.planning.application import accept_proposal
record = accept_proposal(
    runtime, authenticated_traveller_id, exact_proposal_id,
    expected_baseline, accepted=True,
)
```

- expected_baseline：第一次采用为 None；修改方案时为提案对应、仍被选中的基线版本 ID。
- 后端重新检查身份、权限、权益、报价快照、可行性和 Reviewer。
- 报价变化/过期要求重新生成并确认，不暗中更新价格。
- 原子检查选中基线，避免旧页面覆盖新选择；重复采用同一版本返回历史记录。
- 返回被采用的 record，不创建订单、不付款；异常抛 PlanningError（code/message/step）。

### 4.4 价格计算：Jason 调用

```python
from tripmate.planning.pricing import DeterministicPricingService
pricing = DeterministicPricingService(
    markup_rate="0.10", minimum_margin={"amount":"15.00","currency":"AUD"},
    config_version="team-pricing-1",
)
price = pricing.calculate(offer, discount=None)  # -> PriceBreakdown
```

10% 和 AUD 15 仅为调用例子，实际策略由 Supplier 确定。
basePrice=成本×(1+加价率)，sellingPrice=basePrice−优惠，marginAmount=售价−成本；
AUD 两位小数 ROUND_HALF_UP，舍入后检查最低差价，不改原 offer。
计算结果含成本/基础价/折扣/售价/差价、策略版本和报价绑定。
可选单条 discount 的字段为 approved、eligible、memberOfferRuleId、entitlementDecisionId、offerIds、
validFrom、validUntil、amount。approved/eligible 必须为 True；不能叠加。
供应商适配器负责从可信权益服务取得这些字段，价格器本身不联网验证资格。

### 4.5 约束检查：Planning / wrd 调用

```python
from tripmate.planning.validation import PlanningValidator
validator = PlanningValidator(confirmed_request, current_quotes, spec)
checks = validator.validate_plan(itinerary_version)
checks = validator.validate_proposal(itinerary_version)  # 当前为同一校验逻辑
```

返回 ValidationResult 列表：ruleId/ruleVersion/outcome/reason/checkedAt/sourceIds。
所有结果 PASS 才通过；检查完整性、报价/产品绑定、价格、库存、有效期、来源、日期、地点、
衔接时间、住宿覆盖、预算及支持的硬约束。这个接口不是任意供应商/营销对象的通用 validator。

## 5. 原有模型占位如何接入

原占位：`src/tripmate/adapters/ports.py::LLMService`；实现：`src/tripmate/adapters/campus.py::CampusLLMService`。

```python
from tripmate.adapters.campus import CampusLLMService, load_local_config
load_local_config()  # 从当前工作目录 .env 读取白名单字段，已有进程环境变量优先
llm = CampusLLMService(timeout=60)
structured = llm.extract(content, json_schema)  # -> dict；本地 Draft202012 schema 验证
draft = llm.draft(context)                     # -> str，待审核
explanation = llm.explain(validated_result)    # -> str，待审核
```

`extract` 不等于用户确认；返回 JSON 仍需 Operations 的确认/鉴权流程。
draft/explain 不得决定价格、审批或是否符合硬约束。
`chat(messages)->str` 是额外低层能力；Planning 的 ModelPlanningEngine 使用它处理多轮工具反馈，
没有改动原 LLMService 的三个方法。该循环不是仅调用 explain。

共享配置（模板 `.env.example`，实际密钥只在本地 `.env`）：

```dotenv
TRIPMATE_LLM_PROVIDER=elec5620
TRIPMATE_LLM_MODEL=campus-qwen
ELEC5620_BASE_URL=http://10.167.60.148:8000/v1
ELEC5620_API_KEY=REPLACE_LOCALLY
```

模型名优先 TRIPMATE_LLM_MODEL，其次 ELEC5620_MODEL，默认 campus-qwen。
其他 provider 值会被本课程适配器拒绝；TRIPMATE_EXECUTION_MODE/DATABASE_PATH/CURRENCY 是 B02 占位，
本 Planning CLI 没有据此设置 runtime，应使用明确的 CLI 参数/注入值。

HTTP 使用 `POST http://10.167.60.148:8000/v1/chat/completions`，Authorization Bearer，JSON 请求：

```json
{"model":"campus-qwen","messages":[{"role":"user","content":"..."}],"max_completion_tokens":4096,"stream":false}
```

读取 `choices[0].message.content`。记录 finishReason/usage，不保存内部推理或密钥。
需校园可达网络/VPN。超时/HTTP 错误为 TOOL_UNAVAILABLE，空/截断/不合格式输出为 LLM_INVALID_OUTPUT。
不发送 supplier 成本或用户身份给模型，只发送规划所需需求、产品/售价及反馈；实际集成仍需控制自由文字中的隐私。
模型只输出候选 offer IDs，不能执行生成的代码、创建新产品或改预算。每轮最多 8 候选、最多 3 轮。
一轮有通过的候选就结束并进行确定性排序；不保证全库存最优，三轮失败也不证明全局无解。

## 6. 完整可运行接入示例

以下示例使用 fixture 数据和权限，但模型真实联网；不代表其他 Agent 已集成：

```python
from tripmate.planning.fixtures import fixture_runtime
from tripmate.adapters.campus import CampusLLMService, load_local_config
from tripmate.planning.campus import ModelPlanningEngine
from tripmate.agents.planning import TravelPlanningAgent

load_local_config()
case, context, runtime = fixture_runtime(mode="VALUE", budget="450.00")
try:
    runtime.planner = ModelPlanningEngine(CampusLLMService(), runtime.clock)
    result = TravelPlanningAgent(runtime).handle_case(case)
    for ref in result["subjects"]:
        record = runtime.repository.get_version(ref["subjectId"])
        print(record["version"]["totalPrice"], record["metrics"])
finally:
    runtime.repository.close()
```

组员服务准备好后，在共享组合入口按如下方式替换依赖（下面变量名是示意，不是已实现组员对象）：

```python
runtime = PlanningRuntime(
    load_context=request_repository.get_planning_context,
    offers=supplier_adapter,
    access=access_service,
    entitlement=entitlement_service,
    reviewer=review_service,
    repository=PlanningRepository(shared_database_path),
    execution_mode="FIXTURE",  # 模拟业务数据持续标注；不要仅因模型真实就改 REAL
    planner=ModelPlanningEngine(shared_llm, clock),
    clock=clock,
)
agents["planning"] = TravelPlanningAgent(runtime)
```

需导入 `PlanningRuntime`（planning.application）和 `PlanningRepository`（planning.repository）。
shared_llm 是同一个 CampusLLMService；clock 返回带时区时间字符串，整个调用使用一致时钟。
默认不再注入 runtime.llm，避免在候选规划外增加一轮可选解释调用；需要时可设置 `llm=shared_llm`。
通过 `build_agents()` 得到的其他 Agent 仍是 stub，这段不会自动实现四 Agent 全链路。

## 7. 运行、报错和测试

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
# 将 .env.example 复制为 .env 并在本机填写 key，不覆盖已有私有配置
.\.venv\Scripts\python.exe -m tripmate.planning.demo --live-model --budget 450.00 --output output/planning-campus
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

不加 --live-model 时运行离线确定性枚举。--accept 为独立明确接受；--revise-budget 创建新提案，不自动采用。
--database 指定 SQLite 文件；默认内存库每次退出清空。output/ 和 tmp/ 不提交 Git。
共享 git 分支没有个人 .env，组员必须使用自己的本地凭据。

| 错误 | 对接处理 |
| --- | --- |
| INVALID_CONTRACT / MISSING_REQUIRED_FIELDS | 检查完整 schema、绑定、上下文与版本 |
| UNCONFIRMED_REQUEST | Operations 补问并明确确认 |
| ACCESS_DENIED / ENTITLEMENT_DENIED | 由 Jiaheng 核验身份/权益，不绕过 |
| NO_FEASIBLE_ITINERARY / UNSUPPORTED_CONSTRAINT | 展示失败原因；确认后改需求或补充库存，不自动放宽 |
| STALE_EVIDENCE | 更新报价/基线并重新生成、确认 |
| REVIEW_FAILED / APPROVAL_REQUIRED / HUMAN_ASSISTANCE_REQUIRED | 交回 Reviewer/Operations/人工流程 |
| TOOL_UNAVAILABLE / LLM_INVALID_OUTPUT | 检查网络、模型、输出上限；不伪装离线成功 |
| PERSISTENCE_FAILED | 保持 Case 未完成并重试/排查保存 |

## 8. 各成员最小交付清单

- Jiaheng：已确认 Case/TravelRequest/PlanningSpec、权限/权益服务、确认修改与明确采用的交互、受控读取和最终展示。
- Jason：含 offer/price/product 的完整报价包、价格策略配置、来源、过期/库存不足用例、共享启动入口。
- wrd：精确版本 Reviewer、失败/人工处理、共享 trace 集成、异常恢复输入格式。
- Moore：本模块接口实现、规则/版本/比较、共享价格器、模型规划循环、测试、接口文档和联调修复。

## 9. 未完成的接口与限制

1. **Exception 专门恢复 API**：尚无 propose_recovery；普通 handle_case 不能接收 Exception Case。
   待约定：基线版本、受影响项目、异常证据、不可改动/已执行项目、确认后的新约束；输出恢复版本、差价、时间差和失败原因。
   本次过期报价反馈测试验证候选修正，不等于已实现 UC-03 异常恢复。
2. **外部读取/比较 HTTP API**：repository 已有数据，鉴权与展示 DTO/路由未实现；不能直接公开内部记录。
3. **人工审批/会员优惠/生命周期**：等待共享模块联调；不宣称可接受受限报价或完成付费权益全流程。
4. **复杂路线**：当前是直达、一个完整住宿包、一个活动、可选回程；不支持任意多城市、多活动、多中转。
5. **部署/发布**：无真实预订、支付、广告执行；branch 中的代码等待 peer review 和全组验收。

## 10. 验证证据

2026-10-13 真实课程代理测试：预算 450 时模型提出 AUD 396/429 两套方案，各 38 项确定性检查通过。
受控过期住宿测试：模型第一次候选被 OFFER_VALIDITY 拒绝，第二次改住宿，AUD 506 满足 550 预算。
模型回答是真实 API 返回，Supplier/Access/Entitlement/Reviewer 是 fixture，时钟固定 2026-10-12。
精简可分享记录见 [live_model_smoke.json](evidence/live_model_smoke.json)，不包含 key 或内部推理。
共享 extract/draft/explain 与规划 chat 使用相同传输；各方法的本地契约测试与实际联网证据应分别理解。
迁移到共享适配器后已重新运行真实模型规划成功；完整自动测试 70 项通过。
