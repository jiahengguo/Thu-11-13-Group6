# TripMate AI

[English](README.md) · [文档索引](docs/index.md)

TripMate 是旅游服务原型，提供真实认证的旅客、供应商和 Operator 门户。Operations 统一协调 Supplier（报价评估）、Planning（行程生成与校验）和 Exception（异常调查与恢复建议）。

Supabase 提供真实认证和私有持久化，课程 `campus-qwen` 模型用于提取信息和提出行程候选。价格、库存、会员、约束和批准由确定性规则控制。旅游资源与取消事件使用模拟数据，不执行真实订票、支付、退款或改签。

## 当前已实现

- 供应商报价、Operator 明确审核和 AUD 确定性定价。
- 客户确认需求、模型辅助规划、方案比较、明确采用及不可变修订。
- 旅客主动开始行程；Active 行程采用修订后保留状态与原开始时间。
- Operator 录入取消证据，Supplier/Planning 协作生成恢复建议，提案批准与响应审核分离，经 Operations 交付。
- 角色和所有权检查、私有案件历史、幂等命令、重启后可读取的业务记录。

PR #34 后的云端按需读取修复已进入main。完整回归 **292项通过**；其后Supabase边界9项、门户28项专项通过。已实际演练真实账户、课程模型、恢复批准及重启读取，最终未修改的交付ZIP仍需验收。详见[集成流程与限制](docs/stage2/LIVE_WORKFLOW.zh-CN.md)；带日期的旧交接文件保留当时验证范围，其中“尚未合并”等表述属于历史状态。

## 从 ZIP 开始：第一次操作指引

以下根据10月29日实际ZIP初始化与页面演练整理；详见[Demo案例与验证边界](docs/stage2/DEMO_SCENARIOS.zh-CN.md)。最终未修改的交付ZIP仍需再验收。

1. **先解压，再打开终端。** 找到同时包含 `README.md`、`pyproject.toml` 和 `scripts` 的文件夹，这才是项目根目录；不要在 ZIP 预览窗口内运行。
2. **进入根目录。** macOS 可输入 `cd ` 后把解压文件夹拖进终端再回车；Windows 在该文件夹打开 PowerShell。路径有空格时保留引号。出现“找不到 scripts/setup_demo.py”通常是当前目录不对。
3. **先执行下方安装步骤。** 看到安装完成提示后再编辑 `.env`。该文件可能被隐藏；macOS Finder 可用 Command+Shift+. 显示隐藏文件。保持文件名恰好为 `.env`，不要保存成 `.env.txt`；使用纯文本编辑器，不用 Word。
4. **新电脑不等于新数据库。** 如果小组提供的是已准备好的 Supabase 项目，填写配置即可，不重复建表。若没有已有账户的密码文件，按照下面“独立演练账户”命令准备另一组专用账户。
5. **启动后保留终端窗口。** 看到 `TripMate portals | http://127.0.0.1:8780` 后，在浏览器打开该地址。程序持续运行、终端没有返回输入提示是正常现象；Ctrl+C 会停止服务。只关闭网页不会停止服务。
6. **登录资料在哪里？** 打开本次命令指定的本地 `.demo-accounts…json`，在 `accounts` 中找到 `free`、`paid`、`supplier` 或 `operator`，使用其 `email` 和 `password`。文件只是读取登录资料，不要修改角色、密码或 ID，也不要提交或截图它。普通“Create an account”不会创建 Supplier／Operator。
7. **角色如何切换？** 先 Sign out 再登录另一角色。同一浏览器的普通标签页共享登录状态；同时演示多个角色时使用独立浏览器配置文件或不同浏览器。不要靠打开 `/admin` 给自己授予权限。

### 独立演练账户：没有原密码文件时

先完成下方安装和 `.env` 配置。将 `yourname` 换成你自己的小写字母／数字标记，避免与共享项目中已有 namespace 冲突；同一组账户重跑时保持 namespace 和 manifest 不变。日期示例用于 2026 年 11 月 5 日 Demo，之后使用时应选择新的有效旅行日期及场景。

