import os
import json
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pydantic import BaseModel

from api.scheduler import start_scheduler, shutdown_scheduler, STORAGE_DIR, job_generate_daily, job_generate_weekly

class LoginRequest(BaseModel):
    username: str
    password: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

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
