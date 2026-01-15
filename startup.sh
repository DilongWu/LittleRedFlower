#!/bin/bash
# Install dependencies
pip install -r src/requirements.txt

# Start the application
# We assume the startup command for Azure App Service looks for this file
# Uvicorn will run the API, which serves the frontend static files
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
