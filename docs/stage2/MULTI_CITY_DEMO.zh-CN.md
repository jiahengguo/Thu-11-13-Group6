# 多城市模拟供应数据与逐日规划

此入口配合 [Customer daily planner](CUSTOMER_DAILY.md)，补充云端供应目录，不是任意城市的真实旅游搜索。路线固定为 **Sydney → Goulburn → Canberra → Melbourne**，三天、两晚、一人。新增 `--multi-city` 模式不改变默认 Sydney → Melbourne 初始化。

## 准备独立场景

在项目根目录完成安装和 `.env` 配置，使用已经授权的小组云项目。以下日期用于 2026 年 11 月 5 日演示；之后使用应选择新的有效出发日和新场景名。namespace 必须与本地账号 manifest 匹配。

先预览，不访问云端或写入数据：

```sh
.venv/bin/python -m tripmate.portal.demo --multi-city
```

明确写入已有演示账户所属项目，复用其 manifest：

```sh
.venv/bin/python -m tripmate.portal.demo --apply --confirm-project https://YOUR_PROJECT.supabase.co --namespace stage2-demo --manifest .demo-accounts.local.json --scenario multi-city-20261101 --start-date 2026-11-07 --multi-city
```

Windows 将 Python 路径改为 `.venv\Scripts\python.exe`。`--confirm-project` 必须恰好等于 `.env` 中的 SUPABASE_URL；不使用 dashboard 地址，不提交 manifest 或真实密钥。

已完成场景以相同 namespace、scenario、日期和模式重跑，会返回同一批记录，不清空旧数据。若专业任务中途失败或仍为 IN_PROGRESS，先检查已有案件并按正常人工处理／重新确认流程恢复；不能保证直接重跑能重新执行已调用过的任务。普通场景不能原地改为多城场景；日期或模式变化时必须换 scenario。初始化不自动批准报价、不代替旅客确认，也不执行交易。

## 新增的十项模拟资源

时间均为 Australia/Sydney，日期随 `--start-date` 平移，跨夏令时切换使用各自日期的正确偏移。

| 名称后缀 | 第几天 | 服务时间 | 地点 / 路线 |
| --- | --- | --- | --- |
| sydney-goulburn | 1 | 08:00–09:30 | Sydney Central → Goulburn Station |
| goulburn-canberra | 1 | 10:00–11:00 | Goulburn Station → Canberra Central |
| canberra-melbourne | 2 | 09:00–13:00 | Canberra Central → Melbourne Centre |
| canberra-stay | 1→2 | 17:00–次日09:00 | Canberra Hotel |
| melbourne-stay | 2→3 | 17:00–次日10:00 | Melbourne Hotel |
| canberra-museum | 1 | 14:00–15:00 | Canberra Museum |
| melbourne-gallery | 2 | 15:00–16:00 | Melbourne Gallery |
| morning-museum | 3 | 10:00–11:30 | Melbourne Museum |
| outdoor-garden | 3 | 14:00–15:30 | Melbourne Garden（与下一项二选一） |
| indoor-aquarium | 3 | 14:00–15:30 | Melbourne Aquarium（与上一项二选一） |

每项为明确模拟的一人完整套餐，成本 AUD180，沿用现有演示定价：加价10%、最低差价 AUD15，因此基础销售价 AUD198。固定同价只用于可重复演示，不是市场价格。资源可用数量为1，含强制费用，来源为 `synthetic://multi-city/...`，有效期至第四天23:00。活动开放时段08:00–20:00。

每个生成方案使用三段交通、两项住宿和四项活动，9 × AUD198 = AUD1782；三天餐费预算3 × AUD40 = AUD120；模拟转场附加费为0，合计 **AUD1902**。初始总预算为 AUD2500。任何报价版本、成本、优惠、人数或餐费变化后应重新计算，不把此数字硬编码为审批依据。

## Operator 审核后才能在目录选择

初始化输出 `supplierCases`，键为上述后缀、值为实际案件 ID。Supplier 可查看待审核报价；Operator 在 Work queue 搜索相应 ID，核对明确模拟的来源、有效期、数量和定价，填写理由并 **Record offer review → PASS**。十项均审核通过后，旅客目录才有完整的多城候选。

报价评审与 Operations 外发响应审批不同；不通过修改数据库状态或伪造 Approval 来把未审核资源塞入目录。脚本返回 `operatorReviewRequired: true`，没有绕过这一关。

