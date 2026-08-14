"""兼容层：Skill 脚本从 qmt_bridge 包导入信用持仓拆分逻辑。"""

from qmt_bridge.credit_positions import (  # noqa: F401
    COMPACT_TYPE_FIN_BUY,
    build_credit_position_breakdown,
    margin_volume_by_code,
)

__all__ = [
    "COMPACT_TYPE_FIN_BUY",
    "build_credit_position_breakdown",
    "margin_volume_by_code",
]
