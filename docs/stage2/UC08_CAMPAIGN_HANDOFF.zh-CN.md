# Jason：UC-08 营销活动实现与交接

对应 Jira WN5620-17 / B16、SUP-03、SUP-AH-02、UC-08。基于 main `2178568`。

## 已实现

- Operator 门户新增 Campaign proposals，访问 `/campaigns`；Supplier 和 Traveller 无管理权限。
- 明确确认活动目标、非个人化受众、渠道、日期、预算、投放单位数、内容限制及已批准报价。
- 复用 SupplierGateway 读取当前可用报价，保存确切供应商版本、来源、价格和条款。
- 课程模型通过现有 extract 端口选择受约束文案；价格和条款由服务端来源生成，不能由模型发明。
- 模拟渠道成本使用 Decimal 运算。EMAIL 为每单位 AUD2 加固定 AUD10；SOCIAL 为每单位 AUD1 加固定 AUD5。配置在 `CHANNELS`，修改政策需更新 `POLICY`；这些是原型配置，不是真实广告平台定价。
- 确定性检查预算、日期、来源和配置的内容/隐私限制；商业广告面向 Paid 会员时失败。
- 复用共享 DeterministicReviewService，注册 CampaignProposal 域检查；通过后仍待人工批准。
- Approve / Request revision / Reject 绑定确切物料版本、审核、操作者、理由和时间。
- 修改另建版本；旧提案与决定保留，旧批准及会员规则不能继续授权新版本。
- 已批准会员优惠交给 UC-07 检查资格、UC-06 计算独立客户报价；优惠不得叠加，折后差价不足则阻断，不改写基础报价。
- Traveller 的 Membership 页可选择当前合资格服务并请求折后报价，不显示内部供应成本或差价。
- 明确同意的模拟活动响应保留 campaignId/sourceChannel，并进入 Operations 的确认流程。
- 存储、决策、版本失效与轨迹使用现有原子事务及幂等操作键；无新增数据库迁移或公开权限。

## 队友电脑上如何复验

1. 使用合并后的代码，保留现有私有 `.env` 和演示账户文件。`.env.example` 中的课程模型 key、Supabase publishable key 和 server secret 仍为占位符，不能直接当作真实连接。
2. 按 README 安装/启动；在校园网或 VPN 下确认课程模型和云端预检通过。不要重放初始化建表，也不要清理共享历史。
3. Supplier 创建有效报价，例如成本 AUD180、配置加价10%和最低差价 AUD15。Operator 完成报价审核。
4. Operator → Campaign proposals，选择该报价，设置覆盖报价有效期以内的活动日期、Free 受众、EMAIL、20单位、预算 AUD50，以及默认内容限制。确认保存，再 Draft and evaluate。
5. 应看到 AUD50 总成本、来源和 PASS，状态为 Awaiting approval；未决定时不能当作已批准。
6. 可选会员优惠设置 AUD2、Free资格、活动期内的有效日期。批准后在 Free Traveller → Membership 应看到优惠；有效期已开始时，检查报价应得到 AUD196，内部差价仍通过，基础价保持 AUD198。
7. 使用已登录的 Free 账户打开活动预览里的来源链接，明确勾选同意，再确认普通请求。应进入 Operations 并保留活动来源。模拟响应不是自动广告发布。
8. 修改预算为 AUD45，确认保存并重新评估：应 RevisionRequired，不能沿用旧批准。改为 Paid 广告受众也应失败。
9. 分别验证 Request revision、Reject、过期/撤回报价、保存失败和重启读取。失败注入在隔离测试执行，不通过破坏共享云服务制造故障。

## 实现边界

活动文案是模型辅助的受约束生成，不是自由文本广告生成器；支持的三项内容限制已列在默认表单及契约中。新限制需要实现对应检查，不能假装已自动理解任意规则。

本次完成会员优惠规则及独立报价交接；完整地图、Free 广告展示、折扣行程采用及其他 Operations/Planning 剩余验收不属于本卡全部完成的声明。没有真实发布、花费、订票或支付。

## 验证与任务状态

见 [Supplier 与 UC-08 验收证据](SUPPLIER_ACCEPTANCE_2026-10-31.zh-CN.md) 和
[Campaign 原型契约](../contracts/v1/Campaign_Prototype.md)。自动化及隔离浏览器验证不能替代真实 Supabase/课程模型、最终 ZIP、新电脑与四位组员的验收。

WN5620-17 仍需要 Moore 同伴审核、合并和真实环境证据。用户说明 WN5620-12 已完成小组 Demo，本次不重复开展其整组验收，也不以新增 UC-08 的复验撤销原 Demo 结果。没有自动修改 Jira 状态。

## 可用于个人贡献说明的文字

Implemented the Supplier Partnership UC-08 campaign workflow in the authenticated Operator portal, including approved-offer evidence, deterministic simulated budgets, constrained model drafting, domain review, version-linked human decisions, member-offer eligibility and separate customer pricing. Added automated boundary tests and labelled local browser evidence for Supplier and campaign flows. Real cloud/model acceptance of this new feature and peer review remain separate from the completed group Demo.
