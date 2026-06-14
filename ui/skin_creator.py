"""创建皮肤窗口模块。

SkinCreator 是从皮肤选择窗口「创建皮肤」按钮打开的弹窗，两种制作方式：

* 精灵图：添加一张或多张含多个动作的图片，每张切成逐帧；先点中文状态标签，
  再左键点帧把该状态贴到帧上（右键点帧取消），同一状态的帧按顺序成为动画。
* 按状态：为各动画状态分别选择图片。

并提供：

* 一键镜像（每张精灵图可单独「左右翻转」校正源图朝向，素材约定朝右）。
* 一键抠图（自动取角落背景色 / 选色 / 点源图取色）。
* 实时播放预览：可指定播放哪个状态；开「镜像预览」时先播放朝右再播放朝左。
* 播放速度：预览下方的拖拉条 + 数值框调节当前预览状态的速度。

本窗口只负责表单的渲染与交互；选择文件/颜色用 utils.dialogs 弹系统对话框，
实际皮肤构建由 Game.create_skin -> core.skin_builder 完成（经 on_create 回调）。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from config import settings
from ui import theme
from utils import dialogs

PADDING = 14
TITLE_HEIGHT = 26
ROW_HEIGHT = 30
FIELD_HEIGHT = 26
BUTTON_HEIGHT = 30
LIST_ROW_HEIGHT = 30
CHIP_H = 24

# 速度调节范围（秒/帧）
SPEED_MIN = 0.04
SPEED_MAX = 1.0

_ACTIVE_BG = (90, 140, 220)
_ACTIVE_TEXT = (255, 255, 255)


def _cn(state: str) -> str:
    """状态英文 key -> 中文显示名。"""
    return settings.STATE_DISPLAY_NAMES.get(state, state)


class SkinCreator:
    """创建皮肤弹窗。"""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect) -> None:
        self.font = font
        self.rect = rect
        self.visible = False

        self.states: List[str] = list(settings.ANIMATION_FOLDERS.keys())
        self._reset()

        self._hit: Dict[str, pygame.Rect] = {}             # 固定控件命中区（窗口坐标）
        self._row_hit: List[Tuple[pygame.Rect, str]] = []  # 列表内命中区 (rect, action)
        self._list_rect = pygame.Rect(0, 0, 0, 0)

    def _reset(self) -> None:
        self.name = ""
        self.mode = "sheet"            # "sheet" | "states"
        self.chroma_color: Optional[Tuple[int, int, int]] = None  # 按状态模式的全局透明色
        # 精灵图：多张，每张 {path,mirror,chroma_color,thumbs,frame_states}
        self.sheets: List[dict] = []
        self._focused_sheet = 0
        self._assign_state: Optional[str] = None   # 当前要贴的标签（先点标签再点帧）
        self.state_paths: Dict[str, str] = {}
        self.speeds: Dict[str, float] = {
            s: settings.ANIMATION_FRAME_DURATIONS[s] for s in self.states
        }
        self.scroll = 0
        self.status = ""
        self._name_focus = False
        self._highlight_states: set = set()        # 补充模式高亮缺失状态

        # 点图取色
        self._preview_surface = None
        self._preview_rect = pygame.Rect(0, 0, 0, 0)

        # 实时播放
        self._dirty = True
        self._result_frames: Dict[str, list] = {}
        self._play_select: Optional[str] = None    # 指定播放的状态（None=第一个有帧的）
        self._preview_mirror = True                # 开：先右后左
        self._mirror_phase = 0                     # 0=右 1=左
        self._frame_idx = 0
        self._frame_timer = 0.0
        self._preview_err = ""

        # 速度滑块/数值框
        self._slider_rect = pygame.Rect(0, 0, 0, 0)
        self._slider_drag = False
        self._speed_focus = False
        self._speed_text = ""        # 数值框编辑缓冲（毫秒字符串），避免逐键钳制串改
        self._max_scroll = 0

    def open(self, name: str = "", mode: str = "sheet", highlight_states=None) -> None:
        """打开。补充已有皮肤时传 name=皮肤名、mode='states'、highlight_states=缺失状态。"""
        self.visible = True
        self._reset()
        self.name = name
        self.mode = mode if mode in ("sheet", "states") else "sheet"
        self._highlight_states = set(highlight_states or [])
        pygame.key.start_text_input()

    def close(self) -> None:
        self.visible = False
        pygame.key.stop_text_input()

    def set_status(self, text: str) -> None:
        self.status = text

    # ----- 事件 -----

    def handle_event(self, event: pygame.event.Event) -> Optional[tuple]:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return ("close", None)
            if self._name_focus and event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif self._speed_focus and event.key == pygame.K_BACKSPACE:
                self._speed_text_backspace()
            return None

        if event.type == pygame.TEXTINPUT:
            if self._name_focus and len(self.name) < 40:
                self.name += event.text
            elif self._speed_focus and event.text.isdigit():
                self._speed_text_input(event.text)
            return None

        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self._max_scroll, self.scroll - event.y * LIST_ROW_HEIGHT))
            return None

        if event.type == pygame.MOUSEMOTION and self._slider_drag:
            self._slider_set_by_x(event.pos[0])
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._slider_drag = False
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_left(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._handle_right(event.pos)
            return None

        return None

    def _handle_left(self, pos) -> Optional[tuple]:
        self._name_focus = False
        self._speed_focus = False

        # 点源图取色
        if self._preview_surface is not None and self._preview_rect.collidepoint(pos):
            self._sample_color(pos)
            return None

        # 速度滑块
        if self._slider_rect.collidepoint(pos):
            self._slider_drag = True
            self._slider_set_by_x(pos[0])
            return None

        for name, rect in self._hit.items():
            if rect.collidepoint(pos):
                return self._on_control(name)

        if self._list_rect.collidepoint(pos):
            for rect, action in self._row_hit:
                if rect.collidepoint(pos):
                    self._on_row_action(action)
                    return None
        return None

    def _handle_right(self, pos) -> None:
        # 右键点帧：取消该帧的状态分配（设为跳过）
        if self._list_rect.collidepoint(pos):
            for rect, action in self._row_hit:
                if action.startswith("frame:") and rect.collidepoint(pos):
                    si, fi = (int(x) for x in action.split(":", 1)[1].split(","))
                    self.sheets[si]["frame_states"][fi] = "skip"
                    self._dirty = True
                    return

    def _on_control(self, name: str) -> Optional[tuple]:
        if name == "name":
            self._name_focus = True
        elif name == "mode_sheet":
            self.mode = "sheet"
            self._dirty = True
        elif name == "mode_states":
            self.mode = "states"
            self._dirty = True
        elif name == "chroma_auto":
            self._set_chroma(None)
        elif name == "chroma_pick":
            color = dialogs.ask_color()
            if color is not None:
                self._set_chroma(color)
        elif name == "sheet_add":
            path = dialogs.ask_open_image("添加精灵图")
            if path:
                self._add_sheet(path)
        elif name == "speed_box":
            self._speed_focus = True
            state = self._active_play_state()
            self._speed_text = str(int(round(self.speeds[state] * 1000))) if state else ""
        elif name == "preview_mirror":
            self._preview_mirror = not self._preview_mirror
            self._mirror_phase = 0
        elif name.startswith("assign:"):
            state = name.split(":", 1)[1]
            self._assign_state = None if self._assign_state == state else state
        elif name.startswith("play:"):
            self._play_select = name.split(":", 1)[1]
            self._frame_idx = 0
            self._mirror_phase = 0
        elif name == "cancel":
            self.close()
            return ("close", None)
        elif name == "generate":
            return ("generate", self.config())
        return None

    def _on_row_action(self, action: str) -> None:
        kind, key = action.split(":", 1)
        if kind == "frame":
            # 左键点帧：贴上当前选中的标签（未选标签则提示）
            si, fi = (int(x) for x in key.split(","))
            self._focused_sheet = si
            if self._assign_state is None:
                self.status = "请先在上方点选一个状态标签，再点帧"
            else:
                self.sheets[si]["frame_states"][fi] = self._assign_state
                self.status = ""
                self._dirty = True
        elif kind == "smirror":
            sheet = self.sheets[int(key)]
            sheet["mirror"] = not sheet.get("mirror", False)
            self._focused_sheet = int(key)
            self._dirty = True
        elif kind == "sremove":
            si = int(key)
            if 0 <= si < len(self.sheets):
                self.sheets.pop(si)
                self._focused_sheet = max(0, min(self._focused_sheet, len(self.sheets) - 1))
                self._refresh_focus_preview()
                self._dirty = True
        elif kind == "sfocus":
            self._focused_sheet = int(key)
            self._refresh_focus_preview()
        elif kind == "pick":
            path = dialogs.ask_open_image(f"选择 {_cn(key)} 图片")
            if path:
                self.state_paths[key] = path
                self._load_preview(path)
                self._dirty = True

    # ----- 配置 -----

    def config(self) -> dict:
        return {
            "name": self.name.strip(),
            "mode": self.mode,
            "chroma_color": self.chroma_color,
            "sheets": [
                {"path": s["path"], "mirror": s.get("mirror", False),
                 "chroma_color": s.get("chroma_color"), "frame_states": list(s["frame_states"])}
                for s in self.sheets
            ],
            "state_paths": dict(self.state_paths),
            "speeds": dict(self.speeds),
        }

    # ----- 精灵图处理 -----

    def _add_sheet(self, path: str) -> None:
        sheet = {"path": path, "mirror": False, "chroma_color": None,
                 "thumbs": [], "frame_states": []}
        self.sheets.append(sheet)
        self._focused_sheet = len(self.sheets) - 1
        self._slice_sheet(sheet)
        self._load_preview(path)
        self._dirty = True

    def _set_chroma(self, color) -> None:
        if self.mode == "sheet" and self.sheets:
            self.sheets[self._focused_sheet]["chroma_color"] = color
            self._slice_sheet(self.sheets[self._focused_sheet])
        else:
            self.chroma_color = color
        self._dirty = True

    def _refresh_focus_preview(self) -> None:
        if self.sheets and 0 <= self._focused_sheet < len(self.sheets):
            self._load_preview(self.sheets[self._focused_sheet]["path"])
        else:
            self._preview_surface = None

    def _slice_sheet(self, sheet: dict) -> None:
        try:
            from PIL import Image
            from core import skin_builder
            from utils import spritesheet

            img = Image.open(sheet["path"])
            bg = sheet.get("chroma_color") or spritesheet.detect_background_color(img)
            alpha = spritesheet.build_alpha_mask(
                img, bg, spritesheet.DEFAULT_TOLERANCE, spritesheet.DEFAULT_FEATHER
            )
            frames = skin_builder.slice_frames(img, alpha)
        except Exception:
            frames = []
        sheet["thumbs"] = [self._pil_to_surface(f) for f in frames]
        old = sheet.get("frame_states") or []
        sheet["frame_states"] = [old[i] if i < len(old) else "skip" for i in range(len(frames))]

    # ----- 实时预览 -----

    def update(self, dt: float) -> None:
        if self._dirty:
            self._rebuild_preview()
            self._dirty = False
        state = self._active_play_state()
        if state is None:
            return
        frames = self._result_frames.get(state, [])
        if not frames:
            return
        self._frame_timer += dt
        duration = max(SPEED_MIN, self.speeds.get(state, 0.15))
        if self._frame_timer >= duration:
            self._frame_timer -= duration
            self._frame_idx += 1
            if self._frame_idx >= len(frames):
                self._frame_idx = 0
                if self._preview_mirror:
                    self._mirror_phase ^= 1  # 一轮右、一轮左

    def _active_play_state(self) -> Optional[str]:
        avail = [s for s in self.states if self._result_frames.get(s)]
        if not avail:
            return None
        if self._play_select in avail:
            return self._play_select
        return avail[0]

    def _rebuild_preview(self) -> None:
        self._result_frames = {}
        self._preview_err = ""
        self._frame_idx = 0
        self._frame_timer = 0.0
        try:
            from core import skin_builder
            grouped = skin_builder.preview_grouped(self.config())
        except Exception as exc:
            self._preview_err = str(exc)
            return
        for state, frames in grouped.items():
            surfaces = [self._pil_to_surface(f) for f in frames]
            if surfaces:
                self._result_frames[state] = surfaces

    @staticmethod
    def _pil_to_surface(image) -> pygame.Surface:
        return pygame.image.fromstring(image.tobytes(), image.size, "RGBA").convert_alpha()

    def _current_result_frame(self):
        state = self._active_play_state()
        if state is None:
            return None, None
        frames = self._result_frames.get(state, [])
        if not frames:
            return None, None
        frame = frames[self._frame_idx % len(frames)]
        if self._preview_mirror and self._mirror_phase == 1:
            frame = pygame.transform.flip(frame, True, False)
        return state, frame

    def _load_preview(self, path: str) -> None:
        try:
            self._preview_surface = pygame.image.load(path).convert_alpha()
        except Exception:
            self._preview_surface = None

    def _sample_color(self, pos) -> None:
        rel_x = (pos[0] - self._preview_rect.x) / max(1, self._preview_rect.width)
        rel_y = (pos[1] - self._preview_rect.y) / max(1, self._preview_rect.height)
        w, h = self._preview_surface.get_size()
        x = max(0, min(w - 1, int(rel_x * w)))
        y = max(0, min(h - 1, int(rel_y * h)))
        c = self._preview_surface.get_at((x, y))
        self._set_chroma((c[0], c[1], c[2]))

    # ----- 速度滑块/数值框 -----

    def _slider_set_by_x(self, x: int) -> None:
        state = self._active_play_state()
        if state is None or self._slider_rect.width == 0:
            return
        ratio = (x - self._slider_rect.x) / self._slider_rect.width
        ratio = max(0.0, min(1.0, ratio))
        self.speeds[state] = round(SPEED_MIN + ratio * (SPEED_MAX - SPEED_MIN), 3)

    def _speed_text_input(self, ch: str) -> None:
        if len(self._speed_text) < 5:
            self._speed_text += ch
            self._apply_speed_text()

    def _speed_text_backspace(self) -> None:
        self._speed_text = self._speed_text[:-1]
        self._apply_speed_text()

    def _apply_speed_text(self) -> None:
        """把数值框缓冲（毫秒）应用为当前播放状态的速度（钳制到范围）。"""
        state = self._active_play_state()
        if state is None or not self._speed_text:
            return
        ms = int(self._speed_text)
        self.speeds[state] = max(SPEED_MIN, min(SPEED_MAX, ms / 1000.0))

    # ----- 渲染 -----

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        self._hit = {}
        self._row_hit = []
        panel = theme.make_panel(self.rect.size)

        title = self.font.render("创建皮肤 (Esc 取消)", True, theme.TITLE_COLOR)
        panel.blit(title, (PADDING, PADDING))
        pygame.draw.line(panel, theme.BORDER_COLOR,
                         (PADDING, TITLE_HEIGHT + 4), (self.rect.width - PADDING, TITLE_HEIGHT + 4))

        y = TITLE_HEIGHT + 12
        y = self._draw_name_row(panel, y)
        y = self._draw_mode_row(panel, y)
        y = self._draw_chroma_row(panel, y)
        if self.mode == "sheet":
            y = self._draw_sheet_add_row(panel, y)

        y, preview_local = self._draw_preview(panel, y)
        y = self._draw_play_controls(panel, y)
        y = self._draw_speed_row(panel, y)
        if self.mode == "sheet":
            y = self._draw_assign_labels(panel, y)

        list_top = y + 2
        list_bottom = self.rect.height - PADDING - BUTTON_HEIGHT - 8
        self._draw_list(panel, list_top, list_bottom)
        self._draw_bottom(panel)

        surface.blit(panel, self.rect.topleft)
        ox, oy = self.rect.x, self.rect.y
        self._hit = {k: r.move(ox, oy) for k, r in self._hit.items()}
        self._row_hit = [(r.move(ox, oy), a) for r, a in self._row_hit]
        self._preview_rect = preview_local.move(ox, oy) if preview_local else pygame.Rect(0, 0, 0, 0)
        self._slider_rect = self._slider_rect.move(ox, oy) if self._slider_rect.width else self._slider_rect
        self._list_rect = pygame.Rect(ox + PADDING, oy + list_top,
                                      self.rect.width - 2 * PADDING, list_bottom - list_top)

    def _label(self, panel, text, x, y, color=None):
        panel.blit(self.font.render(text, True, color or theme.LABEL_COLOR), (x, y))

    def _button(self, panel, rect, text, name, active=False):
        bg = _ACTIVE_BG if active else theme.BUTTON_BG_COLOR
        fg = _ACTIVE_TEXT if active else theme.BUTTON_TEXT_COLOR
        pygame.draw.rect(panel, bg, rect, border_radius=5)
        pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=5)
        glyph = self.font.render(text, True, fg)
        panel.blit(glyph, glyph.get_rect(center=rect.center))
        if name:
            self._hit[name] = rect

    def _draw_name_row(self, panel, y) -> int:
        self._label(panel, "名称", PADDING, y + 4)
        rect = pygame.Rect(PADDING + 48, y, self.rect.width - PADDING - 48 - PADDING, FIELD_HEIGHT)
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, rect, border_radius=4)
        pygame.draw.rect(panel, theme.FIELD_FOCUS_BORDER if self._name_focus else theme.BORDER_COLOR,
                         rect, 1, border_radius=4)
        text = self.name or "（点此输入皮肤名）"
        panel.blit(self.font.render(text, True, theme.TEXT_COLOR if self.name else theme.PLACEHOLDER_COLOR),
                   (rect.x + 6, rect.y + 4))
        self._hit["name"] = rect
        return y + ROW_HEIGHT + 2

    def _draw_mode_row(self, panel, y) -> int:
        self._label(panel, "方式", PADDING, y + 4)
        bw = 92
        self._button(panel, pygame.Rect(PADDING + 48, y, bw, FIELD_HEIGHT),
                     "精灵图", "mode_sheet", active=self.mode == "sheet")
        self._button(panel, pygame.Rect(PADDING + 48 + bw + 8, y, bw, FIELD_HEIGHT),
                     "按状态", "mode_states", active=self.mode == "states")
        return y + ROW_HEIGHT + 2

    def _draw_chroma_row(self, panel, y) -> int:
        self._label(panel, "透明色", PADDING, y + 4)
        swatch = pygame.Rect(PADDING + 54, y, 26, FIELD_HEIGHT)
        chroma = self.sheets[self._focused_sheet].get("chroma_color") \
            if (self.mode == "sheet" and self.sheets) else self.chroma_color
        if chroma is None:
            pygame.draw.rect(panel, theme.FIELD_BG_COLOR, swatch, border_radius=4)
            panel.blit(self.font.render("自动", True, theme.PLACEHOLDER_COLOR), (swatch.x + 1, swatch.y + 4))
        else:
            pygame.draw.rect(panel, chroma, swatch, border_radius=4)
        pygame.draw.rect(panel, theme.BORDER_COLOR, swatch, 1, border_radius=4)
        self._button(panel, pygame.Rect(swatch.right + 6, y, 50, FIELD_HEIGHT), "选色", "chroma_pick")
        self._button(panel, pygame.Rect(swatch.right + 62, y, 50, FIELD_HEIGHT), "自动", "chroma_auto")
        return y + ROW_HEIGHT + 2

    def _draw_sheet_add_row(self, panel, y) -> int:
        self._button(panel, pygame.Rect(PADDING, y, 110, FIELD_HEIGHT), "添加精灵图", "sheet_add")
        info = f"已添加 {len(self.sheets)} 张" if self.sheets else "可添加多张，逐帧贴标签"
        panel.blit(self.font.render(info, True, theme.PLACEHOLDER_COLOR), (PADDING + 120, y + 4))
        return y + ROW_HEIGHT + 2

    def _draw_preview(self, panel, y):
        box_h = 96
        gap = 10
        half = (self.rect.width - 2 * PADDING - gap) // 2
        left = pygame.Rect(PADDING, y, half, box_h)
        right = pygame.Rect(PADDING + half + gap, y, half, box_h)
        source_local = self._draw_source_box(panel, left)
        self._draw_result_box(panel, right)
        return y + box_h + 4, source_local

    def _draw_source_box(self, panel, box):
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, box, border_radius=4)
        pygame.draw.rect(panel, theme.BORDER_COLOR, box, 1, border_radius=4)
        if self._preview_surface is None:
            panel.blit(self.font.render("选图后点此取透明色", True, theme.PLACEHOLDER_COLOR),
                       self.font.render("选图后点此取透明色", True, theme.PLACEHOLDER_COLOR).get_rect(center=box.center))
            return None
        w, h = self._preview_surface.get_size()
        scale = min((box.width - 8) / w, (box.height - 18) / h)
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        rect = pygame.Rect(box.centerx - dw // 2, box.y + 4, dw, dh)
        panel.blit(pygame.transform.smoothscale(self._preview_surface, (dw, dh)), rect)
        panel.blit(self.font.render("点击取透明色", True, theme.PLACEHOLDER_COLOR),
                   (box.x + 4, box.bottom - 18))
        return rect

    def _draw_result_box(self, panel, box):
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, box, border_radius=4)
        pygame.draw.rect(panel, theme.BORDER_COLOR, box, 1, border_radius=4)
        state, frame = self._current_result_frame()
        if frame is not None:
            scale = min((box.width - 8) / frame.get_width(), (box.height - 18) / frame.get_height())
            disp = (max(1, int(frame.get_width() * scale)), max(1, int(frame.get_height() * scale)))
            panel.blit(pygame.transform.smoothscale(frame, disp),
                       pygame.transform.smoothscale(frame, disp).get_rect(midtop=(box.centerx, box.y + 4)))
            facing = "→" if self._mirror_phase == 0 else "←"
            panel.blit(self.font.render(f"预览：{_cn(state)} {facing}", True, theme.PLACEHOLDER_COLOR),
                       (box.x + 4, box.bottom - 18))
        else:
            msg = self._preview_err or "选好后这里实时播放"
            panel.blit(self.font.render(self._clip(msg, box.width - 8), True, theme.PLACEHOLDER_COLOR),
                       self.font.render(self._clip(msg, box.width - 8), True, theme.PLACEHOLDER_COLOR).get_rect(center=box.center))

    def _draw_play_controls(self, panel, y) -> int:
        self._label(panel, "播放", PADDING, y + 3)
        x = PADDING + 40
        for state in self.states:
            if not self._result_frames.get(state):
                continue
            label = _cn(state)
            w = self.font.size(label)[0] + 12
            if x + w > self.rect.width - PADDING - 90:
                break  # 放不下就省略（一般有帧的状态不多）
            rect = pygame.Rect(x, y, w, CHIP_H)
            self._button(panel, rect, label, f"play:{state}",
                         active=self._active_play_state() == state)
            x += w + 4
        # 镜像预览开关（开=先右后左）
        self._button(panel, pygame.Rect(self.rect.width - PADDING - 84, y, 84, CHIP_H),
                     "镜像预览:" + ("开" if self._preview_mirror else "关"),
                     "preview_mirror", active=self._preview_mirror)
        return y + CHIP_H + 4

    def _draw_speed_row(self, panel, y) -> int:
        state = self._active_play_state()
        self._label(panel, "速度", PADDING, y + 3)
        track = pygame.Rect(PADDING + 40, y + CHIP_H // 2 - 2, self.rect.width - 2 * PADDING - 40 - 86, 4)
        pygame.draw.rect(panel, theme.BORDER_COLOR, track, border_radius=2)
        ms = int(round(self.speeds.get(state, 0.15) * 1000)) if state else 0
        if state is not None:
            ratio = (self.speeds[state] - SPEED_MIN) / (SPEED_MAX - SPEED_MIN)
            knob_x = int(track.x + ratio * track.width)
            pygame.draw.circle(panel, _ACTIVE_BG, (knob_x, track.centery), 7)
        # 滑块命中区（整条轨道加高，便于点击）；保存为面板局部，draw 末尾转窗口坐标
        self._slider_rect = pygame.Rect(track.x, y, track.width, CHIP_H)
        # 数值框
        box = pygame.Rect(self.rect.width - PADDING - 80, y, 80, CHIP_H)
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, box, border_radius=4)
        pygame.draw.rect(panel, theme.FIELD_FOCUS_BORDER if self._speed_focus else theme.BORDER_COLOR,
                         box, 1, border_radius=4)
        shown = f"{self._speed_text}ms" if self._speed_focus else f"{ms}ms"
        panel.blit(self.font.render(shown, True, theme.TEXT_COLOR),
                   self.font.render(shown, True, theme.TEXT_COLOR).get_rect(center=box.center))
        self._hit["speed_box"] = box
        return y + CHIP_H + 4

    def _draw_assign_labels(self, panel, y) -> int:
        """贴标签区：先点中文状态标签，再左键点帧贴上（右键点帧取消）。"""
        self._label(panel, "贴标签", PADDING, y + 3)
        x = PADDING + 52
        row_y = y
        for state in self.states:
            label = _cn(state)
            w = self.font.size(label)[0] + 12
            if x + w > self.rect.width - PADDING:
                x = PADDING + 52
                row_y += CHIP_H + 4
            rect = pygame.Rect(x, row_y, w, CHIP_H)
            self._button(panel, rect, label, f"assign:{state}", active=self._assign_state == state)
            x += w + 4
        return row_y + CHIP_H + 4

    def _draw_list(self, panel, top, bottom) -> None:
        clip = panel.get_clip()
        panel.set_clip(pygame.Rect(PADDING, top, self.rect.width - 2 * PADDING, bottom - top))
        if self.mode == "sheet":
            content_h = self._draw_sheets(panel, top, bottom)
        else:
            content_h = len(self.states) * LIST_ROW_HEIGHT
            y = top - self.scroll
            for state in self.states:
                if y + LIST_ROW_HEIGHT >= top and y <= bottom:
                    self._draw_state_upload_row(panel, y, state)
                y += LIST_ROW_HEIGHT
        panel.set_clip(clip)
        self._max_scroll = max(0, content_h - (bottom - top))
        self.scroll = min(self.scroll, self._max_scroll)

    def _draw_sheets(self, panel, top, bottom) -> int:
        thumb = 36
        cell_w, cell_h = thumb + 8, thumb + 16
        cols = max(1, (self.rect.width - 2 * PADDING) // cell_w)
        y = top - self.scroll
        start = y
        for si, sheet in enumerate(self.sheets):
            if top - 30 <= y <= bottom:
                focused = si == self._focused_sheet
                fname = sheet["path"].rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                title = f"图{si + 1} {fname}" + ("（聚焦）" if focused else "")
                color = theme.FIELD_FOCUS_BORDER if focused else theme.LABEL_COLOR
                label = self.font.render(self._clip(title, self.rect.width - 2 * PADDING - 120), True, color)
                panel.blit(label, (PADDING, y + 4))
                self._row_hit.append((pygame.Rect(PADDING, y, label.get_width(), FIELD_HEIGHT), f"sfocus:{si}"))
                self._row_button(panel, pygame.Rect(self.rect.width - PADDING - 110, y, 56, FIELD_HEIGHT),
                                 "翻转:" + ("开" if sheet.get("mirror") else "关"), f"smirror:{si}")
                self._row_button(panel, pygame.Rect(self.rect.width - PADDING - 48, y, 48, FIELD_HEIGHT),
                                 "删除", f"sremove:{si}")
            y += FIELD_HEIGHT + 4
            for fi, surf in enumerate(sheet["thumbs"]):
                cx = PADDING + (fi % cols) * cell_w
                cy = y + (fi // cols) * cell_h
                if top - cell_h <= cy <= bottom:
                    self._draw_frame_cell(panel, cx, cy, thumb, sheet, si, fi, surf)
            rows = (len(sheet["thumbs"]) + cols - 1) // cols
            y += rows * cell_h + 8
        return max(0, y - start)

    def _draw_frame_cell(self, panel, cx, cy, thumb, sheet, si, fi, surf) -> None:
        rect = pygame.Rect(cx, cy, thumb, thumb)
        state = sheet["frame_states"][fi]
        assigned = state != "skip"
        if surf is not None:
            panel.blit(pygame.transform.smoothscale(surf, (thumb, thumb)), rect)
        pygame.draw.rect(panel, theme.FIELD_FOCUS_BORDER if assigned else theme.BORDER_COLOR,
                         rect, 2 if assigned else 1, border_radius=3)
        tag = _cn(state) if assigned else "—"
        panel.blit(self.font.render(tag, True, theme.BUTTON_TEXT_COLOR if assigned else theme.PLACEHOLDER_COLOR),
                   (cx, cy + thumb))
        self._row_hit.append((rect, f"frame:{si},{fi}"))

    def _draw_state_upload_row(self, panel, y, state) -> None:
        color = theme.STATUS_FAIL_COLOR if state in self._highlight_states else theme.LABEL_COLOR
        panel.blit(self.font.render(_cn(state), True, color), (PADDING, y + 4))
        pick = pygame.Rect(PADDING + 72, y, 50, FIELD_HEIGHT)
        self._row_button(panel, pick, "选图", f"pick:{state}")
        path = self.state_paths.get(state)
        label = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] if path else "—"
        panel.blit(self.font.render(self._clip(label, self.rect.width - PADDING - (pick.right + 6)),
                                    True, theme.TEXT_COLOR), (pick.right + 6, y + 4))

    def _row_button(self, panel, rect, text, action) -> None:
        pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=4)
        pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=4)
        glyph = self.font.render(text, True, theme.BUTTON_TEXT_COLOR)
        panel.blit(glyph, glyph.get_rect(center=rect.center))
        self._row_hit.append((rect, action))

    def _draw_bottom(self, panel) -> None:
        y = self.rect.height - PADDING - BUTTON_HEIGHT
        self._button(panel, pygame.Rect(PADDING, y, 110, BUTTON_HEIGHT), "生成并启用", "generate")
        self._button(panel, pygame.Rect(PADDING + 120, y, 70, BUTTON_HEIGHT), "取消", "cancel")
        if self.status:
            panel.blit(self.font.render(self._clip(self.status, self.rect.width - 210),
                                        True, theme.STATUS_FAIL_COLOR), (PADDING + 200, y + 6))

    def _clip(self, text: str, max_width: int) -> str:
        if self.font.size(text)[0] <= max_width:
            return text
        while text and self.font.size(text + "…")[0] > max_width:
            text = text[:-1]
        return text + "…"
