"""Pet 属性钳制与序列化的回归测试。"""

from config import settings
from core.pet import Pet


def test_attributes_clamped_to_range():
    pet = Pet()
    pet.set_hunger(settings.ATTRIBUTE_MAX + 50)
    assert pet.hunger == settings.ATTRIBUTE_MAX
    pet.set_hunger(settings.ATTRIBUTE_MIN - 50)
    assert pet.hunger == settings.ATTRIBUTE_MIN


def test_relative_changes_clamp():
    pet = Pet()
    pet.set_mood(95)
    pet.increase_mood(20)
    assert pet.mood == settings.ATTRIBUTE_MAX

    pet.set_energy(5)
    pet.decrease_energy(20)
    assert pet.energy == settings.ATTRIBUTE_MIN


def test_record_interaction_tracks_last_action_and_count():
    pet = Pet()
    assert pet.interaction_count == 0
    pet.record_interaction("feed")
    pet.record_interaction("play")
    assert pet.last_action == "play"
    assert pet.interaction_count == 2


def test_to_dict_from_dict_roundtrip():
    pet = Pet()
    pet.set_hunger(42)
    pet.set_mood(77)
    pet.record_interaction("feed")

    restored = Pet.from_dict(pet.to_dict())
    assert restored.hunger == 42
    assert restored.mood == 77
    assert restored.last_action == "feed"
    assert restored.interaction_count == 1


def test_default_facing_is_right():
    # 素材默认朝右，新建宠物不应处于镜像状态
    assert Pet().facing_left is False


def test_default_level_and_exp():
    pet = Pet()
    assert pet.level == 1
    assert pet.exp == 0
    assert pet.exp_to_next() == settings.LEVEL_BASE_EXP  # 1 级 -> 2 级阈值


def test_add_exp_levels_up():
    pet = Pet()
    # 1->2 需 LEVEL_BASE_EXP 经验
    assert pet.add_exp(settings.LEVEL_BASE_EXP) == 1
    assert pet.level == 2
    assert pet.exp == 0
    # 阈值随等级增长：2->3 需 2 * base
    assert pet.exp_to_next() == settings.LEVEL_BASE_EXP * 2


def test_add_exp_multi_level_and_carry():
    pet = Pet()
    base = settings.LEVEL_BASE_EXP
    # 1->2 需 base，2->3 需 2*base；给 base + 2*base + 5 应升 2 级、余 5
    levels = pet.add_exp(base + 2 * base + 5)
    assert levels == 2
    assert pet.level == 3
    assert pet.exp == 5


def test_add_exp_noop_for_nonpositive():
    pet = Pet()
    assert pet.add_exp(0) == 0
    assert pet.add_exp(-10) == 0
    assert pet.level == 1 and pet.exp == 0


def test_level_exp_roundtrip():
    pet = Pet()
    pet.add_exp(settings.LEVEL_BASE_EXP + 7)
    restored = Pet.from_dict(pet.to_dict())
    assert restored.level == pet.level
    assert restored.exp == pet.exp
