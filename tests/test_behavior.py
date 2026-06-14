"""PetBehavior 睡眠模式与危急状态的回归测试。"""

from config import settings
from core.behavior import PetBehavior
from core.pet import Pet


def _behavior(hunger=100, mood=70, energy=100):
    pet = Pet()
    pet.set_hunger(hunger)
    pet.set_mood(mood)
    pet.set_energy(energy)
    return PetBehavior(pet), pet


def test_start_sleep_enters_sleep_animation():
    behavior, pet = _behavior(energy=50)
    behavior.start_sleep()
    assert behavior.is_sleeping
    assert pet.current_animation == "sleep"


def test_sleep_recovers_energy_gradually():
    behavior, pet = _behavior(energy=50)
    behavior.start_sleep()
    behavior.update(settings.ATTRIBUTE_DECAY_INTERVAL)  # 一个 tick
    assert pet.energy == 50 + settings.SLEEP_ENERGY_RECOVER_PER_TICK
    assert behavior.is_sleeping  # 未回满，继续睡


def test_sleep_auto_wakes_when_energy_full():
    behavior, pet = _behavior(energy=98)
    behavior.start_sleep()
    behavior.update(settings.ATTRIBUTE_DECAY_INTERVAL)  # +5 -> 钳制到 100
    assert pet.energy == settings.ATTRIBUTE_MAX
    assert not behavior.is_sleeping


def test_stop_sleep_clears_flag():
    behavior, pet = _behavior(energy=50)
    behavior.start_sleep()
    behavior.stop_sleep()
    assert not behavior.is_sleeping
    assert pet.current_animation != "sleep"


def test_energy_drains_only_while_moving():
    # 移动中：体力按 ENERGY_DECAY_PER_TICK 缓慢下降
    behavior, pet = _behavior(energy=50)
    behavior.update(settings.ATTRIBUTE_DECAY_INTERVAL, moving=True)
    assert pet.energy == 50 - settings.ENERGY_DECAY_PER_TICK


def test_energy_regens_while_idle():
    # 静止（非睡眠）：体力按 ENERGY_REGEN_PER_TICK 缓慢回升
    behavior, pet = _behavior(energy=50)
    behavior.update(settings.ATTRIBUTE_DECAY_INTERVAL, moving=False)
    assert pet.energy == 50 + settings.ENERGY_REGEN_PER_TICK


def test_is_critical_when_hunger_zero():
    behavior, pet = _behavior(hunger=0)
    assert behavior.is_critical


def test_is_critical_when_energy_zero():
    behavior, pet = _behavior(energy=0)
    assert behavior.is_critical


def test_not_critical_when_attributes_above_threshold():
    behavior, pet = _behavior(hunger=100, energy=100)
    assert not behavior.is_critical


def test_critical_forces_state_animation():
    # 饥饿归零：经过一次更新后应显示 hungry 动画（即便此前是漫游动画）
    behavior, pet = _behavior(hunger=0, energy=100)
    pet.change_animation("walk")  # 模拟漫游残留动画
    behavior.update(settings.ATTRIBUTE_DECAY_INTERVAL)
    assert pet.current_animation == "hungry"
