"""StateMachine 状态判定（含新增 SAD 难过状态）的回归测试。"""

from core.animation import AnimationState
from core.behavior import STATE_ANIMATION_MAP
from core.pet_state import PetState
from core.state_machine import StateMachine


def test_low_mood_returns_sad():
    # 心情极低、饥饿/体力正常 -> 难过
    assert StateMachine.evaluate(hunger=80, mood=10, energy=80) == PetState.SAD


def test_hunger_takes_priority_over_sad():
    # 饥饿是更紧迫的需求，优先于难过
    assert StateMachine.evaluate(hunger=10, mood=5, energy=80) == PetState.HUNGRY


def test_tired_takes_priority_over_sad():
    assert StateMachine.evaluate(hunger=80, mood=5, energy=10) == PetState.TIRED


def test_normal_mood_not_sad():
    assert StateMachine.evaluate(hunger=80, mood=50, energy=80) == PetState.IDLE
    assert StateMachine.evaluate(hunger=80, mood=90, energy=80) == PetState.HAPPY


def test_sad_has_dedicated_animation():
    assert AnimationState.SAD.value == "sad"
    assert STATE_ANIMATION_MAP[PetState.SAD] == "sad"
