@echo off
chcp 65001 >nul 2>&1
REM QMT Bridge — PM2 守护启动（崩溃自动拉起）
REM 配置见仓库根 .env；Python 解释器可用环境变量 PM2_PYTHON 指定 venv。

cd /d "%~dp0.."

where pm2 >nul 2>&1
if errorlevel 1 (
    echo [PM2] 未找到 pm2，请先执行: npm install -g pm2
    exit /b 1
)

if "%1"=="" (
    pm2 start ecosystem.config.cjs --only qmt-server
) else (
    pm2 start ecosystem.config.cjs %*
)

echo.
echo [PM2] 状态: pm2 status
echo [PM2] 日志: pm2 logs qmt-server
echo [PM2] 停止: scripts\pm2-stop.bat
