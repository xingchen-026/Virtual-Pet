"""用户交互管理模块。

InteractionManager 负责：

* 鼠标按下/移动/释放事件的监听
* 点击检测（鼠标是否落在宠物精灵范围内）
* 拖拽处理（拖拽开始/移动/结束，宠物跟随鼠标且不产生位置跳动）
* 右键点击（弹出/关闭数值与功能面板，喂食/玩耍按钮位于面板中）

本模块只识别用户输入并产出 InteractionEvent，
不直接修改 Pet 属性、动画或位置，
具体行为由 BehaviorManager（core.action）处理。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from config import settings
from core.event import InteractionEvent, InteractionEventType
from core.sprite import PetSprite


class ClickCounter:
    """记录点击时间戳，用于检测短时间内的连续点击（触发 excited 状态）。"""

    def __init__(self, window: float, threshold: int) -> None:
        self.window = window
        self.threshold = threshold
        self._timestamps: List[float] = []

    def register_click(self, now: float) -> bool:
        """记录一次点击，返回是否已达到连续点击触发阈值。

        达到阈值后会清空记录，重新开始计数。
        """
        self._timestamps = [t for t in self._timestamps if now - t <= self.window]
        self._timestamps.append(now)

        if len(self._timestamps) >= self.threshold:
            self._timestamps.clear()
            return True

        return False


class InteractionManager:
    """处理鼠标拖拽 / 点击与功能按键，产出交互事件供 BehaviorManager 消费。

    使用示例::

        interaction_event = interaction_manager.handle_event(event)
    """

    def __init__(self, pet_sprite: PetSprite) -> None:
        self.pet_sprite = pet_sprite
        self.dragging = False
        self._moved = False
        self._drag_offset: Tuple[int, int] = (0, 0)
        self.click_counter = ClickCounter(
            window=settings.EXCITED_CLICK_WINDOW,
            threshold=settings.EXCITED_CLICK_THRESHOLD,
        )

    def handle_event(self, event: pygame.event.Event) -> Optional[InteractionEvent]:
        """处理单个 Pygame 事件，返回对应的交互事件（无对应行为时返回 None）。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_mouse_down(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            return self._handle_right_click(event.pos)

        if event.type == pygame.MOUSEMOTION and self.dragging:
            return self._handle_mouse_motion(event.pos)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            return self._handle_mouse_up()

        return None

    def _handle_mouse_down(self, position: Tuple[int, int]) -> Optional[InteractionEvent]:
        """鼠标按下：若落在宠物范围内则进入拖拽状态。"""
        if not self.pet_sprite.rect.collidepoint(position):
            return None

        self.dragging = True
        self._moved = False

        rect = self.pet_sprite.rect
        self._drag_offset = (rect.centerx - position[0], rect.centery - position[1])

        return InteractionEvent(type=InteractionEventType.DRAG_START, position=position)

    def _handle_right_click(self, position: Tuple[int, int]) -> Optional[InteractionEvent]:
        """右键点击宠物：弹出/关闭数值信息面板，不影响属性与拖拽。"""
        if self.dragging or not self.pet_sprite.rect.collidepoint(position):
            return None

        return InteractionEvent(type=InteractionEventType.STATS_TOGGLE, position=position)

    def _handle_mouse_motion(self, position: Tuple[int, int]) -> InteractionEvent:
        """拖拽过程中：根据鼠标位置与抓取偏移量计算宠物新的中心坐标。

        保留抓取时的偏移量，避免宠物中心瞬间跳到鼠标指针位置。
        """
        self._moved = True
        new_center = (position[0] + self._drag_offset[0], position[1] + self._drag_offset[1])
        return InteractionEvent(type=InteractionEventType.DRAG_MOVE, position=new_center)

    def _handle_mouse_up(self) -> Optional[InteractionEvent]:
        """鼠标释放：结束拖拽，并根据期间是否发生过移动判定为拖拽结束或点击。"""
        if not self.dragging:
            return None

        self.dragging = False

        if self._moved:
            return InteractionEvent(type=InteractionEventType.DRAG_END)

        now = pygame.time.get_ticks() / 1000.0
        if self.click_counter.register_click(now):
            return InteractionEvent(type=InteractionEventType.EXCITED)

        return InteractionEvent(type=InteractionEventType.CLICK)
