"""宠物行为动作模块。

每个 Action 只负责两件事：

1. 通过 Pet 已有的 increase_/decrease_* 接口修改属性
   （遵循「事件 -> 行为 -> 属性变化」，不在事件处理代码中直接改属性）
2. 返回 ActionResult，描述该行为对应的临时动画与交互提示文案

Action 不直接操作 AnimationManager 或 StateMachine：
临时动画的播放与恢复由 core.behavior.PetBehavior 统一处理。

BehaviorManager 负责将 InteractionEvent 分发给对应的 Action，
统一管理 Click / Excited / Drag(Touch) / Feed / Play / Bath / Gift 等
「一次性」行为（执行即产生属性变化与临时动画）。

注：睡觉（SLEEP）是「持续模式」而非一次性行为——点击后停在原地、
随时间缓慢恢复体力，由 core.behavior.PetBehavior 的睡眠模式实现，
在 Game._dispatch_interaction 中拦截处理，不经过 BehaviorManager。

新增一次性养成动作的扩展点（以 Bath/Gift 为范例）：
新增一个 Action 子类、在 BehaviorManager._actions 注册对应
InteractionEventType、并在数值面板增加按钮即可；UIManager 的面板
按钮按事件类型通用分发，行为分发逻辑无需改动。
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
    duration: 临时动画播放时长（秒），结束后自动恢复为状态对应动画。

    属性变化的数值提示由 Game 对比交互前后的宠物属性生成
    （见 Game._record_attr_deltas），不在此携带文案。
    """

    animation: str
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
        return ActionResult(animation="happy", duration=0.8)


class ExcitedAction(Action):
    """连续点击触发兴奋：额外心情奖励，触发 excited 动画。"""

    MOOD_GAIN = 10

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_mood(self.MOOD_GAIN)
        return ActionResult(animation="excited", duration=1.2)


class TouchAction(Action):
    """抓取/触摸反馈：拖拽开始时的短暂互动动画，不修改属性数值。"""

    def execute(self, pet: Pet) -> ActionResult:
        return ActionResult(animation="interact", duration=0.4)


class FeedAction(Action):
    """喂食：恢复饥饿与心情，触发 eating 动画。"""

    def __init__(self, food: Optional[Food] = None) -> None:
        self.food = food or DEFAULT_FOOD

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_hunger(self.food.hunger_restore)
        pet.increase_mood(self.food.mood_restore)
        return ActionResult(animation="eating", duration=1.5)


class PlayAction(Action):
    """玩耍：心情大幅提升，消耗体力与饥饿，触发 playing 动画。"""

    MOOD_GAIN = 20
    ENERGY_COST = 15
    HUNGER_COST = 10

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_mood(self.MOOD_GAIN)
        pet.decrease_energy(self.ENERGY_COST)
        pet.decrease_hunger(self.HUNGER_COST)
        return ActionResult(animation="playing", duration=1.5)


class BathAction(Action):
    """洗澡：洗干净心情提升，过程略消耗体力，复用 happy 动画。"""

    MOOD_GAIN = 15
    ENERGY_COST = 5

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_mood(self.MOOD_GAIN)
        pet.decrease_energy(self.ENERGY_COST)
        return ActionResult(animation="happy", duration=1.5)


class GiftAction(Action):
    """送礼物：心情大幅提升，复用 excited 动画。"""

    MOOD_GAIN = 30

    def execute(self, pet: Pet) -> ActionResult:
        pet.increase_mood(self.MOOD_GAIN)
        return ActionResult(animation="excited", duration=1.5)


class BehaviorManager:
    """行为管理器：统一管理 Feed / Play / Bath / Sleep / Gift / Click / Drag 等行为。

    根据 InteractionEvent.type 分发到对应的 Action 执行，
    并记录最近一次行为，供数据持久化使用。

    扩展养成动作只需：在 core.event.InteractionEventType 增加事件类型、
    新增 Action 子类、在此 _actions 注册、并在数值面板增加按钮，
    UIManager 的面板路由按事件类型通用分发，无需改动。
    """

    def __init__(self) -> None:
        self._actions: Dict[InteractionEventType, Action] = {
            InteractionEventType.CLICK: ClickAction(),
            InteractionEventType.EXCITED: ExcitedAction(),
            InteractionEventType.DRAG_START: TouchAction(),
            InteractionEventType.FEED: FeedAction(),
            InteractionEventType.PLAY: PlayAction(),
            InteractionEventType.BATH: BathAction(),
            InteractionEventType.GIFT: GiftAction(),
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
