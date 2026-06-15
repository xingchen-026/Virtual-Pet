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

        # 漫游范围（宽, 高）。默认窗口大小；桌面窗口跟随模式下
        # 由 Game 设置为整个屏幕大小，宠物可在桌面上自由漫游。
        self.bounds: Tuple[int, int] = (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)

        # 漫游目标的边缘内缩（左右, 上下）。窗口跟随模式下设为半个窗口，
        # 使宠物不会漫游到屏幕边缘导致窗口（及右键面板）跑出屏幕外。
        self.inset: Tuple[int, int] = (0, 0)

        # 漫游范围的原点（左上角，与 bounds 同坐标系）。多显示器虚拟桌面下
        # 主屏左侧/上方的显示器坐标为负，故原点可能非 (0,0)。默认 (0,0) 即单屏。
        self.origin: Tuple[int, int] = (0, 0)

        # 电子围栏：(x1, y1, x2, y2)，与 bounds 同坐标系。设定后随机漫游
        # 目标被限制在围栏与安全区间的交集内（见 pick_random_target）。
        self.fence: Optional[Tuple[int, int, int, int]] = None

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

    def set_bounds(
        self,
        width: int,
        height: int,
        inset: Tuple[int, int] = (0, 0),
        origin: Tuple[int, int] = (0, 0),
    ) -> None:
        """设置漫游范围、边缘内缩与原点（桌面跟随模式为虚拟桌面尺寸 + 半窗口内缩）。

        origin 为漫游范围左上角，多显示器虚拟桌面下可能为负；默认 (0,0) 即单屏。
        """
        self.bounds = (width, height)
        self.inset = inset
        self.origin = origin

    def set_fence(self, fence: Tuple[int, int, int, int]) -> None:
        """设置电子围栏，限定随机漫游范围（坐标系与 bounds 一致）。"""
        self.fence = fence

    def clear_fence(self) -> None:
        """清除电子围栏，恢复在整个 bounds 内漫游。"""
        self.fence = None

    def set_target(self, point: Tuple[int, int], speed: float) -> None:
        """设置一个显式移动目标（如走向放下的食物），按 speed 平滑移动。

        与 pick_random_target 不同，本方法直接指定目标、不受围栏约束
        （食物位置由用户放置，已在放置时受围栏限制）。
        """
        self.target = (float(point[0]), float(point[1]))
        self.speed = speed
        self._float_position = (float(self.pet.position[0]), float(self.pet.position[1]))

    def pick_random_target(self, speed: float) -> Tuple[float, float]:
        """在漫游范围内随机选取一个目标位置，并设置移动速度。

        范围会同时考虑 movement_margin 与 inset（半窗口），
        并对内缩后区间做钳制，避免屏幕过小时上下限反转。
        设有围栏时，进一步把范围夹到围栏与安全区间的交集内
        （围栏过小或贴屏幕边时 _random_in_range 返回区间中点，仍落在围栏内）。
        """
        margin = self.config["movement_margin"]
        low_x = self.origin[0] + self.inset[0] + margin
        high_x = self.origin[0] + self.bounds[0] - self.inset[0] - margin
        low_y = self.origin[1] + self.inset[1] + margin
        high_y = self.origin[1] + self.bounds[1] - self.inset[1] - margin

        if self.fence is not None:
            fx1, fy1, fx2, fy2 = self.fence
            low_x, high_x = max(low_x, fx1), min(high_x, fx2)
            low_y, high_y = max(low_y, fy1), min(high_y, fy2)

        x = self._random_in_range(low_x, high_x)
        y = self._random_in_range(low_y, high_y)

        self.target = (x, y)
        self.speed = speed
        self._float_position = (float(self.pet.position[0]), float(self.pet.position[1]))
        return self.target

    @staticmethod
    def _random_in_range(low: float, high: float) -> float:
        """在 [low, high] 内取随机值；区间反转时返回其中点。"""
        if low >= high:
            return (low + high) / 2
        return random.uniform(low, high)

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

        # 根据水平移动方向更新朝向（素材默认朝右，向左移动时镜像渲染）
        if abs(dx) > 1.0:
            self.pet.facing_left = dx < 0

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
