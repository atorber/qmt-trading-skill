@echo off
chcp 65001 >nul 2>&1
REM 每日复盘定时调度（前台常驻，Ctrl+C 停止）
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
python scripts\daily_eval_scheduler.py %*
