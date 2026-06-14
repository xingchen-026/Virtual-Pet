"""IntervalTimer 周期触发、重置与间隔变更的回归测试。"""

from utils.timer import IntervalTimer


def test_fires_when_interval_reached():
    fired = []
    timer = IntervalTimer(1.0, lambda: fired.append(True))
    assert timer.update(0.4) is False
    assert timer.update(0.4) is False
    assert timer.update(0.4) is True  # 累计 1.2 >= 1.0
    assert fired == [True]


def test_resets_after_firing():
    timer = IntervalTimer(1.0)
    assert timer.update(1.0) is True
    assert timer.update(0.5) is False  # 触发后重新计时
    assert timer.update(0.5) is True


def test_large_dt_fires_only_once():
    # 远超间隔（如进程挂起后恢复）只触发一次：到点即清零，不补偿连发
    count = []
    timer = IntervalTimer(1.0, lambda: count.append(1))
    assert timer.update(10.0) is True
    assert count == [1]


def test_reset_clears_elapsed():
    timer = IntervalTimer(1.0)
    timer.update(0.9)
    timer.reset()
    assert timer.update(0.2) is False  # 重置后从零累计


def test_works_without_callback():
    timer = IntervalTimer(1.0)
    assert timer.update(1.0) is True  # 无回调也返回触发信号


def test_interval_change_takes_effect():
    timer = IntervalTimer(10.0)
    timer.interval = 1.0
    timer.reset()
    assert timer.update(1.0) is True
