"""交易模块启动与懒重连。

启动时 connect 失败会将 trader_manager 置空；QMT 稍后就绪时，
通过首次 /api/trading/* 请求触发懒重连，无需重启整个 Bridge 进程。
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

    from ..config import Settings
    from .manager import XtTraderManager

logger = logging.getLogger("qmt_bridge.trading")

_RECONNECT_COOLDOWN_SEC = 5.0
_reconnect_lock = threading.Lock()


def build_trader_manager(settings: Settings) -> XtTraderManager:
    """按当前 Settings 构造未连接的 XtTraderManager。"""
    from .manager import XtTraderManager

    account_id, account_type = settings.resolved_trading_account()
    return XtTraderManager(
        mini_qmt_path=settings.mini_qmt_path,
        account_id=account_id,
        account_type=account_type,
        account_type_map=settings.resolved_account_type_map(),
    )


async def init_trading_on_startup(
    app: FastAPI,
    settings: Settings,
    *,
    retries: int = 3,
    delay_sec: float = 2.0,
) -> None:
    """应用启动时连接 miniQMT，失败时重试并记录 trading_init_error。"""
    last_error: Exception | None = None
    for attempt in range(retries):
        manager = build_trader_manager(settings)
        try:
            manager.connect()
            app.state.trader_manager = manager
            app.state.trading_init_error = None
            logger.info("Trading module initialized")
            return
        except Exception as e:
            last_error = e
            logger.warning(
                "Trading connect attempt %d/%d failed: %s",
                attempt + 1,
                retries,
                e,
            )
            if attempt < retries - 1:
                await asyncio.sleep(delay_sec)
    logger.error(
        "Failed to initialize trading module after %d attempts: %s",
        retries,
        last_error,
    )
    app.state.trader_manager = None
    app.state.trading_init_error = (
        str(last_error) if last_error else "XtQuantTrader connect failed"
    )


def try_lazy_reconnect(app, settings: Settings) -> XtTraderManager | None:
    """启动失败后，在冷却间隔外尝试重新连接 miniQMT。"""
    if not settings.trading_enabled:
        return None
    now = time.time()
    last_at = getattr(app.state, "_trading_reconnect_at", 0.0)
    if now - last_at < _RECONNECT_COOLDOWN_SEC:
        return None
    with _reconnect_lock:
        manager = getattr(app.state, "trader_manager", None)
        if manager is not None:
            return manager
        app.state._trading_reconnect_at = now
        manager = build_trader_manager(settings)
        try:
            manager.connect()
            app.state.trader_manager = manager
            app.state.trading_init_error = None
            logger.info("Trading module connected (lazy reconnect)")
            return manager
        except Exception as e:
            app.state.trading_init_error = str(e)
            logger.warning("Trading lazy reconnect failed: %s", e)
            return None
