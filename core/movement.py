"""移动控制模块。

MovementController 负责自主漫游时的位置移动：

* 在窗口范围内随机生成目标位置
* 按可配置速度向目标平滑移动
* 到达目标后停止并报告完成

本模块只负责"如何移动"，不判断"是否应该移动"
（行为决策由 core.behavior_tree.BehaviorTree 完成），
也不直接操作动画（动画切换由 core.autonomous.AutonomousManager 完成）。
"""

from __future__ import annotations

import random
from typing import Optional, Tuple

from config import settings
from core.pet import Pet


class MovementController:
    """控制宠物在窗口范围内的随机漫游与平滑移动。"""

    def __init__(self, pet: Pet, behavior_config: dict) -> None:
        self.pet = pet
        self.config = behavior_config
        self.target: Optional[Tuple[float, float]] = None
        self.speed = float(self.config["walk_speed"])

        # 移动过程中的浮点坐标。Pet.position 为整数坐标（供 Sprite/Rect 使用），
        # 若每帧都从中读回作为移动起点，低速移动时的小数步长会被舍入吞掉，
        # 导致位置卡死不再前进。移动期间改为维护此浮点坐标作为唯一来源。
        self._float_position: Optional[Tuple[float, float]] = None

    def has_target(self) -> bool:
        """是否存在尚未到达的移动目标。"""
        return self.target is not None

    def clear_target(self) -> None:
        """清除当前移动目标（例如用户开始拖拽时）。"""
        self.target = None
        self._float_position = None

    def pick_random_target(self, speed: float) -> Tuple[float, float]:
        """在窗口范围内随机选取一个目标位置，并设置移动速度。"""
        margin = self.config["movement_margin"]
        x = random.uniform(margin, settings.WINDOW_WIDTH - margin)
        y = random.uniform(margin, settings.WINDOW_HEIGHT - margin)

        self.target = (x, y)
        self.speed = speed
        self._float_position = (float(self.pet.position[0]), float(self.pet.position[1]))
        return self.target

    def update(self, dt: float) -> bool:
        """向目标移动一步，返回是否已到达目标。

        到达后会清空目标并将宠物精确放置在目标位置上。
        """
        if self.target is None:
            return False

        current_x, current_y = self._float_position
        target_x, target_y = self.target

        dx = target_x - current_x
        dy = target_y - current_y
        distance = (dx ** 2 + dy ** 2) ** 0.5

        arrival_threshold = self.config["arrival_threshold"]
        if distance <= arrival_threshold:
            self._set_position(target_x, target_y)
            self.target = None
            self._float_position = None
            return True

        step = self.speed * dt
        if step >= distance:
            self._set_position(target_x, target_y)
            self.target = None
            self._float_position = None
            return True

        ratio = step / distance
        new_x = current_x + dx * ratio
        new_y = current_y + dy * ratio
        self._float_position = (new_x, new_y)
        self._set_position(new_x, new_y)
        return False

    def _set_position(self, x: float, y: float) -> None:
        """更新宠物位置，统一转换为整数坐标（与 Sprite/Rect 保持一致）。"""
        self.pet.set_position(int(round(x)), int(round(y)))
