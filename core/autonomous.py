"""宠物自主行为控制模块。

AutonomousManager 是自主行为系统的统一入口，串联完整流程：

    Pet State -> AutonomousManager -> Behavior Decision -> Action Execute -> Animation Update

职责：

* 调用 ScheduleManager 推进昼夜循环与年龄增长
* 调用 EmotionManager 刷新当前表情
* 控制行为决策频率（behavior_config["idle_time"]）
* 调用 BehaviorTree 做出行为决策（决策与执行分离，本类只负责执行）
* 执行决策：触发移动（MovementController）或临时动画
  （PetBehavior.trigger_temporary_animation / sync_to_state_animation）
* 用户正在拖拽宠物时让出控制权，避免与交互系统冲突
* 将关键行为变化写入行为日志（BehaviorLogger）

Game 主循环每帧只需调用一次 AutonomousManager.update()，
不在主循环中堆积任何 AI 判断逻辑。
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

from config import settings
from core.behavior import PetBehavior
from core.behavior_tree import AutonomousBehavior, BehaviorTree
from core.emotion import EmotionManager
from core.movement import MovementController
from core.pet import Pet
from core.schedule import ScheduleManager
from utils.behavior_logger import BehaviorLogger

# 移动类行为 -> 持续播放的动画状态名称（对应 AnimationState 的值）。
# 移动结束后由 PetBehavior.sync_to_state_animation() 恢复为状态动画。
_MOVING_BEHAVIOR_ANIMATIONS: Dict[AutonomousBehavior, str] = {
    AutonomousBehavior.WALK: "walk",
    AutonomousBehavior.TIRED_WALK: "walk",
    AutonomousBehavior.RUN: "run",
    AutonomousBehavior.SEEK_FOOD: "hungry",
}

# 一次性行为 -> (临时动画状态名称, behavior_config 中对应的播放时长配置键)
# 注：SLEEP 不在此列——它会进入 PetBehavior 的持续睡眠模式以恢复体力，
# 仅在体力已满时退化为一次小憩动画（见 _execute）。
_TEMP_ANIMATION_BEHAVIORS: Dict[AutonomousBehavior, Tuple[str, str]] = {
    AutonomousBehavior.LOOK_AROUND: ("look_around", "look_around_duration"),
    AutonomousBehavior.YAWN: ("tired", "yawn_duration"),
    AutonomousBehavior.HAPPY_PLAY: ("happy", "happy_duration"),
}

# 行为 -> 行为日志文案（仅在行为发生变化时记录一次）
_BEHAVIOR_LOG_MESSAGES: Dict[AutonomousBehavior, str] = {
    AutonomousBehavior.WALK: "Pet started walking",
    AutonomousBehavior.TIRED_WALK: "Pet wandered slowly (tired)",
    AutonomousBehavior.RUN: "Pet started running",
    AutonomousBehavior.SEEK_FOOD: "Pet became hungry and went looking for food",
    AutonomousBehavior.LOOK_AROUND: "Pet looked around",
    AutonomousBehavior.YAWN: "Pet yawned",
    AutonomousBehavior.HAPPY_PLAY: "Pet played happily",
    AutonomousBehavior.SLEEP: "Pet fell asleep",
    AutonomousBehavior.IDLE: "Pet is idle",
}


class AutonomousManager:
    """宠物自主行为管理器：协调状态判断、行为决策与动作执行。"""

    def __init__(
        self,
        pet: Pet,
        pet_behavior: PetBehavior,
        behavior_config: dict,
        logger: Optional[BehaviorLogger] = None,
    ) -> None:
        self.pet = pet
        self.pet_behavior = pet_behavior
        self.config = behavior_config
        self.logger = logger

        self.behavior_tree = BehaviorTree(behavior_config)
        self.movement = MovementController(pet, behavior_config)
        self.schedule = ScheduleManager(pet, behavior_config)
        self.emotion_manager = EmotionManager(behavior_config)

        self._idle_timer = 0.0
        self._current_behavior = AutonomousBehavior.IDLE
        self._last_logged_behavior: Optional[AutonomousBehavior] = None

        # 用户放下的食物位置（坐标系同 Pet.position）。非 None 时优先于随机
        # 漫游：宠物走向食物，到达后以到达坐标调用 on_food_reached（Game 据此
        # 移除该份食物、应用喂食效果，并在还有剩余时设定下一个目标）。
        self.food_target: Optional[Tuple[int, int]] = None
        self.on_food_reached: Optional[Callable[[Tuple[int, int]], None]] = None

    def update(self, dt: float, interaction_active: bool) -> None:
        """每帧调用一次。

        interaction_active: 用户是否正在拖拽/操作宠物。
        为 True 时自主行为暂停并清空当前移动目标，避免与交互系统冲突。
        """
        self.schedule.update(dt)
        self.emotion_manager.update(self.pet)

        if interaction_active:
            self.movement.clear_target()
            self._idle_timer = 0.0
            return

        # 食物寻路优先于随机漫游：走向用户放下的食物，到达即触发喂食回调
        if self.food_target is not None:
            self._seek_food(dt)
            return

        if self.movement.has_target():
            arrived = self.movement.update(dt)
            if arrived:
                self.pet_behavior.sync_to_state_animation()
                self._current_behavior = AutonomousBehavior.IDLE
            return

        self._idle_timer += dt
        if self._idle_timer < self.config["idle_time"]:
            return

        self._idle_timer = 0.0
        decision = self.behavior_tree.decide(self.pet, self.schedule.is_night())
        self._execute(decision)

    def _seek_food(self, dt: float) -> None:
        """走向已放下的食物，到达后清除目标并以到达坐标触发喂食回调。"""
        if not self.movement.has_target():
            speed = self.config["walk_speed"] * self.config["hungry_speed_multiplier"]
            self.movement.set_target(self.food_target, speed)
            self.pet.change_animation("hungry")
            self._current_behavior = AutonomousBehavior.SEEK_FOOD

        if self.movement.update(dt):
            reached = self.food_target
            self.food_target = None
            self.pet_behavior.sync_to_state_animation()
            self._current_behavior = AutonomousBehavior.IDLE
            if self.on_food_reached is not None:
                self.on_food_reached(reached)

    @property
    def current_behavior(self) -> AutonomousBehavior:
        """当前正在执行的自主行为。"""
        return self._current_behavior

    @property
    def emotion(self):
        """当前表情（core.emotion.Emotion）。"""
        return self.emotion_manager.current_emotion

    def _execute(self, decision: AutonomousBehavior) -> None:
        """执行一次行为决策：触发移动或临时动画，并记录日志。"""
        self._current_behavior = decision
        self._log(decision)

        if decision == AutonomousBehavior.IDLE:
            self.pet_behavior.sync_to_state_animation()
            return

        if decision == AutonomousBehavior.SLEEP:
            self._start_sleep()
            return

        if decision in _MOVING_BEHAVIOR_ANIMATIONS:
            self._start_moving(decision)
            return

        animation, duration_key = _TEMP_ANIMATION_BEHAVIORS[decision]
        self.pet_behavior.trigger_temporary_animation(animation, self.config[duration_key])

    def _start_sleep(self) -> None:
        """宠物自主进入睡眠：体力未满时进入持续睡眠模式以较快恢复体力，
        体力已满（如夜晚但精力充沛）时只小憩一会儿，不进入恢复循环，
        避免回满后立刻被夜晚规则反复唤醒、再入睡造成抖动。
        """
        if self.pet.energy < settings.ATTRIBUTE_MAX:
            self.pet_behavior.start_sleep()
        else:
            self.pet_behavior.trigger_temporary_animation(
                "sleep", self.config["sleep_duration"]
            )

    def _start_moving(self, decision: AutonomousBehavior) -> None:
        """根据决策选择移动速度并设定随机目标，同时切换为移动动画。"""
        if not self.config.get("random_walk", True):
            self.pet_behavior.sync_to_state_animation()
            return

        if decision == AutonomousBehavior.RUN:
            speed = self.config["run_speed"]
        elif decision == AutonomousBehavior.TIRED_WALK:
            speed = self.config["walk_speed"] * self.config["tired_speed_multiplier"]
        elif decision == AutonomousBehavior.SEEK_FOOD:
            speed = self.config["walk_speed"] * self.config["hungry_speed_multiplier"]
        else:
            speed = self.config["walk_speed"]

        self.movement.pick_random_target(speed)
        self.pet.change_animation(_MOVING_BEHAVIOR_ANIMATIONS[decision])

    def _log(self, decision: AutonomousBehavior) -> None:
        """行为发生变化时写入一条日志，避免重复行为反复刷屏。"""
        if self.logger is None or decision == self._last_logged_behavior:
            return

        message = _BEHAVIOR_LOG_MESSAGES.get(decision)
        if message is None:
            return

        self._last_logged_behavior = decision
        self.logger.log(message)
