# 门户接口与模拟数据接入

## 已接通

- 旅行因素：Operator 在已确认的规划／修订／取消案件中上传 JSON；GET/POST `/api/planning/factors` 查看与保存。来源必须标记 simulated，记录绑定案件及确认内容；历史不可覆盖，重放同一操作不重复写入。缺少、过期、撤销操作者权限的数据阻断规划或交付。
- 逐日规划：Traveller 在行程表单上传 daily-1 日程策略，检查请求摘要后确认；Operator 上传对应天气、延误、路线、场馆快照。生成、域审核和采用都使用相同因素接口。多段交通、多活动、休息和用餐规则沿用既有 daily 引擎。
- 逐日恢复：为取消案件记录自己的因素快照。恢复保持确认的要求及允许的候选服务，保留未受影响的服务，检查后续衔接；餐饮和路线附加费用参与总价及预算核对。原策略中没有允许的替代资源时转澄清／人工处理，不能擅自扩大选择范围。
- 会员优惠：Membership 查询折后报价并取得 quotation reference；在旅行表单中选择该引用。一个确认请求只选择一份报价，不叠加。行程总价、比较、采用和修订均使用该报价；每次重新查询会核对当前会员、活动审批、供应版本、定价配置、有效期和差价。撤销活动或改变价格后旧报价不能授权新的交付／采用。修改优惠需获取新报价并重新确认，历史保留。
- 投诉：只有 DELAY 强制要求实际到达时间；其他类别记录服务证据并进入现有调查／人工处理。
- 模型：共享后端模型服务配置见 DEMO_MODEL_KEYS.zh-CN.md；模型输出继续经过确定性校验和审批。

## 准备模拟输入

运行 `python -m tripmate.planning.daily_demo --output output/daily-planning` 可生成 daily-policy.json、travel-factors.json 和完整示例报告。这是固定时间和固定库存的格式示例。上传到门户前，必须把策略中的 offerIds、因素的 offerId/offerVersion 改成当前已审核供应商目录中的标识，并提供覆盖当前演示时间的真实或明确模拟来源、有效期及行程日期。系统不会把过期模板伪装成当前证据。

策略包含 days、slots、limits、mealWindows、mealBudgetPerDay。因素包含 sources、weather、delays、routes、venues。每条因素必须引用 sources 并记录 capturedAt/validUntil。天气和场馆事实需要覆盖实际活动，路线需要覆盖实际地点衔接。未知数据保留为空并阻断缺少依据的结果，不生成默认好天气或零费用转场。

`Portal/make_server(travel_factors=provider)` 可替换为真实 TravelFactorService；接口是 `snapshot(request, quotes, at)`。默认使用上述已授权、持久化的模拟输入。配置提供方失败会返回错误，不悄悄换回模拟值。暂不提供第三方天气、交通或支付供应商的真实凭据和生产业务规则。

## 开发与验收边界

此改动接通原型内接口，不包含真实订票、支付、退款或广告发布。恢复完成是操作员记录的模拟凭据。到期提醒沿用显式 CHECK_WAIT 操作。真实 Supabase／课程模型演示、跨机器 ZIP 复现和团队签字单独验收。
