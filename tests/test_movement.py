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


def test_bounds_origin_shifts_range():
    # 多显示器虚拟桌面：原点为负时，随机目标落在 [origin, origin+size] 内缩区间
    mover, _ = _mover()
    mover.set_bounds(800, 600, origin=(-1920, -200))
    xs, ys = [], []
    for _ in range(80):
        x, y = mover.pick_random_target(40)
        xs.append(x)
        ys.append(y)
    margin = CONFIG["movement_margin"]
    assert all(-1920 + margin <= x <= -1920 + 800 - margin for x in xs)
    assert all(-200 + margin <= y <= -200 + 600 - margin for y in ys)
    assert min(xs) < 0  # 确实落在主屏左侧的负坐标区域


def test_fence_on_secondary_monitor_with_origin():
    # 围栏落在主屏右侧的副屏（x 在 2560+），漫游目标仍正确夹在围栏内
    mover, _ = _mover()
    mover.set_bounds(5120, 1440, origin=(0, 0))
    mover.set_fence((2700, 300, 3200, 800))
    for _ in range(50):
        x, y = mover.pick_random_target(40)
        assert 2700 <= x <= 3200
        assert 300 <= y <= 800


def test_set_target_moves_and_reaches():
    mover, pet = _mover()
    mover.set_target((150, 190), speed=1000)  # 步长远大于距离 -> 一步到达
    assert mover.has_target()
    arrived = mover.update(1.0)
    assert arrived
    assert pet.position == (150, 190)
    assert not mover.has_target()
