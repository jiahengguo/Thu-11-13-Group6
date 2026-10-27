# TripMate AI 项目功能与 Bug 清单

审计日期：2026-10-27（Australia/Sydney）。仓库：jiahengguo/Thu-11-13-Group6。

本清单依据远程分支提交历史、源代码、集成入口、测试和已提交验收材料整理。功能存在、自动化通过、真实接口验证、完整业务验收是不同状态。UML/需求说明中的设计不直接算成已实现功能。

## 1. 本次合并与验证

- 用户指定的 PR：#20 → #21 → #22 → #23 → #24，已按依赖顺序全部合入远程 main，使用 merge commit 保留原提交历史。
- 累积功能版本：`291a940c5b3b05647eee6493a8fee3ba81714c42`。相对原 main `ab74e2b` 共 27 个文件，新增 1419 行、删除 15 行。
- 本次额外发现并修复：演示密码 manifest 在 Windows 上的权限设置；原 `chmod(0600)` 不会建立仅当前用户可访问的 Windows ACL，原 POSIX 权限断言也无法跨平台通过。新实现先限制空临时文件权限，再写密码，原子替换后再次限制；权限设置失败不写入新密码、不替换旧 manifest。
- 最终合并状态和本次完整回归结果见本文末尾“执行结果”。
- GitHub 查询未返回这些 PR 的 commit status；最终功能提交没有返回 PR-triggered Actions runs，因此不声称 CI 绿灯。本次以本机回归结果单独记证。

## 2. 已有功能 List

