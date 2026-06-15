"""喂食放置 FeedingController 状态机的回归测试。"""

from core.feeding import FeedingController


def test_start_placing_sets_flag():
    fc = FeedingController()
    assert not fc.placing
    fc.start_placing()
    assert fc.placing
    assert not fc.has_food


def test_add_keeps_placing_for_multiple():
    # 放下一份后仍保持放置模式，可连续放多个
    fc = FeedingController()
    fc.start_placing()
    fc.add((320, 240))
    fc.add((400, 300))
    assert fc.placing
    assert fc.has_food
    assert fc.foods == [(320, 240), (400, 300)]


def test_cancel_placing_keeps_placed_foods():
    fc = FeedingController()
    fc.start_placing()
    fc.add((10, 20))
    fc.cancel_placing()
    assert not fc.placing
    assert fc.foods == [(10, 20)]  # 已放下的保留，宠物仍会去吃


def test_remove_one_food():
    fc = FeedingController()
    fc.add((10, 20))
    fc.add((30, 40))
    fc.remove((10, 20))
    assert fc.foods == [(30, 40)]


def test_clear_all_food():
    fc = FeedingController()
    fc.add((10, 20))
    fc.add((30, 40))
    fc.clear()
    assert not fc.has_food


def test_add_respects_max_count():
    # 达到上限后再放置被忽略，add 返回 False，foods 长度停在上限
    fc = FeedingController()
    for i in range(10):
        assert fc.add((i, i), max_count=10) is True
    assert len(fc.foods) == 10
    assert fc.is_full(10)
    assert fc.add((99, 99), max_count=10) is False
    assert len(fc.foods) == 10


def test_is_full_none_never_full():
    fc = FeedingController()
    for i in range(50):
        fc.add((i, i))  # 不传 max_count -> 不限
    assert not fc.is_full(None)
    assert fc.add((0, 0)) is True
