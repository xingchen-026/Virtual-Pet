"""喂食放置模块。

FeedingController 是喂食"放置模式"的纯状态机：

* 点右键面板「喂食」-> 进入放置模式（placing=True），食物图标跟随鼠标
* 左键放下食物（记录 food_position，退出放置模式）
* 右键 / 鼠标移出围栏 -> 取消放置

放下后由 AutonomousManager 驱动宠物走向食物，到达后吃掉并清除食物。
本控制器只维护状态，不涉及渲染、坐标换算或移动逻辑，便于单测。
坐标与 Pet.position 同坐标系（窗口跟随模式下为屏幕坐标）。
"""

from __future__ import annotations

from typing import Optional, Tuple

Point = Tuple[int, int]


class FeedingController:
    """喂食放置状态：是否处于放置模式、已放下的食物位置。"""

    def __init__(self) -> None:
        self.placing = False
        self.food_position: Optional[Point] = None

    @property
    def has_food(self) -> bool:
        """当前是否有一份已放下、待宠物食用的食物。"""
        return self.food_position is not None

    def start_placing(self) -> None:
        """进入放置模式（食物图标开始跟随鼠标）。"""
        self.placing = True

    def cancel_placing(self) -> None:
        """取消放置模式（不放下食物）。"""
        self.placing = False

    def place(self, point: Point) -> None:
        """在指定位置放下食物，并退出放置模式。"""
        self.food_position = point
        self.placing = False

    def clear_food(self) -> None:
        """清除已放下的食物（宠物吃完后调用）。"""
        self.food_position = None