| 模块 | 已实现功能 | 当前使用范围与证据 |
|---|---|---|
| 账户与门户 | Supabase 登录、注册/邮箱回调、刷新与退出；Traveller、Supplier、Operator 独立入口 | `portal/auth.py`、`portal/server.py`；账户身份来自后端验证，不能由页面自选 |
| 权限与隐私 | 角色、所有权、账号有效性检查；CSRF、Origin、会话失效、限流；私有案件/轨迹 | `tests/test_portals.py`；云接口自动化使用 FakeCloud |
| 团队登录 | 同一 IP 多浏览器可独立登录，取消固定在线会话数量上限 | 提交 `38fcc57`，PR #16；不代表已做生产并发压测 |
| Operations 接单 | 结构化/模型辅助意图提取、缺字段追问、完整摘要确认、多意图拆案、角色路由 | `operations/application.py`；模型输出不能代替客户确认 |
| Operations 案件管理 | 分派、跟踪、补充澄清、重新确认、撤回、人工接管、人工关闭 | 保留同案历史；缺少专业服务时保留待人工处理状态 |
| Operations 交付 | 普通咨询、专业结果接收、响应审核、精确版本批准、受控外发/站内收件箱 | 审核与交付分开；未提交交付记录不能向旅客展示正式响应 |
| 会员规则 | Free 最多两个 Planned/Active 行程，每个最多五个含首尾日的日历日；有效 Paid 豁免 | 创建/修订/展示/采用/开始时重新检查；已有行程修订不占新名额 |
| 会员扩展基础 | 去广告/地图权限门槛、会员优惠资格检查、B03 示意路线与模拟广告 | 不是实时地图、完整广告平台或完整会员折扣结算链路 |
| Supplier 报价接收 | 已确认报价、来源、数量、有效期、取消条款、产品交通/住宿/活动信息 | `supplier/intake.py`、`supplier/application.py`、`supplier/gateway.py` |
| Supplier 评估 | 成本、加价、最低毛利、金额舍入、库存、来源和有效期校验；可选报价查询 | 使用确定性 B04 定价；演示定价须显式开启 |
| Supplier 审核 | 普通审核与受限条款人工决策分开；版本历史、修订、撤回、授权失效重检 | 已接入认证 Supplier/Operator 门户和共享存储 |
| 基础 Planning | 交通、住宿、活动和可选返程组合；Comfort/Value/Budget 排序和方案比较 | `planning/engine.py`；满足同一组硬约束，不随排序模式放宽预算 |
| 规划可行性 | 总预算、毛利、报价期限、人数/数量、住宿覆盖、时间冲突、衔接时间、开放时间、无障碍/行李 | `planning/validation.py`、`tests/test_planning.py` |
| 逐日/多城市 Planning | 多段交通、多活动、天气替代、延误、路线衔接、场馆日历/容量、步行/活动上限、休息和用餐窗口/费用 | PR #16；已实现后端和模拟因素适配器。默认认证门户尚未接入完整 daily policy/factors，不能当作默认页面已支持 |
| 规划修订与采用 | 明确确认修订字段、保持原基线、版本差异比较、客户明确采用、防旧版本覆盖 | 本地存储与认证门户集成均有测试 |
| 认证规划主链 | 使用 Supplier 当前已审核报价生成计划，共享审核与私有持久化，经 Operations 交付后比较/采用/修订 | PR #18；不再依靠独立规划 fixture 代替门户库存 |
| 开始行程 | 旅客本人确认 Start this trip；复核会员后从 Planned 转为 Active | PR #19；重复请求幂等；Active 采用修订后保留原开始时间 |
| 课程模型规划 | 模型提出报价 ID 组合，确定性工具核价、校验与排序；无静默离线成功回退 | PR #23/#24；演示启动开启模型模式，规划客户端 25 秒、2048 token，提示请求 1–2 套方案 |
| 共享模型接口 | schema 提取、草稿/说明接口、输出校验、有限重试、错误处理与脱敏 | `adapters/campus.py`；模型不能创造报价、价格或批准 |
| Exception 取消恢复 | 针对 Active 已采用行程的取消证据，调用实际 Supplier/Planning 接口生成替代建议 | PR #17/#21；门户证据由 Operator 录入并明确标注 simulated |
| Exception 客户动作 | 展示已审核恢复建议、确认选择或全部拒绝、同案澄清/重新调查、人工接管 | 选择后仍需响应审核；选择建议不代表真实改签或行程已恢复 |
| Exception 投诉基础 | 本地延误证据/政策评估、解释/道歉或退款人工审核建议；其他投诉收集专业事实并转人工 | 默认门户仍缺可信投诉政策/上下文接线；不能称完整投诉闭环 |
| 共享 Reviewer | 来源/新鲜度/版本检查、领域验证器、规划规则重算、恢复成本和投诉政策重检 | `services/review.py`、`planning/review.py`、`exception_handling/review.py` |
| 审批与追踪 | 提案批准与外发批准分离，绑定对象/版本/权限；不可变历史、关联 trace、重启读取 | 不复用旧版本批准；批准本身不执行交易 |
| 存储与可靠性 | 本地 SQLite、Supabase 私有 snapshot/RPC、事务、幂等命令、乐观并发版本、失败回滚/savepoint | `persistence/`、`portal/repository.py`、各模块 repository；需另做真实云重启故障验收 |
| 启动与预检 | 跨平台 setup/start；检查云、模型与定价；区分 CONFIGURED/VERIFIED/BLOCKED | PR #20；不会把仅填配置当成真实调用成功 |
| 演示账户与数据 | 独立 Free/Paid/Supplier/Operator 账户；七种供应场景、两份客户待确认草稿；可重复初始化 | PR #22；保留已有密码和业务数据，不自动批准报价/确认草稿 |
| 开发工作台 | 显式 workbench、模拟数据重放/受控 reset、本地专业模块演示 | 与默认认证门户隔离，不是用户可切换身份的正式认证功能 |
| 分析辅助 | 模拟 CTR、线索率/转化、CAC、同群留存，以及证据关联实验建议 | `operations/analytics.py`；没有连接实际投放或执行营销活动 |
| 设计与接口材料 | Stage 1 UML、用例、状态图、v1 schema、需求映射、模块交接/演示资料 | 文档资产已存在；不以图中流程代替实现与验收 |

## 3. 已确认修复的 Bug

这里列出有历史提交、PR 描述或本次复现支持的实际修复。下一节的防错测试不一概称为“曾经发生的 Bug”。

