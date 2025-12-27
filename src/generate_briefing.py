import os
import datetime
import akshare as ak
import pandas as pd
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

# 配置 Azure OpenAI
AZURE_CONFIG = {
    "managedIdentityClientId": "",
    "endpoint": "",
    "deploymentName": "gpt-4.1-mini",
    "maxTokens": 800,
    "temperature": 0.7
}

def get_date_str():
    return datetime.datetime.now().strftime("%Y年%m月%d日")

def fetch_market_data():
    print("正在从 AkShare 获取实时市场数据...")
    data_summary = []
    
    # 定义缓存文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(script_dir, "last_successful_data.txt")

    # 1. 获取主要指数行情
    try:
        # 尝试使用东方财富接口 (stock_zh_index_spot_em)
        # 注意：接口名称可能会随版本变化，如果失败请检查 akshare 文档
        indices_df = ak.stock_zh_index_spot_em()
        
        # 东方财富接口返回的代码通常是纯数字字符串
        target_indices = {'000001': '上证指数', '399001': '深证成指', '399006': '创业板指'}
        
        data_summary.append("【市场行情】")
        for code, name in target_indices.items():
            row = indices_df[indices_df['代码'] == code]
            if not row.empty:
                latest = row.iloc[0]['最新价']
                change_pct = row.iloc[0]['涨跌幅']
                data_summary.append(f"{name}: {latest} ({change_pct}%)")
        data_summary.append("")
    except AttributeError:
        # 如果 stock_zh_index_spot_em 不存在，尝试 stock_zh_index_spot_sina
        try:
            indices_df = ak.stock_zh_index_spot_sina()
            target_indices = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指'}
            data_summary.append("【市场行情 (Sina)】")
            for code, name in target_indices.items():
                row = indices_df[indices_df['代码'] == code]
                if not row.empty:
                    latest = row.iloc[0]['最新价']
                    change_pct = row.iloc[0]['涨跌幅']
                    data_summary.append(f"{name}: {latest} ({change_pct}%)")
            data_summary.append("")
        except Exception as e:
             print(f"获取指数数据失败 (Sina): {e}")
    except Exception as e:
        print(f"获取指数数据失败: {e}")

    # 2. 获取财经新闻 (财联社电报)
    try:
        # stock_info_global_cls 财联社电报
        # 移除不支持的参数 'days'
        news_df = ak.stock_info_global_cls()
        
        data_summary.append("【最新资讯】")
        if not news_df.empty:
            print(f"DEBUG: 成功获取到 {len(news_df)} 条新闻。")
            first_title = news_df.iloc[0].get('title') or news_df.iloc[0].get('标题')
            first_time = news_df.iloc[0].get('time') or news_df.iloc[0].get('发布时间')
            print(f"DEBUG: 最新一条新闻: [{first_time}] {first_title}")

            # 确保按时间排序 (假设第一列是时间或发布时间)
            # news_df = news_df.sort_values(by='time', ascending=False) 
            
            # 取前 20 条
            for _, row in news_df.head(20).iterrows():
                # 适配中文列名
                title = row.get('title') or row.get('标题') or ''
                content = row.get('content') or row.get('内容') or ''
                
                if title:
                    data_summary.append(f"- {title}")
                elif content:
                    data_summary.append(f"- {content[:100]}...")
    except Exception as e:
        print(f"获取新闻数据失败: {e}")

    # 3. 获取涨停股池 (新增)
    try:
        zt_pool_df = None
        # 尝试获取最近 5 天的数据 (找到最近的一个交易日)
        for delta in range(0, 5):
            target_date = (datetime.datetime.now() - datetime.timedelta(days=delta)).strftime("%Y%m%d")
            try:
                df = ak.stock_zt_pool_em(date=target_date)
                if not df.empty:
                    zt_pool_df = df
                    print(f"DEBUG: 成功获取到 {target_date} 的涨停数据，共 {len(df)} 条。")
                    break
            except:
                continue
        
        data_summary.append("【涨停梯队数据】")
        if zt_pool_df is not None and not zt_pool_df.empty:
            # 确保连板数是数字
            if '连板数' in zt_pool_df.columns:
                zt_pool_df['连板数'] = pd.to_numeric(zt_pool_df['连板数'], errors='coerce')
                zt_pool_df = zt_pool_df.sort_values(by='连板数', ascending=False)
            
            # 取前 15 只龙头 (连板数高的)
            for _, row in zt_pool_df.head(15).iterrows():
                name = row.get('名称')
                lb = row.get('连板数')
                first_time = row.get('首次封板时间')
                last_time = row.get('最后封板时间')
                open_times = row.get('炸板次数')
                industry = row.get('所属行业')
                
                # 构造描述给 AI 分析
                data_summary.append(f"- {name} ({lb}连板): 行业-{industry}, 首次封板-{first_time}, 最后封板-{last_time}, 炸板-{open_times}次")
        else:
            data_summary.append("未获取到涨停数据。")

    except Exception as e:
        print(f"获取涨停数据失败: {e}")
        
    final_text = "\n".join(data_summary)
    
    # 简单的有效性检查：如果内容太短或缺少关键板块，视为获取失败
    is_valid = len(final_text) > 100 and "【市场行情】" in final_text
    
    if is_valid:
        # 获取成功，保存到缓存
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(final_text)
            print(f"DEBUG: 最新数据已成功备份至 {cache_file}")
        except Exception as e:
            print(f"数据备份失败: {e}")
    else:
        # 获取失败，尝试读取缓存
        print("⚠️ 警告: 本次自动获取的数据似乎不完整或为空。")
        if os.path.exists(cache_file):
            print("🔄 正在尝试加载上次成功的备份数据...")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_text = f.read()
                if len(cached_text) > 50:
                    final_text = cached_text + "\n\n(注：以上为历史备份数据，因实时获取失败，请检查数据时效性)"
                    print("✅ 成功加载备份数据。")
            except Exception as e:
                print(f"加载备份数据失败: {e}")
        else:
            print("❌ 没有可用的备份数据。")

    return final_text

