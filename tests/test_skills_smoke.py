"""Agent Skills 冒烟：--help 与共享模块单元测试（无 Bridge 网络）。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SKILLS = REPO / "skills"

SCRIPT_PATHS = sorted(SKILLS.glob("qmt-bridge-*/scripts/*.py"))


@pytest.mark.parametrize("script", SCRIPT_PATHS, ids=lambda p: p.parent.parent.name)
def test_skill_script_help(script: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_financial_util_codes_without_table() -> None:
    sys.path.insert(0, str(SKILLS / "_shared"))
    from financial_util import codes_without_table  # noqa: WPS433

    data = {
        "600519.SH": {"Pershareindex": [{"m_timetag": "20240101"}]},
        "000001.SZ": {"Pershareindex": []},
    }
    missing = codes_without_table(data, ["600519.SH", "000001.SZ"], "Pershareindex")
    assert missing == ["000001.SZ"]


def test_common_fmt_num() -> None:
    sys.path.insert(0, str(SKILLS / "_shared"))
    from common import fmt_num  # noqa: WPS433

    assert fmt_num(1234.5) == "1,234.50"
    assert fmt_num(None) == "-"
