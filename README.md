# 睿组合小红花晨讯生成器 (Little Red Flower Briefing Generator)

这是一个专为基金投资顾问打造的智能晨报生成工具。它结合了 **AkShare 实时数据** 和 **Azure OpenAI** 的强大能力，一键生成风格专业、排版精美的投资晨训。

## ✨ 核心功能

*   **🚀 全自动数据抓取**：
    *   自动获取 A 股核心指数（上证、深证、创业板）的实时行情。
    *   自动拉取财联社（CLS）最新的财经电报。
    *   **[新增] 涨停复盘**：自动分析最近交易日的涨停股池，统计连板高度、封板时间及分时形态。
*   **🎨 专业定制样式**：
    *   严格复刻“睿组合小红花晨讯”风格。
    *   **红蓝配色逻辑**：<font color='red'>红色(利好/上涨)</font>、<font color='blue'>蓝色(利空/下跌)</font>、黑色(中性)。
    *   精美的 HTML 头部排版，包含日期、投顾信息及风险提示。
*   **🛡️ 容灾与备份**：
    *   自动缓存每次成功获取的数据。
    *   当网络或接口故障时，自动降级使用最近一次的备份数据，确保晨报不缺席。
*   **🤖 Azure AI 驱动**：
    *   使用 Azure OpenAI (GPT-4) 进行深度分析与写作。
    *   基于 Managed Identity (托管标识) 的安全认证，无需硬编码 Key。

## 🛠️ 快速开始

### 1. 环境准备

确保已安装 Python 3.8+。安装项目依赖：

```bash
pip install -r src/requirements.txt
```

### 2. Azure 认证 (必须)

本项目使用 Azure Managed Identity 进行安全认证。

*   **本地运行**：
    1.  安装 [Azure CLI](https://learn.microsoft.com/zh-cn/cli/azure/install-azure-cli)。
    2.  在终端运行 `az login` 登录。
    3.  确保登录账号对 Azure OpenAI 资源有访问权限。

*   **云端运行**：
    确保服务器/容器已启用 Managed Identity 并授权。

### 3. 运行生成

**方式 A (推荐)**：
直接双击根目录下的 **`run_briefing.bat`**。

**方式 B (命令行)**：
```bash
python src/generate_briefing.py
```

### 4. 查看结果

脚本运行完成后，会在 `src/` 目录下生成当天的 Markdown 文件，例如：
`src/2025-12-27-Briefing.md`

你可以直接将内容复制到微信、邮件或支持 Markdown/HTML 的发布平台。

## 📝 进阶用法

### 手动补充素材
虽然程序会自动抓取数据，但你可能有一些内部观点或特定通知。
你可以将这些内容写入 **`src/news_input.txt`**。
*   程序会自动将你的手动输入与抓取的数据合并，一起发给 AI。
*   如果不需要，请保持该文件为空。

### 故障恢复
如果遇到 `AkShare` 接口报错或网络问题，程序会自动尝试读取 `src/last_successful_data.txt` 中的历史数据进行生成，并在晨报末尾标注提示。

## 📂 项目结构

```text
LittleRedFlower/
├── src/
│   ├── generate_briefing.py    # 核心生成脚本
│   ├── news_input.txt          # 手动补充素材入口
│   ├── requirements.txt        # Python 依赖
│   ├── last_successful_data.txt # [自动生成] 数据缓存
│   └── YYYY-MM-DD-Briefing.md  # [自动生成] 最终晨报
├── examples/                   # 样式参考案例
├── run_briefing.bat            # Windows 一键运行脚本
└── README.md                   # 说明文档
```
