"""MovementController 电子围栏取点与显式目标移动的回归测试。"""

from core.movement import MovementController
from core.pet import Pet

CONFIG = {"walk_speed": 40, "movement_margin": 20, "arrival_threshold": 4}


def _mover():
    pet = Pet()
    pet.set_position(150, 150)
    return MovementController(pet, CONFIG), pet


def test_pick_random_target_stays_in_fence():
    mover, _ = _mover()
    mover.set_bounds(800, 600)
    mover.set_fence((100, 100, 200, 200))
    for _ in range(50):
        x, y = mover.pick_random_target(40)
        assert 100 <= x <= 200
        assert 100 <= y <= 200


def test_clear_fence_restores_full_range():
    mover, _ = _mover()
    mover.set_bounds(800, 600)
    mover.set_fence((100, 100, 110, 110))
    mover.clear_fence()
    assert mover.fence is None
    # 清除后范围恢复到整个 bounds（取多次，至少有一次明显超出原围栏）
    xs = [mover.pick_random_target(40)[0] for _ in range(50)]
    assert max(xs) > 200


def test_set_target_moves_and_reaches():
    mover, pet = _mover()
    mover.set_target((150, 190), speed=1000)  # 步长远大于距离 -> 一步到达
    assert mover.has_target()
    arrived = mover.update(1.0)
    assert arrived
    assert pet.position == (150, 190)
    assert not mover.has_target()
