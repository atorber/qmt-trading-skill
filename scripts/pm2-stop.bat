@echo off
chcp 65001 >nul 2>&1
REM QMT Bridge — 停止并移除 PM2 进程

cd /d "%~dp0.."

where pm2 >nul 2>&1
if errorlevel 1 (
    echo [PM2] 未找到 pm2
    exit /b 1
)

pm2 stop qmt-server qmt-scheduler 2>nul
pm2 delete qmt-server qmt-scheduler 2>nul
pm2 status