## 旅客怎么使用

### 直接使用初始化草稿

Free/Paid 各有一份未确认的多城草稿，ID 在输出 `travellerDrafts`。登录相应账号，在 **Requests & support → Continue draft** 打开对应草稿，核对三天日期、全部允许的资源 ID、逐日地点、餐费和模拟因素假设，明确确认后再 Start processing。

草稿使用云端实际创建的 offerId，不使用离线 daily_fixture 的短 ID。第三天下午的园林／水族馆为同一时段的备选资源，不能解释为同一方案连续参加两项。方案仍须经过 Operator 响应审核、交付后，旅客才能比较及采用。

### 自己在新编辑器选择

1. **Plan a trip / new request** 填相同三天日期、1人、AUD2500预算。
2. **Multi-city / daily itinerary → Load available services**，只选本轮 namespace/scenario 的资源，避免混入其他日期的报价。
3. 选三段交通、两项住宿、Canberra Museum、Melbourne Gallery、Melbourne Museum，再选 Garden 或 Aquarium 其中一项，共9项。
4. 点击 **Set daily stops from travel dates**，逐日填：

| 天 | Start location | End location |
| --- | --- | --- |
| 1 | Sydney Central | Canberra Hotel |
| 2 | Canberra Hotel | Melbourne Hotel |
| 3 | Melbourne Hotel | Melbourne Centre |

5. 每日餐费40；核对页面的限时、步行、活动和休息规则，明确勾选模拟因素同意，再 **Apply daily itinerary to request**。
6. Review request，核对完整摘要后确认并处理；继续遵循正常审核、交付与采用流程。

## 模拟因素与边界

PR #46 的 CustomerDailyFactors 会为明确确认该模式的请求提供：交通准点、场馆可用、20°C／无雨、地点之间30分钟步行和0附加费用。它们是明确同意的测试假设，不是实际天气、距离或预订。有效期固定为请求确认后24小时；刷新不能延长，过期需要重新确认。手动上传其他逐日策略时仍需 Operator 提供匹配、有效的因素。

本改动同时修正确认后 `描述: JSON值` 的模拟标记识别，使真实 Operations 确认上下文能使用上述显式模式。不会让未确认或无标记的请求自动获得模拟因素。

缺城市、未审核、过期、零库存、衔接不兼容、预算不足仍应阻断或转人工；本数据不扩展为任意路线搜索。真实云端初始化、隔离集成验证和真实浏览器验收应分别记录，不能把生成数据或自动化通过写成浏览器全流程通过。

## 2026-11-01 实际准备与验证状态

基线为 main `fbb709d`（PR #46），修改位于独立分支 `codex/multicity-demo-data`。完整隔离后端回归 **388/388 通过，291.092秒**。新增验证覆盖：十项报价审核前不可选、审核后实际 offerId 绑定、三段交通与餐费总价、Operator 响应审核／交付与旅客采用、场景模式防覆盖、夏令时日期偏移。默认初始化仍通过原有测试；dry-run 明确 `cloudWrites: false`。

真实共享云端尝试准备 `stage2-demo / multi-city-20261101`，出发日2026-11-07，未改原有场景。因 `tripmate_state()` 反复超时，**没有完成整组云端准备，也没有完成本轮浏览器验收**。按案件范围只读核对的停止状态：

| 已保存资源 | Case ID | 状态 |
| --- | --- | --- |
| sydney-goulburn | `6c605441-4b5e-458b-b349-d1bddc950eac` | UNDER_REVIEW，尚未批准 |
| goulburn-canberra | `38198aa1-ba6b-4be0-bc2d-909d749dae5b` | IN_PROGRESS，需检查中断处理 |

尚未生成整组 Free/Paid 草稿、尚未审核十项资源，当前共享目录不能视为已具备完整路线。用户提供的23:02:29及23:02:40数据库日志均为 SQLSTATE 57014 / statement timeout，对应 `tripmate_state()`。没有清空共享数据、放宽审批、调整数据库超时或关闭版本保护。恢复云服务后，先核对上述已有案件，再继续本场景；不要靠反复换 scenario 创建重复资源。

隔离集成成功只证明所补数据、确认标记和现有业务校验能衔接，不代表这次共享云端写入全部完成。人工准备、接口验证、真实模型与真实浏览器结果分别签收。
