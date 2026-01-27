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
    azure_persist_dir = os.path.join("/home", "site", "wwwroot", "storage")
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
    
    scheduler.start()
    logger.info("Scheduler started.")

def shutdown_scheduler():
    scheduler.shutdown()
