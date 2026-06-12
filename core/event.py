"""交互事件定义模块。

定义 InteractionManager 产出的事件类型与事件数据结构，
作为「用户输入」与「行为系统」之间的统一接口：

User Input -> InteractionManager -> InteractionEvent -> BehaviorManager
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


class InteractionEventType(enum.Enum):
    """交互事件类型。"""

    CLICK = "click"            # 单击宠物（按下后未拖动即释放）
    EXCITED = "excited"         # 短时间内多次点击触发
    DRAG_START = "drag_start"    # 按下并开始拖拽
    DRAG_MOVE = "drag_move"      # 拖拽过程中
    DRAG_END = "drag_end"        # 拖拽结束
    FEED = "feed"               # 喂食
    PLAY = "play"               # 玩耍
    STATS_TOGGLE = "stats_toggle"  # 右键点击宠物，弹出/关闭数值信息面板


@dataclass
class InteractionEvent:
    """交互事件数据。

    position: 鼠标坐标，或拖拽时宠物的目标中心坐标。
    data: 附加数据（例如未来可携带具体食物、玩具信息）。
    """

    type: InteractionEventType
    position: Optional[Tuple[int, int]] = None
    data: Dict[str, Any] = field(default_factory=dict)
