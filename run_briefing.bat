@echo off
cd /d "%~dp0"
echo 正在读取新闻素材并生成晨报...

REM 尝试使用虚拟环境 Python
if exist ".venv\Scripts\python.exe" (
    echo 使用虚拟环境 Python...
    .venv\Scripts\python.exe src/generate_briefing.py
) else (
    echo 未找到虚拟环境，尝试使用系统 Python...
    python src/generate_briefing.py
)

pause
