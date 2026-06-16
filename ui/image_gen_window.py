"""AI 文生图（生成自定义皮肤）窗口。

模态窗口：用户填入自己的 API Key、可改接口地址、选择模型与尺寸、输入提示词，
点「生成」后由 Game 在后台线程调用 ImageGenClient 出图并回填预览；点「应用为皮肤」
把生成图抠图后作为当前宠物皮肤启用。含版权/合规声明。

本模块只负责 UI 与产出动作字典；实际网络请求、图片处理与皮肤构建由 Game 编排。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pygame

from config import settings
from ui import theme

TITLE_TEXT = "AI 绘图 · 生成皮肤"
PADDING = 12
ROW_HEIGHT = 34
FIELD_HEIGHT = 26
BUTTON_HEIGHT = 28
PREVIEW = 132
MAX_FIELD_LENGTH = 400


class ImageGenWindow:
    """文生图窗口：自带 Key + 选模型 + 提示词 -> 生成 -> 应用为皮肤。"""

    def __init__(self, font: pygame.font.Font, rect: pygame.Rect) -> None:
        self.font = font
        self.rect = rect
        self.visible = False

        self.base_url = settings.IMAGE_GEN_BASE_URL
        self.api_key = ""
        self.model = settings.IMAGE_GEN_MODELS[0]
        self.size = settings.IMAGE_GEN_SIZES[0]
        self.prompt = ""

        self.status = ""
        self.status_ok: Optional[bool] = None
        self.busy = False                      # 生成请求进行中
        self.preview: Optional[pygame.Surface] = None  # 生成结果缩略图

        self._focus: Optional[str] = None       # 当前聚焦的文本字段
        self._open: Optional[str] = None        # 展开的下拉："model"/"size"
        self._hit_areas: Dict[str, pygame.Rect] = {}

    # ----- 打开 / 配置 -----

    def open(self, config: dict) -> None:
        """打开窗口，用已保存的图片生成配置初始化。"""
        self.visible = True
        self.base_url = config.get("base_url") or settings.IMAGE_GEN_BASE_URL
        self.api_key = config.get("api_key", "")
        self.model = config.get("model") or settings.IMAGE_GEN_MODELS[0]
        self.size = config.get("size") or settings.IMAGE_GEN_SIZES[0]
        self._focus = None
        self._open = None
        self.status = ""
        self.status_ok = None
        self.busy = False
        pygame.key.start_text_input()

    def close(self) -> dict:
        self.visible = False
        return {"action": "close"}

    def config(self) -> dict:
        """当前编辑中的图片生成配置（供保存与发起请求）。"""
        return {
            "base_url": self.base_url.strip(),
            "api_key": self.api_key.strip(),
            "model": self.model,
            "size": self.size,
        }

    def set_status(self, text: str, ok: Optional[bool]) -> None:
        self.status = text
        self.status_ok = ok

    def set_preview(self, surface: Optional[pygame.Surface]) -> None:
        self.preview = surface

    def _models(self) -> List[str]:
        models = list(settings.IMAGE_GEN_MODELS)
        if self.model and self.model not in models:
            models.insert(0, self.model)
        return models

    # ----- 事件 -----

    def handle_event(self, event: pygame.event.Event) -> Optional[dict]:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return self.close()
            if event.key == pygame.K_BACKSPACE and self._focus:
                setattr(self, self._focus, getattr(self, self._focus)[:-1])
            elif event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL and self._focus:
                self._paste_into_focus()
            return None

        if event.type == pygame.TEXTINPUT and self._focus:
            value = getattr(self, self._focus)
            if len(value) < MAX_FIELD_LENGTH:
                setattr(self, self._focus, value + event.text)
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)
        return None

    def _handle_click(self, pos) -> Optional[dict]:
        # 下拉展开时优先处理选项点击
        if self._open:
            for name, rect in self._hit_areas.items():
                if name.startswith("opt:") and rect.collidepoint(pos):
                    kind, value = name[4:].split("=", 1)
                    setattr(self, kind, value)
                    self._open = None
                    return None
            self._open = None

        for name, rect in self._hit_areas.items():
            if name.startswith("opt:") or not rect.collidepoint(pos):
                continue
            if name in ("base_url", "api_key", "prompt"):
                self._focus = name
                pygame.key.set_text_input_rect(rect)
            elif name == "model":
                self._open = None if self._open == "model" else "model"
            elif name == "size":
                self._open = None if self._open == "size" else "size"
            elif name == "generate":
                if not self.busy:
                    return {"action": "generate", "config": self.config(), "prompt": self.prompt.strip()}
            elif name == "apply":
                return {"action": "apply"}
            elif name == "close":
                return self.close()
            return None

        self._focus = None
        return None

    def _paste_into_focus(self) -> None:
        from ui.settings_window import SettingsWindow

        text = SettingsWindow._read_clipboard().strip().replace("\r", "").replace("\n", "")
        if not text:
            return
        value = getattr(self, self._focus)
        setattr(self, self._focus, (value + text)[:MAX_FIELD_LENGTH])

    # ----- 绘制 -----

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        panel = theme.make_panel(self.rect.size)
        self._hit_areas = {}
        line_h = self.font.get_linesize()

        title = self.font.render(f"{TITLE_TEXT} (Esc 关闭)", True, theme.LABEL_COLOR)
        panel.blit(title, (PADDING, PADDING))
        pygame.draw.line(panel, theme.BORDER_COLOR,
                         (PADDING, PADDING + line_h + 2),
                         (self.rect.width - PADDING, PADDING + line_h + 2))

        y = PADDING + line_h + 10
        y = self._field_row(panel, y, "接口地址", "base_url", self.base_url or "（默认）")
        y = self._field_row(panel, y, "API Key", "api_key", self._masked_key())
        model_rect, y = self._dropdown_row(panel, y, "模型", "model", self.model)
        size_rect, y = self._dropdown_row(panel, y, "尺寸", "size", self.size)
        y = self._field_row(panel, y, "提示词", "prompt", self.prompt or "（描述你想要的宠物外观）")

        # 版权声明（自动换行，灰色）
        from ui.message_box import wrap_text
        for line in wrap_text(self.font, settings.IMAGE_GEN_DISCLAIMER, self.rect.width - 2 * PADDING):
            tip = self.font.render(line, True, theme.PLACEHOLDER_COLOR)
            panel.blit(tip, (PADDING, y))
            y += line_h
        y += 4

        # 预览框
        preview_rect = pygame.Rect((self.rect.width - PREVIEW) // 2, y, PREVIEW, PREVIEW)
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, preview_rect, border_radius=6)
        pygame.draw.rect(panel, theme.BORDER_COLOR, preview_rect, 1, border_radius=6)
        if self.preview is not None:
            panel.blit(self.preview, self.preview.get_rect(center=preview_rect.center))
        else:
            hint = self.font.render("生成结果预览", True, theme.PLACEHOLDER_COLOR)
            panel.blit(hint, hint.get_rect(center=preview_rect.center))
        y = preview_rect.bottom + 6

        self._status_row(panel, y)
        self._bottom_buttons(panel)

        if self._open == "model":
            self._dropdown_popup(panel, model_rect, "model", self._models())
        elif self._open == "size":
            self._dropdown_popup(panel, size_rect, "size", settings.IMAGE_GEN_SIZES)

        surface.blit(panel, self.rect.topleft)
        self._hit_areas = {n: r.move(self.rect.x, self.rect.y) for n, r in self._hit_areas.items()}

    def _field_row(self, panel, y, label_text, name, display) -> int:
        label = self.font.render(label_text, True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))
        rect = pygame.Rect(self.rect.width // 3, y, self.rect.width * 2 // 3 - PADDING, FIELD_HEIGHT)
        pygame.draw.rect(panel, theme.FIELD_BG_COLOR, rect, border_radius=4)
        border = theme.FIELD_FOCUS_BORDER if self._focus == name else theme.BORDER_COLOR
        pygame.draw.rect(panel, border, rect, 1, border_radius=4)
        text = self.font.render(display, True, theme.TEXT_COLOR)
        clip = panel.get_clip()
        panel.set_clip(rect.inflate(-8, 0))
        panel.blit(text, (rect.x + 6, rect.y + (rect.height - text.get_height()) // 2))
        panel.set_clip(clip)
        self._hit_areas[name] = rect
        return y + ROW_HEIGHT

    def _dropdown_row(self, panel, y, label_text, name, value):
        label = self.font.render(label_text, True, theme.LABEL_COLOR)
        panel.blit(label, (PADDING, y + (ROW_HEIGHT - label.get_height()) // 2))
        rect = pygame.Rect(self.rect.width // 3, y, self.rect.width * 2 // 3 - PADDING, FIELD_HEIGHT)
        pygame.draw.rect(panel, theme.BUTTON_BG_COLOR, rect, border_radius=4)
        pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=4)
        text = self.font.render(value, True, theme.BUTTON_TEXT_COLOR)
        panel.blit(text, text.get_rect(midleft=(rect.x + 6, rect.centery)))
        arrow = self.font.render("▾", True, theme.BUTTON_TEXT_COLOR)
        panel.blit(arrow, arrow.get_rect(midright=(rect.right - 6, rect.centery)))
        self._hit_areas[name] = rect
        return rect, y + ROW_HEIGHT

    def _dropdown_popup(self, panel, field_rect, kind, options) -> None:
        for i, opt in enumerate(options):
            r = pygame.Rect(field_rect.x, field_rect.bottom + i * FIELD_HEIGHT,
                            field_rect.width, FIELD_HEIGHT)
            active = opt == getattr(self, kind)
            pygame.draw.rect(panel, theme.FIELD_FOCUS_BORDER if active else theme.PANEL_BG_COLOR, r)
            pygame.draw.rect(panel, theme.BORDER_COLOR, r, 1)
            color = (255, 255, 255) if active else theme.TEXT_COLOR
            text = self.font.render(opt, True, color)
            panel.blit(text, text.get_rect(midleft=(r.x + 6, r.centery)))
            self._hit_areas[f"opt:{kind}={opt}"] = r

    def _masked_key(self) -> str:
        key = self.api_key
        if not key:
            return ""
        return "*" * len(key) if len(key) <= 10 else f"{key[:6]}...{key[-4:]}"

    def _status_row(self, panel, y) -> None:
        if not self.status:
            return
        if self.status_ok is True:
            color = theme.STATUS_OK_COLOR
        elif self.status_ok is False:
            color = theme.STATUS_FAIL_COLOR
        else:
            color = theme.STATUS_PENDING_COLOR
        from ui.message_box import wrap_text
        for i, line in enumerate(wrap_text(self.font, self.status, self.rect.width - 2 * PADDING)[:2]):
            panel.blit(self.font.render(line, True, color), (PADDING, y + i * self.font.get_linesize()))

    def _bottom_buttons(self, panel) -> None:
        gen_label = "生成中..." if self.busy else "生成"
        buttons = (("generate", gen_label), ("apply", "应用为皮肤"), ("close", "关闭"))
        bw = (self.rect.width - (len(buttons) + 1) * PADDING) // len(buttons)
        y = self.rect.height - BUTTON_HEIGHT - PADDING
        for i, (name, text) in enumerate(buttons):
            rect = pygame.Rect(PADDING + i * (bw + PADDING), y, bw, BUTTON_HEIGHT)
            disabled = name == "generate" and self.busy
            bg = theme.FIELD_BG_COLOR if disabled else theme.BUTTON_BG_COLOR
            pygame.draw.rect(panel, bg, rect, border_radius=6)
            pygame.draw.rect(panel, theme.BUTTON_BORDER_COLOR, rect, 1, border_radius=6)
            glyph = self.font.render(text, True, theme.BUTTON_TEXT_COLOR)
            panel.blit(glyph, glyph.get_rect(center=rect.center))
            self._hit_areas[name] = rect
