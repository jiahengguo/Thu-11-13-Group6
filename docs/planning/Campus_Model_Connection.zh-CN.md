# Planning 课程模型接入

2026-10-13：按课程 Proxy Connection Guide 接入 campus-qwen 的 chat/completions。
个人密钥仅位于工作树根目录 .env（Git 已忽略）；不要复制进报告、截图或提交。
环境变量优先于 .env。无需安装 OpenCode，无新增 Python SDK 依赖。

## 运行

先连接可访问 10.167.60.148:8000 的 USYD 网络/VPN，在工作树根目录执行：

```powershell
.\.venv\Scripts\python.exe -m tripmate.planning.demo --live-model --budget 450.00 --output output/planning-campus
```

查看 output/planning-campus/report.html 和 report.json 的模型提案与工具校验记录。
不带 --live-model 时仍运行原确定性离线示例。

## 实际边界

- 模型提出候选 offer ID，Python 从已加载报价构造行程并计算金额、验证约束。
- 校验失败后将结构化反馈交给模型，最多三次模型调用；未知 ID、缺类别和无效 JSON 不能获得成功。
- 通过的候选继续经过现有权限、会员、Reviewer、保存流程，不会自动采用或预订。
- 采用普通对话 JSON 协议；不声称已验证模型原生 function calling。
- 模型失败不会回退离线枚举并伪装成功。三次无有效候选不等于全局无解。
- 只对通过校验的模型候选排序；不能声称穷举最优。
- 供应商、身份、会员和 Reviewer 仍是 FIXTURE。真实模型调用也不改变这个标记。
- 自由文字偏好和模型解释不构成通过确定性校验的事实；解释标记为待审核草稿。
- 当前仍是直达交通、完整住宿包、单活动原型，不支持任意城市和复杂多段行程。

## 本次验证

首次未连接 VPN 时校园代理 TCP 连接失败。2026-10-13 用户连接 VPN 后复测成功：

- 最小真实模型请求返回 PROXY_OK，验证网络、密钥与模型可用。
- 正常场景：预算 AUD 450，真实模型一次调用提出两套候选；Python 计算为 AUD 396 / 429，各通过 38 项检查。
  证据：output/planning-campus/report.json 和 report.html。
- 受控修正场景：预算 AUD 550，限定每轮提出一套最低价候选，将 basic-stay 报价设置为在 fixture 时钟时过期。
  第一次真实模型选择 basic-stay，被 OFFER_VALIDITY 拒绝；第二次收到反馈后改选 comfort-stay，
  Python 计算 AUD 506 并通过检查。模型响应没有用预设答案替换。
  证据：output/planning-campus-recovery/report.json。
- 普通调用使用 4096 completion tokens；记录 finish reason 和 usage，不保存模型内部推理。
  达到输出上限时明确失败。首次 1024 配置未返回有效最终内容，不能将该次算作成功。
- 上述结果只验证真实模型在模拟供应商和受控场景中的规划/反馈修正，不代表任意场景可靠或接入真实旅行服务。

自动测试使用明确的模型替身验证超预算后修正、拒绝虚构报价、缺住宿、重试上限、
同一 plan 的候选及连接失败无回退；这些测试不是 live-model 成功证据。
