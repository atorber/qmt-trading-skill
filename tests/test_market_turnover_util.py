"""market_turnover_util 单元测试（mock client，无需 QMT）。"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[1] / "skills" / "_shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from market_turnover_util import (  # noqa: E402
    amount_map_from_records,
    build_turnover_history,
    ensure_recent_turnover,
    fetch_turnover_amount_maps,
    fetch_turnover_history,
    get_recent_trading_dates,
    merge_cache_into_maps,
)


class _FakeClient:
    def __init__(self, market_data: dict | None = None, trading_dates: list | None = None):
        self._market_data = market_data or {}
        self._trading_dates = trading_dates
        self.tick_calls = 0
        self.market_data_calls = 0

    def get_trading_dates(self, market, start_time="", end_time="", count=-1):
        if self._trading_dates is not None:
            return self._trading_dates
        return ["20260618", "20260619", "20260620"]

    def get_market_data(self, stocks, **kwargs):
        self.market_data_calls += 1
        code = stocks[0]
        return {code: self._market_data.get(code, [])}

    def get_market_snapshot(self, stocks):
        self.tick_calls += 1
        return {
            "000001.SH": {"amount": 5e11},
            "399106.SZ": {"amount": 3e11},
        }


def _rows(dates: list[str], amount: float) -> list[dict]:
    return [{"date": d, "amount": amount} for d in dates]


def test_amount_map_from_records():
    m = amount_map_from_records(
        [{"date": "20260620", "amount": 1e12}, {"date": "bad", "amount": 0}]
    )
    assert m == {"20260620": 1e12}


def test_build_turnover_history_three_days():
    target = ["20260618", "20260619", "20260620"]
    sh = {"20260618": 5e11, "20260619": 5.1e11, "20260620": 5.2e11}
    sz = {"20260618": 3e11, "20260619": 3.1e11, "20260620": 3.2e11}
    hist = build_turnover_history(sh, sz, target)
    assert len(hist) == 3
    assert hist[-1].trade_date == "20260620"
    assert hist[-1].turnover_yi == pytest.approx(8400.0, rel=1e-3)


def test_merge_cache_fills_gaps():
    sh, sz = {}, {}
    cache = {
        "20260619": {"sh_yuan": 4e11, "sz_yuan": 2e11},
    }
    merge_cache_into_maps(sh, sz, cache)
    assert sh["20260619"] == 4e11
    assert sz["20260619"] == 2e11


def test_fetch_turnover_amount_maps_uses_tick_not_market_data(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "market_turnover_util.DEFAULT_CACHE_PATH",
        tmp_path / "cache.json",
    )
    client = _FakeClient()
    sh_map, sz_map, sz_code = fetch_turnover_amount_maps(client, try_history=False)
    today = date.today().strftime("%Y%m%d")
    assert sz_code == "399106.SZ"
    assert today in sh_map and today in sz_map
    assert client.tick_calls >= 1
    assert client.market_data_calls == 0
    assert (tmp_path / "cache.json").is_file()


def test_fetch_turnover_history_from_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "market_turnover_util.DEFAULT_CACHE_PATH",
        tmp_path / "cache.json",
    )
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        """{
  "entries": {
    "20260618": {"sh_yuan": 5e11, "sz_yuan": 3e11},
    "20260619": {"sh_yuan": 5.1e11, "sz_yuan": 3.1e11},
    "20260620": {"sh_yuan": 5.2e11, "sz_yuan": 3.2e11}
  }
}""",
        encoding="utf-8",
    )
    client = _FakeClient(
        trading_dates=["20260618", "20260619", "20260620"],
    )
    hist = fetch_turnover_history(client, 3)
    assert len(hist) == 3
    assert client.market_data_calls == 0


def test_ensure_recent_turnover_ok_from_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "market_turnover_util.DEFAULT_CACHE_PATH",
        tmp_path / "cache.json",
    )
    (tmp_path / "cache.json").write_text(
        """{
  "entries": {
    "20260618": {"sh_yuan": 5e11, "sz_yuan": 3e11},
    "20260619": {"sh_yuan": 5.1e11, "sz_yuan": 3.1e11},
    "20260620": {"sh_yuan": 5.2e11, "sz_yuan": 3.2e11}
  }
}""",
        encoding="utf-8",
    )
    client = _FakeClient(trading_dates=["20260618", "20260619", "20260620"])
    result = ensure_recent_turnover(client, 3)
    assert result["ok"] is True
    assert result["method"] == "full_tick+cache"
    assert result["target_dates"] == ["20260618", "20260619", "20260620"]


def test_get_recent_trading_dates():
    client = _FakeClient(trading_dates=["20260618", "20260619", "20260620", "20260622"])
    assert get_recent_trading_dates(client, 3) == ["20260619", "20260620", "20260622"]
