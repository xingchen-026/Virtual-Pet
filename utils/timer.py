"""周期计时器工具。

IntervalTimer 把"累计 dt、到达间隔即触发一次、随后重新计时"这一在主循环里
反复出现的模式（自动存档 / 窗口置顶维持 / 休息提醒）聚合为一个可独立测试的
小组件，避免在 Game / UIManager 中散落多个 _xxx_timer 浮点字段与重复的累加判断。
"""

from __future__ import annotations

from typing import Callable, Optional


class IntervalTimer:
    """按固定时间间隔触发的计时器。

    每次 update(dt) 累加经过时间，到达 interval 即触发（调用可选回调并返回
    True），随后清零重新计时。单帧 dt 极大时（如进程被挂起后恢复）也只触发
    一次——清零而非扣除间隔，与原 Game._autosave / _refresh_topmost /
    UIManager._update_rest_reminder 的"到点即重置"语义保持一致，避免补偿式连发。
    """

    def __init__(self, interval: float, callback: Optional[Callable[[], None]] = None) -> None:
        self.interval = interval
        self.callback = callback
        self._elapsed = 0.0

    def update(self, dt: float) -> bool:
        """累计 dt；到达间隔则触发回调并清零，返回本次是否触发。"""
        self._elapsed += dt
        if self._elapsed >= self.interval:
            self._elapsed = 0.0
            if self.callback is not None:
                self.callback()
            return True
        return False

    def reset(self) -> None:
        """清零计时（间隔变更或外部主动存档后重新计时）。"""
        self._elapsed = 0.0
