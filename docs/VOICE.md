# 白总语音：复用网站登录，Azure 与 VM 分离

本分支是可审查实现，尚未 push、部署、修改 Azure 配置或启用 VM 常驻服务。用户登录原有网站后，从「工具 → 白总语音」进入。复用 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 的原校验来源与默认行为，没有第二套用户口令。旧 localStorage 登录标记失效，升级后须重新登录一次。

## 拓扑与权限

Safari → 现有网站 HTTPS → FastAPI 持久任务队列 ← VM worker 出站 HTTPS → VM 上现有 loopback CLI bridge → OpenClaw main。

Azure App Service 和 OpenClaw VM 是两台机器。Azure 不执行 OpenClaw CLI，不保存 Gateway 凭据；VM 不保存网站用户名密码。worker 只拿独立机器凭据 `VOICE_WORKER_SECRET`，没有监听端口。bridge 仅监听 `127.0.0.1:8765`，使用本机独立机器口令文件。无需 VPN、公开 Gateway、额外付费语音 provider 或新增云资源。

网站会话是 32 字节随机 opaque token，仅 HttpOnly / Secure / SameSite=Strict cookie，12 小时过期；数据库仅存 token SHA-256。`GET /api/session` 服务端检查，`POST /api/logout` 服务端撤销。每个语音请求重新检查网站会话。登录、退出、语音变更请求校验确切 Origin / Host；worker 接口单独验证 Bearer 凭据，网站 cookie 不授予 worker 权限。原项目其他金融接口的全面权限改造不在这次语音改动范围。

## 任务语义与限制

SQLite 持久化任务、session、限流；`BEGIN IMMEDIATE` 原子领取，任务绑定网站用户。提交 key 幂等、30 秒内请求时间戳校验、每用户每分钟 12 次、全局同时最多一个未结束任务。领取 lease 10 秒，start 只成功一次；运行窗口 130 秒。超时/进程重启绝不重新排队，不自动重试 agent 调用；worker 只重试结果回传。返回失败可能表示工具已经执行，因此 UI 明示先确认结果，不能承诺 exactly-once 外部副作用。

停止会立即停止收音/播报并请求取消当前任务；未 start 的任务不能再执行，已 start 的工具可能继续，不能承诺远程中断。后台/锁屏暂停收音播报，保留已提交任务。用户退出后不能再读取结果，但已授权提交的任务可能完成。lease、取消和结果回传的竞态由条件更新处理，取消/过期任务不能被结果复活。

任务正文完成、取消或过期后清除；回答最多保留 24 小时后在后续请求清理。OpenClaw 继续使用既有会话历史机制。本机默认 `agent:main:voice-car-prototype` 连续上下文，不自动复制飞书当前会话；如需严格共用飞书上下文，可在 bridge 进程设置既有 `VOICE_SESSION_KEY`，该选择须与 main 协调。

**当前只支持一个 App Service 实例、一个 Python worker、一个持久本地队列；不支持横向扩容或共享网络盘的分布式 SQLite。** 启动配置声明单实例，并通过 `flock` 拒绝同存储的第二进程；环境变量本身不能验证 Azure 平台的真实实例数。启用前必须查 Azure 实际 scale-out、启动命令和 `/home` 持久卷，不能只设置变量就宣称满足。默认 `VOICE_ENABLED` 不等于 `1` 时接口 404。语音配置/存储验证失败时仅禁用语音并记录脱敏错误，不拖垮金融网站；preload 后 fork 的进程返回 503。

## 上线所需配置名（不含实际密钥）

网站保留现有 `ADMIN_USERNAME`、`ADMIN_PASSWORD`；确认生产密码已覆盖仓库既有默认值。新增：

| 名称 | 用途 |
| --- | --- |
| `VOICE_ENABLED=1` | 审核后启用中继 |
| `VOICE_PUBLIC_ORIGIN` | 手机访问的网站确切 HTTPS origin，不含末尾 `/` |
| `AUTH_PUBLIC_ORIGIN` | 同一 origin；省略时继承 `VOICE_PUBLIC_ORIGIN` |
| `VOICE_WORKER_SECRET` | 独立随机机器密钥，至少 32 字符，仅 Azure 和 VM worker |
| `VOICE_DB_PATH` | 现有持久本地卷的绝对路径，如 `/home/data/redflower-voice.sqlite3` |
| `AUTH_DB_PATH` | 会话持久卷绝对路径，如 `/home/data/redflower-auth.sqlite3`；不可依赖部署目录默认路径 |
| `VOICE_SINGLE_INSTANCE=1` | 已核实单实例的声明 |
| `VOICE_INSTANCE_COUNT=1` | 同上；不是 Azure 自动扩容控制项 |
| `WEB_CONCURRENCY=1` | 一个 Python worker；还要核对实际 gunicorn `-w 1` |

