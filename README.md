# 小红花 - 智能金融资讯平台

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![React](https://img.shields.io/badge/react-18.0-61dafb.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

一个专为投资顾问和金融分析师打造的智能资讯生成与分析平台，结合 **AI 驱动** 与 **实时数据**，提供专业的市场洞察。

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [架构设计](#-技术架构) • [API 文档](#-api-文档)

</div>

---

## ✨ 功能特性

### 📊 A 股市场分析

#### 🌅 **每日晨讯 & 周报生成**
- 🤖 **AI 驱动写作**：基于 GPT-4 深度分析市场动态
- 📈 **全面数据覆盖**：指数行情、板块表现、涨停梯队、财经新闻
- 🎨 **专业排版**：严格复刻投顾报告风格，红蓝配色清晰直观
- 🔄 **自动化生成**：定时任务每日 08:00 自动输出

#### 🎯 **多维度市场监控**
- **AI 情绪看板**：实时评估市场情绪（0-100 分，恐慌到贪婪）
- **全景雷达**：板块热力图 + 涨停梯队实时追踪
- **指数 K 线**：主要指数走势与技术指标（MA5/MA20）
- **资金流向**：个股主力资金净流入排名
- **热点题材**：概念板块涨跌幅实时监控
- **风险预警**：异常波动提醒与风控建议

#### 🔍 **个股诊断工具**
- 输入股票代码，一键获取：
  - 📉 历史价格与成交量分析
  - 📊 技术指标评估
  - 💡 AI 生成的投资建议

---

### 🇺🇸 **美股科技股看板** <sup>NEW</sup>

> 🎉 **v2.0 新增功能** - 专注全球科技龙头，把握美股投资机遇

#### 📱 **核心亮点**
- **9 只科技巨头实时追踪**：
  - 🍎 Apple (AAPL)
  - Ⓜ️ Microsoft (MSFT)
  - 🔍 Google (GOOGL)
  - 🛒 Amazon (AMZN)
  - 📘 Meta (META)
  - 💻 NVIDIA (NVDA)
  - ⚡ Tesla (TSLA)
  - 🎬 Netflix (NFLX)
  - 🔧 AMD

#### ⚡ **性能优化**
- **多层缓存机制**：内存 + 文件双层缓存，首次 ~9 秒，后续 < 1 秒
- **并发数据获取**：5 线程并行，大幅提升响应速度
- **容错降级策略**：单股失败不影响整体展示
- **超时保护**：智能超时控制，确保系统稳定

#### 📊 **可视化展示**
- **3x3 网格卡片布局**：清晰展示每只股票详情
- **30 日趋势图**：直观识别价格走势
- **实时统计摘要**：领涨/领跌股、平均涨跌幅一目了然
- **红涨绿跌配色**：符合中国市场习惯

#### 🕐 **自动更新**
- **定时生成**：每周二~周六 05:30（美股收盘后）
- **手动触发**：支持实时刷新最新行情

> 📖 详细文档：[美股科技股功能说明](docs/US_TECH_STOCKS_README.md)

---

### 🤖 **AI 聊天助手**
- 💬 智能对话，解答市场疑问
- 📊 自动注入市场上下文，回答更精准
- 🔄 支持多轮对话，连续深入分析

---

## 🛠️ 技术架构

### **后端技术栈**
```
Python 3.8+
├── FastAPI          # 高性能异步 Web 框架
├── APScheduler      # 定时任务调度
├── AkShare          # A 股数据源（东方财富/新浪）
├── yfinance         # 美股数据源（Yahoo Finance）
├── Tushare Pro      # 备用数据源（可选）
├── Azure OpenAI     # GPT-4 AI 分析引擎
└── Pandas/Numpy     # 数据处理
```

### **前端技术栈**
```
React 18
├── Vite             # 极速构建工具
├── Lucide React     # 矢量图标库
├── Recharts/ECharts # 数据可视化（可选）
└── CSS Modules      # 模块化样式
```

### **架构特性**
- ✅ **前后端分离**：API 驱动，易于扩展
- ✅ **容器化部署**：支持 Docker 快速部署
- ✅ **云原生设计**：Azure App Service 托管标识认证
- ✅ **数据持久化**：本地存储 + 云端持久卷
- ✅ **高并发支持**：异步处理 + 线程池优化

---

## 🚀 快速开始

### **环境准备**

#### 1. 克隆仓库
```bash
git clone https://github.com/DilongWu/LittleRedFlower.git
cd LittleRedFlower
```

#### 2. 安装依赖

**后端依赖：**
```bash
pip install -r requirements.txt
```

**前端依赖：**
```bash
cd web
npm install
npm run build  # 构建生产版本
```

#### 3. 配置 Azure OpenAI

创建 `api/config.json`（该文件已在 `.gitignore` 中）：
```json
{
  "endpoint": "https://your-resource.openai.azure.com/",
  "deployment": "your-gpt4-deployment-name",
  "apiVersion": "2024-02-15-preview"
}
```

> ⚠️ **安全提示**：
> - 生产环境建议使用 **Azure Managed Identity** 认证（无需 API Key）
> - 或通过环境变量配置：`AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_DEPLOYMENT`

#### 4. 启动服务

```bash
# 开发模式（带热重载）
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

#### 5. 访问应用

打开浏览器访问：**http://localhost:8000**

**默认登录凭证**：
- 用户名：`admin`
- 密码：`littleredfloweradmin`

> 💡 生产环境请通过环境变量 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 修改密码

---

## 📂 项目结构

```
LittleRedFlower/
├── api/                        # 后端服务
│   ├── main.py                # FastAPI 主应用
│   ├── scheduler.py           # 定时任务调度器
│   ├── config.json            # Azure OpenAI 配置（需自行创建）
│   └── services/              # 业务逻辑模块
│       ├── generator.py       # 晨报生成引擎
│       ├── market.py          # A 股市场数据
│       ├── us_stocks.py       # 美股数据（NEW）
│       ├── diagnosis.py       # 个股诊断
│       ├── chat.py            # AI 聊天服务
│       └── ...
│
├── web/                       # 前端应用
│   ├── src/
│   │   ├── App.jsx           # 主应用组件
│   │   ├── components/       # React 组件
│   │   │   ├── ReportViewer.jsx
│   │   │   ├── USTechStocks.jsx    # 美股看板（NEW）
│   │   │   ├── SentimentDashboard.jsx
│   │   │   └── ...
│   │   └── services/
│   │       └── dataCache.js  # 前端缓存服务
│   └── dist/                 # 构建产物
│
├── storage/                   # 数据持久化目录
│   ├── YYYY-MM-DD_daily.json      # 每日报告
│   ├── YYYY-MM-DD_us_tech.json    # 美股数据（NEW）
│   └── YYYY-MM-DD_sentiment.json  # 市场情绪
│
├── docs/                      # 项目文档
│   └── US_TECH_STOCKS_README.md   # 美股功能文档
│
├── requirements.txt           # Python 依赖
└── README.md                 # 项目说明
```

---

## 📡 API 文档

### **核心端点**

#### A 股数据
```http
GET  /api/reports              # 获取报告列表
GET  /api/reports/{date}       # 获取指定日期报告
POST /api/trigger/daily        # 手动生成日报
POST /api/trigger/weekly       # 手动生成周报
GET  /api/sentiment            # 市场情绪数据
GET  /api/market/radar         # 市场雷达
GET  /api/index/overview       # 指数概览
GET  /api/fund/flow            # 资金流向
GET  /api/concept/hot          # 热点概念
POST /api/stock/diagnosis      # 个股诊断
```

#### 美股数据 <sup>NEW</sup>
```http
GET    /api/us-tech/latest         # 获取最新美股数据
POST   /api/trigger/us-tech        # 手动生成美股数据
DELETE /api/us-tech/cache          # 清空缓存
GET    /api/us-tech/cache/stats    # 缓存统计
```

#### AI 服务
```http
POST /api/chat                 # AI 聊天对话
```

#### 系统管理
```http
POST /api/login                # 用户登录
GET  /api/datasource           # 获取数据源配置
POST /api/datasource           # 切换数据源
```

> 📖 完整 API 文档请参考各 service 模块的 docstring

---

## ⚙️ 配置说明

### **数据源配置**

支持三种数据源（可在 Web 界面切换）：

1. **东方财富（eastmoney）** - 默认推荐
2. **新浪财经（sina）** - 备用方案
3. **Tushare Pro（tushare）** - 需要 Token，支持更多数据

切换数据源：
```bash
# 通过 API
POST /api/datasource
{
  "source": "eastmoney"  # 或 "sina", "tushare"
}
```

### **定时任务配置**

默认调度时间（在 `api/scheduler.py` 中配置）：

| 任务 | 时间 | 说明 |
|------|------|------|
| 每日晨报 | 周二~周六 08:00 | 生成前一交易日报告 |
| 每周周报 | 周六 09:00 | 生成上周总结 |
| 美股数据 | 周二~周六 05:30 | 美股收盘后更新 |
| 缓存预热 | 周一~周五 09:25, 13:00 | 开盘前预加载 |

---

## 🐛 常见问题

### 1. **数据获取失败**
**症状**：部分数据显示"数据获取失败"

**解决方案**：
- 检查网络连接
- 尝试切换数据源（东方财富 ↔ 新浪财经）
- 查看 logs 确认错误详情

### 2. **AI 生成失败**
**症状**：晨报生成卡住或报错

**解决方案**：
- 确认 Azure OpenAI 配置正确
- 检查 API 配额是否用尽
- 验证 Managed Identity 权限

### 3. **美股数据加载慢**
**症状**：首次加载超过 15 秒

**解决方案**：
- 使用缓存数据（点击"刷新"而非"生成数据"）
- 调整并发线程数（`max_workers` 参数）
- 检查 Yahoo Finance API 访问速度

### 4. **登录失败**
**症状**：无法登录系统

**解决方案**：
- 确认用户名密码正确
- 检查是否设置了环境变量 `ADMIN_USERNAME` / `ADMIN_PASSWORD`
- 清除浏览器缓存重试

---

## 🔐 安全最佳实践

1. ✅ **密码管理**：生产环境务必修改默认密码
2. ✅ **API Key 保护**：使用 Managed Identity 或环境变量，勿硬编码
3. ✅ **CORS 配置**：生产环境限制允许的域名
4. ✅ **HTTPS 部署**：使用反向代理（Nginx）配置 SSL 证书
5. ✅ **日志脱敏**：避免在日志中记录敏感信息

---

## 🚢 部署指南

### **Docker 部署（推荐）**

```bash
# 构建镜像
docker build -t littleredflower:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/storage:/app/storage \
  -e ADMIN_PASSWORD=your_secure_password \
  --name littleredflower \
  littleredflower:latest
```

### **Azure App Service 部署**

```bash
# 使用 Azure CLI
az webapp up \
  --name your-app-name \
  --runtime "PYTHON:3.11" \
  --sku B1
```

> 📖 详细部署文档请参考 Azure 官方指南

---

## 📈 性能指标

- **晨报生成时间**：30-60 秒（含 AI 分析）
- **美股数据首次加载**：~9 秒（9 只股票并发）
- **缓存命中后响应**：< 1 秒
- **并发支持**：推荐 4 workers，可支撑 100+ QPS

---

## 🤝 贡献指南

欢迎贡献代码、报告 Bug 或提出新功能建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📜 更新日志

### v2.0.0 (2026-01-30)
- ✨ **新增**：美股科技股看板功能
  - 支持 9 只科技龙头实时追踪
  - 多层缓存 + 并发优化
  - 3x3 网格卡片可视化
- ⚡ **优化**：前端性能提升
- 🐛 **修复**：数据源切换稳定性

### v1.x
- ✨ A 股晨报生成
- ✨ AI 情绪看板
- ✨ 市场雷达与个股诊断

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 💡 致谢

- **数据来源**：[AkShare](https://akshare.xyz/)、[Yahoo Finance](https://finance.yahoo.com/)
- **AI 驱动**：[Azure OpenAI](https://azure.microsoft.com/products/ai-services/openai-service)
- **图标库**：[Lucide](https://lucide.dev/)

---

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 📝 提交 [Issue](https://github.com/DilongWu/LittleRedFlower/issues)
- 🔗 GitHub 仓库：https://github.com/DilongWu/LittleRedFlower

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！⭐**

Made with ❤️ by [DilongWu](https://github.com/DilongWu) & Claude Sonnet 4.5

</div>
