# CI 与源码 ZIP 持续交付

对应 WN5620-63、WN5620-64。交付目标是经过检查的源码 ZIP，
不是部署到新的云服务器，也不会自动提交 Canvas。

## 自动检查

`.github/workflows/ci.yml` 在 PR、main 推送、`v*` 标签推送和手动触发时运行。
`ci-release-delivery` 是首次实现的预览验证分支，也会在推送后运行全流程。

- Linux Python 3.9、Linux Python 3.12、Windows Python 3.12：安装项目并运行完整
  unittest 回归。测试使用明确的提供方替身，不配置学校模型或共享 Supabase 密钥。
- Node 22：按锁文件执行 `npm ci`、React 测试与生产构建；新生成文件须与仓库中
  随源码交付的 React 文件一致。发现漏构建或过期文件会失败。
- 两组检查全部成功后，才允许打包验证和上传 ZIP。PR 只运行检查，不发布 ZIP。
- 官方 Actions 固定为已核对的提交 SHA；工作流使用 `contents: read`，
  不将 Git 凭据留在检出目录，不使用 `pull_request_target` 或共享业务密钥。

main 和标签用于正式发布候选；实现分支的产物仅为预览，不能替代发布验收。
手动运行入口需要工作流先进入默认分支；不要把尚未合并时没有该按钮当成故障。
分支保护是否要求这些检查由仓库设置决定，本次工作流不会自动更改仓库权限。

## 打包边界

`scripts/package_release.py` 只从当前提交读取文件，核对工作流触发的 commit SHA。
打包白名单包含项目源码、前端源码和锁文件、构建产物、许可证、初始化脚本、
迁移、测试、已提交文档及工作流文件。

本地未提交文档不会被读取或上传。`.env`、演示密码清单、虚拟环境、node_modules、
本地数据库、缓存和系统文件排除；只包含无密钥的 `.env.example`。
若必要脚本或 React 文件未提交，打包会直接失败。

每次交付包含：

- `TripMate-<commit前12位>.zip`：实际项目包，顶层为同名项目目录。
- 同名 `.zip.sha256`：完整 ZIP 校验值。
- `release-metadata.json`：完整 commit/tree、工作流地址、构建运行时、依赖版本，
  以及逐文件大小和哈希。项目包中也含同一份 `RELEASE.json`。

## 下载与运行

1. 在 GitHub Actions 打开成功的 **CI and source ZIP delivery** 运行。
2. 从 Artifacts 下载 `TripMate-<完整commit>`。产物保留14天，过期需重新运行。
3. GitHub 可能把整个 Artifact 再包装成 ZIP；先解压该外层，再找到实际的
   `TripMate-<12位commit>.zip`、校验文件及 metadata，然后解压实际项目包。
4. 按项目 README 执行 `setup_demo.py`、配置 `.env` 并执行 `start_demo.py`。
   演示电脑无需 Node/npm；现有云配置和校园网/VPN 要求仍然适用。

不要把 GitHub 页面上的 **Download ZIP** 当成已验收的发布产物。

## 产物验证

上传前，`scripts/verify_release.py` 检查路径、符号链接、大小、清单和哈希，再在
新临时目录解压。在找不到 Node/npm 的 PATH 下实际初始化两次，确认已有配置
保留，并启动真实门户的隔离提供方演练，验证三角色登录、React 资源及 CSP。
任何一步失败都不会执行上传。

本地复现（从已提交的源码目录运行）：

```sh
python scripts/package_release.py --output /path/to/fresh-output
python scripts/verify_release.py /path/to/fresh-output/TripMate-<12位commit>.zip
```

验证安装依赖需要网络，但不会调用共享云数据或真实模型。完整真实业务演练与
同伴确认仍属于 WN5620-65；自动测试、ZIP 冒烟检查不等同于这些人工验收。