macOS / Linux：

```sh
.venv/bin/python -m tripmate.portal.demo --apply --confirm-project https://YOUR_PROJECT.supabase.co --namespace demo-yourname-20261105 --scenario rehearsal-one --manifest .demo-accounts-rehearsal.local.json --start-date 2026-11-07
```

Windows PowerShell：

```powershell
.venv\Scripts\python.exe -m tripmate.portal.demo --apply --confirm-project https://YOUR_PROJECT.supabase.co --namespace demo-yourname-20261105 --scenario rehearsal-one --manifest .demo-accounts-rehearsal.local.json --start-date 2026-11-07
```

`--confirm-project` 必须与 `.env` 的 `SUPABASE_URL` 完全相同，不能粘贴 dashboard 网页地址。密码文件丢失时不要删除云用户、覆盖原身份或反复换密码；改用独立 namespace，或联系小组管理员。初始化失败时保留已生成的密码文件以便接续。

### 页面打开后为什么还没有方案？

初始化只准备数据，不代替用户确认或人工审批。先由 Supplier 查看报价、Operator 审核普通资源，再由 Traveller 打开自己的草稿并确认、开始处理；模型生成后仍需 Operator 审核与交付，客户才可比较和采用。采用方案后还需要旅客明确点击开始行程。过期／零库存／受限样例不能当作普通可用资源。

模型处理期间等待当前操作结束，不连续重复点击；若显示失败或人工处理，保留案件并按提示操作，不能当作成功。端口被占用时可给启动命令加 `--port 8781`，浏览器也须打开对应端口；不要停止不认识的其他进程。修改 `.env` 后停止自己启动的服务并重新运行启动脚本，再重新登录。

## 简单初始化

在项目根目录执行。需要 **Python 3.9+**、用于安装依赖和访问 Supabase 的网络，以及访问课程模型的校园网或 USYD VPN。当前启动方式无需 Docker。

### 1. 安装

macOS / Linux：

```sh
python3 scripts/setup_demo.py
```

Windows PowerShell：

```powershell
py -3 scripts/setup_demo.py
```

脚本建立 `.venv`、安装项目，并仅在 `.env` 不存在时从模板创建；不覆盖已有配置和数据，也不会自动部署数据库或创建账户。

### 2. 只修改根目录一个 `.env`

所有 Agent 共用该文件的服务器配置，不需要分别改源码或前端。

```dotenv
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PROJECT_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY=YOUR_PROJECT_SERVER_SECRET
TRIPMATE_LLM_PROVIDER=elec5620
TRIPMATE_LLM_MODEL=campus-qwen
ELEC5620_API_KEY=YOUR_COURSE_KEY
ELEC5620_BASE_URL=http://10.167.60.148:8000/v1
ELEC5620_MODEL=campus-qwen
```

Supabase 三项必须来自同一个项目；本地演示的其他模板设置保持原值即可。启动脚本显式启用模拟定价：加价 10%、最低差价 AUD 15、版本 `demo-2026-10-24`。直接启动服务器而不启用演示定价时，需要另行明确配置定价政策。

**新 Supabase 项目**需要管理员按文件名顺序执行 `supabase/migrations/` 中的迁移；已准备的项目不应重复执行最初建表文件。填写密钥不等于自动建立数据库。详见[云端配置](docs/portal/PORTAL_HANDOFF.md)与[账户准备](docs/stage2/DEMO_ACCOUNTS.zh-CN.md)。向 tutor 提供 Supabase 凭据的方式仍待确认。

### 3. 按需准备演示账户和资源

先预览，不写云端：

```sh
.venv/bin/python -m tripmate.portal.demo
```

明确确认项目后准备专用模拟场景：

```sh
.venv/bin/python -m tripmate.portal.demo --apply --confirm-project https://YOUR_PROJECT.supabase.co --start-date 2026-11-07
```

