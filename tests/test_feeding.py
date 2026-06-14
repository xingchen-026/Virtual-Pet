"""喂食放置 FeedingController 状态机的回归测试。"""

from core.feeding import FeedingController


def test_start_placing_sets_flag():
    fc = FeedingController()
    assert not fc.placing
    fc.start_placing()
    assert fc.placing
    assert not fc.has_food


def test_place_records_food_and_exits_placing():
    fc = FeedingController()
    fc.start_placing()
    fc.place((320, 240))
    assert not fc.placing
    assert fc.has_food
    assert fc.food_position == (320, 240)


def test_cancel_placing_keeps_no_food():
    fc = FeedingController()
    fc.start_placing()
    fc.cancel_placing()
    assert not fc.placing
    assert not fc.has_food


def test_clear_food():
    fc = FeedingController()
    fc.place((10, 20))
    fc.clear_food()
    assert not fc.has_food
    assert fc.food_position is None
