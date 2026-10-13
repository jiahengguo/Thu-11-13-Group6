# Moore — Travel Planning 实现与交接

分支：`codex/travel-planning`。基于共享主分支 `f7a61ed`。
范围：B04、B09、B13、B14 的可运行离线实现，以及 B20 的模块运行/交接说明。
这是待 Jason review 和全组联调的实现，不能据此把 Jira 卡标记 Done。

2026-10-13 更新：已接入课程真实模型的候选生成/工具反馈循环，并实现共享 LLMService 占位。
最新输入输出、签名及完整对接方法以 [API 交接文档](Travel_Planning_API_Handoff.zh-CN.md) 为准。

## 1. 已实现

| 卡片 | 本次实现 | 仍需团队验收 |
| --- | --- | --- |
| B04 / WN5620-5 | Decimal / AUD / ROUND_HALF_UP、售价/差价、预算、日期、时间/换乘、库存、报价有效性、来源完整性及硬约束校验 | Jason 确认真实 B03/B08 数据与价格配置；确认舍入中点规则 |
| B09 / WN5620-10 | 完整候选组合、先校验后评分、明确无解、结构化 AgentResult、数据库/trace、受控服务边界 | B06/B07/B08/B10 实际适配器、团队网页、真实 LLM 联调 |
| B13 / WN5620-14 | 三种模式、版本化确定性权重、共同硬约束、成本/时间/舒适/可靠性/条款比较 | 小组确认权重并在共享 UI 展示 |
| B14 / WN5620-15 | 确认字段后重算、不可变基线、逐项比较、单独接受、过期/变化重核、SQLite 原子选择与重复接受保护 | Operations 身份校验和交互确认、B07 权益、生产审核/审批适配 |
| B20 / WN5620-21 | 本文件、启动命令、测试与边界说明 | B19 最终验收、全组贡献确认、最终模型一致性检查 |

原始个人需求中 TP-02 表示比较、TP-03 表示修改；当前 planning 的 B13 归 UC-01/TP-01，B14 归 UC-02/TP-02。此实现以 UC-01/UC-02 与 B04/B09/B13/B14 追踪，不重编号历史文件。

## 2. Windows 启动

在本分支根目录，用 Python 3.9+ 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m tripmate.planning.demo --accept --revise-budget 450.00
Start-Process .\output\planning-demo\report.html
```

本次开发环境已安装 `.venv`，可直接执行后两条 Python 命令。
macOS/Linux 将 `.venv\Scripts\python.exe` 替换为 `.venv/bin/python`。
Windows 时区数据库通过显式 `tzdata` 依赖提供。

其他场景：

```powershell
.\.venv\Scripts\python.exe -m tripmate.planning.demo --mode BUDGET --budget 450.00 --output output/planning-budget
.\.venv\Scripts\python.exe -m tripmate.planning.demo --mode COMFORT --output output/planning-comfort
.\.venv\Scripts\python.exe -m tripmate.planning.demo --budget 1.00 --output output/planning-infeasible
.\.venv\Scripts\python.exe -m tripmate.planning.demo --database output/planning.sqlite3
```

预算 1.00 的演示应返回 FAILURE 和退出码 1，这是预期业务拒绝。
无 `--database` 时每次使用全新的内存数据库；文件数据库会保留历史，不自动覆盖。
`--accept` 仅表示显式接受本次推荐的模拟初始方案；修改后的方案不会自动被采用。

每次导出 `report.html` 与完整 `report.json`。HTML 是可展开校验详情的运行报告，
不是最终网页应用，也没有输入表单或在线预订。JSON 含完整内部证据与供应商数据，
团队前端应通过 Operations 选择可向旅客展示的字段。

## 3. 文件职责

| 文件 | 职责 |
| --- | --- |
| `src/tripmate/agents/planning.py` | 兼容 `handle_case(case) -> AgentResult`；注入 runtime 后执行实现 |
| `src/tripmate/planning/pricing.py` | B04 价格计算和供应商报价算术复核 |
| `src/tripmate/planning/validation.py` | 完整行程、连接、库存、证据、硬约束验证 |
| `src/tripmate/planning/engine.py` | 候选生成、评分、不可变版本与比较 |
| `src/tripmate/planning/application.py` | 身份/权益/审核调用、结果保存、最终接受 |
| `src/tripmate/planning/repository.py` | SQLite 版本、运行记录、trace、采用事务 |
| `src/tripmate/planning/fixtures.py` | 明确命名的离线数据和模拟依赖 |
| `src/tripmate/planning/demo.py` | CLI 与 HTML/JSON 报告 |
| `tests/test_planning.py` | 规则边界、集成、失败、版本与持久化测试 |

默认 `build_agents()` 尚未安装团队真实服务，仍返回显式 STUB 失败。
不把没有集成的其他 Agent 改成成功，也不偷偷把共享入口连到模拟权限。

## 4. 给 Jiaheng / Jason / wrd 的接入方式

```python
from tripmate.agents.planning import TravelPlanningAgent
from tripmate.planning.application import PlanningRuntime, accept_proposal
from tripmate.planning.repository import PlanningRepository

