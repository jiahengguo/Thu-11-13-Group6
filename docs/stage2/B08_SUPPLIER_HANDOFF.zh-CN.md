# B08：供应商报价评估与定价交接

负责人：Jason。对应 UC-06、SUP-01、SUP-02、AD-04、SD-04、SM-04。
代码位于 `src/tripmate/supplier/`；`SupplierPartnershipAgent(runtime)` 调用实际流程，
未注入 runtime 的共享组合仍显式返回 STUB。

## 已实现的流程

1. 接受 Operations 确认的 Supplier Case，检查请求状态与源数据访问权限。
2. 分配新的 materialVersion，并立即停止旧版本的可选资格。
3. 接受已确认的结构化源数据，或通过共享 LLMService.extract 提取。LLM 只能输出
   来源业务字段，不能设置 ID、版本、状态、审核或审批。独立核实的成本与报价数量基础
   必须保持不变；来源引用由后端提供。
4. 拒绝缺字段、非 AUD、有效期外、库存不足、负成本、缺强制费用或空白取消条款。
5. 调用 B04 PricingService.calculate，再独立检查成本、数量基础、配置版本、
   ROUND_HALF_UP 两位小数、basePrice/sellingPrice/marginAmount 及最低差价。
   B08 处理可重复使用的基础报价，折扣为零；会员折扣留给 B17。
6. 调用 B10 Reviewer，核对当前对象、版本、全部来源及审核时间。未知商业条款默认
   请求人工审批；只有确定性配置中明确允许的普通条款可免于该项审批。
7. 保存审批请求和 Trace 后保存 Supplier 快照；保存失败不会返回成功，也不会留下可选报价。
8. 消费 B10 已持久化的明确人工决定；必须匹配对象、版本、reviewId、scope、来源和时间，
   并通过后端操作员权限检查。批准也不执行真实供应商承诺。

新材料版本清除旧审核和审批资格；历史版本保留。失败修订也保留供应商所有权，
不同供应商不能接管同一个 offerId，FIXTURE/REAL 不能共用同一报价身份。
较晚返回的旧评估不能覆盖更新版本。

## Planning 提供接口

`SupplierRuntime.find_selectable(criteria, at)` 实现共享 ApprovedOfferLookup：

- 支持 offerId/supplierId/productId/productType 筛选，或完整的已验证 TravelRequest。
- 返回当前 APPROVED、有效、库存充足、价格与当前配置一致的报价。
- 受限报价再次检查其当前、唯一、已授权的人工批准。
- Planning 请求只返回有匹配来源的 product 元数据的
  `{"offer": SupplierOffer, "price": PriceBreakdown, "product": ProductSpec}` bundle。
- Planning 仍负责预算、行程时间、换乘等整体可行性检查。

实际 B04/Planning 接入测试把 `planning_runtime.offers` 设置为 SupplierRuntime，
无需修改 Moore 的代码。

## 模拟演示

需要先合入 Moore 的 B04/Planning 分支。B08 不复制或重写他的定价实现。

```powershell
$env:PYTHONPATH="src"
python -m tripmate.supplier.demo --scenario coach
python -m tripmate.supplier.demo --scenario zero-stock
python -m tripmate.supplier.demo --scenario pending-approval
python -m tripmate.api.server --port 8765
```

网页新增 Supplier assessment，可手动选择有效报价、过期、零库存、缺成本、USD、
缺取消条款和等待人工审批。API：`POST /api/supplier-demo`，
请求体 `{"scenario":"coach"}`，沿用本地 JSON/token 限制。
没有 B04 时返回明确的 TOOL_UNAVAILABLE，页面禁用演示按钮。

模拟演示用实际 B04 定价，LLM 提取是已知 JSON 重放；Access、Reviewer、Trace 和
Approval 也是明确命名的 FIXTURE adapters。它们不能作为真实 B05/B07/B10 的完成证据。
演示不会自动批准受限条款，也不会调用真实 AI。

演示写入独立的 `*.supplier-demo.sqlite3`。Reset 只清理其中 B08 的四张已知表，
不会清除共享数据库内的 supplier_*、Planning、审批或 Trace 记录。

## 团队接入依赖与完成范围

SupplierRuntime 注入：load_input(caseId)、SupplierRepository、B04 PricingService、
PricingPolicy、B10 ReviewService、B05 TraceRepository、B10 ApprovalRepository、
B07 AccessControlService，以及可选共享 LLMService。
load_input 提供 offerId、sourceReferences 和 candidate；文本提取路径提供 sourceText
与 verifiedFacts（至少包含 supplierCost、quotedQuantity、unitBasis）。
给 Planning 使用时还需匹配 productId/sourceIds 的 ProductSpec。

B08 的实现和 FIXTURE 集成可本地验证。真实共享服务接入、校园模型提取、Moore 评审和
Jira/PR 证据仍需团队完成；四 Agent 的统一编排属于 B11。

执行 `python -m unittest discover -s tests -q`。独立分支没有 B04 时跳过四项集成测试，
合入 Planning 后运行全部测试。最终 Windows 检查记录见 B08_TEST_RESULTS.md。
