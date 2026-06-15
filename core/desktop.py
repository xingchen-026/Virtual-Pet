"""桌面窗口管理模块。

DesktopManager 封装所有与操作系统窗口相关的能力：

* 创建/识别无边框窗口
* 设置背景透明（颜色键 + 分层窗口）
* 窗口置顶
* 隐藏 / 显示窗口
* 移动窗口位置（供桌面拖动使用）
* 读取窗口位置与鼠标在屏幕坐标系下的位置

Game 不直接调用任何操作系统 API，统一通过本模块：

    Game -> DesktopManager -> OS API

仅 Windows 平台通过 pywin32 提供完整能力；其他平台（或 pywin32
不可用时）各方法退化为安全的空操作并记录一次日志，
保证程序在非 Windows 平台仍可作为普通窗口正常运行。
所有初始配置（是否透明/置顶/初始位置/启动即隐藏）均来自
config/desktop_config.json，不在代码中硬编码。
"""

from __future__ import annotations

import platform
from typing import Optional, Tuple

import pygame

from config import settings
from utils.exception import DesktopWindowError, log_exception

_IS_WINDOWS = platform.system() == "Windows"

if _IS_WINDOWS:
    try:
        import win32api
        import win32con
        import win32gui
    except ImportError:  # pragma: no cover - pywin32 未安装时的兜底
        _IS_WINDOWS = False