def read_news_input(file_path="news_input.txt"):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_briefing(news_content):
    # 使用 Managed Identity 获取凭证
    credential = DefaultAzureCredential(managed_identity_client_id=AZURE_CONFIG["managedIdentityClientId"])
    token_provider = lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token

    client = AzureOpenAI(
        azure_endpoint=AZURE_CONFIG["endpoint"],
        azure_ad_token_provider=token_provider,
        api_version="2024-05-01-preview"
    )
    
    date_str = get_date_str()
    date_str_header = datetime.datetime.now().strftime("%Y%m%d")
    
    # 定义晨报的样式模板
    # 严格模仿"睿组合小红花晨讯"的样式
    system_prompt = f"""
    你是一位专业的广发证券投资顾问（施晓斌，执业证书 xxxxxxx）。请根据提供的市场资讯，撰写一篇风格严格模仿“睿组合小红花晨讯”的投资晨报。

    ### 1. 核心样式规则 (HTML in Markdown)
    请直接输出包含 HTML 标签的 Markdown，以实现复杂的排版和颜色。

    **头部排版 (必须完全一致):**
    请使用 HTML 表格来模拟头部布局：
    ```html
    <table style="width: 100%; border: none; margin-bottom: 10px;">
        <tr>
            <td style="text-align: left; width: 60%; vertical-align: bottom;">
                <span style="color: red; font-size: 24px; font-weight: bold;">睿组合小红花晨讯</span>
            </td>
            <td style="text-align: right; width: 40%; vertical-align: bottom;">
                <span style="color: red; font-weight: bold; font-size: 12px;">组合建议仅供参考，股市有风险，投资需谨慎。</span>
            </td>
        </tr>
        <tr>
            <td style="text-align: left;">
                <span style="color: blue; font-weight: bold; text-decoration: underline;">张济涛 广发证券投资顾问 (S0260617110030)</span>
            </td>
            <td style="text-align: right;">
                <span style="border: 1px solid black; padding: 2px; font-weight: bold;">{date_str_header}</span>
            </td>
        </tr>
    </table>
    <hr style="border-top: 2px solid black; margin-top: 0px;">
    ```

    ### 2. 正文内容与颜色逻辑
    **不要使用** "## 市场回顾" 这种分段标题。正文应该是 **3-4 段紧凑的文字**，段落之间空一行。

    **颜色使用规则 (非常重要):**
    *   **<font color='red'>红色 (Red)</font>**：
        *   **上涨** (如 "沪指上涨", "收获六连阳", "创新高").
        *   **利好消息** (如 "政策驱动", "重组", "业绩超预期").
        *   **强势板块/个股** (如 "宁德时代大涨", "半导体爆发").
        *   **乐观观点** (如 "牛市起点", "积极布局").
        *   **关键强调** (如 "核心主线", "资金流入").
    *   **<font color='blue'>蓝色 (Blue)</font>**：
        *   **下跌** (如 "创业板指下跌", "冲高回落", "调整").
        *   **利空/风险** (如 "成交额萎缩", "外资流出", "减持").
        *   **弱势板块** (如 "白酒回调", "地产承压").
        *   **谨慎观点** (如 "震荡整理", "观望").
        *   **中性/描述性数据** (如 "成交额不足8000亿", "沪指报3000点").
    *   **黑色 (Black)**：
        *   连接词、普通叙述、背景描述。

    ### 3. 写作结构
    *   **第一段 (市场全景)**：描述指数涨跌、成交量、北向资金、市场情绪。重点突出“涨”或“跌”的定性。
    *   **第二段 (板块与热点)**：详细描述领涨板块（红）和领跌板块（蓝）。结合新闻解释原因（如“受...政策催化”）。
    *   **第三段 (涨停复盘)**：请分析【涨停梯队数据】，挑选 3-5 只代表性个股（如连板高度最高的），标注其**涨停时间**（如 "09:35封板"）和**分时形态**（根据封板时间和炸板次数推断，如 "早盘快速封板"、"烂板回封"、"T字板"）。
    *   **第四段 (宏观与策略)**：结合宏观新闻（如美联储、国内政策）给出策略建议。
    *   **结尾 (订阅信息)**：最后一句必须是蓝色背景或蓝色文字的订阅路径：
        *   `<span style="background-color: blue; color: white; padding: 2px;">订阅路径：易淘金APP-投顾-睿组合-睿组合18号 (小红花)</span>`

    ### 4. 语气风格
    *   专业、干练、逻辑性强。
    *   多用金融术语（如“震荡上行”、“结构性分化”、“存量博弈”）。
    *   **不要**输出 Markdown 代码块标记 (```markdown)，直接输出内容。
    """

    user_prompt = f"以下是今日的市场资讯素材：\n\n{news_content}"

    try:
        response = client.chat.completions.create(
            model=AZURE_CONFIG["deploymentName"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=AZURE_CONFIG["temperature"],
            max_tokens=AZURE_CONFIG["maxTokens"]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"生成失败: {str(e)}"

def save_markdown(content, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"晨训已生成: {filename}")

if __name__ == "__main__":
    # 1. 获取自动数据
    fetched_data = fetch_market_data()
    
    # 2. 读取手动补充素材 (可选)
    manual_input = read_news_input("src/news_input.txt")
    
    final_content = ""
    if fetched_data:
        final_content += fetched_data + "\n\n"
    if manual_input:
        final_content += "【手动补充素材】\n" + manual_input
        
    if not final_content.strip():
        print("未获取到任何数据 (AkShare 失败且无手动输入)，请检查网络或手动填入 src/news_input.txt。")
    else:
        # 3. 调用 AI 生成
        print("正在生成晨训，请稍候...")
        # print(f"发送给 AI 的内容预览:\n{final_content[:500]}...") # 调试用
        briefing_content = generate_briefing(final_content)
        
        # 4. 保存文件
        # 获取脚本所在目录，确保文件保存在 src 目录下，无论从哪里运行
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}-Briefing.md")
        save_markdown(briefing_content, output_file)
