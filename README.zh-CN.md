# TripMate AI

**Supplier Partnership B02/B03 独立分支（2026-10-13）：** 已新增本地 Web/API、SQLite、可重复的模拟供应商/旅客/取消测试数据和安全 Reset。启动及交接见 [B02/B03 说明](docs/stage2/B02_B03_HANDOFF.md)。四 Agent 仍未完成集成；Moore 的 Planning 及校园模型适配器属于另一分支，未合入时会明确提示不可用，不伪装成已完成。

[English](README.md) | [简体中文](README.zh-CN.md)

TripMate AI 是 ELEC5620 课程项目，用于验证一名人类创始人能否在四个协作式 AI Agent 的支持下运营旅行服务。项目聚焦澳大利亚境内短途旅行，并使用模拟的供应商、预订、支付和异常数据。

Stage 1 报告作为设计基线。**Stage 2 B01 的共享契约和模块框架已搭建，待四位成员审核**。B02 已补充本地 Web/API、SQLite 工作台；真实校园模型检测仍依赖独立适配器、凭据和校园网络。

入口：[项目框架](#项目框架)、[v1.0.0 契约](docs/contracts/v1/CONTRACTS.md)、[需求映射](docs/contracts/v1/REQUIREMENT_MAPPING.md)、[B01 验收记录](docs/contracts/v1/B01_ACCEPTANCE.md)。

## 项目构想

旅行规划的信息分散在交通、住宿、活动、价格、天气和政策等多个来源。TripMate AI 将这些信息组合为可行的行程方案，解释取舍，在情况变化时修改计划，并由人类运营者对重要决策负责。

本项目是 One-Person AI Company，而不是单一旅行聊天机器人。四名组员各负责一个 Agent 方向：

| Agent | 业务职责 |
| --- | --- |
| Operations Agent | 获客、前台服务、意图收集、会员校验和任务分流 |
| Travel Planning Agent | 交通、住宿和活动规划；约束校验；方案比较与修改 |
| Customer Exception Agent | 旅行异常恢复、投诉处理、证据收集和升级 |
| Supplier Partnership Agent | 供应商资源、库存条款、价格和差价校验 |

共享的 Reviewer/Guardrail 负责检查约束、证据、价格、政策和审批条件。人类创始人/运营者监督整个公司，并处理不应交给 AI 的决策。

## 核心流程

1. Operations Agent 接收 Lead 或客户请求，补齐信息、检查会员规则并分流 Case。
2. Travel Planning Agent 获取合格资源并生成完整行程方案。
3. 确定性工具校验预算、时间、库存、价格、差价和其他硬约束。
4. Reviewer/Guardrail 在方案展示给 Traveller 前完成检查。
5. Customer Exception Agent 处理旅行异常或投诉，并在需要时请求人工审批。
6. 系统记录决策、工具结果、行程版本、成本和结果，用于评估。

## 产品基线

- 初始场景：悉尼到墨尔本的短途旅行。
- 旅行模式：Comfort、Value 和 Budget。
- 免费会员：最多同时拥有两条规划中或进行中的行程，每条最多五天；可以展示清晰标注的广告。
- 付费会员：不受免费版行程数量和时长限制，无广告，并可使用路线地图和已批准的高级功能。
- 盈利方式：供应商差价、付费会员和免费用户广告。
- 真实广告发布或预算支出、供应商承诺、支付、退款或赔偿等重要操作仍需人工审批。

## 项目框架

本框架依据 Stage 1 报告的四 Agent 架构、UC-01–UC-08、G-04/G-05，以及
planning 中 B01 的接口约定要求建立。2026-10-10 的交付范围为共享契约和模块边界。
Python 3.9+ 是本次后端骨架的实现选择；报告没有指定语言。
B02 已实现本地 HTTP/静态页面和 SQLite 工作台，B03 已实现可重置模拟数据。
真实模型检测依赖另行合并的校园适配器、本地密钥及校园/VPN 网络；四 Agent 业务集成待完成。

## 整体结构

```text
Traveller / Supplier                    Human Founder / Operator
        │                                           │
        └────── 统一 Web 界面：接待、行程、Operator 工作台 ──┘   [B02]
                              │
                     API / Orchestrator
                              │
                    Operations（Jiaheng）
                 ┌────────────┼─────────────┐
          Planning（Moore） Exception（wrd） Supplier（Jason）
                 └────────────┼─────────────┘
                共享 Reviewer / Guardrail（wrd）
                              │
           会员/权限、约束校验、价格、LLM 与工具适配器
                              │
                一个数据库、Trace、人工审批记录
```

四个 Agent 是同一应用中的内部模块。Operations 负责确认、协调和对外回复；
专门 Agent 返回建议，不能自行对 Traveller 作出承诺。Reviewer 是共享控制服务，
不额外设置第五个业务 Agent。审批、人工协助和真实交易执行是不同概念。

```text
src/tripmate/
  __main__.py          框架检查和 JSON 示例校验入口
  orchestrator.py      四 Agent 组合入口
  agents/              四位成员各自的模块 + 统一 handle_case 协议
  contracts/           Schema 加载、验证器、v1/schemas.json
  services/ports.py    会员、约束、价格、Review、权限服务接口
  adapters/ports.py    LLM 与合格报价查询接口
  persistence/ports.py Trace 和审批存储接口
  api/                 B02 的 HTTP 接入边界
api/static/            B02 前端资源（位于 src/tripmate/ 内）
docs/
  contracts/v1/        契约文档、需求映射、审核记录与 JSON 示例
tests/                 B01 正向和拒绝路径测试
```

这些接口是待实现的协议，不会保存数据或调用外部模型。Agent stub 返回
`executionMode=STUB`、`status=FAILURE` 和 `NOT_IMPLEMENTED`，不会伪造成功。
JSON 示例中的 FIXTURE 表示人工构造的契约样本，不是应用已经执行的业务结果。

## 本地检查

在仓库根目录执行；首次安装依赖需要网络。所有配置模板都不包含密钥。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
.venv/bin/python -m tripmate
.venv/bin/python -m tripmate --validate-examples docs/contracts/v1/examples
.venv/bin/python -m unittest discover -s tests -v
```

如果暂时没有安装项目本身，也可先安装 `jsonschema[format]>=4.23,<5`，在后三条
命令前加 `PYTHONPATH=src`。B02 服务会读取 `.env`，框架检查 CLI 不读取它。
用 `python -m tripmate.api.server --port 8765` 启动工作台。业务模式支持 FIXTURE 和 STUB；
模型检测单独记录真实调用结果或阻塞原因。

## B01 文件入口

- `docs/contracts/v1/CONTRACTS.md`：v1.0.0 的字段、状态、错误码、来源与审批语义。
- `docs/contracts/v1/REQUIREMENT_MAPPING.md`：UC、需求、模块和负责人；旧 PLAN 与新 TP 的已确认语义关系和未决项。
- `docs/contracts/v1/B01_ACCEPTANCE.md`：实际测试证据与四人待确认表。
- `src/tripmate/contracts/v1/schemas.json`：语言无关的机器可校验契约。

所有公开 Schema 都拒绝未知字段，并要求来源、验证结果、错误和审批标志显式出现。
Money 使用 AUD 两位小数字符串；时间戳必须带时区。Schema 检查结构，不代替预算、
库存、会员、报价过期、差价或行程可行性规则。那些规则按 B04/B07/B08/B09 接入。

## 后续交接

| 负责人 | 下一步 |
| --- | --- |
| Jiaheng | B06 在确认后创建 Case，再接 B07 的会员/权限和统一对外回复 |
| Moore | B04 确定性校验；B09 行程生成；版本评估状态与旅行生命周期分别处理 |
| wrd | B05 持久化 trace；B10 Review/人工审批，按对象版本与 scope 检查 |
| Jason | B02 统一 Web/后端/数据库/LLM；B03 模拟数据；B08 报价和 B16 营销 |

接入时保留 caseId/correlationId/sourceReferences，验证每次输入输出；实际保存失败
必须显式报告。审批须关联当前对象版本，修改后重新审核。报告未规定的 rounding tie
规则由 B04 明确记录，不能偷偷把测试示例金额变成全局政策。

B01 的代码和文档已准备审核；四位成员的确认仍待记录，尚不能标记为 Done。

## 文档

- [Stage 1 计划](docs/Stage1_Modeling_Task_List.md)：交付物、四个 Agent 的分工、建模规则、完成顺序和检查清单。
- [当前项目 Requirement](https://unisydneyedu-my.sharepoint.com/:w:/r/personal/jguo9172_uni_sydney_edu_au/_layouts/15/doc.aspx?sourcedoc=%7Bdb7e1c58-8a31-419c-a0cf-9058e8145514%7D&action=edit)：当前产品需求基线。
- [Stage 1 评分标准](docs/ELEC5620_Project_Stage_1_Marking_Criteria.pdf)：评分要求以及个人/小组交付物。

README 包含项目总览、框架、启动和交接说明。详细契约、需求映射与验收证据保留在 docs/contracts/v1 中。

## 当前范围

Stage 1 包括需求基线、Agent 职责、Use Case、架构、UML 模型、追踪矩阵、演示和贡献证据。Stage 2 将实现其中可演示的一部分。真实预订、支付、广告发布和供应商合同不属于原型范围。

## 贡献规范

Requirement ID、Use Case ID 和 Diagram ID 应保持稳定。Agent 范围发生变化时，先更新当前项目 Requirement，再同步 Stage 1 计划和受影响的模型。通过 commit、pull request 和最终贡献表记录个人贡献。

## 课程说明

TripMate AI 是 ELEC5620 的教学可行性原型，不是实际旅行社或预订服务。