class DesktopManager:
    """管理桌宠窗口的桌面相关属性（透明 / 置顶 / 隐藏 / 拖动）。"""

    def __init__(self, desktop_config: dict) -> None:
        self.config = desktop_config
        self._hwnd: Optional[int] = None
        self._visible = True

        self.initialize()

    @property
    def supported(self) -> bool:
        """当前平台是否支持完整桌面窗口能力（拿到了有效窗口句柄）。"""
        return self._hwnd is not None

    @property
    def visible(self) -> bool:
        """窗口当前是否处于显示状态。"""
        return self._visible

    def initialize(self) -> None:
        """获取窗口句柄并应用初始配置（位置 / 透明 / 置顶 / 启动即隐藏）。"""
        if not _IS_WINDOWS:
            log_exception(DesktopWindowError("当前平台不支持桌面窗口扩展能力，使用普通窗口模式运行"))
            return

        try:
            self._hwnd = pygame.display.get_wm_info()["window"]
        except Exception as exc:
            log_exception(DesktopWindowError(f"获取窗口句柄失败: {exc}"))
            self._hwnd = None
            return

        position = self.config.get("window_position")
        if position:
            self.set_position(position[0], position[1])

        if self.config.get("transparent", False):
            self.set_transparent()

        if self.config.get("always_on_top", False):
            self.set_topmost()

        if self.config.get("start_hidden", False):
            self.hide()

    def reapply_after_resize(self, x: int, y: int) -> None:
        """运行时 pygame.display.set_mode 重设窗口尺寸后重新应用桌面属性。

        SDL 重建显示表面后窗口句柄可能变化、分层透明/置顶属性可能丢失，
        故重新获取句柄并按 desktop_config 重新设置透明/置顶，最后移动到 (x, y)。
        Game 在 set_mode 之后调用本方法，保证缩放后窗口仍透明、置顶、定位正确。
        """
        if not _IS_WINDOWS:
            return

        try:
            self._hwnd = pygame.display.get_wm_info()["window"]
        except Exception as exc:
            log_exception(DesktopWindowError(f"缩放后获取窗口句柄失败: {exc}"))
            self._hwnd = None
            return

        if self.config.get("transparent", False):
            self.set_transparent()
        if self.config.get("always_on_top", False):
            self.set_topmost()
        self.set_position(x, y)

    def set_transparent(self) -> None:
        """将窗口背景设置为透明（基于 settings.TRANSPARENT_COLOR_KEY 颜色键）。"""
        if not self.supported:
            return

        try:
            styles = win32gui.GetWindowLong(self._hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                self._hwnd, win32con.GWL_EXSTYLE, styles | win32con.WS_EX_LAYERED
            )
            color_key = win32api.RGB(*settings.TRANSPARENT_COLOR_KEY)
            win32gui.SetLayeredWindowAttributes(self._hwnd, color_key, 0, win32con.LWA_COLORKEY)
        except Exception as exc:
            log_exception(DesktopWindowError(f"设置窗口透明失败: {exc}"))

    def set_overlay_alpha(self, alpha: int) -> None:
        """把分层窗口切到统一半透明（LWA_ALPHA），使整窗都能接收鼠标点击。

        颜色键透明（LWA_COLORKEY）下，透明像素上的点击会穿透到桌面，
        全屏取点/放置时无法在空白处点选；改用统一 alpha 后整屏都可点击，
        桌面也以背景色淡淡压暗。退出遮罩时再由 set_transparent 还原颜色键。
        """
        if not self.supported:
            return

        try:
            styles = win32gui.GetWindowLong(self._hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                self._hwnd, win32con.GWL_EXSTYLE, styles | win32con.WS_EX_LAYERED
            )
            win32gui.SetLayeredWindowAttributes(self._hwnd, 0, alpha, win32con.LWA_ALPHA)
        except Exception as exc:
            log_exception(DesktopWindowError(f"设置遮罩半透明失败: {exc}"))

    def set_topmost(self) -> None:
        """将窗口设置为置顶显示，不改变窗口位置/大小，不抢占焦点。"""
        if not self.supported:
            return

        try:
            win32gui.SetWindowPos(
                self._hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
            )
        except Exception as exc:
            log_exception(DesktopWindowError(f"设置窗口置顶失败: {exc}"))

    def keep_on_top(self) -> None:
        """维持置顶状态。语义与 set_topmost 相同，供主循环周期性调用。"""
        self.set_topmost()

    def hide(self) -> None:
        """隐藏桌宠窗口（最小化到系统托盘场景使用）。"""
        if not self.supported:
            self._visible = False
            return

        try:
            win32gui.ShowWindow(self._hwnd, win32con.SW_HIDE)
            self._visible = False
        except Exception as exc:
            log_exception(DesktopWindowError(f"隐藏窗口失败: {exc}"))

    def show(self) -> None:
        """显示桌宠窗口。"""
        if not self.supported:
            self._visible = True
            return

        try:
            win32gui.ShowWindow(self._hwnd, win32con.SW_SHOWNOACTIVATE)
            self._visible = True
        except Exception as exc:
            log_exception(DesktopWindowError(f"显示窗口失败: {exc}"))

    def focus(self) -> None:
        """将窗口设为前台并获取键盘焦点（打开聊天/设置等输入窗口时调用）。

        桌宠窗口平时以不抢焦点的方式显示/置顶，打开需要键盘输入的
        窗口时需主动取得焦点，否则按键事件不会送达本窗口。
        """
        if not self.supported:
            return

        try:
            win32gui.SetForegroundWindow(self._hwnd)
        except Exception as exc:
            log_exception(DesktopWindowError(f"窗口获取焦点失败: {exc}"))

    def set_position(self, x: int, y: int) -> None:
        """将窗口移动到屏幕坐标 (x, y)（不改变大小与层级）。"""
        if not self.supported:
            return

        try:
            win32gui.SetWindowPos(
                self._hwnd,
                0, x, y, 0, 0,
                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE,
            )
        except Exception as exc:
            log_exception(DesktopWindowError(f"移动窗口失败: {exc}"))

    def get_position(self) -> Tuple[int, int]:
        """返回窗口左上角在屏幕坐标系下的位置。"""
        if not self.supported:
            return (0, 0)

        try:
            left, top, _right, _bottom = win32gui.GetWindowRect(self._hwnd)
            return (left, top)
        except Exception as exc:
            log_exception(DesktopWindowError(f"读取窗口位置失败: {exc}"))
            return (0, 0)

    def get_screen_size(self) -> Tuple[int, int]:
        """返回主屏幕分辨率（宽, 高），用于限定宠物在桌面上的漫游范围。"""
        if not _IS_WINDOWS:
            return (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)

        try:
            return (
                win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
                win32api.GetSystemMetrics(win32con.SM_CYSCREEN),
            )
        except Exception as exc:
            log_exception(DesktopWindowError(f"读取屏幕分辨率失败: {exc}"))
            return (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT)

    def get_cursor_position(self) -> Tuple[int, int]:
        """返回鼠标在屏幕坐标系下的位置，用于拖动窗口时计算位移。"""
        if not _IS_WINDOWS:
            return pygame.mouse.get_pos()

        try:
            return win32gui.GetCursorPos()
        except Exception as exc:
            log_exception(DesktopWindowError(f"读取鼠标位置失败: {exc}"))
            return (0, 0)
