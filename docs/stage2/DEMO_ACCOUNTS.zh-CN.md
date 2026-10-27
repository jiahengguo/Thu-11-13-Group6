# 默认演示账户和供应数据

2026-10-27 最新结果：已在用户确认的项目实际部署 `202610270001_demo_profiles.sql`，真实 RPC 返回 demoProvisioning=1，原 404/PGRST202 已解除。数据库权限检查为 anon=false、authenticated=false、service_role=true。四类专用云账户实际登录及角色/会员校验通过，七个供应案件、两个待确认客户草稿完成准备；重复执行未重复业务记录或更换密码。见 [脱敏云端验证记录](cloud-demo-init-evidence-2026-10-27.json) 和 [验证审计](PR_VALIDATION_AUDIT_2026-10-27.zh-CN.md)。

本入口复用 Supabase Auth、现有私有 RPC、Operations 和 Supplier 服务。它不会启动角色切换工作台，不会自动批准报价，也不会创建已采用或 Active 的行程。云端初始化已完成上述限定验证，完整旅行/恢复业务尚待验收；Supabase 凭据交付给 tutor 的安排仍待确认。

## 准备与启动

先运行 `python3 scripts/setup_demo.py` 并在本地 `.env` 填写已有云项目配置。项目管理员需按顺序应用 `supabase/migrations/` 下的 SQL，包括新增的 `202610270001_demo_profiles.sql`；不要对已有项目重复执行建表 migration。新增函数只允许服务器 service_role 调用，并核实专属模拟邮箱、已确认邮箱和管理员写入的 demo 标记，不开放普通浏览器更改角色。

先预览，不读取凭据或写入云端：

```sh
.venv/bin/python -m tripmate.portal.demo
```

确认目标项目和允许的专属演示账户后执行（将 URL 换成实际项目 URL）：

```sh
.venv/bin/python -m tripmate.portal.demo --apply --confirm-project https://PROJECT.supabase.co
.venv/bin/python scripts/start_demo.py
```

Windows 使用 `.venv\Scripts\python.exe`。默认日期为执行当天悉尼日期加两天；指定演示日期可加 `--start-date 2026-11-07`。同一场景不能静默改日期，也不能在日期已过去后继续声称可用。课程模型仍需校园网络/VPN和老师提供的本地密钥；本入口不会将课程调用回放当成真实成功。

四个账号为 `stage2-demo.free@example.invalid`、`stage2-demo.paid@example.invalid`、`stage2-demo.supplier@example.invalid`、`stage2-demo.operator@example.invalid`。密码各自随机生成，保存在权限 0600 的 `.demo-accounts.local.json`，不会打印；此文件已被 Git 忽略，必须排除于最终 ZIP、PR、日志和截图。它只是本地演示登录资料，不替代 tutor 尚待确认的云密钥安排。不要把 `--manifest` 指向受版本控制的文件。

当前已准备场景为 namespace `stage2-demo` / scenario `demo`，行程日期 2026-11-07 至 2026-11-09，报价覆盖 11 月 5 日演示期间。新机器没有原密码 manifest 时，不要覆盖既有身份；可选新的 `--namespace` 创建独立专用测试身份，或由项目管理员按团队确定的方式提供现有测试账号登录资料。

账户准备操作仅针对带匹配服务器 demo 标记的专用身份，付费模拟账号有效期 30 天，不修改普通用户。重新执行复用已有身份和密码。若中途失败保留 manifest；若已创建身份但本地保存失败，需管理员核实恢复，不能通过覆盖其他账号或批量删除用户来重试。

## 演示步骤

1. Supplier 登录可看到两项交通（express / coach）、住宿和活动四项完整报价，以及 zero-stock、expired、restricted 三个失败或待批准示例。正常报价成本 AUD 180，按显式模拟策略售 AUD 198，差价 AUD 18。
2. Operator 审核四项正常报价的来源和价格后逐项 Pass。restricted 即使 Pass 仍需单独的精确范围人工批准；初始化不会代替这一步。过期报价保留 EXPIRED，零库存要求修订，两者均不能被选入方案。
3. Free/Paid Traveller 登录后看到自己的待确认行程草稿。明确确认并开始处理，生成含交通、住宿和活动的完整候选（本场景总价 AUD 594），经 Operator 审核并交付后比较、采用。客户仍须明确点击开始行程，不能由脚本代替确认。
4. 取消恢复继续按 [默认门户 Exception 流程](../exception/PORTAL_INTEGRATION.zh-CN.md) 录入当前 Active 行程的受影响交通项和 Operator 模拟取消证据。不得将未真实执行的订票或改签标为完成。

## 重复运行与场景范围

同一 namespace/scenario 完成后重跑返回原记录，不重复创建业务案件，不旋转已有密码。报价输入日期被冻结，已经结束的场景明确拒绝重用。需要重新开始一场演示时使用新的 `--scenario rehearsal-two`，必要时明确新的 `--start-date`；这会为同一组账户新增一组可识别的模拟案件和草稿，保留旧案件与审核轨迹，不重置全项目或其他用户数据。

当前提供这种保留历史的场景重开方式；物理删除/完整清空不是本批功能。部分失败时先检查保存的案件；已记录的失败派发不会被脚本偷偷改成成功，可用新场景重新演练。不同 namespace 创建另一组明确隔离的模拟身份，不能通过现有 manifest 擅自切换项目或 namespace。

## 验证范围

6 项新增测试通过：账号可恢复准备、随机密码与文件权限、身份标记防篡改、角色先决条件、重复执行与无关数据保留、日期失效拒绝、经人工审核生成完整方案，以及受限条款保持待批准。这批自动化测试用 FakeCloud 替代云传输；后续真实云初始化、登录、角色和重复执行已单独验证，不能混为同一次测试。

历史完整回归 273 项全部通过（156.569 秒），包含 main 合入后的既有 248 项基线。此后真实云/模型联合连接及有界模型规划已通过，当前账号准备也已实际执行。账户初始化验证不等于 Operator 审核、客户确认、模型规划及恢复流程已连续验收；这些仍需下一步执行。

管理员接口依据：[Supabase 创建用户说明](https://supabase.com/docs/reference/python/auth-admin-createuser) 和 [管理员接口权限](https://supabase.com/docs/reference/python/admin-api)。未制作 ZIP 或执行解压部署验收。
