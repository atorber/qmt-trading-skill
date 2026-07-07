/**
 * PM2 守护 QMT Bridge（Windows 推荐）
 *
 * 前置：
 *   npm install -g pm2
 *   pip install -e ".[server,ws,notify]"
 *   copy .env.example .env   # 端口、TRADING、账户等
 *
 * 指定 venv Python（推荐）：
 *   set PM2_PYTHON=C:\path\to\venv\Scripts\python.exe
 *
 * 常用：
 *   pm2 start ecosystem.config.cjs --only qmt-server
 *   pm2 logs qmt-server
 *   pm2 restart qmt-server
 *   pm2 stop qmt-server
 *   pm2 delete qmt-server
 *
 * 调度器（独立进程，按需）：
 *   pm2 start ecosystem.config.cjs --only qmt-scheduler
 *
 * 开机自启（管理员终端）：
 *   pm2 startup
 *   pm2 save
 */
const path = require("path");

const ROOT = __dirname;
const PYTHON = process.env.PM2_PYTHON || "python";
const LOG_DIR = path.join(ROOT, "logs", "pm2");

const serverApp = {
  name: "qmt-server",
  cwd: ROOT,
  script: path.join(ROOT, "scripts", "pm2_qmt_server.py"),
  interpreter: PYTHON,
  autorestart: true,
  restart_delay: 5000,
  max_restarts: 100,
  min_uptime: "10s",
  kill_timeout: 8000,
  watch: false,
  merge_logs: true,
  time: true,
  log_date_format: "YYYY-MM-DD HH:mm:ss Z",
  out_file: path.join(LOG_DIR, "qmt-server-out.log"),
  error_file: path.join(LOG_DIR, "qmt-server-error.log"),
};

const schedulerApp = {
  name: "qmt-scheduler",
  cwd: ROOT,
  script: path.join(ROOT, "scripts", "pm2_qmt_scheduler.py"),
  interpreter: PYTHON,
  autorestart: true,
  restart_delay: 10000,
  max_restarts: 50,
  min_uptime: "30s",
  kill_timeout: 8000,
  watch: false,
  merge_logs: true,
  time: true,
  log_date_format: "YYYY-MM-DD HH:mm:ss Z",
  out_file: path.join(LOG_DIR, "qmt-scheduler-out.log"),
  error_file: path.join(LOG_DIR, "qmt-scheduler-error.log"),
};

module.exports = {
  apps: [serverApp, schedulerApp],
};
