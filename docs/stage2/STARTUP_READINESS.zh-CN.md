# 初始化入口与课程模型就绪检查

2026-10-27 更新：当前开发分支的真实 Auth、私有 RPC、JWKS 和课程模型提取已通过，联合 doctor 返回 ready=true。下方 TOOL_UNAVAILABLE 是连接 VPN 前的历史记录，不再是当前连接状态。真实账户/种子数据和完整云端业务仍未验收，具体见 [PR 验证与剩余工作审计](PR_VALIDATION_AUDIT_2026-10-27.zh-CN.md)。

对应 WN5620-54 和初始化任务，依赖尚未合并的 PR #18、#19；本批没有替换云认证、创建真实云账户或制作 ZIP。

## 操作入口

```sh
python3 scripts/setup_demo.py
.venv/bin/python scripts/start_demo.py
```

Windows 使用 `python scripts/setup_demo.py`，然后 `.venv\Scripts\python.exe scripts\start_demo.py`。

setup 根据脚本所在源码目录安装项目，不依赖调用者当前目录。已有 `.env`、账号和业务数据不会被覆盖；缺少 `.env` 时仅复制不含密钥的模板。运行者在本地填写模型及云配置。首次运行仍需要可安装 Python 包的网络。

start 在同一源码目录下调用配置/云 RPC/真实模型检查，再启动统一认证门户，显式选择用户确认的模拟定价（10% 加价、最低差价 AUD 15）。不生成报价、不伪造审核、不会自动清空数据或绕过认证。

```sh
.venv/bin/python -m tripmate.portal.doctor --demo-pricing
.venv/bin/python -m tripmate.portal.doctor --demo-pricing --check-cloud --check-model
```

不带 live 参数时只判断配置，不访问模型或云。`CONFIGURED` 不代表真实接口已通过；`VERIFIED` 只在对应调用成功后显示。模型探测通过共享 LLMService 对无敏感信息的两人出行句子进行实际 schema 提取，要求结果为 partySize=2；不使用固定回放当作成功。一次调用最多 1024 completion tokens，20 秒超时，密钥及提供方原始报文不会输出。

`--skip-model-probe` 仅跳过启动前的实时探测，不会移除模型配置要求、伪造已验证结果或切换到模拟模型。

Supabase 的交付凭据安排仍待用户与 tutor确认。此处继续使用现有账号认证和私有 RPC；需先完成现有 migration，不自动重跑建表、不将密钥放入源码或提交包。

## 验证记录（2026-10-26 夜间）

- 7 项就绪检查测试通过，覆盖缺配置、部分定价、占位密钥、错误提取、真实探测分支及错误信息脱敏。
- 现有 12 项 campus 相关测试通过。
- 完整回归：255 项全部通过，103.501 秒。
- 两个脚本的帮助入口正常；没有进行 ZIP 制作或解压测试，也没有声称已完成 tutor 的现场部署验收。
- 本机实际课程探测未通过：稳定分类 `TOOL_UNAVAILABLE`。因此尚不能声称真实模型已现场可用；需复核校园网络/VPN和课程服务。继续推进不依赖该连接的功能。

默认测试账号与带时间有效性的业务数据还需后续实现，不能将此安装脚本视为账号/数据已齐全。
