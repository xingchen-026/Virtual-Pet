"""电子围栏模块。

FenceController 是围栏的纯逻辑状态机：用户在右键面板点「围栏」后进入全屏
取点态，鼠标依次点击两个对角点（经 toggle 记录），两点成矩形，限定宠物
自主漫游范围；已有围栏时点按钮走 clear 清除。所有坐标与 Pet.position 同坐标系
（窗口跟随模式下为屏幕坐标），状态变更不涉及任何渲染或 OS 调用，便于单测。

popup_topleft 是一个纯函数：设围栏后，把弹出界面统一锚定到围栏上边两角，
选能在画布内完整显示的一侧，使所有弹窗出现在同一基点，避免鼠标来回移动。
"""

from __future__ import annotations

from typing import Optional, Tuple

Point = Tuple[int, int]
Rect = Tuple[int, int, int, int]


class FenceController:
    """围栏取点状态机：两次点击定对角，已有围栏时清除。"""

    def __init__(self) -> None:
        self.fence: Optional[Rect] = None
        self._pending: Optional[Point] = None

    @property
    def pending(self) -> Optional[Point]:
        """取点中已记录的第一个角（供绘制橡皮筋预览框），未记录时为 None。"""
        return self._pending

    def clear(self) -> None:
        """清除围栏与待定取点（已设围栏时点按钮走此路径）。"""
        self.fence = None
        self._pending = None

    def toggle(self, point: Point) -> str:
        """处理一次「围栏」点击，返回状态：

        * "cleared"      —— 原本有围栏，本次清除
        * "first_corner" —— 记录第一个角，等待第二个角
        * "set"          —— 记录第二个角，围栏设定完成
        """
        if self.fence is not None:
            self.fence = None
            self._pending = None
            return "cleared"

        if self._pending is None:
            self._pending = point
            return "first_corner"

        self.fence = self._normalize(self._pending, point)
        self._pending = None
        return "set"

    @staticmethod
    def _normalize(a: Point, b: Point) -> Rect:
        """把两个对角点规范化为 (minx, miny, maxx, maxy)。"""
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))

    def contains(self, point: Point) -> bool:
        """点是否在围栏内；无围栏时恒为 True（不约束）。"""
        if self.fence is None:
            return True
        x1, y1, x2, y2 = self.fence
        return x1 <= point[0] <= x2 and y1 <= point[1] <= y2


def popup_topleft(
    fence: Optional[Rect],
    window_pos: Point,
    canvas_size: Tuple[int, int],
    popup_size: Tuple[int, int],
) -> Optional[Point]:
    """计算弹窗在窗口画布坐标系下的统一左上角；无围栏返回 None（沿用默认停靠）。

    以围栏上边两角为基点：优先把弹窗左边对齐围栏左上角（向右展开），
    若能在画布内完整显示则用之；否则把弹窗右边对齐围栏右上角（向左展开）；
    两侧都放不下时夹取到画布内。y 取围栏上边，并夹取到画布内。
    所有坐标先由屏幕坐标减去 window_pos 转换到画布坐标。
    """
    if fence is None:
        return None

    canvas_w, canvas_h = canvas_size
    popup_w, popup_h = popup_size
    x1, y1, x2, _y2 = fence

    left_anchor = x1 - window_pos[0]               # 左对齐围栏左上角
    right_anchor = x2 - window_pos[0] - popup_w     # 右对齐围栏右上角
    top = y1 - window_pos[1]

    if 0 <= left_anchor and left_anchor + popup_w <= canvas_w:
        x = left_anchor
    elif 0 <= right_anchor and right_anchor + popup_w <= canvas_w:
        x = right_anchor
    else:
        x = max(0, min(left_anchor, canvas_w - popup_w))

    y = max(0, min(top, canvas_h - popup_h))
    return (int(x), int(y))
