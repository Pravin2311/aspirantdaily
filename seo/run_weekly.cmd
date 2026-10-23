@echo off
rem Weekly read-only SEO run for AspirantDaily. Uses the Teachings.ai venv and the shared
rem OAuth token in %APPDATA%\teachings-seo. Output is appended to seo\logs\weekly.log.
cd /d "%~dp0.."
if not exist seo\logs mkdir seo\logs
set PYTHONIOENCODING=utf-8
echo ===== %date% %time% >> seo\logs\weekly.log
"%USERPROFILE%\Documents\GitHub\Teachings.ai\seo\.venv\Scripts\python.exe" seo\weekly.py >> seo\logs\weekly.log 2>&1
echo exit code %errorlevel% >> seo\logs\weekly.log
