import os
import datetime
import argparse
import akshare as ak
import pandas as pd
import markdown
import json
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

# 配置 Azure OpenAI
def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"配置文件读取失败: {e}")
    return {}

AZURE_CONFIG = load_config()

# 如果配置文件不存在或缺少关键字段,提供默认值(不含敏感信息)
if not AZURE_CONFIG:
    AZURE_CONFIG = {
        "deploymentName": "gpt-4.1-mini",
        "maxTokens": 3000,
        "temperature": 0.7
    }

def get_azure_client():
    try:
        if "apiKey" in AZURE_CONFIG and AZURE_CONFIG["apiKey"]:
            return AzureOpenAI(
                azure_endpoint=AZURE_CONFIG["endpoint"],
                api_key=AZURE_CONFIG["apiKey"],
                api_version="2024-05-01-preview"
            )

        credential = DefaultAzureCredential(managed_identity_client_id=AZURE_CONFIG.get("managedIdentityClientId"))
        token_provider = lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token
        return AzureOpenAI(
            azure_endpoint=AZURE_CONFIG["endpoint"],
            azure_ad_token_provider=token_provider,
            api_version="2024-05-01-preview"
        )
    except Exception as e:
        print(f"初始化 Azure Client 失败了: {e}")
        return None

def get_date_str():
    return datetime.datetime.now().strftime("%Y年%m月%d日")

