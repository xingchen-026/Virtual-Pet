"""宠物行为动作模块。

每个 Action 只负责两件事：

1. 通过 Pet 已有的 increase_/decrease_* 接口修改属性
   （遵循「事件 -> 行为 -> 属性变化」，不在事件处理代码中直接改属性）
2. 返回 ActionResult，描述该行为对应的临时动画与交互提示文案

Action 不直接操作 AnimationManager 或 StateMachine：
临时动画的播放与恢复由 core.behavior.PetBehavior 统一处理。

BehaviorManager 负责将 InteractionEvent 分发给对应的 Action，
统一管理 Click / Excited / Drag(Touch) / Feed / Play 等行为。

未来新增行为（例如 BathAction、SleepAction、GiftAction）时，
只需新增一个 Action 子类并在 BehaviorManager 中注册即可，
不需要改动事件系统或行为分发逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from core.event import InteractionEvent, InteractionEventType
from core.food import DEFAULT_FOOD, Food
from core.pet import Pet


@dataclass
class ActionResult:
    """行为执行结果。

    animation: 行为触发的临时动画状态名称（对应 AnimationState 的值）。
    message: 交互提示文案，空字符串表示不显示提示。
    duration: 临时动画播放时长（秒），结束后自动恢复为状态对应动画。
    """

    animation: str
    message: str
    duration: float = 1.0


class Action:
    """宠物行为动作基类。"""

    def execute(self, pet: Pet) -> ActionResult:
        """对宠物应用本行为的属性变化，并返回对应的动画与提示信息。"""
        raise NotImplementedError


class ClickAction(Action):
    """普通点击：心情 +5，体力 -2，触发 happy 动画。"""

    MOOD_GAIN = 5
    ENERGY_COST = 2

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_mood(self.MOOD_GAIN)
        pet.decrease_energy(self.ENERGY_COST)
        return ActionResult(animation="happy", message=f"+{self.MOOD_GAIN} Mood", duration=0.8)


class ExcitedAction(Action):
    """连续点击触发兴奋：额外心情奖励，触发 excited 动画。"""

    MOOD_GAIN = 10

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_mood(self.MOOD_GAIN)
        return ActionResult(
            animation="excited",
            message=f"Excited! +{self.MOOD_GAIN} Mood",
            duration=1.2,
        )


class TouchAction(Action):
    """抓取/触摸反馈：拖拽开始时的短暂互动动画，不修改属性数值。"""

    def execute(self, pet: Pet) -> ActionResult:
        return ActionResult(animation="interact", message="", duration=0.4)


class FeedAction(Action):
    """喂食：恢复饥饿与心情，触发 eating 动画。"""

    def __init__(self, food: Optional[Food] = None) -> None:
        self.food = food or DEFAULT_FOOD

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_hunger(self.food.hunger_restore)
        pet.increase_mood(self.food.mood_restore)
        message = f"+{self.food.hunger_restore:g} Hunger  +{self.food.mood_restore:g} Mood"
        return ActionResult(animation="eating", message=message, duration=1.5)


class PlayAction(Action):
    """玩耍：心情大幅提升，消耗体力与饥饿，触发 playing 动画。"""

    MOOD_GAIN = 20
    ENERGY_COST = 15
    HUNGER_COST = 10

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_mood(self.MOOD_GAIN)
        pet.decrease_energy(self.ENERGY_COST)
        pet.decrease_hunger(self.HUNGER_COST)
        message = (
            f"+{self.MOOD_GAIN} Mood  -{self.ENERGY_COST} Energy  -{self.HUNGER_COST} Hunger"
        )
        return ActionResult(animation="playing", message=message, duration=1.5)


class BehaviorManager:
    """行为管理器：统一管理 Feed / Play / Click / Drag 等交互行为。

    根据 InteractionEvent.type 分发到对应的 Action 执行，
    并记录最近一次行为，供数据持久化使用。
    """

    def __init__(self) -> None:
        self._actions: Dict[InteractionEventType, Action] = {
            InteractionEventType.CLICK: ClickAction(),
            InteractionEventType.EXCITED: ExcitedAction(),
            InteractionEventType.DRAG_START: TouchAction(),
            InteractionEventType.FEED: FeedAction(),
            InteractionEventType.PLAY: PlayAction(),
        }

    def handle(self, event: InteractionEvent, pet: Pet) -> Optional[ActionResult]:
        """执行事件对应的行为，并将结果记录到 Pet。

        返回 None 表示该事件不对应任何行为（例如拖拽移动/结束）。
        """
        action = self._actions.get(event.type)
        if action is None:
            return None

        result = action.execute(pet)
        pet.record_interaction(event.type.value)
        return result
