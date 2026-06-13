"""养成动作与行为分发的回归测试。

覆盖喂食/玩耍及新增的洗澡/睡觉/送礼三个养成动作的属性效果、
动画返回、BehaviorManager 分发，以及数值面板按钮的通用路由映射。
"""

from core.action import (
    BathAction,
    BehaviorManager,
    FeedAction,
    GiftAction,
    PlayAction,
)
from core.event import InteractionEvent, InteractionEventType
from core.pet import Pet


def _pet(hunger=50, mood=50, energy=50):
    pet = Pet()
    pet.set_hunger(hunger)
    pet.set_mood(mood)
    pet.set_energy(energy)
    return pet


def test_bath_raises_mood_costs_energy():
    pet = _pet(mood=50, energy=50)
    result = BathAction().execute(pet)
    assert pet.mood == 50 + BathAction.MOOD_GAIN
    assert pet.energy == 50 - BathAction.ENERGY_COST
    assert result.animation == "happy"


def test_gift_big_mood_boost():
    pet = _pet(mood=40)
    result = GiftAction().execute(pet)
    assert pet.mood == 40 + GiftAction.MOOD_GAIN
    assert result.animation == "excited"


def test_behavior_manager_dispatches_new_actions():
    manager = BehaviorManager()
    for event_type in (
        InteractionEventType.BATH,
        InteractionEventType.GIFT,
    ):
        pet = _pet()
        result = manager.handle(InteractionEvent(type=event_type), pet)
        assert result is not None
        assert pet.last_action == event_type.value
        assert pet.interaction_count == 1


def test_sleep_is_not_a_behavior_manager_action():
    # 睡觉是持续模式，由 PetBehavior 处理，不在一次性行为管线中
    pet = _pet()
    result = BehaviorManager().handle(InteractionEvent(type=InteractionEventType.SLEEP), pet)
    assert result is None


def test_feed_play_still_work():
    manager = BehaviorManager()
    pet = _pet(hunger=40, mood=40)
    manager.handle(InteractionEvent(type=InteractionEventType.FEED), pet)
    assert pet.hunger > 40
    assert isinstance(FeedAction().execute(_pet()).animation, str)
    assert PlayAction().execute(_pet()).animation == "playing"


def test_panel_interaction_mapping_covers_nurture_actions():
    from ui.ui_manager import _PANEL_INTERACTION_TYPES

    for action_id in ("feed", "play", "bath", "sleep", "gift"):
        assert action_id in _PANEL_INTERACTION_TYPES
        assert _PANEL_INTERACTION_TYPES[action_id].value == action_id

    # 内部事件不应作为面板按钮动作
    for internal in ("click", "drag_start", "stats_toggle"):
        assert internal not in _PANEL_INTERACTION_TYPES
