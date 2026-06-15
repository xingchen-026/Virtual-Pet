"""喂食放置模块。

FeedingController 是喂食"放置模式"的纯状态机：

* 点右键面板「喂食」-> 进入放置模式（placing=True），食物图标跟随鼠标
* 左键放下食物（追加到 foods 列表，**仍保持放置模式**，可连续放多个）
* 右键 / 鼠标移出围栏 -> 退出放置模式（已放下的食物保留）

放下后由 AutonomousManager 驱动宠物逐个走向食物，吃掉一个即从列表移除，
还有剩余则继续走向下一个。本控制器只维护状态，不涉及渲染、坐标换算或移动
逻辑，便于单测。坐标与 Pet.position 同坐标系（窗口跟随模式下为屏幕坐标）。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

Point = Tuple[int, int]


class FeedingController:
    """喂食放置状态：是否处于放置模式、已放下尚未吃掉的食物列表。"""

    def __init__(self) -> None:
        self.placing = False
        self.foods: List[Point] = []

    @property
    def has_food(self) -> bool:
        """当前是否有已放下、待宠物食用的食物。"""
        return bool(self.foods)

    def is_full(self, max_count: Optional[int]) -> bool:
        """已放下的食物是否已达上限（max_count 为 None 时永不满）。"""
        return max_count is not None and len(self.foods) >= max_count

    def start_placing(self) -> None:
        """进入放置模式（食物图标开始跟随鼠标）。"""
        self.placing = True

    def cancel_placing(self) -> None:
        """退出放置模式（已放下的食物保留，宠物仍会去吃）。"""
        self.placing = False

    def add(self, point: Point, max_count: Optional[int] = None) -> bool:
        """放下一份食物（保持放置模式，可继续放多个）。

        达到 max_count 上限时忽略本次放置并返回 False；成功放下返回 True。
        max_count 为 None 表示不限。
        """
        if self.is_full(max_count):
            return False
        self.foods.append(point)
        return True

    def remove(self, point: Point) -> None:
        """移除一份食物（宠物吃完该份后调用）。"""
        if point in self.foods:
            self.foods.remove(point)

    def clear(self) -> None:
        """清空所有食物。"""
        self.foods = []
