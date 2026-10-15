# 逐日规划与旅游影响因素后端

日期：2026-10-14。按用户确认，先实现接口与模拟联调，不选择或假装连接真实天气/地图/预约供应商。

## 已实现的新增行为

| 因素 | 数据与实际规则 |
| --- | --- |
| 天气 | 每个活动时段/地点的预报；户外检查降雨概率、温度、风速和严重天气标记；阈值由用户确认 |
| 交通延误 | 精确交通报价版本的状态、出发/到达延误；使用有效时间计算衔接，取消/未知状态拒绝 |
| 实际地点间移动 | 查询有起终点和时段覆盖的路线估计；移动时间、步行时间和全团费用进入计划，缺失不假设免费瞬移 |
| 每日体力负担 | 每日步行分钟、活动分钟、连续安排时长上限；超限方案被排除，符合要求的候选按负担调整舒适评分 |
| 用餐与休息 | 在确认用餐窗口内分配不重叠的用餐时段，显示可用休息时段；餐饮预算预留计入总价 |
| 开放日期与预约 | 用具体日期的开放区间与临时关闭区间检查活动；核验该报价版本的剩余名额及预约可用状态 |
| 多城市/多段交通/多个活动 | 逐日地点、多个交通和活动槽位、分城市住宿；检查每晚覆盖、当地移动和中转次数 |
| 采用前复核 | 重新读取外部因素；数据过期、来源冲突、快照变化均阻止旧版本被直接采用，要求重生成与确认 |

这不是医疗建议或天气安全保证；体力和天气阈值是明确的用户容忍度，不是模型决定的安全标准。
预约 AVAILABLE 表示可预约，不代表占位成功；餐饮为时间和费用预留，不代表餐厅推荐或订位。

## 运行后端示例

```powershell
.\.venv\Scripts\python.exe -m tripmate.planning.daily_demo
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_daily_planning.py -v
```

输出 `output/daily-planning/report.json`（全记录）和 `report.md`（按时间排列的后端报告）。
需要真实课程模型时增加 `--live-model`；仍使用模拟旅游数据，需本机 key 和 VPN。
本次模型反馈修正测试使用明确的模型替身，不作为新的真实 LLM 成功证据。

场景：10/20 悉尼 → Goulburn 中转 → 堪培拉，10/21 到墨尔本，10/22 两个活动。
包含 3 段交通、2 个住宿包、4 个活动、5 次用餐时间预留及当地步行衔接。
模拟降雨 0.85 高于确认阈值 0.60，户外花园被拒绝，改用室内水族馆。
通过方案 AUD 851.50 = 报价项目 AUD 731.50 + 三天餐饮预留 AUD 120.00；示例当地路线为有证据的免费步行。
时间和事实均明确标为模拟，验证时钟固定 2026-10-12；不是实时天气或实时班次。

## 接口 1：确认逐日策略

不改变共享 v1 对象结构。Operations 输入 `constraints` 新支持特定的 OTHER 绑定：

```python
{"kind": "OTHER", "description": "Confirmed daily policy", "value": daily_policy}
```

`daily_policy` 的全部字段：

| 字段 | 内容 |
| --- | --- |
| version | 固定 `daily-1` |
| days | 1–14 个连续日历日；每项 date/startAt/endAt/startLocation/endLocation |
| slots | 3–48 个需填入的服务槽位；每项 id/role/offerIds，role 沿用 OUTBOUND/RETURN/STAY/ACTIVITY |
| limits | maxWalkingMinutes/maxActivityMinutes/maxContinuousMinutes/minRestMinutes 为正整数；maxRainProbability/minTemperatureC/maxTemperatureC/maxWindKph 为十进制字符串 |
| mealWindows | 每日窗口：start/end 为 HH:MM，minutes 为预留时长；按悉尼当地时间计算 |
| mealBudgetPerDay | AUD Money；每天的全团餐饮预留，已纳入确认 |

可运行完整策略见 `daily_demo.daily_fixture()` 返回的 context.spec.constraintBindings.daily.value。
Operations 会将策略写入确认后的 TravelRequest.hardConstraints 和 PlanningSpec.constraintBindings，
修改策略需重新确认并产生新的约束版本；不能只改内部 spec 绕过确认。
自然语言模型提取还没有自动生成这份复杂策略；当前通过结构化输入接入。

槽位定义要安排什么和可选报价，生成器选择每槽一项并计算日程，不再固定三个报价。
可支持多站多段，但目前不是无限范围自动搜索全球路线：需要 Supplier/Operations 提供可选城市、日期和服务槽位。
默认最多枚举 256 个组合，超过会明确失败；模型模式每轮最多 8 套候选、默认最多 3 轮，通过工具反馈调整选择。
不支持跨午夜交通；延误导致跨日会被拒绝，不能将这种情况误报为可行。

## 接口 2：外部旅游因素