def get_stock_reason(symbol, name, industry=None, first_time=None, client=None):
    """
    获取个股相关新闻,并尝试利用 AI 总结涨停原因
    """
    try:
        # 获取最近的新闻
        news_df = ak.stock_news_em(symbol=symbol)
        if news_df.empty:
            return ""

        related_news = []
        news_contexts = [] # 用于发给 AI 的纯文本素材

        # 遍历前 10 条新闻,筛选有效信息,保留 3 条展示
        valid_count = 0

        for _, row in news_df.head(10).iterrows():
            title = str(row.get('新闻标题', '')).strip()
            content = str(row.get('新闻内容', '')).strip()

            if not title or title == 'nan':
                continue

            summary = content[:100].replace('\n', ' ').strip()

            # 格式化展示用
            if valid_count < 3:
                news_item = f"    * 资讯: {title} (摘要: {summary}...)"
                related_news.append(news_item)

            # 收集给 AI 分析用 (多收集一点也可以,比如前5条的标题)
            news_contexts.append(f"- {title}: {summary}")

            valid_count += 1

        analysis_result = ""
        # 如果有客户端且有新闻,调用 AI 进行总结
        if client and news_contexts:
            try:
                # 构造一个小 Prompt
                context_str = "\n".join(news_contexts[:5]) # 给 AI 看前5条
                prompt = f"""请阅读以下关于股票【{name}】(代码{symbol})的近期新闻,分析并总结其涨停或异动的核心原因。

新闻列表:
{context_str}

要求:
1. 重点指出具体利好事件、涉及的具体概念(如"低空经济"、"并购重组"等)。
2. 逻辑清晰,一句话概括,不要有"经分析"等废话。
3. 控制在 60 字以内,保留关键信息。"""

                # 快速调用,temperature 低一点保证稳定
                response = client.chat.completions.create(
                    model=AZURE_CONFIG["deploymentName"],
                    messages=[
                        {"role": "system", "content": "你是一名A股短线分析师。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=200
                )
                reason_text = response.choices[0].message.content.strip()
                # 去除可能的引号
                reason_text = reason_text.replace('"', '').replace("'", "")

                # 补充板块和时间信息
                meta_info = ""
                if industry:
                    meta_info += f"[板块:{industry}]"
                if first_time:
                    # 格式化时间 HHMMSS -> HH:MM:SS
                    ft_str = str(first_time).strip()
                    if len(ft_str) == 6 and ft_str.isdigit():
                        ft_str = f"{ft_str[:2]}:{ft_str[2:4]}:{ft_str[4:]}"
                    meta_info += f"[首封:{ft_str}]"
                if meta_info:
                    meta_info += " "

                analysis_result = f"    * AI分析: {meta_info}{reason_text}"
            except Exception as ai_e:
                # AI 分析失败不影响主流程,只打印日志
                print(f"  [AI分析 {name} 失败]: {ai_e}")

        # 组合返回结果
        result_parts = []
        if analysis_result:
            result_parts.append("\n" + analysis_result)
        if related_news:
             result_parts.append("\n" + "\n".join(related_news))

        return "".join(result_parts)

    except Exception:
        pass
    return ""

def fetch_daily_market_data():
    print("正在从 AkShare 获取实时市场数据 (日报模式)...")

    # 尝试初始化 AI 客户端用于个股分析
    ai_client = get_azure_client()
    if ai_client:
        print("DEBUG: AI 辅助分析模块已就绪")
    else:
        print("DEBUG: AI 模块初始化失败,将仅展示原始新闻")

    data_summary = []

    # 定义缓存文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(script_dir, "last_successful_data_daily.txt")

    # 1. 获取主要指数行情 (使用历史日线数据以确保通过日期匹配)
    data_summary.append("【昨日市场行情】")
    try:
        # 使用 ak.stock_zh_index_daily 获取历史数据
        # sh000001: 上证指数, sz399001: 深证成指, sz399006: 创业板指
        target_indices = {
            'sh000001': '上证指数',
            'sz399001': '深证成指',
            'sz399006': '创业板指'
        }

        # 确定"昨日"的日期:即最近一个已收盘的交易日
        # 策略:获取上证指数最近几行数据,取最新的一行作为参考日期(如果不算今日的话)
        # 如果脚本是在交易日盘中运行,我们可能想要的是前一个交易日的数据
        # 但通常晨讯是在第二天早上运行,所以想要的是 df.iloc[-1] (如果 API 还没更新今日数据)
        # 或者 df.iloc[-2] (如果 API 已经更新了今日数据)

        # 先获取一次上证指数来确定日期
        ref_df = ak.stock_zh_index_daily(symbol='sh000001')
        if ref_df.empty:
            raise Exception("无法获取基准指数数据")

        # 简单的逻辑:如果最后一行日期是今天,且现在不是晚上,那可能是盘中数据,或者我们其实想要昨天的数据
        # 既然是"晨讯",通常是还没开盘或者刚开盘,所以我们想要的是"最近一个完整的交易日"
        # 查看最后一行日期
        last_date = pd.to_datetime(ref_df.iloc[-1]['date']).date()
        current_date = datetime.datetime.now().date()

        target_row_idx = -1
        if last_date == current_date:
            # 如果API返回了今天的数据(说明今天已经开始交易或已结束),作为晨讯我们应该取昨天(即上一行)
            target_row_idx = -2

        report_date = ref_df.iloc[target_row_idx]['date']
        print(f"DEBUG: 选定的报告日期为 {report_date}")

        for code, name in target_indices.items():
            df = ak.stock_zh_index_daily(symbol=code)
            # 找到对应日期的行
            row = df[df['date'].astype(str) == str(report_date)]

            if not row.empty:
                close_price = row.iloc[0]['close']
                # 计算涨跌幅: (close - prev_close) / prev_close
                # 需找到前一天的收盘价
                row_idx = row.index[0]
                if row_idx > 0:
                    prev_close = df.iloc[row_idx - 1]['close']
                    change_pct = (close_price - prev_close) / prev_close * 100

                    # 格式化
                    change_pct_str = f"{change_pct:.2f}"
                    data_summary.append(f"{name}: {close_price:.2f} ({change_pct_str}%)")
                else:
                    data_summary.append(f"{name}: {close_price:.2f} (无法计算涨跌)")
            else:
                data_summary.append(f"{name}: 数据缺失")

        data_summary.append("")
        print(f"DEBUG: 成功获取历史指数数据: {data_summary}")

    except Exception as e:
        print(f"获取指数数据失败: {e}")

    # 1.2 获取两市成交额
    try:
        # 使用 daily_em 接口获取历史成交额
        sh_daily = ak.stock_zh_index_daily_em(symbol='sh000001')
        sz_daily = ak.stock_zh_index_daily_em(symbol='sz399001')

        if not sh_daily.empty and not sz_daily.empty:
            # 确保日期列为 datetime 类型以便合并
            sh_daily['date'] = pd.to_datetime(sh_daily['date'])
            sz_daily['date'] = pd.to_datetime(sz_daily['date'])

            # 合并数据
            merged = pd.merge(sh_daily[['date', 'amount']], sz_daily[['date', 'amount']], on='date', suffixes=('_sh', '_sz'))
            merged['total_amount'] = merged['amount_sh'] + merged['amount_sz']

            # 同样使用 report_date 来定位数据
            # 注意 report_date 是 string 或 date,需要匹配
            target_row = merged[merged['date'].dt.date.astype(str) == str(report_date)]

            if not target_row.empty:
                today_row = target_row.iloc[0]
                # 获取前一交易日
                # 在 merged 中找到 target_row 的前一行
                # 这种方法依赖 merged 是按时间排序的(通常是)
                target_idx = target_row.index[0]

                today_amount = today_row['total_amount']
                today_trillion = today_amount / 1e12

                data_summary.append(f"【昨日成交额】")
                data_summary.append(f"沪深两市总成交额: {today_trillion:.2f}万亿元")

                if target_idx > 0:
                    prev_row = merged.iloc[target_idx - 1]
                    prev_amount = prev_row['total_amount']
                    change = today_amount - prev_amount
                    change_trillion = change / 1e12

                    if change > 0:
                        data_summary.append(f"较前一交易日放量: {abs(change_trillion):.2f}万亿元")
                    else:
                        data_summary.append(f"较前一交易日缩量: {abs(change_trillion):.2f}万亿元")

                data_summary.append(f"- 上证指数成交额: {today_row['amount_sh']/1e12:.2f}万亿元")
                data_summary.append(f"- 深证成指成交额: {today_row['amount_sz']/1e12:.2f}万亿元")
                data_summary.append("")
                print(f"DEBUG: 成功计算成交额: {today_trillion:.2f}万亿")
            else:
                print(f"未找到日期 {report_date} 的成交额数据")

    except Exception as e:
        print(f"计算成交额失败: {e}")

    # 1.5 获取板块涨跌幅 (新增)
    try:
        data_summary.append("【昨日板块表现】")
        # 行业板块
        ind_df = ak.stock_board_industry_name_em()
        if not ind_df.empty and '涨跌幅' in ind_df.columns:
            ind_df['涨跌幅'] = pd.to_numeric(ind_df['涨跌幅'], errors='coerce')
            ind_sorted = ind_df.sort_values(by='涨跌幅', ascending=False)

            top_ind = ind_sorted.head(5)
            bottom_ind = ind_sorted.tail(5)

            data_summary.append("领涨行业:")
            for _, row in top_ind.iterrows():
                data_summary.append(f"- {row['板块名称']}: {row['涨跌幅']:.2f}% (领涨股: {row.get('领涨股票', 'N/A')})")

            data_summary.append("领跌行业:")
            for _, row in bottom_ind.iterrows():
                data_summary.append(f"- {row['板块名称']}: {row['涨跌幅']:.2f}% (领跌股: {row.get('领涨股票', 'N/A')})")

        # 概念板块
        con_df = ak.stock_board_concept_name_em()
        if not con_df.empty and '涨跌幅' in con_df.columns:
            con_df['涨跌幅'] = pd.to_numeric(con_df['涨跌幅'], errors='coerce')
            con_sorted = con_df.sort_values(by='涨跌幅', ascending=False)

            data_summary.append("领涨概念:")
            for _, row in con_sorted.head(5).iterrows():
                data_summary.append(f"- {row['板块名称']}: {row['涨跌幅']:.2f}%")

        data_summary.append("")
    except Exception as e:
        print(f"获取板块数据失败: {e}")

    # 2. 获取财经新闻 (财联社电报)
    try:
        # stock_info_global_cls 财联社电报
        # 移除不支持的参数 'days'
        news_df = ak.stock_info_global_cls()

        data_summary.append("【昨日资讯】")
        if not news_df.empty:
            print(f"DEBUG: 成功获取到 {len(news_df)} 条新闻。")
            first_title = news_df.iloc[0].get('title') or news_df.iloc[0].get('标题')
            first_time = news_df.iloc[0].get('time') or news_df.iloc[0].get('发布时间')
            print(f"DEBUG: 最新一条新闻: [{first_time}] {first_title}")

            # 确保按时间排序 (假设第一列是时间或发布时间)
            # news_df = news_df.sort_values(by='time', ascending=False)

            # 取前 50 条 (增加数量)
            for _, row in news_df.head(50).iterrows():
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
                    print(f"DEBUG: 成功获取到 {target_date} 的涨停数据,共 {len(df)} 条。")
                    break
            except:
                continue

        data_summary.append("【昨日涨停梯队数据】")
        if zt_pool_df is not None and not zt_pool_df.empty:
            # 确保连板数是数字
            if '连板数' in zt_pool_df.columns:
                zt_pool_df['连板数'] = pd.to_numeric(zt_pool_df['连板数'], errors='coerce')
                zt_pool_df = zt_pool_df.sort_values(by='连板数', ascending=False)

            # 限制 Prompt 中展示的股票总数,防止上下文溢出
            # MAX_DISPLAY = 50 # 移除限制,展示全部
            display_count = 0

            # 分析计数器
            analyzed_count = 0

            for _, row in zt_pool_df.iterrows():
                lb = row.get('连板数')
                # 判定是否为高标股 (>=2连板)
                is_high_lb = isinstance(lb, (int, float)) and lb >= 2

                # 移除截断逻辑,确保展示所有股票
                # if display_count >= MAX_DISPLAY and not is_high_lb:
                #      remaining = len(zt_pool_df) - display_count
                #      data_summary.append(f"... (剩余 {remaining} 只首板/低位涨停股略去)")
                #      break

                name = row.get('名称')
                code = row.get('代码')
                first_time = row.get('首次封板时间')
                last_time = row.get('最后封板时间')
                open_times = row.get('炸板次数')
                industry = row.get('所属行业')

                reason_str = ""

                # --- 核心分析逻辑 ---
                # 1. 如果是 2连板及以上:必须分析
                # 2. 如果是 首板:只有在"已分析总数"不足 10 个时才分析 (填补空位)
                should_analyze = is_high_lb or (analyzed_count < 10)

                if should_analyze:
                    print(f"DEBUG: 正在获取 {name} ({code}) 的涨停原因...")
                    reason_str = get_stock_reason(code, name, industry=industry, first_time=first_time, client=ai_client)
                    analyzed_count += 1

                # 构造描述
                data_summary.append(f"- {name} ({lb}连板): 行业-{industry}, 首次封板-{first_time}, 最后封板-{last_time}, 炸板-{open_times}次{reason_str}")
                display_count += 1
        else:
            data_summary.append("未获取到涨停数据。")

    except Exception as e:
        print(f"获取涨停数据失败: {e}")

    final_text = "\n".join(data_summary)

    # 简单的有效性检查:如果内容太短或缺少关键板块,视为获取失败
    is_valid = len(final_text) > 100 and "【昨日市场行情】" in final_text

    if is_valid:
        # 获取成功,保存到缓存
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(final_text)
            print(f"DEBUG: 最新数据已成功备份至 {cache_file}")
        except Exception as e:
            print(f"数据备份失败: {e}")
    else:
        # 获取失败,尝试读取缓存
        print("⚠️ 警告: 本次自动获取的数据似乎不完整或为空。")
        if os.path.exists(cache_file):
            print("🔄 正在尝试加载上次成功的备份数据...")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_text = f.read()
                if len(cached_text) > 50:
                    final_text = cached_text + "\n\n(注:以上为历史备份数据,因实时获取失败,请检查数据时效性)"
                    print("✅ 成功加载备份数据。")
            except Exception as e:
                print(f"加载备份数据失败: {e}")
        else:
            print("❌ 没有可用的备份数据。")

    return final_text

def fetch_weekly_market_data():
    print("正在获取周报数据 (过去5个交易日)...")

    # 初始化 AI 客户端
    ai_client = get_azure_client()
    if ai_client:
        print("DEBUG: AI 辅助分析模块已就绪 (Weekly)")

    data_summary = []

    # 定义缓存文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file = os.path.join(script_dir, "last_successful_data_weekly.txt")

    # 1. 指数周度表现
    try:
        # 上证指数, 深证成指, 创业板指
        indices = {
            'sh000001': '上证指数',
            'sz399001': '深证成指',
            'sz399006': '创业板指'
        }
        data_summary.append("【上周指数表现】")

        for code, name in indices.items():
            # 获取日线数据
            df = ak.stock_zh_index_daily(symbol=code)
            if not df.empty and len(df) >= 5:
                last_5 = df.tail(5)
                start_close = last_5.iloc[0]['close']
                end_close = last_5.iloc[-1]['close']
                pct_change = (end_close - start_close) / start_close * 100

                data_summary.append(f"{name}: 上周收盘 {end_close:.2f}, 5日涨跌幅 {pct_change:.2f}%")
            else:
                data_summary.append(f"{name}: 数据不足")
        data_summary.append("")
    except Exception as e:
        print(f"获取指数周度数据失败: {e}")

    # 1.2 Calculate Weekly Turnover (New)
    try:
        # Use EM interface for daily data as it includes 'amount'
        sh_df = ak.stock_zh_index_daily_em(symbol='sh000001')
        sz_df = ak.stock_zh_index_daily_em(symbol='sz399001')

        if not sh_df.empty and not sz_df.empty:
            # Ensure date column is datetime for merging
            sh_df['date'] = pd.to_datetime(sh_df['date'])
            sz_df['date'] = pd.to_datetime(sz_df['date'])

            # Merge on date
            merged = pd.merge(sh_df[['date', 'amount']], sz_df[['date', 'amount']], on='date', suffixes=('_sh', '_sz'))

            # Get last 5 days
            last_5 = merged.tail(5)

            if not last_5.empty:
                last_5['total_amount'] = last_5['amount_sh'] + last_5['amount_sz']
                avg_turnover = last_5['total_amount'].mean()
                avg_turnover_trillion = avg_turnover / 1e12

                data_summary.append(f"【上周成交额】")
                data_summary.append(f"沪深两市日均成交额: {avg_turnover_trillion:.2f}万亿元")
                data_summary.append("")
                print(f"DEBUG: 成功计算周均成交额: {avg_turnover_trillion:.2f}万亿")

    except Exception as e:
        print(f"计算周成交额失败: {e}")

    # 1.5 获取板块涨跌幅 (周度 - 使用当前实时排名近似)
    try:
        data_summary.append("【上周板块表现 (参考)】")
        # 行业板块
        ind_df = ak.stock_board_industry_name_em()
        if not ind_df.empty and '涨跌幅' in ind_df.columns:
            ind_df['涨跌幅'] = pd.to_numeric(ind_df['涨跌幅'], errors='coerce')
            ind_sorted = ind_df.sort_values(by='涨跌幅', ascending=False)

            top_ind = ind_sorted.head(5)
            bottom_ind = ind_sorted.tail(5)

            data_summary.append("领涨行业:")
            for _, row in top_ind.iterrows():
                data_summary.append(f"- {row['板块名称']}: {row['涨跌幅']:.2f}%")

            data_summary.append("领跌行业:")
            for _, row in bottom_ind.iterrows():
                data_summary.append(f"- {row['板块名称']}: {row['涨跌幅']:.2f}%")
        data_summary.append("")
    except Exception as e:
        print(f"获取板块数据失败: {e}")

    # 2. 涨停梯队 (周度汇总)
    try:
        data_summary.append("【上周强势股 (涨停统计)】")
        zt_counts = {}

        successful_days = 0
        check_days = 10
        current_date = datetime.datetime.now()

        for i in range(check_days):
            if successful_days >= 5:
                break

            target_date = (current_date - datetime.timedelta(days=i)).strftime("%Y%m%d")
            try:
                df = ak.stock_zt_pool_em(date=target_date)
                if not df.empty:
                    successful_days += 1
                    print(f"DEBUG: 获取到 {target_date} 涨停数据")
                    for _, row in df.iterrows():
                        name = row['名称']
                        industry = row['所属行业']
                        code = row['代码']
                        if name not in zt_counts:
                            zt_counts[name] = {'count': 0, 'industry': industry, 'code': code}
                        zt_counts[name]['count'] += 1
            except:
                pass

        # Sort by count
        sorted_zt = sorted(zt_counts.items(), key=lambda x: x[1]['count'], reverse=True)

        # All
        for name, info in sorted_zt:
            reason_str = ""
            if info['count'] >= 2:
                print(f"DEBUG: 正在获取 {name} ({info['code']}) 的周度涨停原因...")
                reason_str = get_stock_reason(info['code'], name, industry=info['industry'], client=ai_client)

            data_summary.append(f"- {name} ({info['industry']}): 上周涨停 {info['count']} 次{reason_str}")

    except Exception as e:
        print(f"获取周度涨停数据失败: {e}")

    # 3. News (Just fetch recent)
    try:
        news_df = ak.stock_info_global_cls()
        data_summary.append("【近期重要资讯】")
        if not news_df.empty:
             # 取前 50 条
             for _, row in news_df.head(50).iterrows():
                title = row.get('title') or row.get('标题') or ''
                if title:
                    data_summary.append(f"- {title}")
    except Exception as e:
        print(f"获取新闻失败: {e}")

    final_text = "\n".join(data_summary)

    # 简单的有效性检查
    is_valid = len(final_text) > 100 and "【上周指数表现】" in final_text

    if is_valid:
        # 获取成功,保存到缓存
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(final_text)
            print(f"DEBUG: 最新周报数据已成功备份至 {cache_file}")
        except Exception as e:
            print(f"数据备份失败: {e}")
    else:
        # 获取失败,尝试读取缓存
        print("⚠️ 警告: 本次自动获取的周报数据似乎不完整或为空。")
        if os.path.exists(cache_file):
            print("🔄 正在尝试加载上次成功的周报备份数据...")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_text = f.read()
                if len(cached_text) > 50:
                    final_text = cached_text + "\n\n(注:以上为历史备份数据,因实时获取失败,请检查数据时效性)"
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

def generate_briefing(news_content, report_type="daily"):
    # 使用 Managed Identity 获取凭证 (复用 get_azure_client 的逻辑,或者直接调用)
    client = get_azure_client()
    if not client:
        return "无法初始化 Azure OpenAI 客户端"

    date_str = get_date_str()
    date_str_header = datetime.datetime.now().strftime("%Y%m%d")

    if report_type == "weekly":
        title_text = "小红花周报"
        prompt_role = "上周"
        prompt_style = "小红花周报"
        section1_title = "上周市场全景回顾"
        section1_desc = "总结上周指数整体表现(涨跌幅),成交量变化趋势。概括上周的主线行情和风格切换。请务必使用"上周"作为时间状语。"
        section2_title = "深度逻辑与复盘"
        section2_desc = "分析上周涨跌的核心逻辑。点评上周表现最强的板块和个股(结合涨停统计)。"
        section3_title = "热点题材与新闻驱动"
        section3_desc = "将【近期重要资讯】融入到板块分析中。重点挖掘科技、消费、政策相关的题材。内容要丰富详实,不要简略。"
        section4_title = "后市展望与策略建议"
        section4_desc = "给出对本周市场的判断。给出具体操作建议。"
    else:
        title_text = "小红花晨讯"
        prompt_role = "昨日"
        prompt_style = "小红花晨讯"
        section1_title = "市场全景回顾"
        section1_desc = "描述昨日指数表现(涨跌幅)、成交金额及变化(必须提及具体数值)、市场情绪(如"普涨"、"分化"、"修复")。概括领涨和领跌的板块。请务必使用"昨日"作为时间状语。"
        section2_title = "市场深度逻辑分析"
        section2_desc = "分析涨跌背后的原因(如"政策驱动"、"外围影响"、"资金高低切换")。点评市场风格(如"权重搭台"、"题材唱戏"、"高位股分歧")。结合【涨停梯队数据】及其中的个股涨停原因(如有),点评连板高度和短线情绪。"
        section3_title = "热点题材与新闻驱动"
        section3_desc = "将【最新资讯】中的新闻融入到板块分析中。不要罗列新闻,而是写成"受...消息刺激,...板块表现活跃"。内容要丰富详实,不要简略。"
        section4_title = "后市展望与策略建议"
        section4_desc = "给出对今日或短期市场的判断。给出具体操作建议。"

    # 定义晨报/周报的样式模板
    system_prompt = f"""
    你是一位专业的投资分析师。请根据提供的{prompt_role}市场资讯，撰写一篇风格严格模仿"{prompt_style}"的投资报告。

    ### 1. 核心样式规则 (HTML in Markdown)
    请直接输出包含 HTML 标签的 Markdown,以实现复杂的排版和颜色。
    **严禁使用 Markdown 的列表(如 - 或 1.)或分段标题(如 ## 标题),所有内容必须是 3-4 段紧凑的段落文本,像新闻通稿一样连贯。**

    **头部排版 (必须完全一致):**
    请使用 HTML 表格来模拟头部布局:
    ```html
    <table style="width: 100%; border: none; margin-bottom: 10px;">
        <tr>
            <td style="text-align: left; width: 60%; vertical-align: bottom;">
                <span style="color: red; font-size: 24px; font-weight: bold;">{title_text}</span>
            </td>
            <td style="text-align: right; width: 40%; vertical-align: bottom;">
                <span style="color: red; font-weight: bold; font-size: 12px;">组合建议仅供参考,股市有风险,投资需谨慎。</span>
            </td>
        </tr>
        <tr>
            <td style="text-align: left;">
                <span style="color: blue; font-weight: bold; text-decoration: underline;">小红花智能投研</span>
            </td>
            <td style="text-align: right;">
                <span style="border: 1px solid black; padding: 2px; font-weight: bold;">{date_str_header}</span>
            </td>
        </tr>
    </table>
    <hr style="border-top: 2px solid black; margin-top: 0px;">
    ```

    ### 2. 正文结构 (4段式,每段约150-200字,紧凑排版)
    **第一段:{section1_title}**
    *   {section1_desc}
    *   **关键要求**:多用数据支撑。

    **第二段:{section2_title}**
    *   {section2_desc}

    **第三段:{section3_title}**
    *   {section3_desc}

    **第四段:{section4_title}**
    *   {section4_desc}

    **结尾页脚 (必须完全一致)**
    正文结束后,请输出以下 HTML 表格作为页脚(全蓝色):
    ```html
    <br>
    <table style="width: 100%; border: none; color: blue; font-weight: bold; font-size: 14px;">
        <tr>
            <td style="text-align: left;">• 小红花智能金融资讯平台</td>
            <td style="text-align: right;">• 股市有风险,投资需谨慎,组合建议仅供参考</td>
        </tr>
    </table>
    ```

    ### 3. 颜色使用规则 (严格执行 - 必须大量使用颜色)
    **原则:除了连接词和标点符号,几乎所有实词都应该上色。不要让黑色文字占据主导。**

    *   **<font color='red'>红色 (Red) - 代表积极、强势、上涨、热点</font>**:
        *   **所有上涨相关的动词/形容词**:如 "上涨", "收红", "大涨", "创新高", "七连阳", "反弹", "修复", "活跃", "爆发", "走强", "回升".
        *   **所有强势板块和个股名称**:如 "半导体", "宁德时代", "大消费", "商业航天".
        *   **所有利好因素**:如 "政策红利", "资金流入", "业绩超预期", "重组", "突破".
        *   **核心观点/机会**:如 "牛市初期", "积极做多", "主线", "结构性机会".
        *   **关键正向数据**:如 "1.5万亿", "超4000家".

    *   **<font color='blue'>蓝色 (Blue) - 代表消极、弱势、下跌、风险、冷静描述</font>**:
        *   **所有下跌相关的动词/形容词**:如 "下跌", "收跌", "翻绿", "调整", "回落", "跳水", "下挫", "承压", "走弱".
        *   **所有弱势板块和个股名称**:如 "地产", "白酒" (当它们下跌时).
        *   **所有负面/谨慎因素**:如 "缩量", "分歧", "流出", "减持", "解禁", "利空", "观望", "谨慎".
        *   **中性偏空的描述**:如 "震荡", "分化", "存量博弈", "结构性", "轮动".
        *   **结尾的订阅路径和风险提示**。

    *   **黑色 (Black)**:
        *   仅用于连接词 (的, 了, 是, 和)、标点符号、以及非常普通的叙述性文字。

    ### 4. 写作风格
    *   **紧凑密集且内容丰富**:不要分点,不要换行太频繁,像新闻通稿一样连贯。**每段内容要充实,尽可能多地包含细节、数据和逻辑分析,模仿专业投研报告的深度。**
    *   **专业术语**:使用"结构性行情"、"存量博弈"、"获利盘兑现"、"情绪冰点"等专业词汇。
    *   **数据驱动**:尽可能引用输入数据中的具体数值。
    *   **重要:不要使用 Markdown 代码块**。请直接输出 HTML/Markdown 混合文本,不要用 ```html 或 ```markdown 包裹。
    """

    user_prompt = f"以下是{prompt_role}的市场资讯素材:\n\n{news_content}"

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

        # 后处理:移除可能存在的 Markdown 代码块标记
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

    # 构造完整的 HTML,添加一些基础样式以优化阅读体验
    full_html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>小红花晨讯</title>
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
    parser = argparse.ArgumentParser(description="生成小红花晨讯/周报")
    parser.add_argument("--type", choices=["daily", "weekly"], default="daily", help="报告类型: daily (日报) 或 weekly (周报)")
    args = parser.parse_args()

    report_type = args.type
    print(f"正在生成: {report_type} 报告")

    # 1. 获取自动数据
    if report_type == "weekly":
        fetched_data = fetch_weekly_market_data()
    else:
        fetched_data = fetch_daily_market_data()

    # 2. 读取手动补充素材 (可选)
    manual_input = read_news_input("src/news_input.txt")

    final_content = ""
    if fetched_data:
        final_content += fetched_data + "\n\n"
    if manual_input:
        final_content += "【手动补充素材】\n" + manual_input

    if not final_content.strip():
        print("未获取到任何数据 (AkShare 失败且无手动输入),请检查网络或手动填入 src/news_input.txt。")
    else:
        # 3. 调用 AI 生成
        print("正在生成报告,请稍候...")
        briefing_content = generate_briefing(final_content, report_type=report_type)

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
        file_prefix = "Weekly" if report_type == "weekly" else "Briefing"
        md_file = os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}-{file_prefix}.md")
        save_markdown(briefing_content, md_file)

        # 保存 HTML
        html_file = os.path.join(output_dir, f"{datetime.datetime.now().strftime('%Y-%m-%d')}-{file_prefix}.html")
        save_html(briefing_content, html_file)
