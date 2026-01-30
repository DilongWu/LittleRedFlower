import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel

from api.scheduler import start_scheduler, shutdown_scheduler, STORAGE_DIR, job_generate_daily, job_generate_weekly, job_warmup_cache, job_refresh_quotes_cache
from api.services.market import get_market_radar_data
from api.services.diagnosis import get_stock_diagnosis
from api.services.index_overview import get_index_overview
from api.services.fund_flow import get_fund_flow_rank
from api.services.concepts import get_hot_concepts
from api.services.data_source import get_data_source, set_data_source, test_data_source, get_tushare_token, set_tushare_token, VALID_DATA_SOURCES
from api.services.http_client import close_session
from api.services.chat import chat_service
from api.services.us_stocks import get_us_tech_overview, save_us_tech_data, load_us_tech_data

class LoginRequest(BaseModel):
    username: str
    password: str

class StockDiagnosisRequest(BaseModel):
    symbol: str
    days: int = 60

class DataSourceRequest(BaseModel):
    source: str  # "eastmoney", "sina", or "tushare"


class TushareTokenRequest(BaseModel):
    token: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
    close_session()  # Clean up HTTP connections

app = FastAPI(lifespan=lifespan, title="Little Red Flower API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/login")
async def login(request: LoginRequest):
    # Retrieve credentials from environment variables or use default
    expected_username = os.getenv("ADMIN_USERNAME", "admin")
    expected_password = os.getenv("ADMIN_PASSWORD", "littleredfloweradmin")
    
    if request.username == expected_username and request.password == expected_password:
        return {"status": "success", "token": "valid_token_from_server"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/reports")
async def list_reports():
    """List all available reports."""
    if not os.path.exists(STORAGE_DIR):
        return []
    
    reports = []
    for filename in os.listdir(STORAGE_DIR):
        if filename.endswith(".json"):
            try:
                # Optimized: ideally we don't read full content, just metadata
                # naming convention: {date}_{type}.json
                parts = filename.replace(".json", "").split("_")
                if len(parts) == 2:
                    date_str, report_type = parts
                    reports.append({
                        "date": date_str,
                        "type": report_type,
                        "filename": filename
                    })
            except Exception:
                continue
    
    # Sort by date desc
    reports.sort(key=lambda x: x["date"], reverse=True)
    return reports

@app.get("/api/reports/{date}")
async def get_report(date: str, type: str = "daily"):
    """Get a specific report."""
    filename = f"{date}_{type}.json"
    file_path = os.path.join(STORAGE_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/{date}/data")
async def get_report_data(date: str, type: str = "daily"):
    """
    Get only the parsed structured data from a report (optimized endpoint).

    This endpoint is much faster than /api/reports/{date} because it:
    - Returns only parsed data (no markdown/html content)
    - Performs server-side parsing (faster than client-side)
    - Reduces response size by ~70%
    """
    from api.services.data_parser import parse_raw_data

    filename = f"{date}_{type}.json"
    file_path = os.path.join(STORAGE_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Get sentiment data if available
        sentiment = data.get('sentiment')
        if not sentiment:
            # Try to load sentiment from separate file
            sentiment_file = os.path.join(STORAGE_DIR, f"{date}_sentiment.json")
            if os.path.exists(sentiment_file):
                with open(sentiment_file, "r", encoding="utf-8") as sf:
                    sentiment = json.load(sf)

        # Parse raw_data to structured format
        raw_data = data.get('raw_data', '')
        parsed_data = parse_raw_data(raw_data, sentiment)

        # Return lightweight response
        return {
            'date': data.get('date'),
            'type': data.get('type'),
            'created_at': data.get('created_at'),
            'data': parsed_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse report data: {str(e)}")

@app.get("/api/sentiment")
async def get_sentiment(date: str = Query(None, description="Date in YYYY-MM-DD format")):
    """Get market sentiment data. Defaults to today's or latest available."""
    target_date = date
    
    if not target_date:
        # Default to today
        import datetime
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
    filename = f"{target_date}_sentiment.json"
    file_path = os.path.join(STORAGE_DIR, filename)
    
    # If today's not found, try finding the latest one in the last 7 days
    if not os.path.exists(file_path) and not date:
        import datetime
        for i in range(1, 8):
            prev_date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            prev_path = os.path.join(STORAGE_DIR, f"{prev_date}_sentiment.json")
            if os.path.exists(prev_path):
                file_path = prev_path
                break
    
    if not os.path.exists(file_path):
        # Return a neutral placeholder if nothing found
        return {
            "score": 50,
            "label": "中性",
            "summary": "暂无情绪数据，请等待系统生成每日情绪分析报告。",
            "timestamp": None,
            "is_placeholder": True,
            "history": []
        }
    
    try:
        current_data = {}
        with open(file_path, "r", encoding="utf-8") as f:
            current_data = json.load(f)
            
        # Enrich with history (last 7 days including today)
        history = []
        import datetime
        # We need the base date of the current report to look back from
        try:
            base_date = datetime.datetime.strptime(current_data.get("date", target_date), "%Y-%m-%d")
        except:
            base_date = datetime.datetime.now()
            
        for i in range(6, -1, -1): # 6 days ago to 0 days ago
            loop_date = (base_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            loop_path = os.path.join(STORAGE_DIR, f"{loop_date}_sentiment.json")
            if os.path.exists(loop_path):
                try:
                    with open(loop_path, "r", encoding="utf-8") as hf:
                        h_data = json.load(hf)
                        history.append({
                            "date": loop_date,
                            "score": h_data.get("score"),
                            "label": h_data.get("label")
                        })
                except:
                    pass
        
        current_data["history"] = history
        return current_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trigger/daily")
async def trigger_daily(background_tasks: BackgroundTasks):
    """Manual trigger for daily report (Background Task)"""
    background_tasks.add_task(job_generate_daily)
    return {"status": "triggered", "message": "Daily report generation started in background"}

@app.post("/api/trigger/weekly")
async def trigger_weekly(background_tasks: BackgroundTasks):
    """Manual trigger for weekly report (Background Task)"""
    background_tasks.add_task(job_generate_weekly)
    return {"status": "triggered", "message": "Weekly report generation started in background"}

@app.post("/api/trigger/warmup")
async def trigger_warmup(background_tasks: BackgroundTasks):
    """Manual trigger for cache warmup (Background Task)"""
    background_tasks.add_task(job_warmup_cache)
    return {"status": "triggered", "message": "Cache warmup started in background"}

@app.post("/api/trigger/quotes-refresh")
async def trigger_quotes_refresh(background_tasks: BackgroundTasks):
    """Manual trigger for quotes cache refresh (Background Task)"""
    background_tasks.add_task(job_refresh_quotes_cache)
    return {"status": "triggered", "message": "Quotes cache refresh started in background"}

@app.get("/api/market/radar")
async def get_market_radar():
    """Get real-time market radar data (heatmaps, ladders)"""
    return get_market_radar_data()

@app.post("/api/stock/diagnosis")
async def stock_diagnosis(request: StockDiagnosisRequest):
    """Get basic stock diagnosis based on recent price/volume and fundamentals."""
    result = get_stock_diagnosis(request.symbol, request.days)
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/api/index/overview")
async def index_overview():
    """Get index K-line overview for major indexes."""
    return get_index_overview()

@app.get("/api/fund/flow")
async def fund_flow_rank():
    """Get fund flow ranking for individual stocks."""
    result = get_fund_flow_rank()
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/api/concept/hot")
@app.get("/api/concepts/hot")  # Add plural form for consistency
async def concept_hot():
    """Get hot concept list ranked by change percent."""
    result = get_hot_concepts()
    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/api/us-tech/latest")
async def get_us_tech():
    """Get latest US tech stocks data (with cache support)."""
    try:
        # 首先尝试从缓存/文件加载
        cached_data = load_us_tech_data()
        if cached_data:
            return cached_data

        # 如果没有缓存，实时获取（使用内存缓存）
        data = get_us_tech_overview(use_cache=True, max_workers=5)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取美股数据失败: {str(e)}")

@app.post("/api/trigger/us-tech")
async def trigger_us_tech(background_tasks: BackgroundTasks):
    """Manual trigger for US tech stocks data generation (Background Task)."""
    def generate_us_tech():
        data = get_us_tech_overview(use_cache=False, max_workers=5)
        save_us_tech_data(data)

    background_tasks.add_task(generate_us_tech)
    return {"status": "triggered", "message": "美股科技股数据生成已启动（后台任务）"}

@app.delete("/api/us-tech/cache")
async def clear_us_tech_cache():
    """Clear US tech stocks cache."""
    from api.services.us_stocks import clear_cache
    clear_cache()
    return {"status": "success", "message": "美股数据缓存已清空"}

@app.get("/api/us-tech/cache/stats")
async def get_us_tech_cache_stats():
    """Get US tech stocks cache statistics."""
    from api.services.us_stocks import get_cache_stats
    return get_cache_stats()

@app.get("/api/datasource")
async def get_datasource():
    """Get current data source configuration."""
    source = get_data_source()
    # Always check if tushare token is configured, regardless of current source
    token_configured = bool(get_tushare_token())
    return {
        "source": source,
        "available_sources": VALID_DATA_SOURCES,
        "tushare_token_configured": token_configured
    }


@app.post("/api/datasource")
async def set_datasource(request: DataSourceRequest):
    """Set data source (eastmoney, sina, or tushare)."""
    if request.source not in VALID_DATA_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data source. Use one of: {', '.join(VALID_DATA_SOURCES)}"
        )

    # If switching to tushare, check token is configured
    if request.source == "tushare" and not get_tushare_token():
        raise HTTPException(
            status_code=400,
            detail="Tushare token not configured. Set token first via POST /api/datasource/tushare-token"
        )

    success = set_data_source(request.source)
    if success:
        return {"status": "success", "source": request.source}
    else:
        raise HTTPException(status_code=500, detail="Failed to save data source configuration.")


@app.get("/api/datasource/test")
async def test_datasource(source: str = Query("eastmoney", description="Data source to test")):
    """Test if a data source is available."""
    result = test_data_source(source)
    return result


@app.post("/api/datasource/tushare-token")
async def set_tushare_token_api(request: TushareTokenRequest):
    """Set Tushare Pro API token."""
    if not request.token or len(request.token) < 10:
        raise HTTPException(status_code=400, detail="Invalid token format")

    success = set_tushare_token(request.token)
    if success:
        # Reset the tushare client to use new token
        from api.services.tushare_client import reset_pro_api
        reset_pro_api()
        return {"status": "success", "message": "Tushare token saved"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save Tushare token")


@app.get("/api/datasource/tushare-token")
async def get_tushare_token_status():
    """Check if Tushare token is configured (does not return the actual token)."""
    token = get_tushare_token()
    return {
        "configured": bool(token),
        "token_preview": f"{token[:8]}...{token[-4:]}" if token and len(token) > 12 else None
    }


# Thread pool for running sync functions concurrently
_executor = ThreadPoolExecutor(max_workers=6)


@app.get("/api/dashboard/all")
async def get_dashboard_all():
    """
    Get all dashboard data in a single request (concurrent fetching).
    This reduces latency by fetching radar, index, fund flow, and concepts in parallel.
    """
    loop = asyncio.get_event_loop()

    # Run all data fetching functions concurrently
    radar_task = loop.run_in_executor(_executor, get_market_radar_data)
    index_task = loop.run_in_executor(_executor, get_index_overview)
    fund_task = loop.run_in_executor(_executor, get_fund_flow_rank)
    concept_task = loop.run_in_executor(_executor, get_hot_concepts)

    # Wait for all tasks to complete
    results = await asyncio.gather(
        radar_task, index_task, fund_task, concept_task,
        return_exceptions=True
    )

    # Process results, handle any exceptions
    def safe_result(r, default):
        if isinstance(r, Exception):
            return default
        return r

    return {
        "radar": safe_result(results[0], {"sectors": [], "ladder": {}}),
        "index": safe_result(results[1], []),
        "fund_flow": safe_result(results[2], {"data": []}),
        "concepts": safe_result(results[3], {"data": []}),
    }

# AI Chat Assistant Endpoint
@app.post("/api/chat")
async def chat_endpoint(request: dict):
    """Chat with market-aware AI assistant"""
    try:
        user_message = request.get("message", "")
        history = request.get("history", [])

        if not user_message:
            raise HTTPException(status_code=400, detail="消息不能为空")

        # Fetch market context
        market_context = {}

        # Try to get sentiment data
        try:
            import datetime
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            sentiment_file = os.path.join(STORAGE_DIR, f"{today}_sentiment.json")

            if os.path.exists(sentiment_file):
                with open(sentiment_file, "r", encoding="utf-8") as f:
                    sentiment_data = json.load(f)
                    market_context["sentiment"] = sentiment_data
        except Exception:
            pass

        # Try to get index data
        try:
            indexes = get_index_overview()
            if indexes:
                market_context["indexes"] = indexes[:3]  # Top 3 indexes
        except Exception:
            pass

        # Convert history to proper format
        conversation = []
        if history:
            for msg in history[-10:]:  # Last 10 messages
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    # Filter out error messages from history
                    if msg.get("role") != "error":
                        conversation.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })

        # Get AI response
        response_text = chat_service.get_response(
            user_message=user_message,
            conversation_history=conversation,
            market_context=market_context
        )

        return {
            "response": response_text,
            "role": "assistant"
        }

    except Exception as e:
        print(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail="抱歉，发生了错误，请稍后重试。")

# Serve Frontend Static Files (After API routes to avoid conflict)
# In production, we assume 'web/dist' exists
web_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")

if os.path.exists(web_dist_path):
    app.mount("/", StaticFiles(directory=web_dist_path, html=True), name="static")
else:
    print(f"Warning: frontend dist folder not found at {web_dist_path}. API only mode.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