`tripmate.planning.factors.TravelFactorService`：

```python
snapshot(request: dict, quotes: list, at: str) -> dict
```

返回恰好 `sources/weather/delays/routes/venues` 五个数组。实际供应商适配器可以组合四种 API，
但不把未经证实的 LLM 文字当作来源。snapshot 应返回同一次评估的快照。

sources 使用共享 SourceReference 格式。每条 fact 都必须包含：

```text
capturedAt: 带时区的数据采集时间
validUntil: 当前数据新鲜度截止时间，不是活动日期
sourceIds: 对应 sources 中的证据 ID
```

fact 还需要下列字段：

| 数组 | 必需业务字段 |
| --- | --- |
| weather | location、startAt/endAt（预报覆盖时段）、rainProbability/temperatureC/windKph（十进制字符串）、severe（bool） |
| delays | offerId、offerVersion、status（ON_TIME/DELAYED；CANCELLED 或未知状态拒绝）、departureDelayMinutes/arrivalDelayMinutes（非负整数） |
| routes | origin、destination、startAt/endAt（路线估计覆盖时段）、minutes、walkingMinutes（整数）、partySize、cost（对应该人数的完整 AUD Money） |
| venues | offerId、offerVersion、openIntervals/closedIntervals（每项 startAt/endAt）、reservationRequired（bool）、reservationStatus（AVAILABLE 或 NOT_REQUIRED）、remainingCapacity（人数）、outdoor（bool）、walkingMinutes（整数） |

关键约束：

- 数据采集不晚于校验时间，validUntil 必须在校验时刻之后；来源重复/冲突、缺失或过期不能通过。
- 预报/路线覆盖服务时段，不能用今天的数据无限推断未来；没有所需日期的预报则该方案不能获得通过声明。
- 交通/预约必须绑定精确报价 materialVersion，不能拿其他日期或其他团体的名额代替。
- 多条可匹配事实属于歧义，适配器需要先消歧；系统不偷偷挑最乐观的一条。
- REAL 执行模式拒绝 simulated=true 的来源。本次只提供 FixtureTravelFactors，不包含真实供应商密钥或外部 endpoint。
- 当前保守地对整个返回快照做新鲜度和采用前一致性检查；无关数据更新也可能要求重新生成。供应商适配器应缩小快照范围。

## 接口 3：接入已有 Operations/Planning

```python
from tripmate.operations.integration import connect_planning

connect_planning(
    operations, offers, reviewer, planning_repository,
    factors=travel_factor_service,
    planner_factory=optional_model_planner_factory,
)
```

或直接 `PlanningRuntime(..., factors=travel_factor_service)`。
已确认 daily-1 策略存在时自动走 DailyPlanningEngine；没有策略时保持原有模式以兼容其他成员。
有策略但没有 factors 服务会返回 TOOL_UNAVAILABLE，不暗中回退简单规划。
现有 B03 数据没有多城市/因素数据，因此旧工作台启动参数不会自动提供这些能力；需要注入扩展报价与因素适配器。

## 输出、审核与采用

- `ItineraryVersion.items` 保留供应商原定服务时间，`dailySchedule.timeline` 保存延误后的有效时间、当地交通、用餐和休息。
- `version.totalPrice` = 原报价合计 + 日程当地交通估计费用 + 确认餐饮预留，不能再只加 items 得到总价。
- 内部 record 增加 `dailySchedule` 和 `factorSnapshot`，不向严格 v1 对象增加未知字段。
- 审核版本的 assumptions 记录因素快照摘要，sourceReferences 包含因素证据，validationResults 包含确定性因素检查。
- Operations 受控 `plan_view` 在交付后返回允许展示的 dailySchedule 字段，不返回原始因素快照或供应商成本。
- 排序考虑当地交通/延误后的旅行时间及完整费用；舒适度按最大每日负担比例折减最多 25%，配置版本 `daily-1`。
  天气、开放、预约等先作为硬门槛；不是让评分覆盖不满足条件的方案。
- 修改仍是不可变版本；采用前数据变化需要重新生成和确认，不自动订位，不覆盖用户旧方案。
- 当前 dedicated Exception 恢复仍未实现；遇到采用失败交回 Operations，不宣称已经完成 UC-03 自动异常恢复。

## 本次测试范围

多城市/中转/多活动、天气室内替代、延误衔接失败、取消、缺路线/预报、过期因素、闭馆/名额不足、
步行/活动/连续时长超限、用餐冲突、餐饮计入预算、路线人数基准、住宿城市、因素变化后拒绝采用、
重复采用、确认修改、模型反馈修正、缺适配器、实际 Operations 确认→派发→审核→交付→日程读取→采用。
模拟测试能证明规则执行，不能证明未来真实第三方 API 可用或数据准确。

本次完整回归：171 项测试全部通过，其中逐日模式新增 21 项；`python -m tripmate.planning.daily_demo` 实际运行成功。
