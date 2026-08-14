"""飞书文档标题与注册表（无网络）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills" / "_shared"))

from feishu_doc import DOC_TYPES, format_title, title_from_markdown  # noqa: E402


def test_format_title_with_trade_date() -> None:
    t = format_title("QMT Bridge 当日复盘", trade_date="2026-05-21", synced_at="2026-05-21 12:00:00")
    assert t == "QMT Bridge 当日复盘 2026-05-21 12:00:00"


def test_format_title_with_subject() -> None:
    t = format_title("QMT Bridge 涨跌分析", subject="持仓", synced_at="2026-05-21 12:00:00")
    assert "持仓" in t and t.endswith("12:00:00")


def test_title_from_markdown(tmp_path: Path) -> None:
    p = tmp_path / "a.md"
    h1 = "QMT Bridge 当日复盘 2026-05-21 11:00:00"
    p.write_text(f"# {h1}\n\nbody\n", encoding="utf-8")
    assert title_from_markdown(p) == h1


def test_doc_types_registry() -> None:
    assert "daily-eval" in DOC_TYPES
    assert DOC_TYPES["daily-eval"].folder_name == "每日复盘"
    assert DOC_TYPES["return-analysis"].source_skill == "qmt-bridge-return-analysis"
