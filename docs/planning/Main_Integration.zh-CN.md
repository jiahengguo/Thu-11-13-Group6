# Planning 与 main 联调说明

日期：2026-10-13。集成基线：`a1605f4`（main，已合并 Operations PR #13、Portal PR #12、Supplier 基础设施 PR #10）。

## 已确认的主分支能力

- Operations：实际需求收集/确认、Case 管理、权限、会员权益、统一响应审核/交付、行程读取/采用。
- B03：Jason 提供的 SQLite 模拟供应商产品、报价与价格数据；不是正式 Supplier B08 Agent。
- Portal：Supabase 登录与角色隔离；本次没有操作云端用户/数据库，也没有将模拟权限注入 Portal。
- Supplier Agent、Exception Agent、共享自动 Reviewer 在这个 main 基线上仍未实现/接入。
  其他远程分支的存在不代表它们已合入 main；本次不擅自合并其他成员未合并的工作。

## 本次修改

1. 合并 main，保留 Supabase 配置、Operations 代码、B02/B03 基础设施和 Planning 的 tzdata 依赖。
2. 复用 `operations.integration.connect_planning` 与 `CaseEntitlements`，不再在联调路径使用 Moore 的模拟身份/会员服务。
3. 新增 `planning.integration.B03ApprovedOffers`，从 Jason 的数据库读取当前报价，不复制自己的 fixture 列表。
   读取时排除非 APPROVED、过期、需审批、错误、审核版本不匹配和库存不足报价，Planning 再校验完整数据。
4. 保持正式 Reviewer 依赖显式注入；仅在开发联调显式启用 `WorkbenchFixtureReviewer`，并在 status 中标明。
5. 新增按 Case 创建模型 planner 的 factory，避免跨请求共享可变模型尝试记录。
6. Integrated Planning 使用共享 SQLite 中的 `planning_*` 表；旧 `/api/planning-demo` 继续使用独立 demo 数据库。
   B03 reset 不删除共享 Planning 版本或 Operations 记录。
7. 修复跨分支验收脚本在 Windows 上未关闭 SQLite 连接、导致临时数据库清理失败的问题。

## 启动实际 Operations + B03 + Planning 联调

从仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m tripmate.api.server --workbench --planning-fixture --port 8765
```

打开 `http://127.0.0.1:8765/operations`。选模拟 Paid traveller，输入悉尼至墨尔本、
2026-10-20 至 10-22、1 人、AUD 450、VALUE，确认后继续处理；切换模拟 Operator 审核，
再以旅客身份接收响应、查看行程并明确采用。Free fixture 已有两条 Planned/Active 行程，应被规则拒绝新增。

需要真实课程模型参与候选生成时：

```powershell
.\.venv\Scripts\python.exe -m tripmate.api.server --workbench --planning-fixture --planning-live-model --port 8765
```

先在本地 .env 配置 key，并连接可访问校园代理的网络。不要覆盖已有 .env。
该路径每次模型请求 20 秒、最多两轮，Operations 等待上限 60 秒。
单轮失败不会伪装为离线成功；Operations 会按其规则保留上下文并进入人工处理。
开发时钟固定为 `2026-10-12T10:00:00+11:00`，在 status 的 fixtureTime 标明；这不是当前真实业务时间。
Supplier 数据和 Reviewer 仍为 fixture，真实模型不改变这个标记。

不加 `--planning-fixture` 时保持原工作台行为，不自动注入通过的 Reviewer。
默认不加 `--workbench` 仍启动现有 Supabase Portal。此 Portal 未自动启用本开发组合；正式接入应注入真实报价、Reviewer 和匹配云持久化需求的 Planning repository。

## 现有 HTTP 接口如何调用

开发工作台：先 GET `/api/status` 获取 `csrfToken`，POST 带 JSON Content-Type 和 `X-TripMate-Token`。
POST `/api/operations/session`，body `{"identityId":"traveller:paid"}` 获取 session；后续请求带 `X-Ops-Session`。
写操作带唯一 `requestKey`；Case/Intake 写操作使用服务器返回的最新 `revision`。丢失响应时复用原 requestKey 重试。

| API | 调用者及用途 |
| --- | --- |
| POST `/api/operations/intake` | 旅客；text、intents（结构化需求） |
| POST `/api/operations/confirm` | 旅客；intakeId/revision/intents/confirmed=true，创建 Case |
| POST `/api/operations/dispatch` | 旅客；caseId/revision，实际调用 Planning |
| POST `/api/operations/review` | Operator；caseId/revision/decision/reason，复核输出 |
| POST `/api/operations/deliver` | 已授权角色；caseId/revision，受控交付响应 |
| GET `/api/operations/plan?versionId=...` | 所有者；交付后读取行程与允许展示的 comparison 字段 |
| POST `/api/operations/adopt` | 旅客；versionId/expectedBaseline/accepted=true，明确采用 |
| GET `/api/operations/traces?caseId=...` | 按角色过滤的 Operations 处理记录 |

共享 envelope、Python signatures、PlanningProduct 等仍见 [API 交接文档](Travel_Planning_API_Handoff.zh-CN.md)。
Operations 返回详情字段见其 [交接说明](../operations/OPERATIONS_HANDOFF.md)。
Portal 同名接口使用 HttpOnly 登录 session 和 `X-CSRF-Token`；开发工作台的 session header 不能代替真实登录。
没有新增直接向公众开放的 `/api/planning/generate`，所有用户操作经 Operations 权限与发布边界。

## 正式依赖注入

```python
from tripmate.operations.integration import connect_planning
from tripmate.adapters.campus import CampusLLMService
from tripmate.planning.campus import ModelPlanningEngine

connect_planning(
    operations, approved_offer_adapter, shared_reviewer, planning_repository,
    planner_factory=lambda: ModelPlanningEngine(
        CampusLLMService(timeout=20), operations.clock, max_attempts=2),
)
```

这里 operations/报价/审核/repository 必须是共享应用选定的服务实例；示例不是自动创建这些依赖。
`planner=` 仍保持兼容；同时传 planner 和 planner_factory 会拒绝。
适配器按 caseId 加载确认上下文，真实 Operations access 负责所有权，CaseEntitlements 处理已有行程修改不重复占用 Free 名额。
采用与 Operations 审计仍是两个事务，沿用 main 的失败恢复和幂等边界，不宣称分布式原子事务。

## 验证结果

- `python -m unittest discover -s tests -q`：150 项通过，含 Operations/Portal/B02 原有测试与 5 项新增联调测试。
- 新增 HTTP 测试验证实际确认、派发、审核、交付、读取、采用；未交付访问/跨用户访问被拒绝；旅客响应不泄露成本和模型草稿。
- B03 数据库报价更新立即影响查询，过期报价不会被选用；reset 保留共享 Planning 版本。
- 原跨分支验收脚本继续检查修改、Free 名额、过期采用、过时基线、审计失败重试等，现直接使用合并后的代码。
- 本次真实模型集成尝试：代理不可达/超时，返回 TOOL_UNAVAILABLE，Operations 进入 HUMAN_ASSISTANCE。
  记录见 [main_integration_smoke.json](evidence/main_integration_smoke.json)；不算模型成功或完整四 Agent 完成证据。
- 之前独立 Planning 的真实模型成功记录仍保留，但与本次网络失败明确区分。

需要继续对接的仍是正式 Supplier/Reviewer/Exception、云 Planning 持久化和 Portal 部署联调。
