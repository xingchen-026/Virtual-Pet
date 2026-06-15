"""窗口跟随控制模块。

WindowController 维护"窗口中心 = 宠物屏幕坐标"这一不变式，集中处理
桌宠窗口跟随模式下的坐标换算与窗口移动：

* 窗口跟随模式（DesktopManager 支持，Windows）：宠物固定渲染在
  窗口中心，Pet.position 表示宠物在屏幕坐标系下的位置；宠物的
  自主移动 / 拖拽统一通过移动整个窗口实现。
* 不支持时（非 Windows）：退化为"宠物在窗口内移动"，本控制器的
  窗口移动相关方法均为安全空操作。

将坐标换算与 DesktopManager 的 OS 调用集中于此，Game 不再直接
维护窗口位置 / 拖拽锚点等状态。
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from core.desktop import DesktopManager
from core.pet import Pet
from core.sprite import PetSprite


class WindowController:
    """桌宠窗口跟随宠物的坐标控制器。"""

    def __init__(
        self,
        desktop_manager: DesktopManager,
        pet: Pet,
        pet_sprite: PetSprite,
        window_size: Tuple[int, int],
    ) -> None:
        self.desktop = desktop_manager
        self.pet = pet
        self.pet_sprite = pet_sprite
        self.center = (window_size[0] // 2, window_size[1] // 2)
        self.window_pos = desktop_manager.get_position()

        # 是否处于"跟随模式"：True=窗口跟随宠物（宠物恒居中心，默认）；
        # False=窗口固定（围栏模式），宠物在固定窗口内按屏幕坐标渲染、漫游。
        self.follow = True

        # 窗口移动拖拽的起始锚点 (起始鼠标屏幕坐标, 起始窗口坐标)，
        # 为 None 表示当前不处于窗口移动拖拽中
        self._drag_anchor: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None

    @property
    def supported(self) -> bool:
        """是否拿到了有效窗口句柄（具备桌面窗口能力）。"""
        return self.desktop.supported

    @property
    def dragging_window(self) -> bool:
        """当前是否正在进行窗口移动拖拽（仅跟随模式才会移动整窗）。"""
        return self._drag_anchor is not None

    def set_geometry(
        self,
        window_size: Tuple[int, int],
        window_pos: Tuple[int, int],
        follow: bool,
    ) -> None:
        """窗口尺寸/位置/模式发生变化后同步内部状态（由 Game 缩放窗口时调用）。

        重算窗口中心、记录窗口左上角与是否跟随。不直接操作 OS，OS 侧的
        set_mode/移动由 Game 与 DesktopManager 负责。
        """
        self.center = (window_size[0] // 2, window_size[1] // 2)
        self.window_pos = window_pos
        self.follow = follow

    def initialize(self, saved_position: Optional[Sequence[int]] = None) -> None:
        """应用初始/上次保存的窗口位置，并建立宠物与窗口中心的坐标关系。

        窗口跟随模式下，将宠物精灵固定渲染在窗口中心，并把
        Pet.position 设为窗口中心对应的屏幕坐标。
        """
        if saved_position and self.desktop.supported:
            self.desktop.set_position(int(saved_position[0]), int(saved_position[1]))

        self.window_pos = self.desktop.get_position()

        if self.desktop.supported:
            self.pet_sprite.render_center = self.center
            self.pet.set_position(
                self.window_pos[0] + self.center[0],
                self.window_pos[1] + self.center[1],
            )

    def begin_drag(self) -> None:
        """开始窗口移动拖拽：记录起始锚点。

        仅在跟随模式且支持桌面窗口能力时记录；不支持的平台或围栏模式下
        保持 _drag_anchor 为 None，由调用方退化为"宠物在窗口内移动"。
        """
        if not self.desktop.supported or not self.follow:
            return
        self._drag_anchor = (
            self.desktop.get_cursor_position(),
            self.desktop.get_position(),
        )

    def update_drag(self) -> None:
        """根据鼠标在屏幕坐标系下的位移移动整个窗口，并同步宠物位置。

        同步更新 Pet.position 维持"窗口中心 = 宠物位置"的不变式，
        避免拖拽结束后窗口被 sync_to_pet() 拉回原位。
        """
        if self._drag_anchor is None:
            return

        start_cursor, start_window = self._drag_anchor
        cursor_x, cursor_y = self.desktop.get_cursor_position()
        new_x = start_window[0] + cursor_x - start_cursor[0]
        new_y = start_window[1] + cursor_y - start_cursor[1]

        self.desktop.set_position(new_x, new_y)
        self.window_pos = (new_x, new_y)
        self.pet.set_position(new_x + self.center[0], new_y + self.center[1])

    def end_drag(self) -> None:
        """结束窗口移动拖拽。"""
        self._drag_anchor = None

    def sync_to_pet(self) -> None:
        """每帧同步窗口与宠物的位置关系。

        * 跟随模式：移动整窗使窗口中心对准宠物屏幕坐标（宠物恒居中心）。
        * 围栏模式（follow=False）：窗口固定不动，改为把宠物精灵的渲染中心
          设为"宠物屏幕坐标 - 窗口左上角"，使宠物在固定窗口内按其位置呈现。
        """
        if not self.desktop.supported:
            return

        if not self.follow:
            self.pet_sprite.render_center = (
                self.pet.position[0] - self.window_pos[0],
                self.pet.position[1] - self.window_pos[1],
            )
            return

        target = (
            self.pet.position[0] - self.center[0],
            self.pet.position[1] - self.center[1],
        )
        if target != self.window_pos:
            self.desktop.set_position(*target)
            self.window_pos = target
