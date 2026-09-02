# TripMate AI

[English](README.md) | [简体中文](README.zh-CN.md)

TripMate AI 是 ELEC5620 课程项目，用于验证一名人类创始人能否在四个协作式 AI Agent 的支持下运营旅行服务。项目聚焦澳大利亚境内短途旅行，并使用模拟的供应商、预订、支付和异常数据。

当前重点是 **Stage 1：需求、架构与系统建模**，截止日期为 **2026 年 9 月 24 日**。可运行原型计划在 Stage 2 完成。

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

## 计划中的系统形态

```text
Traveller / Operator
        |
      Web 界面
        |
  Orchestrator/API
        |
  +-----+----------------+-------------------+--------------------+
  | Operations Agent    | Travel Planning   | Customer Exception | Supplier Partnership
  +-----+----------------+-------------------+--------------------+
        |
  Reviewer / Guardrail
        |
  Tool adapters、repositories、trace store 与 approval queue
```

Stage 2 概念验证预计采用轻量 Web 界面、结构化 Agent 输出、确定性校验工具和简单可追踪的数据存储。具体技术栈将在 Stage 1 模型稳定后确定。

## 文档

- [Stage 1 计划](docs/Stage1_Modeling_Task_List.md)：交付物、四个 Agent 的分工、建模规则、完成顺序和检查清单。
- [当前项目 Requirement](https://unisydneyedu-my.sharepoint.com/:w:/r/personal/jguo9172_uni_sydney_edu_au/_layouts/15/doc.aspx?sourcedoc=%7Bdb7e1c58-8a31-419c-a0cf-9058e8145514%7D&action=edit)：当前产品需求基线。
- [Stage 1 评分标准](docs/ELEC5620_Project_Stage_1_Marking_Criteria.pdf)：评分要求以及个人/小组交付物。

README 只保留项目总览。详细需求、Use Case、模型分工和提交检查清单统一放在 Stage 1 计划或最终报告中，避免多处重复维护。

## 当前范围

Stage 1 包括需求基线、Agent 职责、Use Case、架构、UML 模型、追踪矩阵、演示和贡献证据。Stage 2 将实现其中可演示的一部分。真实预订、支付、广告发布和供应商合同不属于原型范围。

## 贡献规范

Requirement ID、Use Case ID 和 Diagram ID 应保持稳定。Agent 范围发生变化时，先更新当前项目 Requirement，再同步 Stage 1 计划和受影响的模型。通过 commit、pull request 和最终贡献表记录个人贡献。

## 课程说明

TripMate AI 是 ELEC5620 的教学可行性原型，不是实际旅行社或预订服务。
