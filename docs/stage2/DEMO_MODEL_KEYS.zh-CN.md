# 演示时的统一模型调用

演示后端从本机未提交的 `.env` 读取 `ELEC5620_API_KEY`、`ELEC5620_BASE_URL` 和 `TRIPMATE_LLM_MODEL`。使用课程授权的 key；模型 key 与 Supabase publishable/secret key 是不同凭据。

运行 `python -m tripmate.portal.server --model-planning --demo-pricing`，其中 `--demo-pricing` 明确选择模拟定价。模型服务器需要校园网或 VPN 可达。所有演示用户连接同一个后端时，只需在该后端配置一次；队友各自启动后端时，各自在自己的 `.env` 配置获授权使用的凭据。

Portal 创建一个 CampusLLMService，Operations 提取/草稿、Campaign 文案和模型 Planning 复用该服务。不同 Agent 的上下文、提示词、结果与审核仍分别处理。Supplier 定价及 Exception 校验保留确定性工具，不能声称每个步骤都由模型生成。浏览器通过登录会话调用项目后端，后端才携带模型 Authorization；前端不收集或存放模型 key 与 Supabase secret。

`Portal/make_server(..., llm_service=...)` 可注入替代的共享服务，用于隔离演示测试；`travel_factors=...` 接入 TravelFactorService。配置了模型但配置无效时启动失败，不静默伪装成真实模型运行。真实端到端验收需要另行记录。
