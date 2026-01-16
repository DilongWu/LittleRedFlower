#!/bin/bash
# Azure App Service start script

# Azure Oryx build automatically installs requirements.txt
# if you need extra install steps, un-comment below:
# pip install -r requirements.txt

# Start the application
# Use Gunicorn with Uvicorn workers for production
python -m gunicorn api.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