runtime = PlanningRuntime(
    load_context=request_repository.get_planning_context,
    offers=supplier_planning_adapter,
    access=access_service,
    entitlement=entitlement_service,
    reviewer=review_service,
    repository=PlanningRepository(shared_database_path),
    execution_mode="FIXTURE",  # 模拟数据一直标注 FIXTURE
    llm=llm_adapter,            # 可选 LLMService.explain
)
agent = TravelPlanningAgent(runtime)
result = agent.handle_case(confirmed_case)
# 成功返回的 subjects 可通过 repository.get_version(id) 获取提案/比较。
# 旅客另行接受，Operations 提供经过身份验证的 traveller_id：
accepted_record = accept_proposal(
    runtime, traveller_id, exact_proposal_id, expected_selected_version_id,
    accepted=True,
)
```

这里的名字是接入示例，不代表团队依赖已经实现。可运行实例见 `fixture_runtime()`。

### Operations / Jiaheng

- `load_context(caseId)` 返回 `{request: TravelRequest, spec: PlanningSpec}`。
- Case/TravelRequest 的 caseId、correlationId、travellerId 必须匹配。
- `access.authorise` 接收 CREATE_PLAN、REVISE_PLAN、READ_PLAN、ADOPT_PLAN。
- `entitlement.evaluate(travellerId, action, travelDates)` 必须返回匹配的 travellerId、action、outcome。
- 权益动作还包括 PRESENT_PLAN。不可把生成授权当作采用授权。
- Operations 负责真实身份、明确需求确认、最终对外发布和会员数量限制。
- 行程天数使用悉尼日历日期、含首尾；Planning 提供事实，不复制 B07 的会员状态机。
- 有未决问题、两次请求人工或受限要求时，此模块会停止并交还 Operations；不伪造审批记录。

### Supplier / Jason

`find_selectable(criteria, at)` 接收已确认 TravelRequest 与带时区时间，返回列表：

```text
{offer: SupplierOffer, price: PriceBreakdown, product: PlanningProduct}
```

这是一层明确的 Planning 适配器记录，不是在 v1 SupplierOffer 上添加未知字段。
`PlanningProduct` 完整字段见 `validate_product()` 和 `fixture_quotes()`：
productId、role、startAt/endAt、origin/destination、partySize、accessible、baggageKg、
comfort/reliability（0–1 十进制字符串）、minConnectionMinutes、openingStart/openingEnd、sourceIds。
role 为 OUTBOUND、RETURN、STAY、ACTIVITY。活动须有覆盖服务时段的营业时间证据。

所有价格是该 `quotedQuantity/unitBasis` 对应的完整包价，绝不再次乘人数。
Product.partySize 必须与请求相同；换人数需要新报价。
只接收已审核、未过期的非受限 Approved 基础报价；Planning 仍独立检查字段/金额/来源。
按完整 Supplier/PriceBreakdown schema 检查适配器输入，坏结构会中止本次处理。
有效结构但业务不可行的候选会逐一排除，保留其他可行组合。
PriceBreakdown 的优惠资格不是一个 ID 能证明的：当前 Planning 基础报价入口拒绝会员折扣报价，
待 B17 接入实时优惠资格复核后扩展；共享价格计算器本身支持一条已核验折扣。

### Reviewer / wrd

- `review(version, evidence, policies)` 返回完整 v1 ReviewResult。
- outcome 必须 PASS，subjectId/materialVersion 必须精确匹配，才能存储为已审核提案。
- 未通过审核不会生成可发布结果。需要人工审批的报价/请求目前交还共享流程处理。
- Planning 使用同一个 SQLite 文件中的 `planning_*` 表，在一笔事务保存提案/结果/trace。
- B05 可调用 `repository.find_by_case(case_id)` 汇总规划 trace，之后接入团队统一展示。
- Planning 不直接标记 Case 已关闭或响应已送达。

## 5. 硬约束的结构化绑定

v1 Constraint 只有 ID/kind/description/confirmed，没有数字阈值。
本模块不会让模型从自然语言猜阈值。PlanningSpec 为独立内部记录：

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

绑定 ID 和描述必须与确认后的 Constraint 一致，由 Operations 与用户确认后的解析层提供。
支持 BUDGET（与 budgetCeiling 完全相同）、DATES（与 travelDates 完全相同）、
ACCESSIBILITY（bool）、BAGGAGE（非负整数 kg）、ARRIVAL_TIME（带时区时间戳）、
TRANSFER_LIMIT（非负整数）。当前直达路由每方向零次换乘。
其他 kind 或未绑定/描述不匹配条件不能获得可行声明。
修改时必须有 confirmedChangedFields；隐藏改变 roundTrip 或未确认约束含义会被拒绝。

## 6. 范围、评分与版本规则

- 首个受控数据集：悉尼至墨尔本，2026-10-20 至 10-22，1 人，单程，1 个完整住宿包与 1 个活动。
- 示例地点是明确共址的城市中心；不存在暗含免费机场接驳。地点断开会失败。
- 生成器枚举直达去程、可选直达回程、一个全程住宿包和一个活动；上限 256 个组合。
- 跨多个酒店、多个中转段、多活动日程和任意自然语言偏好尚未实现。
- 往返日游可包含去程/活动/回程；单程日游与 v1 的 FEASIBLE 最少 3 项规则冲突，会显式拒绝，待全组确认 schema。
- 日期和报价当前有效性分开；fixture 时钟固定为 2026-10-12 10:00 +11:00，界面会标明。
- 舒适/可靠性评分来源于模拟产品事实。三种模式权重见 `PROFILES`，版本 `planning-demo-1.0`。
- 价格和交通时间按当前可行候选集合做 min-max benefit；同值时 benefit=1。评分不会改变硬约束。
- 广告未进入输入或评分。自由文字 preferences 被保留，但不会被假装自动满足。
- 不可行返回的是“这次给定库存内没有合格方案”，不声称全球无解。
- 需求变化创建新 versionId，baseline 内容不可覆盖。比较不把随机 itemId 当作业务变化。
- 基线与新报价时间、scopeChanged、dataRefresh 分开记录；不编造价格变化因果。
- 提案不自动采用。接受需同一对象、实时报价复核、权限/权益/审核与基线 CAS。
- 采用时保留已审核 ItineraryVersion，不改其历史内容；`planning_selected` 与 `planning_acceptances`
  单独保存选择/采用状态，`repository.lifecycle(planId)` 返回 PLANNED 或 DRAFT。
  因此历史 version.planStatus 可为 DRAFT，B07 应读取生命周期接口而不是版本快照。
- 重复接受返回既有结果，不新增订单或版本；没有任何真实或模拟订单适配器调用。

## 7. LLM 与演示状态

默认生成路径为确定性候选组合 + 工具校验 + 排序，离线不需要 API key。
增加 `--live-model` 使用 campus-qwen 提出候选、确定性工具校验和最多三轮反馈修正。
可注入共享 LLMService.explain，传入已验证事实。模型草稿单独存为 `llmDraftForReview`，
不会覆盖确定性对外建议、金额、可行性和批准状态；模型失败不破坏已有事实。
真实模型调用和受控候选反馈修正已验证；团队网页、专门异常恢复和四 Agent 端到端联调仍需后续工作。
不能用这份 FIXTURE 演示宣称真实四 Agent 产品或课程 Stage 2 已完成。

## 8. 验证与交付证据

执行 `python -m unittest discover -s tests -v`。
包含原有 13 项 B01 契约测试，以及本次规则/流程测试：预算恰好/超出、舍入和差价、
五/六天、时间与悉尼日期、库存/过期/来源、缺住宿/接驳、营业时间、三种模式共同约束、
权限/会员/审核/工具/存储失败、不可变基线、未确认修改、+15 AUD 差额、重复接受、
过期接受、并发基线变化、原子失败回滚、重启读取。
测试通过不代表 B01 四人签字、Jason peer review 或真实依赖验收已完成。

建议评审顺序：先 B04 规则及测试 → B03/B08 适配器 → B06/B07/B10 边界 → B09/B13/B14 演示。
