"""自主行为决策树模块。

定义 AutonomousBehavior 枚举（自主行为的可能决策结果）与
BehaviorTree：根据宠物当前属性与昼夜信息，按优先级规则
选择一个行为决策。

决策与执行严格分离：

    State -> Behavior Decision -> Action

BehaviorTree 只产生决策（返回 AutonomousBehavior 枚举值），
不修改 Pet 的 hunger / mood / energy，也不直接操作动画或位置——
具体执行由 core.autonomous.AutonomousManager 完成。

所有概率与阈值均来自 behavior_config（config/behavior_config.json），
不在代码中硬编码。
"""

from __future__ import annotations

import enum
import random

from core.pet import Pet


class AutonomousBehavior(enum.Enum):
    """自主行为决策结果。"""

    IDLE = "idle"                # 保持当前状态对应动画，不做任何动作
    WALK = "walk"                # 随机漫游
    TIRED_WALK = "tired_walk"     # 疲劳时的低速漫游
    RUN = "run"                  # 心情愉悦时的快速移动
    LOOK_AROUND = "look_around"   # 观察周围
    YAWN = "yawn"                # 打哈欠（tired 动画）
    SLEEP = "sleep"              # 睡觉
    HAPPY_PLAY = "happy_play"     # 开心动作
    SEEK_FOOD = "seek_food"       # 饥饿时寻找食物（降低移动速度）


class BehaviorTree:
    """根据宠物状态选择自主行为的决策树。

    决策优先级（自上而下）：

    1. 饥饿（hunger < hunger_threshold） -> SEEK_FOOD
    2. 疲劳过度或夜晚（energy < sleep_threshold or is_night） -> SLEEP
    3. 疲劳（energy < tired_threshold） -> 概率性 SLEEP / TIRED_WALK
    4. 开心（mood > happy_threshold） -> 概率性 RUN / HAPPY_PLAY
    5. 默认 -> 空闲行为（概率性 LOOK_AROUND / YAWN / WALK / IDLE）
    """

    def __init__(self, behavior_config: dict) -> None:
        self.config = behavior_config

    def decide(self, pet: Pet, is_night: bool) -> AutonomousBehavior:
        """根据宠物当前属性与昼夜信息做出一次行为决策。"""
        if pet.hunger < self.config["hunger_threshold"]:
            return AutonomousBehavior.SEEK_FOOD

        if pet.energy < self.config["sleep_threshold"] or is_night:
            return AutonomousBehavior.SLEEP

        if pet.energy < self.config["tired_threshold"]:
            return self._tired_decision()

        if pet.mood > self.config["happy_threshold"]:
            return self._happy_decision()

        return self._idle_decision()

    def _tired_decision(self) -> AutonomousBehavior:
        """疲劳但未到睡眠阈值：增加休息概率，否则低速漫游。"""
        if random.random() < self.config["tired_sleep_probability"]:
            return AutonomousBehavior.SLEEP
        return AutonomousBehavior.TIRED_WALK

    def _happy_decision(self) -> AutonomousBehavior:
        """心情愉悦：增加随机活动，概率性快速移动或开心动作。"""
        if random.random() < self.config["happy_run_probability"]:
            return AutonomousBehavior.RUN
        return AutonomousBehavior.HAPPY_PLAY

    def _idle_decision(self) -> AutonomousBehavior:
        """默认空闲行为：按 idle_action_probability 概率随机执行一个空闲动作。"""
        if random.random() >= self.config["idle_action_probability"]:
            return AutonomousBehavior.IDLE

        return random.choice(
            [
                AutonomousBehavior.LOOK_AROUND,
                AutonomousBehavior.YAWN,
                AutonomousBehavior.WALK,
            ]
        )
