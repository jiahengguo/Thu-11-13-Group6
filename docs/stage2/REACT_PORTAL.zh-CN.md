# React 门户渐进重构与验证

2026-11-01，Australia/Sydney。分支 `react-portal-refactor`，基于 main
`2178568` 的 React 请求队列改动。对应 WN5620-62。

## 实际改动

- Traveller、Supplier、Operator 共用 `web/src/RequestQueue.jsx`，负责案件列表、
  ID/类型/状态文本搜索、状态筛选、清除筛选、结果数量和选中状态。
- 通过 React state 保留刷新前的搜索及筛选；两种后端审核状态合并为一个
  `Under review` 筛选项。过滤掉当前选中案件时，详情仍保留，清除筛选后仍可看到选择。
- Operator 指标由 React 渲染，统计整个已授权队列，页面明确说明不随筛选变化。
- `queue-entry.jsx` 将受后端授权的摘要和已有选择回调接入 React。处理请求时同步
  禁用 React 控件；旧脚本不再修改 React 所管理的两个节点及其按钮。
- 原有表单、详情、提交、审批、会员和云端权限流程保留；这是局部 React 接入，
  不是整个前端或所有页面已经迁移。

## 构建和初始化

React/React DOM 19.3.1，Vite 8.3.5；依赖和锁文件位于 `web/`。
开发时执行 `npm ci`、`npm test`、`npm run build`。构建产物
`portal-queue.js` 和 `portal-queue.LICENSE.txt` 随 Python 包和完整源码交付。
许可证从实际安装的 React、React DOM、Scheduler 包复制。

三类认证 HTML 在旧 `portal.js` 之前加载同站点的生产 bundle；服务端显式提供
该静态地址，不使用外部 CDN、浏览器 JSX 编译器或额外前端服务器。
现有 `script-src 'self'` 等 CSP 保留。

`setup_demo.py` 和 `start_demo.py` 的使用方式保留。运行已构建的完整源码不需要
Node/npm；只有重新开发、构建前端时才需要。开发者必须将前端源码与对应产物一起
交付，不能只交付不含产物的源码。

## 本轮验证

1. React 组件与桥接测试 **15/15**：三角色复用、组合搜索与筛选、刷新保留、选中
   ID 回调、忙碌禁用、全局统计口径、加载/失败/空列表和文本转义。
2. Python 完整回归 **297/297**，152.602 秒。新增 HTTP 检查确认本地 React 文件
   可读、JavaScript MIME、CSP 和三角色页面的脚本顺序/挂载节点。
3. 清洁依赖安装 `npm ci --offline` 后再次构建，产物 SHA-256 与首次一致：
   `0329bb84ae296e61e8bb14c3e0dcd4583f4ed5d83ca02031d69216d8f5412c32`。
   JavaScript 大小约 223 KB，gzip 约 70 KB；不是整站性能测试。
4. 在独立临时源码目录实际运行初始化两次，第二次保留已有 `.env`。另在 PATH
   中无法找到 Node/npm 的环境再次初始化成功，私密配置内容未改变。
5. 实际构建 Python wheel 并检查归档：React bundle 与许可证均已包含。已初始化
   环境可从安装后的 package resources 读到这些文件。
6. 真实 Chrome、相同 Python 门户、隔离 FakeCloud：实际登录三角色，检查队列
   隔离、搜索、状态筛选、无匹配、案件详情、刷新保留及 Operator 全局统计。
   停止本轮隔离测试服务器后点击刷新，明确显示连接失败，保留上次队列及筛选，
   控件解除禁用；未影响另一个连接真实提供方的启动实例。
   该浏览器演练使用明确的合成数据，不是共享 Supabase 的业务验收。
7. 独立初始化环境实际执行默认 `start_demo.py`。VPN 未连接时课程模型返回
   `TOOL_UNAVAILABLE`，启动按原规则阻断；用户连接学校 VPN 后重新执行，
   Supabase 与课程模型均为 **VERIFIED**，服务成功启动。未用跳过模型探测的结果
   冒充模型通过，也没有初始化或重置共享云数据。

## 当前边界

本轮没有重新执行共享云环境的完整规划、采用、取消恢复和审批业务链路，也没有
制作新的最终提交 ZIP。之前已验收的 ZIP 保留为基线；不能把旧验收等同于本次
React 修改后的最终发布验收。独立同伴 review 和改动后发布验收仍待完成。

CI、自动 ZIP 持续交付及发布验收分别由 WN5620-63、64、65 跟踪；本次没有
实现或宣称这些任务完成。用户最新本地 `DEMO_SCENARIOS.zh-CN.md` 保留不动，
不纳入提交或上传。
