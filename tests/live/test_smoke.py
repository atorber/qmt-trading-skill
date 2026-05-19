"""真实 Bridge 冒烟联调（元数据 + 常用行情）。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


def test_live_health(live_client) -> None:
    resp = live_client.get("/api/meta/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_live_version(live_client) -> None:
    resp = live_client.get("/api/meta/version")
    assert resp.status_code == 200
    assert "version" in resp.json()


def test_live_markets(live_client) -> None:
    resp = live_client.get("/api/meta/markets")
    assert resp.status_code == 200
    body = resp.json()
    assert "markets" in body


def test_live_sector_list(live_client) -> None:
    resp = live_client.get("/api/sector/list")
    assert resp.status_code == 200
    body = resp.json()
    sectors = body.get("sectors") or body.get("data") or body
    assert sectors


def test_live_sector_stocks(live_client) -> None:
    resp = live_client.get(
        "/api/sector/stocks",
        params={"sector": "沪深A股"},
    )
    assert resp.status_code == 200


def test_live_full_tick(live_client) -> None:
    resp = live_client.get(
        "/api/market/full_tick",
        params={"stocks": "000001.SZ"},
    )
    assert resp.status_code == 200


def test_live_trading_dates(live_client) -> None:
    resp = live_client.get(
        "/api/calendar/trading_dates",
        params={"market": "SH"},
    )
    assert resp.status_code == 200
