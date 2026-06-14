"""自主睡眠恢复体力与休息提醒气泡计时的回归测试。"""

from config import settings
from core.autonomous import AutonomousManager
from core.behavior import PetBehavior
from core.behavior_tree import AutonomousBehavior
from core.pet import Pet
from ui.speech_bubble import SpeechBubble
from utils.helper import load_json


def _manager(energy=100):
    pet = Pet()
    pet.set_energy(energy)
    behavior = PetBehavior(pet)
    config = load_json(settings.BEHAVIOR_CONFIG_FILE)
    return AutonomousManager(pet, behavior, config), pet, behavior


def test_autonomous_sleep_enters_sustained_sleep_when_tired():
    # 体力未满时自主睡眠 -> 进入持续睡眠模式（可恢复体力）
    manager, pet, behavior = _manager(energy=30)
    manager._execute(AutonomousBehavior.SLEEP)
    assert behavior.is_sleeping


def test_autonomous_sleep_naps_only_when_energy_full():
    # 体力已满时自主睡眠 -> 仅小憩动画，不进入持续恢复（避免夜晚抖动）
    manager, pet, behavior = _manager(energy=settings.ATTRIBUTE_MAX)
    manager._execute(AutonomousBehavior.SLEEP)
    assert not behavior.is_sleeping
    assert pet.current_animation == "sleep"


def test_speech_bubble_expires_after_duration():
    bubble = SpeechBubble(font=None)
    bubble.show("该休息啦", duration=2.0)
    assert bubble.visible
    bubble.update(1.0)
    assert bubble.visible
    bubble.update(1.5)
    assert not bubble.visible
