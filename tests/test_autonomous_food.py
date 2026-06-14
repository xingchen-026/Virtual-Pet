"""AutonomousManager 食物寻路（走向食物 -> 到达回调）的回归测试。"""

from config import settings
from core.autonomous import AutonomousManager
from core.behavior import PetBehavior
from core.pet import Pet
from utils.helper import load_json


def _manager():
    pet = Pet()
    pet.set_position(400, 300)
    behavior = PetBehavior(pet)
    config = load_json(settings.BEHAVIOR_CONFIG_FILE)
    return AutonomousManager(pet, behavior, config), pet


def test_food_target_triggers_callback_on_arrival():
    manager, pet = _manager()
    reached = []
    manager.on_food_reached = lambda: reached.append(True)
    manager.food_target = (410, 300)  # 距离 10，一次大 dt 即可走到
    manager.update(1.0, interaction_active=False)
    assert reached == [True]
    assert manager.food_target is None
    assert pet.position == (410, 300)


def test_interaction_active_suppresses_food_seek():
    manager, _ = _manager()
    reached = []
    manager.on_food_reached = lambda: reached.append(True)
    manager.food_target = (410, 300)
    manager.update(1.0, interaction_active=True)
    assert reached == []
    assert manager.food_target == (410, 300)  # 未被消费


def test_food_seek_switches_to_hungry_animation():
    manager, pet = _manager()
    manager.food_target = (700, 300)  # 较远，一次走不到，仍在寻路
    manager.update(0.1, interaction_active=False)
    assert pet.current_animation == "hungry"
    assert manager.food_target is not None
