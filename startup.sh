#!/bin/bash
# Azure App Service start script

# Azure Oryx build automatically installs requirements.txt
# if you need extra install steps, un-comment below:
# pip install -r requirements.txt

# Start the application
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