| 问题 | 修复结果 | 依据 |
|---|---|---|
| 团队共用 IP 登录受限、固定在线会话上限干扰独立登录 | 调整认证限流，移除固定 session 数量限制 | `38fcc57` / PR #16；`test_four_browsers_can_repeatedly_login_from_the_same_ip`、`test_portal_sessions_have_no_fixed_online_count_limit` |
| Windows 跨模块验收脚本的 SQLite 连接未正确释放 | 关闭连接，避免数据库文件占用影响验证/清理 | PR #9，`scripts/verify_operations_planning.py` |
| 真实课程模型只产生推理、最终方案被 token 预算截断 | 收紧候选请求，把计算/排序交给工具，规划客户端改为 25 秒/2048 token | `d44a873` / PR #24；历史真实调用证据得到两套完整方案；不保证消除所有超时/502 |
| demo-profile RPC 不存在导致 404/PGRST202，无法初始化专用演示账户 | 新增专用迁移及受限执行权限；已提交证据记录真实部署和成功调用 | PR #22/#24，`cloud-demo-init-evidence-2026-10-27.json`；本次未重新部署云数据库 |
| Windows 演示密码文件未建立 owner-only ACL，完整测试权限断言失败 | Windows 显式仅当前用户 FullControl、禁用继承；POSIX 保留 0600；测试按平台验证实际权限 | 本次复现 `438 != 384` 后修复；另测权限失败时不写密码、不替换旧文件 |

## 4. 已实现并有回归测试的防错能力

| 防止的问题 | 现有处理 / 测试文件 |
|---|---|
| 冒充 Operator、跨用户读案件/轨迹/计划、注册自授角色 | 后端身份与所有权检查；`test_portals.py`、`test_supplier_portal.py` |
| 重复提交造成重复案件/重复模型调用、同 key 换内容、旧版本覆盖新状态 | 命令幂等、内容指纹、版本/CAS 检查；`test_operations.py`、`test_portals.py` |
| 无库存或云/模型故障却返回模拟成功 | 明确失败或人工接管，不悄悄替代数据源；`test_planning_portal.py`、`test_model_planning_portal.py` |
| 模型捏造报价/金额、总价不一致、少算餐饮/路线费或人数不匹配 | schema、报价 ID、Decimal 定价和确定性完整校验；`test_planning.py`、`test_daily_planning.py` |
| 报价/证据过期或来源已变，旧方案仍被采用/交付 | 采用、审核、发布前重检；`test_supplier.py`、`test_planning_portal.py`、`test_exception_portal.py` |
| 修订悄悄放宽约束、丢失住宿或覆盖已采用基线 | 确认字段、约束绑定和基线版本校验；`test_planning.py`、`test_exception_project_ports.py` |
| 旧批准、错误审批范围、被撤销 Operator 权限继续授权 | 精确对象/版本/当前权限检查；`test_exception_integration.py`、`test_supplier_portal.py` |
| 把客户描述当作供应商确认的取消事实 | 必须提供当前 Active 版本对应的 Operator 证据；`test_exception_portal.py` |
| 保存失败仍呈现成功、半份专业结果/轨迹落库 | 原子事务、savepoint 回滚、失败阻断；`test_exception_portal.py`、`test_planning_portal.py` |
| 重复开始行程、旧版本/他人激活、Active 修订后退回 Planned | 明确开始操作、幂等与生命周期保留；`test_start_trip.py` |
| 重置演示数据误删账户、审批、计划或案件 | 隔离 fixture reset 和业务记录；`test_supplier_portal.py`、`test_planning_main_integration.py` |
| 同一演示场景重复准备改密码/重复数据、跨项目 manifest 误用 | 项目/namespace/身份校验，幂等种子；`test_demo_seed.py` |

## 5. 尚未完成或尚未验收

1. **完整真实云业务验收**：Supplier 报价 → Operator 审核 → Traveller 确认 → 真实模型规划 → 审核交付 → 比较/采用/修订 → Active → 模拟取消 → 恢复建议/选择/批准，以及真实重启和失败路径。接口已连通不代表这条链已验收。
2. **默认门户投诉闭环**：可信投诉上下文、适用政策、完整类别处理；提醒、截止时间、无回应处理和外部完成确认。
3. **受限报价进入 Planning**：Supplier 层已有受限条款审批，但 PlanningValidator 仍拒绝 `requiresApproval` 报价，跨模块完整链未实现。
4. **逐日因素门户和真实来源**：后端模拟天气/延误/路线/场馆能力已有，默认认证门户尚未完整接线，真实因素提供方尚未配置。
5. **营销和会员闭环**：Campaign 提案、预算、内容审核、人工决策/会员优惠衔接，真实地图与广告差异展示仍不完整。
6. **完整状态机和交付**：剩余审批等待/恢复转换、统一 runbook、最终 UML/需求映射、贡献材料、新机器安装/ZIP 解压复跑、导师凭据交付安排。
7. **生产运维与真实交易**：多实例会话、扩容、运维未完成；原型不执行真实订票、付款、退款、广告投放或供应商合同。

