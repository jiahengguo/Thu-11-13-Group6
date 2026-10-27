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

截至 PR #26 已合入，最近一次实现回归 **283 项通过**，受支持的规划与恢复链已通过真实云账户和课程模型演练。新电脑及最终 ZIP 部署验收仍未完成。详见[集成流程与限制](docs/stage2/LIVE_WORKFLOW.zh-CN.md)；带日期的旧交接文件保留当时验证范围，其中“尚未合并”等表述属于历史状态。

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
