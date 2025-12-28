import os
import datetime
import akshare as ak
import pandas as pd
import markdown
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

# 配置 Azure OpenAI
AZURE_CONFIG = {
    
    "deploymentName": "gpt-4.1-mini",
    "maxTokens": 2500,
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
        print(f"DEBUG: 成功从东方财富获取指数数据: {data_summary}")
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
            for _, row in zt_pool_df.iterrows():
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
    你是一位专业的广发证券投资顾问（施晓斌，执业证书 S0260617110030）。请根据提供的市场资讯，撰写一篇风格严格模仿“睿组合小红花晨讯”的投资晨报。

    ### 1. 核心样式规则 (HTML in Markdown)
    请直接输出包含 HTML 标签的 Markdown，以实现复杂的排版和颜色。
    **严禁使用 Markdown 的列表（如 - 或 1.）或分段标题（如 ## 标题），所有内容必须是 3-4 段紧凑的段落文本，像新闻通稿一样连贯。**

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

    ### 2. 正文结构 (4段式，每段约150-200字，紧凑排版)
    **第一段：市场全景回顾**
    *   描述昨日指数表现（涨跌幅）、成交金额（必须提及具体数值）、市场情绪（如“普涨”、“分化”、“修复”）。
    *   概括领涨和领跌的板块。
    *   **关键要求**：多用数据支撑，如“成交额突破1.5万亿”、“超4000家上涨”。

    **第二段：市场深度逻辑分析**
    *   分析涨跌背后的原因（如“政策驱动”、“外围影响”、“资金高低切换”）。
    *   点评市场风格（如“权重搭台”、“题材唱戏”、“高位股分歧”）。
    *   结合【涨停梯队数据】，点评连板高度和短线情绪（如“高标股出现亏钱效应”、“连板晋级率提升”），可提及1-2只代表性龙头股。

    **第三段：热点题材与新闻驱动**
    *   将【最新资讯】中的新闻融入到板块分析中。**不要罗列新闻**，而是写成“受...消息刺激，...板块表现活跃”或“...行业迎来利好，相关个股走强”。
    *   重点挖掘科技、消费、政策相关的题材。

    **第四段：后市展望与策略建议**
    *   给出对今日或短期市场的判断（如“震荡整理”、“有望冲击新高”）。
    *   给出具体操作建议（如“控制仓位”、“逢低吸纳”、“去弱留强”）。

    **结尾页脚 (必须完全一致)**
    正文结束后，请输出以下 HTML 表格作为页脚（全蓝色）：
    ```html
    <br>
    <table style="width: 100%; border: none; color: blue; font-weight: bold; font-size: 14px;">
        <tr>
            <td style="text-align: left;">• 订阅路径：易淘金APP-投顾-睿组合-睿组合xx号 (小红花)</td>
            <td style="text-align: right;">• 股市有风险，投资需谨慎，组合建议仅供参考</td>
        </tr>
    </table>
    ```

    ### 3. 颜色使用规则 (严格执行 - 必须大量使用颜色)
    **原则：除了连接词和标点符号，几乎所有实词都应该上色。不要让黑色文字占据主导。**

    *   **<font color='red'>红色 (Red) - 代表积极、强势、上涨、热点</font>**：
        *   **所有上涨相关的动词/形容词**：如 "上涨", "收红", "大涨", "创新高", "七连阳", "反弹", "修复", "活跃", "爆发", "走强", "回升".
        *   **所有强势板块和个股名称**：如 "半导体", "宁德时代", "大消费", "商业航天".
        *   **所有利好因素**：如 "政策红利", "资金流入", "业绩超预期", "重组", "突破".
        *   **核心观点/机会**：如 "牛市初期", "积极做多", "主线", "结构性机会".
        *   **关键正向数据**：如 "1.5万亿", "超4000家".

    *   **<font color='blue'>蓝色 (Blue) - 代表消极、弱势、下跌、风险、冷静描述</font>**：
        *   **所有下跌相关的动词/形容词**：如 "下跌", "收跌", "翻绿", "调整", "回落", "跳水", "下挫", "承压", "走弱".
        *   **所有弱势板块和个股名称**：如 "地产", "白酒" (当它们下跌时).
        *   **所有负面/谨慎因素**：如 "缩量", "分歧", "流出", "减持", "解禁", "利空", "观望", "谨慎".
        *   **中性偏空的描述**：如 "震荡", "分化", "存量博弈", "结构性", "轮动".
        *   **结尾的订阅路径和风险提示**。

    *   **黑色 (Black)**：
        *   仅用于连接词 (的, 了, 是, 和)、标点符号、以及非常普通的叙述性文字。

    ### 4. 写作风格
    *   **紧凑密集**：不要分点，不要换行太频繁，像新闻通稿一样连贯。
    *   **专业术语**：使用“结构性行情”、“存量博弈”、“获利盘兑现”、“情绪冰点”等专业词汇。
    *   **数据驱动**：尽可能引用输入数据中的具体数值。
    *   **重要：不要使用 Markdown 代码块**。请直接输出 HTML/Markdown 混合文本，不要用 ```html 或 ```markdown 包裹。
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
        content = response.choices[0].message.content
        
        # 后处理：移除可能存在的 Markdown 代码块标记
        if content.strip().startswith("```"):
            lines = content.strip().split('\n')
            # 移除第一行 (如 ```html)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # 移除最后一行 (如 ```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
            
        return content
    except Exception as e:
        return f"生成失败: {str(e)}"

def save_markdown(content, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"晨训 Markdown 已生成: {filename}")

def save_html(content, filename):
    # 将 Markdown 转换为 HTML
    html_body = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    
    # 构造完整的 HTML，添加一些基础样式以优化阅读体验
    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>睿组合小红花晨讯</title>
        <style>
            body {{
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
                line-height: 1.6;
                max_width: 800px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            /* 针对数据来源的代码块样式 */
            pre {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: Consolas, monospace;
            }}
            /* 针对生成的 HTML 表格样式 (如果有) */
            td, th {{
                padding: 5px;
            }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"晨训 HTML 已生成: {filename}")

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
        
        # 添加数据来源板块
        if fetched_data:
            briefing_content += "\n\n---\n### 数据来源\n\n```text\n" + fetched_data + "\n```"

        # 4. 保存文件
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 定义输出目录为项目根目录下的 briefings 文件夹
        output_dir = os.path.join(os.path.dirname(script_dir), "briefings")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 保存 Markdown
        md_file = os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}-Briefing.md")
        save_markdown(briefing_content, md_file)
        
        # 保存 HTML
        html_file = os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}-Briefing.html")
        save_html(briefing_content, html_file)
