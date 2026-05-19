"""真实 Bridge 交易端点联调（需 --trading 与 API Key）。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def require_trading(live_trading_enabled: bool, live_auth_headers: dict):
    if not live_auth_headers:
        pytest.skip("未配置 QMT_BRIDGE_API_KEY，跳过交易联调")
    if not live_trading_enabled:
        pytest.skip("服务端未启用交易模块（/api/trading/* 返回 404）")


def test_live_trading_positions(
    live_client,
    live_auth_headers,
    require_trading,
) -> None:
    resp = live_client.get(
        "/api/trading/positions",
        headers=live_auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body


def test_live_trading_asset(
    live_client,
    live_auth_headers,
    require_trading,
) -> None:
    resp = live_client.get(
        "/api/trading/asset",
        headers=live_auth_headers,
    )
    assert resp.status_code == 200


def test_live_trading_orders(
    live_client,
    live_auth_headers,
    require_trading,
) -> None:
    resp = live_client.get(
        "/api/trading/orders",
        headers=live_auth_headers,
    )
    assert resp.status_code == 200


def test_live_trading_account_status(
    live_client,
    live_auth_headers,
    require_trading,
) -> None:
    resp = live_client.get(
        "/api/trading/account_status",
        headers=live_auth_headers,
    )
    assert resp.status_code == 200


def test_live_trading_requires_key(live_client, require_trading) -> None:
    """未带 Key 应被拒绝。"""
    resp = live_client.get("/api/trading/positions")
    assert resp.status_code == 401
