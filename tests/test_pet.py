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