VM worker：`VOICE_RELAY_ORIGIN`（同一网站 origin）、`VOICE_WORKER_SECRET`、`VOICE_BRIDGE_CODE_FILE`（原型现有 `.local/access-code` 文件的绝对路径）；可选 `VOICE_BRIDGE_ORIGIN`（默认 `http://127.0.0.1:8765`）。不要把网站密码、Gateway token 放这些变量中。

仅本机测试可设置 `VOICE_LOCAL_TEST=1`，允许 127.0.0.1 HTTP 与非 Secure cookie；生产不得设置。`VOICE_MOCK_AGENT=1` 仅模拟 agent，生产不得设置。没有 `VOICE_ACCESS_HASH` 或用户语音密码。

## 手动运行（审查后由部署方执行）

网站使用现有部署，只在确认单实例和持久卷后启用上述配置。既有 App Service 启动命令需保持其他选项并确保单 worker；本次未修改系统或平台启动配置。

在 VM 上复用已经审查的原型 bridge：

```sh
cd /home/azureuser/.openclaw/workspace/voice-car-prototype
node server.mjs
```

bridge 的 `VOICE_PUBLIC_ORIGIN` 保持未设置/loopback，不能继承 Azure 的同名网站变量，否则 loopback worker Origin 会不匹配。网站公开 origin 在 worker 使用 `VOICE_RELAY_ORIGIN`。

另一个 VM 前台进程，在代码仓库根目录、以安全方式注入所需 worker 环境后：

```sh
node voice/worker.mjs
```

当前没有创建 systemd/cron、修改 Gateway 或部署常驻 worker。退出前台进程即可停止。长期运行需要 main 后续审查既有进程管理方式。

## 验证命令与证据边界

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -p test_voice.py -v
node voice/worker.test.mjs
npm ci --prefix web
npm run build --prefix web
PYTHONPATH=. python3 voice/smoke.py
```

`smoke.py` 启动随机 loopback 端口和临时数据库，动态生成测试凭据，不输出密钥，退出关闭进程/锁。默认两轮 HTTP relay → worker → MOCK agent → SQLite 答案验证；不调用真实 Gateway。

可选 `TEST_BRIDGE_MODULE=file:///.../voice-car-prototype/server.mjs` 加测原 bridge（agent 显式注入模拟）。可选 `TEST_PLAYWRIGHT_MODULE=file:///.../playwright-core/index.mjs` 和 `TEST_CHROMIUM=/.../chrome` 加测 390px UI；识别和 TTS 明确模拟，校验播报后再听、停止、文字后备、真实 React 登录→语音 iframe、刷新保持登录、退出撤销语音授权。前提先 build 前端。金融报告列表使用空列表测试 fixture；认证/语音接口全部走真实 HTTP 后端。本分支还以 `TEST_REAL_AGENT=1`、`VOICE_SESSION_KEY=agent:main:voice-relay-validation` 和既有 `TEST_BRIDGE_MODULE` 完成了两轮真实 Gateway/main 连续上下文测试（中继/worker/bridge 都实际运行；网站为临时 loopback 测试服务）。不能将其描述为 Azure 生产部署或真机音频已验证。该选项会调用真实 main、使用既有模型额度并记录专用会话，只在明确授权后运行。

iPhone Safari 真机、真实麦克风/TTS、车载蓝牙未验收。识别依赖 Safari/Apple 支持和权限；播报后重新启动可能需用户手势。锁屏、后台、来电均可能暂停，PWA 不能保证后台语音；页面明确提示保持前台亮屏，支持文字/键盘听写和手动重播。无语音打断能力。

## 部署风险核对

`.github/workflows/main_littleflowerbriefing.yml` 和 `main_littleredflower.yml` 都由 main push 触发，分别部署 `LittleFlowerBriefing` / `littleredflower`，且两个构建使用不同 Python/Node 版本。此次没有更改 workflow。**push main 会影响两个目标**，上线前需确认真正手机访问的 App Service、对应 secret/持久卷/单实例设置，以及另一个应用是否应部署；不要在未确认时 push main。当前分支应先审查，不 push 不部署。
