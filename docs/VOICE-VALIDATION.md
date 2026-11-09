# 本分支验证记录

分支：`feat/voice-shared-web-session`，基线 `fd250bd`。工作目录：`voice-car-prototype/shared-session-worktree`。原 `integration-worktree` 正在被另一开发者使用；本分支独立复制其当时的中继基础实现后完成网站登录集成，不覆盖原工作树。原分支之后提交为 `2207d7f`；不要同时将两份完整实现直接 cherry-pick 到 main，优先审查本分支完整版本。

已完成（本地，没有 push/部署）：

- React/Vite 生产构建成功：1493 modules；最终入口 `index-DkuLVVFj.js`，236.25 kB / gzip 71.73 kB。
- `PYTHONPATH=. python3 -m unittest discover -s tests -p test_voice.py -v`：11 项通过。
- `node voice/worker.test.mjs`：来源/密钥验证、不重试 agent、只重试结果、陈旧 dispatch 不执行，通过。
- HTTP relay → worker → MOCK agent → 持久化答案，连续两轮通过。
- HTTP relay → worker → 既有 loopback bridge（注入 MOCK agent），通过。
- 390px Chromium，语音 API 显式模拟：网站会话认证、开始、识别文本、播报后自动再听、停止、文字后备、无识别 API 降级，通过；另以实际 React 登录 UI 验证登录→activeTab voice iframe→刷新保留登录→退出撤销语音授权。只有金融报告列表返回空列表 fixture，auth/voice 请求使用真实 HTTP 服务。
- 真实 Gateway/main：`TEST_REAL_AGENT=1`，独立 `agent:main:voice-relay-validation` 会话，两轮上下文通过。实际经过临时 HTTP 中继、worker、原 loopback CLI bridge、Gateway/main；第二轮正确回答第一轮要求记住的测试标记。未调用当前飞书会话；测试请求明确要求不使用工具。
- `git diff --check` 通过，前端构建产物已包含更新的独立语音静态文件。

11 项后端测试涵盖：

1. 并发两个 worker 只有一个取得任务、preload 后 fork 拒绝、语音错误配置安全降级。
2. 拒绝旧固定 token、错误 Origin/Host、网页 cookie 不能调用 worker。
3. 退出后已捕获的 cookie 无法重放，使用既有 ADMIN 凭据来源。
4. 默认语音关闭、短密钥、多个实例/worker、非 HTTPS/相对数据库路径、重复持锁进程拒绝。
5. 过期提交、过期领取不能 start、不重新排队。
6. 相同提交 key 幂等、冲突拒绝、start 只能一次、结果回传幂等、用户隔离、正文清除。
7. 登录限流与请求体上限。
8. 文本上限、语音提交限流、worker Bearer 不能代替网站用户 session。
9. 持久队列重启恢复、运行中的任务不重新领取、迟到结果拒绝。
10. 运行中取消后结果不能复活，非法 lease 格式拒绝。
11. 网站 session 过期后 session/voice 均拒绝，领取后取消不能执行。

验证边界：没有在真实 Azure App Service 部署；没有 iPhone Safari 实机麦克风/TTS或小鹏蓝牙实测。真实 agent 测试有模型调用与专用会话记录，其他端到端测试的 agent / 浏览器语音接口均显式模拟。`npm ci` 报告既有依赖 14 项漏洞（1 low、3 moderate、10 high），未顺带做破坏性依赖升级。

上线配置名和限制见 [VOICE.md](VOICE.md)。两个 main push workflow 都仍存在，目标分别是 `LittleFlowerBriefing` 与 `littleredflower`，未改动。测试临时监听器、SQLite 数据库和锁均已关闭；没有新增系统服务、cron、Gateway 配置、收费资源、公网端口、真实密钥文件或后台常驻 worker。
