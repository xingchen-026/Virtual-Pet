"""系统托盘模块。

TrayIcon 使用 pystray 在后台线程运行系统托盘图标，提供菜单：

    Virtual Pet
    ├── 显示宠物
    ├── 隐藏宠物
    ├── 保存数据
    └── 退出程序

托盘图标自带占位图标（运行时用 Pillow 绘制，无需额外图片资源）。

托盘菜单的回调在 pystray 的后台线程中执行，本模块不直接操作
pygame / 窗口状态，仅将动作名称放入回调函数（通常是线程安全的
queue.Queue.put），具体执行交由主循环处理，避免跨线程操作
Pygame/窗口对象。
"""

from __future__ import annotations

from typing import Callable

import pystray
from PIL import Image, ImageDraw

_ICON_SIZE = 64
_BODY_COLOR = (120, 180, 255, 255)
_EYE_COLOR = (40, 40, 40, 255)


def _build_icon_image() -> Image.Image:
    """绘制一个简单的圆形宠物占位图标，用于系统托盘显示。"""
    image = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = 4
    draw.ellipse((margin, margin, _ICON_SIZE - margin, _ICON_SIZE - margin), fill=_BODY_COLOR)

    eye_y = _ICON_SIZE // 2 - 6
    for eye_x in (_ICON_SIZE // 2 - 14, _ICON_SIZE // 2 + 14):
        draw.ellipse((eye_x - 4, eye_y - 4, eye_x + 4, eye_y + 4), fill=_EYE_COLOR)

    return image


class TrayIcon:
    """桌宠系统托盘图标：显示/隐藏窗口、保存数据、退出程序。"""

    def __init__(
        self,
        on_show: Callable[[], None],
        on_hide: Callable[[], None],
        on_save: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("显示宠物", lambda icon, item: on_show()),
            pystray.MenuItem("隐藏宠物", lambda icon, item: on_hide()),
            pystray.MenuItem("保存数据", lambda icon, item: on_save()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出程序", lambda icon, item: self._on_exit_clicked(on_exit)),
        )
        self._icon = pystray.Icon("virtual_pet", _build_icon_image(), "Virtual Pet", menu)

    def _on_exit_clicked(self, on_exit: Callable[[], None]) -> None:
        on_exit()
        self._icon.stop()

    def run_detached(self) -> None:
        """在后台线程启动托盘图标，不阻塞主循环。"""
        self._icon.run_detached()

    def stop(self) -> None:
        """停止托盘图标（程序退出时调用）。"""
        self._icon.stop()
