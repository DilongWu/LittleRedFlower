#!/bin/bash
# Azure App Service start script (keep it simple to avoid CRLF issues and memory pressure)

# Start the application with a single Uvicorn worker
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
