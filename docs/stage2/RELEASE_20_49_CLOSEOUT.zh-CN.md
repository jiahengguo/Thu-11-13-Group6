# WN5620-20 / 49：实现范围、验证入口与签收

日期：2026-11-01，Australia/Sydney。检查基线：main `c14b83e`。
两张卡均由 Runda 负责；20 指定 Jiaheng 复核，49 的另一位复核成员由负责人确认。Supplier/Campaign 证据由 Jason 提供，Planning 由 Moore 提供。
本记录补充默认认证门户的 HTTP 验收，不替代组员实际复核或真实服务验收，也不自动改变 Jira 状态。

## WN5620-20：最终发布验证

最新代码已经包含三组场景脚本 `scripts/verify_release_scenarios.py`。本次将 SM-03 的四个关单/人工接管边界补进 `tests/test_exception_portal.py`，它们因此也会随第二组场景连续重放两轮。

三组证据的实现位置和负责模块如下：

- Planning / membership：`tests/test_planning_portal.py`、`tests/test_operations.py`；Moore / Jiaheng。涵盖确认、规划、权限、审核、采用、版本与会员限制。
- Disruption / complaint：`tests/test_exception_portal.py`、`tests/test_complaint_portal.py`；Runda。涵盖调查、恢复建议、受限批准、失败、当前版本选择、拒绝、人工接管和未解决关单。
- Supplier / campaign：`tests/test_supplier_portal.py`、`tests/test_campaigns.py`；Jason。涵盖来源、报价/差价、审核、营销预算、版本批准、会员优惠和有来源的模拟响应。

脚本每次为各测试创建隔离新数据，不会重置共享 Supabase。输出保留实际提交、源文件摘要、工作区是否修改、轮次、模块、测试数量、跳过数量和结果。退出成功但零测试、缺失结果摘要或存在跳过项，均不再算本组验收通过。

复现命令（使用已安装本项目依赖的 Python）：

```sh
python -m unittest discover -s tests -q
python scripts/verify_release_scenarios.py --output output/release-20-49-evidence.json
```

两轮自动重放与最终发布演示是不同证据。组员还应使用最终发布版本，在一台配置齐全的电脑上记录两轮三组页面路径：

1. 准备独立的模拟演练数据/场景，不清空共享历史；记录 main 提交或 ZIP 校验值。
2. 每组保留一个成功路径、一个有意义的失败或待批准路径，以及对应案件/活动引用。
3. 覆盖至少一次越权拒绝和重启读取。根据课程要求记录真实云/模型检查，不能把隔离替身写成真实服务成功。
4. 第一轮、第二轮分别记录实际结果；若复用已有最终版本的有效记录，应注明原记录，不假装重新操作。
5. Runda 汇总，Jiaheng 核对，相关模块成员确认各自证据。若存在未完成的 Must 或阻断缺陷，20 继续保持未完成；Should/未来项单独列出。

这项验收可由队友已配置的电脑执行，不要求 Jason 再单独部署。WN5620-12 已完成的 Demo 不被本记录撤销。

### 本次自动执行结果

代码提交 `94e2825`、干净工作区下，完整回归 **356/356 通过**（212.943秒）；三组场景各重放两轮，合计 **200 次测试执行全部通过、0 跳过**。Planning/会员每轮46次，异常/投诉每轮22次，Supplier/Campaign每轮32次。机器记录见 [两轮原始结果](release-20-49-evidence.json)。新增4条认证门户边界与5条证据判定检查的专项测试也已通过。

此处的“通过”仅指实际执行的自动化断言；不是组员手工演示或签收。

## WN5620-49：已约定的 SM-03 子集

依据卡片 2026-10-15 的负责人记录：支持选择、审批、拒绝、交付和关单，自动提醒暂缓。本次不新增期限、提醒次数或重试上限，也不将建议交付等同于旅行恢复。

默认门户当前采用以下状态与责任边界：

- `AWAITING_HUMAN_APPROVAL`：受限提案等待 Operator 明确决定；Traveller 无建议可选，不能提前关单。
- `UNDER_REVIEW`：提案或选择的外发响应仍需审核；选择建议本身不能直接完成关单。
- `AWAITING_TRAVELLER_DECISION`：Operations 已交付建议，等待 Traveller 明确选择或拒绝；重新打开/重启不产生超时决定。
- Traveller 选择当前 `runId` 的确切选项后，重新进入响应审核；再次交付后为 `RECOMMENDATION_DELIVERED`。
- Traveller 明确拒绝，或 Operator 记录无人回应并明确 Take over 后，为 `HUMAN_TAKEOVER` / `HUMAN_ASSISTANCE`。
- Operator 在已交付推荐或已人工接管后，才可填写理由关单。结果为 `CLOSED_UNRESOLVED`；不产生 Resolved、改签、付款或旅行恢复的声明。

提醒、期限与外部动作完成证据仍属于暂缓/未来范围。若小组决定将它们列入本阶段，须先由负责人确认规则及模型变更，再实现；当前不能虚构默认值来关卡。

### 新增默认门户验证

以下测试通过现有认证、CSRF、权限、版本和 Operations HTTP 端点执行；使用隔离云/账户与模拟资源：

- `test_decline_through_authenticated_portal_keeps_case_unresolved`：拒绝后转人工；Traveller 关单 403，空理由失败，Operator 可带理由关闭为未解决。
- `test_no_response_uses_explicit_operator_takeover_without_invented_deadline`：等待/重启保持开放；明确人工接管后才允许带理由关闭，无自动提醒或截止时刻。
- `test_pending_recovery_cannot_be_selected_or_closed_before_human_decision`：待人工作决定不能选择或关单；拒绝后人工处理，不执行外部交易。
- `test_selection_requires_followup_delivery_before_reasoned_unresolved_closure`：选择后不能绕过再次审核交付；交付后关单仍为未解决。

所有路径核对原行程版本不变、最终关闭事件及理由可追溯。现有测试继续覆盖旧提案、证据变更、审批分离、来源私密性和保存失败。

### 组员最后需要确认

Runda 和复核人应在最终页面检查以上四条路径，保留等待、拒绝/接管、再次交付和带理由关单的关键结果。确认沿用已记录的暂缓范围后，将真实复核人、日期、版本和证据链接填写到原卡。只有范围和证据都签收后，才判断能否关闭 49。

## 边界

自动测试通过证明实现和列出的约束，不代表真实 Supabase、课程模型、新电脑最终 ZIP、人工页面操作或独立组员审核已经通过。此前各卡的 Done 状态不由本记录重新推断；20 和 49 保持由实际负责人签收。
