"""
Yahoo Finance Tools for OpenAI Function Calling
Provides stock data via yfinance, exposed as OpenAI-compatible tools.
"""

import json
import yfinance as yf
from typing import Any, Dict, List


# Tool definitions in OpenAI function calling format
FINANCE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "获取股票实时行情（当前价格、涨跌幅、成交量等）。支持美股代码如 MSFT, NVDA, AAPL, TSLA 等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，例如 MSFT, NVDA, AAPL"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_history",
            "description": "获取股票历史价格数据。可指定时间范围。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码"
                    },
                    "period": {
                        "type": "string",
                        "description": "时间范围: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max",
                        "default": "1mo"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_analyst_ratings",
            "description": "获取分析师对股票的评级和目标价。包括买入/持有/卖出建议数量和平均目标价。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financials",
            "description": "获取公司财务数据（收入、利润、EPS等关键指标）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码"
                    },
                    "statement": {
                        "type": "string",
                        "description": "财务报表类型: income(利润表), balance(资产负债表), cashflow(现金流量表)",
                        "default": "income"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_info",
            "description": "获取公司基本信息（行业、市值、员工数、简介等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码"
                    }
                },
                "required": ["symbol"]
            }
        }
    }
]


def get_stock_quote(symbol: str) -> str:
    """Get real-time stock quote"""
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        result = {
            "symbol": symbol.upper(),
            "name": info.get("shortName", "N/A"),
            "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
            "previousClose": info.get("previousClose"),
            "open": info.get("open") or info.get("regularMarketOpen"),
            "dayHigh": info.get("dayHigh") or info.get("regularMarketDayHigh"),
            "dayLow": info.get("dayLow") or info.get("regularMarketDayLow"),
            "volume": info.get("volume") or info.get("regularMarketVolume"),
            "marketCap": info.get("marketCap"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "currency": info.get("currency", "USD"),
        }
        # Calculate change
        if result["currentPrice"] and result["previousClose"]:
            change = result["currentPrice"] - result["previousClose"]
            change_pct = (change / result["previousClose"]) * 100
            result["change"] = round(change, 2)
            result["changePercent"] = round(change_pct, 2)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取 {symbol} 行情失败: {str(e)}"})


def get_stock_history(symbol: str, period: str = "1mo") -> str:
    """Get stock price history"""
    try:
        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period)
        if hist.empty:
            return json.dumps({"error": f"{symbol} 无历史数据"})

        # Return summary + last 5 data points
        records = []
        for date, row in hist.tail(10).iterrows():
            records.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })

        result = {
            "symbol": symbol.upper(),
            "period": period,
            "totalDays": len(hist),
            "startDate": hist.index[0].strftime("%Y-%m-%d"),
            "endDate": hist.index[-1].strftime("%Y-%m-%d"),
            "highestClose": round(hist["Close"].max(), 2),
            "lowestClose": round(hist["Close"].min(), 2),
            "recentData": records
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取 {symbol} 历史数据失败: {str(e)}"})


def get_analyst_ratings(symbol: str) -> str:
    """Get analyst ratings and recommendations"""
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        result = {
            "symbol": symbol.upper(),
            "name": info.get("shortName", "N/A"),
            "recommendationKey": info.get("recommendationKey", "N/A"),
            "recommendationMean": info.get("recommendationMean"),
            "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
            "targetHighPrice": info.get("targetHighPrice"),
            "targetLowPrice": info.get("targetLowPrice"),
            "targetMeanPrice": info.get("targetMeanPrice"),
            "targetMedianPrice": info.get("targetMedianPrice"),
            "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
        }

        # Calculate upside potential
        if result["targetMeanPrice"] and result["currentPrice"]:
            upside = ((result["targetMeanPrice"] - result["currentPrice"]) / result["currentPrice"]) * 100
            result["upsidePotential"] = round(upside, 2)

        # Try to get recent recommendations
        try:
            recs = ticker.recommendations
            if recs is not None and not recs.empty:
                recent = recs.tail(5)
                rec_list = []
                for date, row in recent.iterrows():
                    rec_list.append({
                        "date": date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date),
                        "firm": row.get("Firm", "N/A"),
                        "toGrade": row.get("To Grade", "N/A"),
                        "fromGrade": row.get("From Grade", "N/A"),
                        "action": row.get("Action", "N/A")
                    })
                result["recentRatings"] = rec_list
        except Exception:
            pass

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取 {symbol} 分析师评级失败: {str(e)}"})


def get_financials(symbol: str, statement: str = "income") -> str:
    """Get company financial statements"""
    try:
        ticker = yf.Ticker(symbol.upper())

        if statement == "balance":
            df = ticker.balance_sheet
            stmt_name = "资产负债表"
        elif statement == "cashflow":
            df = ticker.cashflow
            stmt_name = "现金流量表"
        else:
            df = ticker.income_stmt
            stmt_name = "利润表"

        if df is None or df.empty:
            return json.dumps({"error": f"{symbol} 无{stmt_name}数据"})

        # Get the most recent period (first column)
        latest = df.iloc[:, 0]
        result = {
            "symbol": symbol.upper(),
            "statement": stmt_name,
            "period": df.columns[0].strftime("%Y-%m-%d") if hasattr(df.columns[0], 'strftime') else str(df.columns[0]),
            "data": {}
        }

        # Include key metrics (non-null only)
        for idx, val in latest.items():
            if val is not None and str(val) != "nan":
                try:
                    result["data"][str(idx)] = float(val)
                except (ValueError, TypeError):
                    result["data"][str(idx)] = str(val)

        # Limit to top 15 items to avoid overly long responses
        if len(result["data"]) > 15:
            important_keys = list(result["data"].keys())[:15]
            result["data"] = {k: result["data"][k] for k in important_keys}

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取 {symbol} 财务数据失败: {str(e)}"})


def get_company_info(symbol: str) -> str:
    """Get company basic information"""
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
        result = {
            "symbol": symbol.upper(),
            "name": info.get("shortName", "N/A"),
            "longName": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country": info.get("country", "N/A"),
            "website": info.get("website", "N/A"),
            "fullTimeEmployees": info.get("fullTimeEmployees"),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "dividendYield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "summary": info.get("longBusinessSummary", "N/A")[:300]  # Truncate
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取 {symbol} 公司信息失败: {str(e)}"})


# Dispatcher: map function name to handler
TOOL_HANDLERS = {
    "get_stock_quote": lambda args: get_stock_quote(args["symbol"]),
    "get_stock_history": lambda args: get_stock_history(args["symbol"], args.get("period", "1mo")),
    "get_analyst_ratings": lambda args: get_analyst_ratings(args["symbol"]),
    "get_financials": lambda args: get_financials(args["symbol"], args.get("statement", "income")),
    "get_company_info": lambda args: get_company_info(args["symbol"]),
}


def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool by name with given arguments"""
    handler = TOOL_HANDLERS.get(name)
    if handler:
        return handler(arguments)
    return json.dumps({"error": f"未知工具: {name}"})
