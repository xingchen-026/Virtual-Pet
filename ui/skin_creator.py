"""创建皮肤窗口模块。

SkinCreator 是从皮肤选择窗口「创建皮肤」按钮打开的弹窗，提供两种制作方式：

* 精灵图：选择一张含多个动作的图片，自动切分（按行映射到动画状态）。
* 按状态：为各动画状态分别选择图片。

并提供：

* 一键镜像：源图朝左时开启，使动画统一朝右（素材约定朝右）。
* 一键抠图：把指定颜色改为透明（默认自动取角落背景色，或点「选色」指定）。
* 逐动画播放速度：每个状态可单独调快/调慢。

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

# 速度调节范围与步长（秒/帧）
SPEED_MIN = 0.04
SPEED_MAX = 1.0
SPEED_STEP = 0.02

_ACTIVE_BG = (90, 140, 220)
_ACTIVE_TEXT = (255, 255, 255)


class SkinCreator:
    """创建皮肤弹窗：精灵图 / 按状态两种方式 + 镜像 / 抠图 / 逐动画速度。"""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect) -> None:
        self.font = font
        self.rect = rect
        self.visible = False

        self.states: List[str] = list(settings.ANIMATION_FOLDERS.keys())
        self._reset()

        self._hit: Dict[str, pygame.Rect] = {}      # 固定控件命中区（窗口坐标）
        self._row_hit: List[Tuple[pygame.Rect, str]] = []  # 列表内控件命中区 (rect, action)
        self._list_rect = pygame.Rect(0, 0, 0, 0)   # 滚动列表可视区（窗口坐标）

    def _reset(self) -> None:
        self.name = ""
        self.mode = "sheet"            # "sheet" | "states"
        self.mirror = False
        self.chroma_color: Optional[Tuple[int, int, int]] = None  # None=自动（按状态模式全局）
        # 精灵图模式：多张精灵图，每张逐帧分配状态
        # sheet = {"path","mirror","chroma_color","frames"(PIL),"thumbs"(Surface),"frame_states"}
        self.sheets: List[dict] = []
        self._focused_sheet = 0
        self.state_paths: Dict[str, str] = {}
        self.speeds: Dict[str, float] = {
            s: settings.ANIMATION_FRAME_DURATIONS[s] for s in self.states
        }
        self.scroll = 0
        self.status = ""
        self._name_focus = False

        # 补充模式：从皮肤选择窗口「补充动画」进入时高亮缺失状态
        self._highlight_states: set = set()

        # 点图取色：预览当前所选图片，点击预览像素取该颜色为透明色
        self._preview_surface = None              # 原始分辨率 Surface（用于采样）
        self._preview_rect = pygame.Rect(0, 0, 0, 0)  # 预览中图片实际显示区（窗口坐标）

        # 实时播放预览：把当前配置处理成各状态帧并循环播放
        self._dirty = True                        # 配置变化后需重建预览帧
        self._result_frames = {}                  # state -> [pygame.Surface]
        self._play_states = []                    # 有帧的状态顺序
        self._play_idx = 0
        self._frame_idx = 0
        self._frame_timer = 0.0
        self._preview_err = ""

    def open(self, name: str = "", mode: str = "sheet", highlight_states=None) -> None:
        """打开创建窗口。补充已有皮肤时传 name=皮肤名、mode='states'、
        highlight_states=缺失状态集合（高亮提示用户优先补充）。"""
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
        """返回 ("generate", config) / ("close", None) / None。"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return ("close", None)
            if self._name_focus:
                if event.key == pygame.K_BACKSPACE:
                    self.name = self.name[:-1]
            return None

        if event.type == pygame.TEXTINPUT and self._name_focus:
            if len(self.name) < 40:
                self.name += event.text
            return None

        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll - event.y * LIST_ROW_HEIGHT)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)

        return None

    def _handle_click(self, pos) -> Optional[tuple]:
        self._name_focus = False

        # 点图取色：点击预览图上的像素，取该颜色为透明色
        if self._preview_surface is not None and self._preview_rect.collidepoint(pos):
            self._sample_color(pos)
            return None

        for name, rect in self._hit.items():
            if not rect.collidepoint(pos):
                continue
            return self._on_control(name)

        # 列表内控件（仅在可视区内响应）
        if self._list_rect.collidepoint(pos):
            for rect, action in self._row_hit:
                if rect.collidepoint(pos):
                    self._on_row_action(action)
                    return None

        return None

    def _on_control(self, name: str) -> Optional[tuple]:
        if name == "name":
            self._name_focus = True
        elif name == "mode_sheet":
            self.mode = "sheet"
            self._dirty = True
        elif name == "mode_states":
            self.mode = "states"
            self._dirty = True
        elif name == "mirror":
            self.mirror = not self.mirror
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
        elif name == "cancel":
            self.close()
            return ("close", None)
        elif name == "generate":
            return ("generate", self.config())
        return None

    def _on_row_action(self, action: str) -> None:
        kind, key = action.split(":", 1)
        if kind == "pick":
            path = dialogs.ask_open_image(f"选择 {key} 图片")
            if path:
                self.state_paths[key] = path
                self._load_preview(path)
                self._dirty = True
        elif kind == "slower":
            self.speeds[key] = min(SPEED_MAX, round(self.speeds[key] + SPEED_STEP, 3))
        elif kind == "faster":
            self.speeds[key] = max(SPEED_MIN, round(self.speeds[key] - SPEED_STEP, 3))
        elif kind == "frame":
            # 精灵图逐帧循环切换状态（skip -> 各状态 -> skip），实现「选一部分帧作为某状态」
            si, fi = (int(x) for x in key.split(","))
            sheet = self.sheets[si]
            options = ["skip"] + self.states
            current = sheet["frame_states"][fi]
            cur_i = options.index(current) if current in options else 0
            sheet["frame_states"][fi] = options[(cur_i + 1) % len(options)]
            self._focused_sheet = si
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

    def update(self, dt: float) -> None:
        """逐帧推进实时预览动画（配置变化时先重建帧）。"""
        if self._dirty:
            self._rebuild_preview()
            self._dirty = False

        if not self._play_states:
            return

        state = self._play_states[self._play_idx % len(self._play_states)]
        frames = self._result_frames.get(state, [])
        if not frames:
            return

        self._frame_timer += dt
        duration = max(0.02, self.speeds.get(state, 0.15))
        if self._frame_timer >= duration:
            self._frame_timer -= duration
            self._frame_idx += 1
            if self._frame_idx >= len(frames):
                # 当前状态播完一轮，切换到下一个有帧的状态
                self._frame_idx = 0
                self._play_idx = (self._play_idx + 1) % len(self._play_states)

    def _rebuild_preview(self) -> None:
        """按当前配置在内存中处理出各状态帧，转为 pygame Surface 供播放。"""
        self._result_frames = {}
        self._play_states = []
        self._preview_err = ""
        self._play_idx = self._frame_idx = 0
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
                self._play_states.append(state)

    @staticmethod
    def _pil_to_surface(image) -> pygame.Surface:
        return pygame.image.fromstring(image.tobytes(), image.size, "RGBA").convert_alpha()

    def _current_result_frame(self):
        """返回 (当前状态名, 当前帧 Surface) 或 (None, None)。"""
        if not self._play_states:
            return None, None
        state = self._play_states[self._play_idx % len(self._play_states)]
        frames = self._result_frames.get(state, [])
        if not frames:
            return None, None
        return state, frames[self._frame_idx % len(frames)]

    def _load_preview(self, path: str) -> None:
        """加载所选图片为预览（原始分辨率 Surface，供点图取色采样）。"""
        try:
            self._preview_surface = pygame.image.load(path).convert_alpha()
        except Exception:
            self._preview_surface = None

    def _add_sheet(self, path: str) -> None:
        """添加一张精灵图：切成逐帧，默认全部「跳过」，等待用户逐帧分配状态。"""
        sheet = {"path": path, "mirror": False, "chroma_color": None,
                 "frames": [], "thumbs": [], "frame_states": []}
        self.sheets.append(sheet)
        self._focused_sheet = len(self.sheets) - 1
        self._slice_sheet(sheet)
        self._load_preview(path)
        self._dirty = True

    def _set_chroma(self, color) -> None:
        """设置透明色：精灵图模式作用于当前聚焦的那张图，按状态模式为全局。"""
        if self.mode == "sheet" and self.sheets:
            self.sheets[self._focused_sheet]["chroma_color"] = color
            self._slice_sheet(self.sheets[self._focused_sheet])
        else:
            self.chroma_color = color
        self._dirty = True

    def _refresh_focus_preview(self) -> None:
        """把源图预览切到当前聚焦的精灵图。"""
        if self.sheets and 0 <= self._focused_sheet < len(self.sheets):
            self._load_preview(self.sheets[self._focused_sheet]["path"])
        else:
            self._preview_surface = None

    def _slice_sheet(self, sheet: dict) -> None:
        """按该图当前透明色切成逐帧缩略图，保留已有的逐帧状态分配（长度对齐）。"""
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
        sheet["frame_states"] = [
            old[i] if i < len(old) else "skip" for i in range(len(frames))
        ]

    def _sample_color(self, pos) -> None:
        """把预览上点击位置映射回原图像素，取其颜色为透明色。"""
        rel_x = (pos[0] - self._preview_rect.x) / max(1, self._preview_rect.width)
        rel_y = (pos[1] - self._preview_rect.y) / max(1, self._preview_rect.height)
        src_w, src_h = self._preview_surface.get_size()
        x = max(0, min(src_w - 1, int(rel_x * src_w)))
        y = max(0, min(src_h - 1, int(rel_y * src_h)))
        color = self._preview_surface.get_at((x, y))
        self._set_chroma((color[0], color[1], color[2]))

    def config(self) -> dict:
        """收集当前表单为创建配置。"""
        return {
            "name": self.name.strip(),
            "mode": self.mode,
            "mirror": self.mirror,
            "chroma_color": self.chroma_color,
            "sheets": [
                {
                    "path": s["path"],
                    "mirror": s.get("mirror", False),
                    "chroma_color": s.get("chroma_color"),
                    "frame_states": list(s["frame_states"]),
                }
                for s in self.sheets
            ],
            "state_paths": dict(self.state_paths),
            "speeds": dict(self.speeds),
        }

    # ----- 渲染 -----

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        self._hit = {}
        self._row_hit = []
        panel = pygame.Surface(self.rect.size)
        panel.fill(theme.PANEL_BG_COLOR)
        pygame.draw.rect(panel, theme.BORDER_COLOR, panel.get_rect(), 1)

        title = self.font.render("创建皮肤 (Esc 取消)", True, theme.TITLE_COLOR)
        panel.blit(title, (PADDING, PADDING))
        pygame.draw.line(panel, theme.BORDER_COLOR,
                         (PADDING, TITLE_HEIGHT + 4), (self.rect.width - PADDING, TITLE_HEIGHT + 4))

        y = TITLE_HEIGHT + 12
        y = self._draw_name_row(panel, y)
        y = self._draw_mode_row(panel, y)
        y = self._draw_options_row(panel, y)
        if self.mode == "sheet":
            y = self._draw_sheet_row(panel, y)

        y, preview_local = self._draw_preview(panel, y)

        # 滚动列表（状态图片 + 逐动画速度），占据中部到底部按钮之上
        list_top = y + 4
        list_bottom = self.rect.height - PADDING - BUTTON_HEIGHT - 10
        self._draw_state_list(panel, list_top, list_bottom)

        self._draw_bottom(panel)

        surface.blit(panel, self.rect.topleft)
        # 命中区转窗口坐标
        self._hit = {k: r.move(self.rect.x, self.rect.y) for k, r in self._hit.items()}
        self._row_hit = [(r.move(self.rect.x, self.rect.y), a) for r, a in self._row_hit]
        self._preview_rect = (
            preview_local.move(self.rect.x, self.rect.y) if preview_local else pygame.Rect(0, 0, 0, 0)
        )
        self._list_rect = pygame.Rect(
            self.rect.x + PADDING, self.rect.y + list_top,
            self.rect.width - 2 * PADDING, list_bottom - list_top,
        )

    def _label(self, panel, text, x, y):
        panel.blit(self.font.render(text, True, theme.LABEL_COLOR), (x, y))

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
        border = theme.FIELD_FOCUS_BORDER if self._name_focus else theme.BORDER_COLOR
        pygame.draw.rect(panel, border, rect, 1, border_radius=4)
        text = self.name or "（点此输入皮肤名）"
        color = theme.TEXT_COLOR if self.name else theme.PLACEHOLDER_COLOR
        panel.blit(self.font.render(text, True, color), (rect.x + 6, rect.y + 4))
        self._hit["name"] = rect
        return y + ROW_HEIGHT + 4

    def _draw_mode_row(self, panel, y) -> int:
        self._label(panel, "方式", PADDING, y + 4)
        bw = 92
        self._button(panel, pygame.Rect(PADDING + 48, y, bw, FIELD_HEIGHT),
                     "精灵图", "mode_sheet", active=self.mode == "sheet")
        self._button(panel, pygame.Rect(PADDING + 48 + bw + 8, y, bw, FIELD_HEIGHT),
                     "按状态", "mode_states", active=self.mode == "states")
        return y + ROW_HEIGHT + 4

    def _current_chroma(self):
        """当前生效的透明色：精灵图模式取聚焦图的，按状态模式取全局。"""
        if self.mode == "sheet" and self.sheets:
            return self.sheets[self._focused_sheet].get("chroma_color")
        return self.chroma_color

    def _draw_options_row(self, panel, y) -> int:
        cx = PADDING
        # 镜像（仅按状态模式为全局；精灵图模式镜像在每张图标题上单独控制）
        if self.mode == "states":
            self._label(panel, "镜像", cx, y + 4)
            self._button(panel, pygame.Rect(cx + 48, y, 60, FIELD_HEIGHT),
                         "开" if self.mirror else "关", "mirror", active=self.mirror)
            cx = cx + 48 + 60 + 16

        # 透明色
        self._label(panel, "透明色", cx, y + 4)
        swatch = pygame.Rect(cx + 50, y, 26, FIELD_HEIGHT)
        chroma = self._current_chroma()
        if chroma is None:
            pygame.draw.rect(panel, theme.FIELD_BG_COLOR, swatch, border_radius=4)
            panel.blit(self.font.render("自动", True, theme.PLACEHOLDER_COLOR), (swatch.x + 1, swatch.y + 4))
        else:
            pygame.draw.rect(panel, chroma, swatch, border_radius=4)
        pygame.draw.rect(panel, theme.BORDER_COLOR, swatch, 1, border_radius=4)
        self._button(panel, pygame.Rect(swatch.right + 6, y, 50, FIELD_HEIGHT), "选色", "chroma_pick")
        self._button(panel, pygame.Rect(swatch.right + 6 + 56, y, 50, FIELD_HEIGHT), "自动", "chroma_auto")
        return y + ROW_HEIGHT + 4

    def _draw_sheet_row(self, panel, y) -> int:
        self._button(panel, pygame.Rect(PADDING, y, 110, FIELD_HEIGHT), "添加精灵图", "sheet_add")
        info = f"已添加 {len(self.sheets)} 张（聚焦第 {self._focused_sheet + 1} 张可取色）" \
            if self.sheets else "可添加多张，逐帧分配状态"
        panel.blit(self.font.render(self._clip(info, self.rect.width - PADDING - 130),
                                    True, theme.PLACEHOLDER_COLOR), (PADDING + 120, y + 4))
        return y + ROW_HEIGHT + 4
        return y + ROW_HEIGHT + 4

    def _draw_preview(self, panel, y):
        """左：源图（点击取透明色）；右：处理后动画实时播放。

        返回 (下一个 y, 源图显示区的面板局部矩形或 None)。
        """
        box_h = 100
        gap = 10
        half = (self.rect.width - 2 * PADDING - gap) // 2
        left = pygame.Rect(PADDING, y, half, box_h)
        right = pygame.Rect(PADDING + half + gap, y, half, box_h)

        source_local = self._draw_source_box(panel, left)
        self._draw_result_box(panel, right)

        return y + box_h + 6, source_local

    def _draw_source_box(self, panel, box):
        """左侧源图预览框（点击取色），返回图片显示区矩形或 None。"""
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, box, border_radius=4)
        pygame.draw.rect(panel, theme.BORDER_COLOR, box, 1, border_radius=4)
        if self._preview_surface is None:
            tip = self.font.render("选图后点此取透明色", True, theme.PLACEHOLDER_COLOR)
            panel.blit(tip, tip.get_rect(center=box.center))
            return None

        src_w, src_h = self._preview_surface.get_size()
        scale = min((box.width - 8) / src_w, (box.height - 18) / src_h)
        disp_w, disp_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
        rect = pygame.Rect(box.centerx - disp_w // 2, box.y + 4, disp_w, disp_h)
        panel.blit(pygame.transform.smoothscale(self._preview_surface, (disp_w, disp_h)), rect)
        hint = self.font.render("点击取透明色", True, theme.PLACEHOLDER_COLOR)
        panel.blit(hint, (box.x + 4, box.bottom - hint.get_height() - 2))
        return rect

    def _draw_result_box(self, panel, box):
        """右侧实时播放框：展示处理后当前状态动画帧。"""
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, box, border_radius=4)
        pygame.draw.rect(panel, theme.BORDER_COLOR, box, 1, border_radius=4)

        state, frame = self._current_result_frame()
        if frame is not None:
            scale = min((box.width - 8) / frame.get_width(), (box.height - 18) / frame.get_height())
            disp = (max(1, int(frame.get_width() * scale)), max(1, int(frame.get_height() * scale)))
            scaled = pygame.transform.smoothscale(frame, disp)
            panel.blit(scaled, scaled.get_rect(midtop=(box.centerx, box.y + 4)))
            label = self.font.render(f"预览：{state}", True, theme.PLACEHOLDER_COLOR)
            panel.blit(label, (box.x + 4, box.bottom - label.get_height() - 2))
        else:
            msg = self._preview_err or "选好后这里实时播放"
            text = self.font.render(self._clip(msg, box.width - 8), True, theme.PLACEHOLDER_COLOR)
            panel.blit(text, text.get_rect(center=box.center))

    def _draw_state_list(self, panel, top, bottom) -> None:
        if self.mode == "sheet":
            header = "逐帧点选分配状态（点帧循环切换状态/跳过；同一状态的帧按顺序成为动画）" \
                if self.sheets else "点「添加精灵图」后，逐帧点选分配动画状态"
        else:
            header = "各状态：选图 + 播放速度（缺失状态会回退内置动画）"
        panel.blit(self.font.render(self._clip(header, self.rect.width - 2 * PADDING),
                                    True, theme.PLACEHOLDER_COLOR), (PADDING, top))
        list_y0 = top + 22

        clip = panel.get_clip()
        panel.set_clip(pygame.Rect(PADDING, list_y0, self.rect.width - 2 * PADDING, bottom - list_y0))

        if self.mode == "sheet":
            content_h = self._draw_sheets_content(panel, list_y0, bottom)
        else:
            content_h = len(self.states) * LIST_ROW_HEIGHT
            y = list_y0 - self.scroll
            for state in self.states:
                if y + LIST_ROW_HEIGHT >= list_y0 and y <= bottom:
                    self._draw_state_row(panel, y, state)
                y += LIST_ROW_HEIGHT

        panel.set_clip(clip)
        self._max_scroll = max(0, content_h - (bottom - list_y0))
        self.scroll = min(self.scroll, self._max_scroll)

    def _draw_sheets_content(self, panel, list_y0, bottom) -> int:
        """精灵图模式：逐张显示标题（镜像/删除）+ 逐帧缩略图网格供点选状态。"""
        thumb = 36
        cell_w, cell_h = thumb + 8, thumb + 16
        cols = max(1, (self.rect.width - 2 * PADDING) // cell_w)
        y = list_y0 - self.scroll
        start = y

        for si, sheet in enumerate(self.sheets):
            # 标题行：图号 + 文件名（点击聚焦）+ 镜像 + 删除
            if list_y0 - 30 <= y <= bottom:
                focused = si == self._focused_sheet
                fname = sheet["path"].rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                title = f"图{si + 1} {fname}" + ("（聚焦）" if focused else "")
                color = theme.FIELD_FOCUS_BORDER if focused else theme.LABEL_COLOR
                label = self.font.render(self._clip(title, self.rect.width - 2 * PADDING - 120), True, color)
                panel.blit(label, (PADDING, y + 4))
                self._row_hit.append((pygame.Rect(PADDING, y, label.get_width(), FIELD_HEIGHT), f"sfocus:{si}"))
                mr = pygame.Rect(self.rect.width - PADDING - 110, y, 56, FIELD_HEIGHT)
                self._row_button(panel, mr, "镜像:" + ("开" if sheet.get("mirror") else "关"), f"smirror:{si}")
                self._row_button(panel, pygame.Rect(self.rect.width - PADDING - 48, y, 48, FIELD_HEIGHT),
                                 "删除", f"sremove:{si}")
            y += FIELD_HEIGHT + 4

            # 帧网格
            for fi, surf in enumerate(sheet["thumbs"]):
                col = fi % cols
                row = fi // cols
                cx = PADDING + col * cell_w
                cy = y + row * cell_h
                if list_y0 - cell_h <= cy <= bottom:
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
        border = theme.FIELD_FOCUS_BORDER if assigned else theme.BORDER_COLOR
        pygame.draw.rect(panel, border, rect, 2 if assigned else 1, border_radius=3)
        tag = state[:5] if assigned else "—"
        color = theme.BUTTON_TEXT_COLOR if assigned else theme.PLACEHOLDER_COLOR
        glyph = self.font.render(tag, True, color)
        panel.blit(glyph, (cx, cy + thumb))
        self._row_hit.append((rect, f"frame:{si},{fi}"))

    def _draw_state_row(self, panel, y, state) -> None:
        highlight = state in self._highlight_states
        color = theme.STATUS_FAIL_COLOR if highlight else theme.LABEL_COLOR
        panel.blit(self.font.render(state, True, color), (PADDING, y + 4))

        self._draw_speed_controls(panel, y, state)

        # 按状态模式：选图按钮 + 文件名
        if self.mode == "states":
            pick = pygame.Rect(PADDING + 90, y, 50, FIELD_HEIGHT)
            self._row_button(panel, pick, "选图", f"pick:{state}")
            path = self.state_paths.get(state)
            label = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] if path else "—"
            limit = (self.rect.width - PADDING - 110) - (pick.right + 6)
            panel.blit(self.font.render(self._clip(label, limit),
                                        True, theme.TEXT_COLOR), (pick.right + 6, y + 4))

    def _draw_speed_controls(self, panel, y, state) -> None:
        """右侧速度调节 [-] {ms} [+]。"""
        right = self.rect.width - PADDING
        plus = pygame.Rect(right - 24, y, 24, FIELD_HEIGHT)
        val = pygame.Rect(plus.x - 52, y, 48, FIELD_HEIGHT)
        minus = pygame.Rect(val.x - 28, y, 24, FIELD_HEIGHT)
        self._row_button(panel, plus, "+", f"slower:{state}")
        self._row_button(panel, minus, "-", f"faster:{state}")
        ms = int(self.speeds.get(state, 0.15) * 1000)
        glyph = self.font.render(f"{ms}ms", True, theme.TEXT_COLOR)
        panel.blit(glyph, glyph.get_rect(center=val.center))

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
            status = self.font.render(self._clip(self.status, self.rect.width - 210), True,
                                      theme.STATUS_FAIL_COLOR)
            panel.blit(status, (PADDING + 200, y + 6))

    def _clip(self, text: str, max_width: int) -> str:
        """按像素宽度裁剪文本，超出加省略号。"""
        if self.font.size(text)[0] <= max_width:
            return text
        while text and self.font.size(text + "…")[0] > max_width:
            text = text[:-1]
        return text + "…"
