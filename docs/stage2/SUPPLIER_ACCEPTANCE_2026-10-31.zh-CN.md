# Supplier 与 UC-08：2026-10-31 验收证据

测试范围：Jason 的 UC-06 Supplier 流程及新增 UC-08。所有本页截图均为实际操作本地页面所得，顶部明确标注 ISOLATED UI ACCEPTANCE。认证提供方、云存储和模型使用隔离替身；门户 HTTP、业务验证、审批、定价和页面代码使用真实实现。固定测试时刻为 2026-10-31 12:00 Australia/Sydney。

这不是实际 Supabase 或课程模型成功截图，不能据此声明最终 ZIP 或全组发布验收完成。用户确认现有可运行配置在队友电脑；本机 `.env.example` 的三个 key 仍是占位符。

## 实际浏览器操作

- 普通报价：成本 AUD180，基础销售价 AUD198，差价 AUD18，高于 AUD15 门槛。Operator 先审核报价，再单独审核及交付 Operations 响应；Supplier 重新登录可读取响应和关闭记录。
- 低差价报价：成本 AUD50，加价10%后差价不足，进入 RevisionRequired，未出现可交付的成功结果。
- UC-08：EMAIL 20单位 × AUD2 + 固定 AUD10 = AUD50；保存、模型替身草拟、域检查通过，等待明确人工决定，之后批准版本1。
- 会员优惠：批准 AUD2 固定优惠，Free Traveller 在 Membership 选择服务，得到 AUD196 的独立报价。前端不显示内部成本、内部差价或审批实现字段。
- 来源响应：Free Traveller 从活动链接创建普通询问，明确同意并确认后进入 Operations，活动ID与来源通道在后端保留。
- 改预算：同一活动另建版本2、预算 AUD45，评估显示 BUDGET_EXCEEDED；旧批准不能继续使用。
- Paid广告：版本3改为 Paid 受众，评估显示 ACCESS_DENIED，不能批准。
- 本地服务重启后重新登录，保存的测试活动和优惠可重新读取。此项使用测试存储重载；另有 SQLite 新连接持久化测试，不冒充真实云端重启验收。
- 浏览器没有记录脚本错误。更细的并发、权限、持久化失败和不可变历史由自动化测试覆盖。

## 截图

- [报价审核通过](images/uc08/supplier-approved.jpg)
- [Operations 响应已交付](images/uc08/supplier-response-delivered.jpg)
- [Supplier 实际收到响应](images/uc08/supplier-received-response.jpg)
- [低差价报价被阻断](images/uc08/supplier-margin-blocked.jpg)
- [活动等待人工批准](images/uc08/campaign-awaiting-approval.jpg)
- [活动版本1批准](images/uc08/campaign-approved.jpg)
- [会员独立报价](images/uc08/member-quotation.jpg)
- [活动响应确认进入 Operations](images/uc08/campaign-response-confirmed.jpg)
- [修改预算后的失败](images/uc08/campaign-budget-blocked.jpg)
- [Paid广告受众被阻断](images/uc08/campaign-paid-ad-blocked.jpg)

## 自动化覆盖

`tests/test_campaigns.py` 包含20个验收场景，均通过真实 HTTP 门户/业务服务运行并使用明确的测试依赖：

- AC-UC08-01：缺预算、日期、目标、报价或限制，以及未确认需求，不能发明事实或获得批准。
- AC-UC08-02：报价必须当前可选；日期超出供应有效期失败；物料在草拟期间变化由版本冲突阻断。
- AC-UC08-03：预算恰好通过及超预算失败；客户端不能伪造渠道和成本。
- AC-UC08-04：未知模型输出、无模型、依赖故障及个人联系内容限制均失败。
- AC-UC08-05：未决定保持待批准；三种人工决定和新版本重新检查。
- AC-UC08-06：注入保存失败，批准、规则、历史不得部分提交；修复后允许人工重试。
- AC-UC08-07：新版本、旧操作键、过期/撤回来源与旧规则失效；原提案不被覆盖。
- AC-UC08-08：只预览，无外部发布/支出端口；活动响应经明确同意进入 Operations。
- AC-UC08-09：资格、适用报价、固定折扣与有效期交接；折后差价检查、不叠加、不改基础价、隐藏内部价格信息。
- AC-UC08-10：Paid商业广告拒绝；Paid会员不因规则存在而获得面向Free的广告响应权限。
- 补充：Operator专属权限、CSRF、严格请求字段、幂等与并发冲突，新建 SQLite 服务实例后读取提案/决定/历史，活动开始后的人工作决定，以及登录跳转保留活动来源。

## 仍需队友执行的真实环境验收

在配置齐全的电脑，用最终代码/提交包启动，真实课程模型生成一份活动草案，真实 Supabase 保存并重新登录/重启读取。复验一个成功与一个失败场景，并附代码版本、日期、角色、步骤、预期、实际和截图。之后由 Moore 审核，按 Jira 的 Definition of Done 判断是否关闭 WN5620-17。用户说明 WN5620-12 已完成小组 Demo；本次只复验新增 UC-08，不重复该整组任务。
