import os
import json
import logging
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from api.services.generator import generate_full_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def _resolve_storage_dir():
    """Prefer persisted storage on Azure; fall back to project storage when local."""
    env_dir = os.getenv("STORAGE_DIR")
    if env_dir:
        return env_dir
    # Use /home/data/ for Azure persistence (survives deployments)
    # /home/site/wwwroot/ gets overwritten on each deployment
    azure_persist_dir = os.path.join("/home", "data", "storage")
    if os.path.isdir(os.path.join("/home", "site")):
        return azure_persist_dir
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")

STORAGE_DIR = _resolve_storage_dir()

def save_report(report_data):
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)

    date_str = report_data["date"]

    # Save Sentiment Data separately
    if "sentiment" in report_data and report_data["sentiment"]:
        sentiment_path = os.path.join(STORAGE_DIR, f"{date_str}_sentiment.json")
        try:
            with open(sentiment_path, "w", encoding="utf-8") as f:
                json.dump(report_data["sentiment"], f, ensure_ascii=False, indent=2)
            logger.info(f"Saved sentiment data to {sentiment_path}")
        except Exception as e:
            logger.error(f"Failed to save sentiment data: {e}")

    # Determine filename based on report type

    report_type = report_data["type"]
    filename = f"{date_str}_{report_type}.json"

    file_path = os.path.join(STORAGE_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Report saved to {file_path}")

async def job_generate_daily():
    logger.info("Starting Daily Report Generation Job...")
    try:
        # Run in executor to avoid blocking main thread as generator is sync
        # But wait, generator calls network which blocks.
        # Ideally generator should be async or run in thread pool.
        # Akshare and OpenAI sync client are blocking.
        import asyncio
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, generate_full_report, "daily")
        save_report(report)
        logger.info("Daily Report Generation Completed.")
    except Exception as e:
        logger.error(f"Daily Report Generation Failed: {e}")

async def job_generate_weekly():
    logger.info("Starting Weekly Report Generation Job...")
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        report = await loop.run_in_executor(None, generate_full_report, "weekly")
        save_report(report)
        logger.info("Weekly Report Generation Completed.")
    except Exception as e:
        logger.error(f"Weekly Report Generation Failed: {e}")


async def job_warmup_cache():
    """
    Pre-warm cache before market opens.
    This ensures the first user gets fast response times.
    Runs at 9:25 AM on trading days (Mon-Fri).
    """
    logger.info("Starting cache warmup job...")
    try:
        import asyncio
        from api.services.market import get_market_radar_data
        from api.services.index_overview import get_index_overview
        from api.services.fund_flow import get_fund_flow_rank
        from api.services.concepts import get_hot_concepts

        loop = asyncio.get_running_loop()

        # Run all data fetching functions concurrently
        tasks = [
            loop.run_in_executor(None, get_market_radar_data),
            loop.run_in_executor(None, get_index_overview),
            loop.run_in_executor(None, get_fund_flow_rank),
            loop.run_in_executor(None, get_hot_concepts),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log results
        names = ["market_radar", "index_overview", "fund_flow", "hot_concepts"]
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                logger.warning(f"Cache warmup failed for {name}: {result}")
            else:
                logger.info(f"Cache warmup success: {name}")

        logger.info("Cache warmup completed.")
    except Exception as e:
        logger.error(f"Cache warmup job failed: {e}")


async def job_generate_us_tech():
    """
    Generate US tech stocks data report.
    Runs at 5:30 AM Beijing time (after US market closes at 4:00 PM ET).
    """
    logger.info("Starting US Tech Stocks Data Generation Job...")
    try:
        import asyncio
        from api.services.us_stocks import get_us_tech_overview, save_us_tech_data

        loop = asyncio.get_running_loop()

        # 获取美股数据（不使用缓存，强制刷新）
        data = await loop.run_in_executor(None, lambda: get_us_tech_overview(use_cache=False, max_workers=5))

        # 保存数据
        save_us_tech_data(data)

        logger.info(f"US Tech Stocks Data Generation Completed. Success: {data['summary']['success']}/{data['summary']['total']}")
    except Exception as e:
        logger.error(f"US Tech Stocks Data Generation Failed: {e}")


def start_scheduler():
    # 每天早上 08:00 生成日报 (周二到周六，对应周一到周五的交易日)
    # Cron: minute=0, hour=8, day_of_week='tue-sat'
    scheduler.add_job(
        job_generate_daily,
        CronTrigger(hour=8, minute=0, day_of_week='tue-sat'),
        id="daily_briefing",
        replace_existing=True
    )

    # 每周六早上 09:00 生成周报
    scheduler.add_job(
        job_generate_weekly,
        CronTrigger(hour=9, minute=0, day_of_week='sat'),
        id="weekly_briefing",
        replace_existing=True
    )

    # 每天 09:25 预热缓存（开盘前5分钟，周一到周五）
    # This ensures data is cached before market opens at 9:30
    scheduler.add_job(
        job_warmup_cache,
        CronTrigger(hour=9, minute=25, day_of_week='mon-fri'),
        id="cache_warmup",
        replace_existing=True
    )

    # 每天 13:00 再次预热（午盘开盘前）
    scheduler.add_job(
        job_warmup_cache,
        CronTrigger(hour=13, minute=0, day_of_week='mon-fri'),
        id="cache_warmup_afternoon",
        replace_existing=True
    )

    # 美股数据生成：周二到周六 05:30（美东时间前一日收盘后，对应周一到周五的交易日）
    # 美股交易时间：美东 9:30-16:00，对应北京时间 22:30-次日5:00（冬令时）或 21:30-次日4:00（夏令时）
    # 我们选择北京时间 5:30 生成，确保美股收盘后数据可用
    scheduler.add_job(
        job_generate_us_tech,
        CronTrigger(hour=5, minute=30, day_of_week='tue-sat'),
        id="us_tech_daily",
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started with daily/weekly reports, cache warmup, and US tech stocks jobs.")

def shutdown_scheduler():
    scheduler.shutdown()