## 6. 全部分支核对

本次 fetch 得到 main 加 13 条功能分支。逐一执行相对累积版本的提交包含性检查，以下分支没有超出 `291a940` 的独立提交。因此合入 #20–#24 后，其余分支无需重复合并；分支名仍存在不等于存在未合代码。

| 远程分支（省略 origin/） | 审计时 tip | 内容 |
|---|---|---|
| main | ab74e2b | 已合入 #18/#19 的原主支 |
| codex/customer-exception-agent | 2518226 | Exception 与 Operations/Planning/审核集成 |
| codex/fix-course-model-planning | 291a940 | #24 模型修复与最新验收材料 |
| codex/sprint2-demo-seed | b41488b | #22 专用演示账户和种子 |
| codex/sprint2-exception-portal | 3159f86 | #21 认证恢复门户 |
| codex/sprint2-model-planning | 4a1d351 | #23 模型规划接线 |
| codex/sprint2-planning-portal-integration | 5dcf5c2 | #18 认证规划门户 |
| codex/sprint2-start-trip | 123b15c | #19 明确开始行程 |
| codex/sprint2-startup-readiness | 2127932 | #20 启动与预检 |
| codex/travel-planning | 8b35742 | 规划、逐日因素与既有合并 |
| operations-agent | 7b603b0 | Operations 和交接材料 |
| portal-supabase-integration | 325687a | 认证门户和云存储 |
| portal-team-debug-access | 38fcc57 | 团队登录修复 |
| supplier-partnership | 2c716a4 | Supplier/B02/B03/B08 门户集成 |

本机原 main 停在 `6acb1d5`，另有 `codex/travel-planning` 工作区停在 `8b35742`；这两者都没有超出上述累积版本的提交。原目录存在用户未提交文档，保留不动；本次在独立工作区完成验证和合并。

## 7. 证据与执行结果

- 原始累积版本：Windows 完整回归 277 项，276 通过、1 失败（149.119 秒）；失败仅为演示密码文件 POSIX 权限断言，同时暴露 Windows ACL 未限制问题。
- 修复后的完整代码：`PYTHONPATH=src python -m unittest discover -s tests -v`，**278/278 全部通过，187.716 秒**。新增测试确认权限设置失败不会写入新密码或替换旧 manifest；Windows 权限专项实际检查 ACL。
- `python scripts/verify_operations_planning.py`：**7/7 通过，12.246 秒**；共享 schema 示例 **20/20 通过**；portal.js/auth.js 的 `node --check`、`git diff --check` 通过；演示账户命令默认 dry-run 检查通过（无云写入）。
- #20 合并提交 `5f9d7cf`；#21 `d9b7535`；#22 `8effabb`；#23 `91cf275`；#24 `f4cf3dc`。拉取后 `git diff origin/main 291a940` 为空，确认五次合并没有改变已审查累积功能内容。Windows 修复和本清单作为后续集成补充提交。
- 已提交的真实接口证据：四类真实账户登录/角色、七个 Supplier 案件、两份未确认草稿、重复初始化保持记录和密码；见 [云初始化证据](cloud-demo-init-evidence-2026-10-27.json)。这些是 Jiaheng 已提交记录，本次没有重新发起云写入或模型付费调用。
- 完整云业务验收仍为 `false`。此前 248/255/267/273/277 属于不同阶段测试基线，不能累加。
- 历史工作范围与剩余 Jira 映射见 [原 PR 验收审计](PR_VALIDATION_AUDIT_2026-10-27.zh-CN.md)；其中分支/待合并状态是当时快照，以本次执行结果为准。