Windows 将 Python 路径换为 `.venv\Scripts\python.exe`。旅行日期应选择演示之后的有效日期。四类账户为 Free/Paid Traveller、Supplier、Operator；随机密码仅保存在忽略的 `.demo-accounts.local.json`。其他电脑没有原密码文件时，应使用约定的资料交接方式，或用新的 `--namespace` 和独立 manifest 创建账户，不覆盖已有身份。新的 `--scenario` 用于另建演练场景，保留历史。

初始化不会代替 Operator 审核、客户确认、方案采用或开始行程。过期、零库存和受限报价是失败／待批准示例；正常规划使用四项普通报价，并先由 Operator 审核。

### 4. 检查并启动

macOS / Linux：

```sh
.venv/bin/python scripts/start_demo.py
```

Windows：

```powershell
.venv\Scripts\python.exe scripts/start_demo.py
```

打开 **http://127.0.0.1:8780**。启动脚本先检查私有云存储、显式模拟定价和一次真实模型调用，再开启模型规划认证门户。更换端口可加 `--port 8781`。

| 门户 | 路径 | 用途 |
| --- | --- | --- |
| Traveller | `/app` | 确认需求、比较／采用／修订、开始行程、选择已交付恢复建议 |
| Supplier | `/supplier` | 提交报价、查看评估 |
| Operator | `/admin` | 审核报价、录入取消证据、批准／交付响应、查看轨迹 |

使用对应后台角色的账户；普通注册只创建 Traveller，不授予管理员身份。完整演示顺序见[操作指南](docs/stage2/LIVE_WORKFLOW.zh-CN.md)。

## 检查与常见问题

```sh
.venv/bin/python -m tripmate.portal.doctor --demo-pricing --check-cloud --check-model
.venv/bin/python -m unittest discover -s tests -v
```

- 云端检查失败：检查项目是否可用、密钥是否匹配、迁移是否执行；服务器 secret 不进入浏览器。
- 模型检查失败：检查校园网／VPN与课程 key；跳过探测或运行 fixture 不代表真实 AI 成功。
- 账户准备失败：检查 demo-profile 迁移及 manifest 的项目／namespace，不通过清空共享数据库来重试。
- 没有可用方案：核对库存、有效期及 Operator 审核；未通过审核或未交付的结果保持隐藏。
- 服务重启：需要重新登录，会话不跨进程保存；云端业务记录仍保留。

## 目录与尚未完成范围

| 路径 | 内容 |
| --- | --- |
| `src/tripmate/` | 门户、四 Agent、共享服务／契约与接口适配 |
| `scripts/` | 初始化、启动及验证入口 |
| `supabase/migrations/` | 有序数据库迁移 |
| `tests/` | 自动化回归，明确区分隔离替身与真实调用 |
| `docs/` | [实现说明和历史交接索引](docs/index.md) |

默认门户的可信投诉政策、受限报价进入规划、剩余状态流转／提醒、营销和完整会员权益仍未全部完成。当前是单进程教学演示，私有快照有 32 MB 上限，分页、扩容和生产运维尚未实现。

后续还需新电脑启动复现、小组发布演练、完整交付说明／贡献声明，以及最终 ZIP 解压部署验收。提交包不得包含 `.env`、`.demo-accounts*.json`、虚拟环境和本地数据库。Stage 1 仅保留[报告 PDF](docs/TripMate_AI_stage1_report.pdf)作为设计依据，独立建模草稿和 UML 文件已清理。

### 云端操作报错时怎么办

等待按钮恢复后，重新打开同一个请求并查看Request history，再决定是否重试。曾出现决定已保存、后续刷新失败的情况，不能连续重复批准或重新创建案件。同一浏览器配置文件尽量只保留一个演示页。当前云项目已部署按需读取迁移；其他项目需按文件名顺序补齐缺失迁移。见[读取修复说明](docs/stage2/SCOPED_CLOUD_READS.zh-CN.md)。不要清空数据或关闭审核来解决失败。
