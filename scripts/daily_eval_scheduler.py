#!/usr/bin/env python3
"""每日复盘定时调度（前台常驻，不依赖 Windows 任务计划程序）。

每个交易日到点自动：
  1. 生成复盘 Markdown（combined_trade_report 或 daily_trade_report）
  2. 新建飞书 Wiki 节点并上传正文（lark-cli）

用法:
    python scripts/daily_eval_scheduler.py
    python scripts/daily_eval_scheduler.py --run-now
    python scripts/daily_eval_scheduler.py --time 15:10 --interval 30
    python scripts/daily_eval_scheduler.py --run-now --skip-feishu

环境变量（可选，见 .env.example）:
    DAILY_EVAL_SCHEDULE_TIME=15:10
    DAILY_EVAL_SCHEDULE_COMBINED=true
    FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN=...
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SHARED = _REPO / "skills" / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from common import add_client_args, call_api, load_env_files, make_client  # noqa: E402
from feishu_doc import (  # noqa: E402
    DOC_TYPES,
    format_title,
    resolve_wiki_parent_token,
    title_from_markdown,
)

_TITLE_PREFIX = "QMT Trading Skill 当日复盘"
_STATE_FILE = _REPO / "reports" / "daily_eval_scheduler_state.json"
_WIKI_REGISTRY = _REPO / "reports" / "feishu_wiki_daily_eval.json"
_LOG_DIR = _REPO / "logs"

_COMBINED_SCRIPT = (
    _REPO / "skills" / "qmt-bridge-execution-review" / "scripts" / "combined_trade_report.py"
)
_SINGLE_SCRIPT = (
    _REPO / "skills" / "qmt-bridge-execution-review" / "scripts" / "daily_trade_report.py"
)
_COMBINED_MD = _REPO / "reports" / "feishu_combined_daily_eval.md"
_SINGLE_MD = _REPO / "reports" / "feishu_daily_eval.md"


def _setup_logging(verbose: bool) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(_LOG_DIR / "daily_eval_scheduler.log", encoding="utf-8"),
        ],
    )


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"时间格式应为 HH:MM，收到: {value!r}")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"非法时间: {value}")
    return hour, minute


def _load_state() -> dict:
    if not _STATE_FILE.is_file():
        return {}
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _save_state(**fields: object) -> None:
    data = _load_state()
    data.update(fields)
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _already_ran(trade_date: str) -> bool:
    state = _load_state()
    return state.get("last_trade_date") == trade_date and state.get("last_status") == "ok"


def _use_combined(flag: bool | None) -> bool:
    if flag is not None:
        return flag
    env = os.environ.get("DAILY_EVAL_SCHEDULE_COMBINED", "").strip().lower()
    if env in ("0", "false", "no"):
        return False
    if env in ("1", "true", "yes"):
        return True
    stock = os.environ.get("QMT_BRIDGE_STOCK_ACCOUNT_ID", "").strip()
    credit = os.environ.get("QMT_BRIDGE_CREDIT_ACCOUNT_ID", "").strip()
    return bool(stock and credit)


def _bridge_health_ok(host: str, port: int) -> bool:
    url = f"http://{host}:{port}/api/meta/health"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("status") == "ok"
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return False


def _is_trading_day(args) -> bool:
    client, _ = make_client(args, require_api_key=False)
    today = date.today().strftime("%Y%m%d")
    return bool(call_api(client.is_trading_date, "SH", today))


def _patch_md_title(md_path: Path, title: str) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return
    if lines[0].startswith("# "):
        lines[0] = f"# {title}"
    else:
        lines.insert(0, f"# {title}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_report(args, *, combined: bool) -> Path:
    script = _COMBINED_SCRIPT if combined else _SINGLE_SCRIPT
    md_path = _COMBINED_MD if combined else _SINGLE_MD
    cmd = [
        sys.executable,
        str(script),
        "--host",
        args.host or "127.0.0.1",
        "--port",
        str(args.port or int(os.environ.get("QMT_BRIDGE_PORT", "8080"))),
        "--feishu-md",
        str(md_path),
    ]
    api_key = args.api_key or os.environ.get("QMT_BRIDGE_API_KEY", "")
    if api_key:
        cmd.extend(["--api-key", api_key])
    logging.info("生成复盘: %s", " ".join(cmd))
    subprocess.run(cmd, cwd=_REPO, check=True)

    trade_date = date.today().isoformat()
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = format_title(_TITLE_PREFIX, trade_date=trade_date, synced_at=synced_at)
    _patch_md_title(md_path, title)
    return md_path


def _run_lark(args_list: list[str]) -> dict:
    lark_cli = _resolve_lark_cli()
    logging.debug("%s %s", lark_cli, " ".join(args_list))
    proc = subprocess.run(
        [lark_cli, *args_list],
        cwd=_REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"lark-cli 失败 (exit {proc.returncode}): {proc.stderr or proc.stdout}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"lark-cli 输出非 JSON: {proc.stdout[:500]}") from exc


def _resolve_lark_cli() -> str:
    """解析 lark-cli 可执行路径（兼容 Windows 的 .cmd/.exe）。"""
    env_bin = os.environ.get("LARK_CLI_BIN", "").strip()
    if env_bin:
        return env_bin

    candidates = [
        "lark-cli",
        "lark-cli.cmd",
        "lark-cli.exe",
    ]
    for cand in candidates:
        found = shutil.which(cand)
        if found:
            return found

    common = [
        Path(r"C:\Program Files (x86)\nodejs\lark-cli.cmd"),
        Path(r"C:\Program Files (x86)\nodejs\lark-cli"),
        Path.home() / "AppData" / "Roaming" / "npm" / "lark-cli.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "lark-cli",
    ]
    for p in common:
        if p.is_file():
            return str(p)

    raise RuntimeError(
        "未找到 lark-cli。请先安装并登录，或在环境变量 LARK_CLI_BIN 指定可执行文件路径。"
    )


def _sync_feishu(md_path: Path, *, lark_as: str, parent_token: str, combined: bool) -> dict:
    title = title_from_markdown(md_path)
    if not title:
        raise RuntimeError(f"无法从 {md_path} 读取标题")

    create = _run_lark(
        [
            "wiki",
            "+node-create",
            "--as",
            lark_as,
            "--parent-node-token",
            parent_token,
            "--title",
            title,
        ]
    )
    data = create.get("data") or {}
    obj_token = data.get("obj_token")
    node_token = data.get("node_token")
    if not obj_token:
        raise RuntimeError(f"wiki +node-create 未返回 obj_token: {create}")

    rel_md = md_path.relative_to(_REPO).as_posix()
    _run_lark(
        [
            "docs",
            "+update",
            "--api-version",
            "v2",
            "--doc",
            obj_token,
            "--as",
            lark_as,
            "--command",
            "overwrite",
            "--doc-format",
            "markdown",
            "--content",
            f"@{rel_md}",
        ]
    )

    wiki_url = data.get("url") or (
        f"https://oou2hscgt2.feishu.cn/wiki/{node_token}" if node_token else ""
    )
    docx_url = f"https://oou2hscgt2.feishu.cn/docx/{obj_token}"
    registry = {
        "trade_date": date.today().isoformat(),
        "scope": "combined" if combined else "single",
        "title": title,
        "obj_token": obj_token,
        "node_token": node_token,
        "parent_node_token": parent_token,
        "wiki_url": wiki_url,
        "docx_url": docx_url,
        "synced_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_md": rel_md,
        "scheduler": "daily_eval_scheduler.py",
    }
    _WIKI_REGISTRY.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logging.info("飞书已同步: %s", wiki_url or docx_url)
    return registry


def run_once(args) -> None:
    combined = _use_combined(args.combined)
    trade_date = date.today().isoformat()

    if not args.force and _already_ran(trade_date):
        logging.info("今日 %s 已成功执行，跳过（可用 --force 重跑）", trade_date)
        return

    if not args.force and not args.skip_trading_day_check and not args.dry_run:
        if not _is_trading_day(args):
            logging.info("今日 %s 非交易日，跳过", trade_date)
            return

    if not args.dry_run:
        host = args.host or os.environ.get("QMT_BRIDGE_HOST", "127.0.0.1")
        if host in ("0.0.0.0", "::"):
            host = "127.0.0.1"
        port = args.port or int(os.environ.get("QMT_BRIDGE_PORT", "8080"))
        if not _bridge_health_ok(host, port):
            raise RuntimeError(
                f"Bridge 不可用: http://{host}:{port}/api/meta/health "
                "（请先启动 qmt-server / PM2）"
            )
    else:
        logging.info(
            "[dry-run] combined=%s skip_feishu=%s trade_date=%s",
            combined,
            args.skip_feishu,
            trade_date,
        )
        return

    md_path = _run_report(args, combined=combined)

    if not args.skip_feishu:
        parent = resolve_wiki_parent_token()
        if not parent:
            raise RuntimeError(
                "未配置 FEISHU_DAILY_EVAL_WIKI_PARENT_TOKEN，无法同步飞书"
            )
        _sync_feishu(
            md_path,
            lark_as=args.lark_as,
            parent_token=parent,
            combined=combined,
        )

    _save_state(
        last_trade_date=trade_date,
        last_status="ok",
        last_run_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        combined=combined,
    )
    logging.info("每日复盘任务完成: %s", trade_date)


def _sleep_until(target: datetime, interval_sec: int) -> None:
    while True:
        now = datetime.now()
        if now >= target:
            return
        remaining = (target - now).total_seconds()
        time.sleep(min(interval_sec, max(1, remaining)))


def scheduler_loop(args) -> None:
    hour, minute = _parse_hhmm(args.time)
    logging.info(
        "定时调度已启动：每交易日 %02d:%02d 执行（检查间隔 %ds，Ctrl+C 停止）",
        hour,
        minute,
        args.interval,
    )
    while True:
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)

        logging.info("下次触发: %s", target.strftime("%Y-%m-%d %H:%M:%S"))
        _sleep_until(target, args.interval)

        try:
            run_once(args)
        except Exception:
            logging.exception("定时任务执行失败")
            _save_state(
                last_trade_date=date.today().isoformat(),
                last_status="error",
                last_run_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            )


def main() -> int:
    load_env_files()
    parser = argparse.ArgumentParser(description="每日复盘定时调度（前台常驻）")
    add_client_args(parser)
    parser.add_argument(
        "--time",
        default=os.environ.get("DAILY_EVAL_SCHEDULE_TIME", "15:10"),
        help="触发时刻 HH:MM（默认 15:10 或 DAILY_EVAL_SCHEDULE_TIME）",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("DAILY_EVAL_SCHEDULE_INTERVAL_SEC", "30")),
        help="临近触发时的轮询间隔秒（默认 30）",
    )
    parser.add_argument(
        "--combined",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="使用全账户综合复盘（默认：双账户已配置则为 true）",
    )
    parser.add_argument("--run-now", action="store_true", help="立即执行一次后退出")
    parser.add_argument("--force", action="store_true", help="忽略今日已执行标记")
    parser.add_argument(
        "--skip-trading-day-check",
        action="store_true",
        help="不检查是否交易日",
    )
    parser.add_argument("--skip-feishu", action="store_true", help="仅生成 Markdown，不上传飞书")
    parser.add_argument("--dry-run", action="store_true", help="只检查条件，不实际执行")
    parser.add_argument(
        "--lark-as",
        default=os.environ.get("LARK_CLI_AS", "user"),
        choices=["user", "bot"],
        help="lark-cli 身份（默认 user）",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 日志")
    args = parser.parse_args()

    _setup_logging(args.verbose)

    if args.run_now:
        try:
            run_once(args)
        except Exception:
            logging.exception("执行失败")
            return 1
        return 0

    try:
        scheduler_loop(args)
    except KeyboardInterrupt:
        logging.info("已停止定时调度")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
