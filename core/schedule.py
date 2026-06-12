"""生命周期时间调度模块。

ScheduleManager 基于帧时间增量（dt）累计游戏内时间，
模拟昼夜循环与宠物年龄增长，不依赖真实时钟、不阻塞主循环
（与 pygame.time.Clock 提供的 dt 配合使用）。

昼夜信息供 core.behavior_tree.BehaviorTree 在决策时参考
（例如夜间倾向于 SLEEP），属性的周期性衰减仍由
core.behavior.PetBehavior 负责，本模块不修改 Pet 的
hunger / mood / energy。
"""

from __future__ import annotations

from core.pet import Pet


class ScheduleManager:
    """管理游戏内昼夜循环与宠物年龄增长。"""

    def __init__(self, pet: Pet, behavior_config: dict) -> None:
        self.pet = pet
        self.config = behavior_config

        self.day_length = float(self.config["day_length_seconds"])
        self.night_ratio = float(self.config["night_ratio"])
        self.days_per_age_year = max(1, int(self.config["days_per_age_year"]))

        self._elapsed = 0.0
        self._day_count = 0

    def update(self, dt: float) -> None:
        """累计游戏内时间，跨过一整天时增加天数计数并更新年龄。"""
        self._elapsed += dt

        while self._elapsed >= self.day_length:
            self._elapsed -= self.day_length
            self._day_count += 1

            if self._day_count % self.days_per_age_year == 0:
                self.pet.age += 1

    def is_night(self) -> bool:
        """是否处于夜晚时段（一天中后 night_ratio 比例的时间）。"""
        day_progress = self._elapsed / self.day_length
        return day_progress >= (1.0 - self.night_ratio)

    def time_of_day(self) -> str:
        """返回当前时段："day" 或 "night"。"""
        return "night" if self.is_night() else "day"

    @property
    def day_count(self) -> int:
        """已经历的完整天数。"""
        return self._day_count
