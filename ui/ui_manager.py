"""UI 管理模块。

UIManager 统一管理桌宠的三个界面窗口及其异步/显示状态：

* ChatWindow   —— AI 对话窗口
* StatsPanel   —— 右键数值信息与功能按钮面板
* SettingsWindow —— 设置窗口（宠物大小 / AI 配置）

并集中处理：

* 与界面相关的输入事件路由（设置窗口模态、聊天输入、面板按钮点击）
* AI 对话/连接测试的后台线程结果回传（两个 queue.Queue）
* 交互引起的属性变化（+xx/-xx）在数值面板的短暂显示

UIManager 不直接修改宠物属性，也不执行喂食/玩耍的行为管线：
喂食/玩耍按钮通过 on_interaction 回调交还 Game 的交互分发流程
（事件 -> BehaviorManager -> 属性 -> 临时动画 -> 记忆联动）；
保存设置后通过 on_user_prefs_changed 回调让 Game 合并持久化用户偏好。
"""

from __future__ import annotations

import queue
import threading
from typing import Callable, List

import pygame

from config import settings
from core.ai.ai_service import AIService
from core.event import InteractionEvent, InteractionEventType
from ui.chat_window import ChatWindow
from ui.settings_window import SettingsWindow
from ui.stats_panel import StatsPanel
from utils.exception import AIServiceError, log_exception

# 聊天工作线程意外异常时回传给用户的兜底回复
_CHAT_FALLBACK_REPLY = "（呜……我刚才走神了，再和我说一遍好吗？）"

# 非面板触发的内部交互事件（点击/拖拽/面板开关），不作为面板按钮动作
_NON_PANEL_EVENTS = {
    InteractionEventType.CLICK,
    InteractionEventType.EXCITED,
    InteractionEventType.DRAG_START,
    InteractionEventType.DRAG_MOVE,
    InteractionEventType.DRAG_END,
    InteractionEventType.STATS_TOGGLE,
}

# 数值面板可触发的养成动作：按钮标识 -> 事件类型，由枚举自动派生。
# 新增养成动作只要在 InteractionEventType 增加成员（值即按钮标识），
# 即自动可被面板分发，本映射与 _handle_panel_action 无需改动。
_PANEL_INTERACTION_TYPES = {
    event_type.value: event_type
    for event_type in InteractionEventType
    if event_type not in _NON_PANEL_EVENTS
}


class UIManager:
    """桌宠界面窗口与界面相关交互的统一管理器。"""

    def __init__(
        self,
        font: pygame.font.Font,
        pet,
        pet_sprite,
        autonomous_manager,
        ai_service: AIService,
        desktop_manager,
        ai_config: dict,
        window_size,
        on_interaction: Callable[[InteractionEvent], None],
        on_user_prefs_changed: Callable[[], None],
    ) -> None:
        self.font = font
        self.pet = pet
        self.pet_sprite = pet_sprite
        self.autonomous_manager = autonomous_manager
        self.ai_service = ai_service
        self.desktop_manager = desktop_manager
        self.ai_config = ai_config
        self._on_interaction = on_interaction
        self._on_user_prefs_changed = on_user_prefs_changed

        # 数值信息面板：右键点击宠物弹出/关闭
        self.stats_panel = StatsPanel(font)

        # 交互引起的属性变化（属性名 -> [变化量, 剩余显示时间]）
        self._attr_deltas: dict = {}

        # 设置窗口：靠右侧停靠、垂直居中，避免遮挡居中的宠物
        settings_rect = pygame.Rect(
            window_size[0] - settings.SETTINGS_WINDOW_WIDTH - settings.CHAT_WINDOW_MARGIN,
            (window_size[1] - settings.SETTINGS_WINDOW_HEIGHT) // 2,
            settings.SETTINGS_WINDOW_WIDTH,
            settings.SETTINGS_WINDOW_HEIGHT,
        )
        self.settings_window = SettingsWindow(font, settings_rect)
        self._ai_test_results: "queue.Queue[tuple]" = queue.Queue()

        # AI 对话窗口：靠左侧停靠，避免遮挡居中的宠物。
        # UI 与 AIService 解耦，AI 回复在后台线程获取，经队列回传主循环。
        chat_rect = pygame.Rect(
            settings.CHAT_WINDOW_MARGIN,
            settings.CHAT_WINDOW_MARGIN,
            settings.CHAT_WINDOW_WIDTH,
            settings.CHAT_WINDOW_HEIGHT,
        )
        self.chat_window = ChatWindow(font, chat_rect, pet_name=self.pet_name())
        self._ai_replies: "queue.Queue[str]" = queue.Queue()

    def pet_name(self) -> str:
        """对话窗口标题使用的宠物名（取自人格服务）。"""
        return self.ai_service.personality.name

    # ----- 状态查询（供 Game 决定帧率/暂停自主行为） -----

    @property
    def is_active(self) -> bool:
        """是否有界面窗口/面板正在显示（活跃态，需要高帧率）。"""
        return (
            self.chat_window.visible
            or self.settings_window.visible
            or self.stats_panel.visible
        )

    @property
    def blocks_autonomous(self) -> bool:
        """是否应暂停自主行为（聊天/设置窗口打开时窗口需保持静止）。"""
        return self.chat_window.visible or self.settings_window.visible

    # ----- 事件路由 -----

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理界面相关输入事件，返回是否已消化（消化则 Game 不再处理交互）。

        路由顺序与原 Game._handle_events 保持一致：
        设置窗口模态 -> 聊天开关键 -> 聊天输入 -> 面板按钮点击。
        """
        # 设置窗口为模态：打开期间吞掉全部事件
        if self.settings_window.visible:
            if event.type in (pygame.KEYDOWN, pygame.TEXTINPUT, pygame.MOUSEBUTTONDOWN):
                result = self.settings_window.handle_event(event)
                if result is not None:
                    self._handle_settings_result(result)
            return True

        # 聊天开关键（仅在聊天窗口关闭时响应）
        if event.type == pygame.KEYDOWN and not self.chat_window.visible:
            if pygame.key.name(event.key) == settings.CHAT_TOGGLE_KEY:
                self.chat_window.toggle()
                self.desktop_manager.focus()
                return True

        # 聊天窗口打开时，键盘/文本/滚轮事件交给对话窗口
        if self.chat_window.visible and event.type in (
            pygame.KEYDOWN, pygame.TEXTINPUT, pygame.MOUSEWHEEL,
        ):
            message = self.chat_window.handle_event(event)
            if message:
                self._send_chat_message(message)
            return True

        # 数值面板内的左键点击（功能按钮）优先于宠物交互处理
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.stats_panel.contains(event.pos)
        ):
            self._handle_panel_action(self.stats_panel.handle_click(event.pos))
            return True

        return False

    def toggle_stats_panel(self) -> None:
        """切换数值面板显示（右键宠物时由 Game 的交互分发调用）。"""
        self.stats_panel.toggle()

    # ----- 面板按钮动作 -----

    def _handle_panel_action(self, action) -> None:
        """分发数值面板功能按钮的动作。

        养成动作（feed/play/bath/sleep/gift 等，按钮标识与
        InteractionEventType 的值一致）统一经 on_interaction 回调走
        Game 的交互管线；chat/settings 为界面动作，在此直接处理。
        新增养成按钮无需改动本方法。
        """
        event_type = _PANEL_INTERACTION_TYPES.get(action)
        if event_type is not None:
            self._on_interaction(InteractionEvent(type=event_type))
            return

        if action == "chat":
            self.chat_window.toggle()
            self.stats_panel.hide()
            if self.chat_window.visible:
                self.desktop_manager.focus()
        elif action == "settings":
            personality = self.ai_service.personality
            self.settings_window.open(
                self.pet_sprite.scale, personality.name, personality.tone, self.ai_config
            )
            self.stats_panel.hide()
            self.desktop_manager.focus()

    # ----- 设置窗口结果 -----

    def _handle_settings_result(self, result: dict) -> None:
        """应用设置窗口的保存/测试结果。"""
        if result.get("action") == "test":
            self._test_ai_config(result["ai_config"])
            return

        if result.get("action") == "save":
            self.pet_sprite.scale = result["pet_scale"]
            self._on_user_prefs_changed()  # 由 Game 合并写回 user_config（含窗口位置）

            # 统一宠物名称：同时更新 Pet、人格服务与聊天窗口标题，并持久化人格
            personality = self.ai_service.personality
            name = result["name"] or personality.name
            self.pet.set_name(name)
            personality.name = name
            personality.tone = result["persona"]
            personality.save()
            self.chat_window.pet_name = name

            self.ai_config.update(result["ai_config"])
            save_ai_config(self.ai_config)
            self.ai_service.apply_config(self.ai_config)

        # 设置窗口已关闭：聊天窗口未打开时停用文本输入
        if not self.chat_window.visible:
            pygame.key.stop_text_input()

    def _test_ai_config(self, partial_config: dict) -> None:
        """在后台线程中用设置窗口的当前编辑值测试 LLM 连接。"""
        config = {**self.ai_config, **partial_config}
        self.settings_window.set_status("正在测试连接...", None)

        def worker() -> None:
            self._ai_test_results.put(AIService.test_connection(config))

        threading.Thread(target=worker, daemon=True).start()

    # ----- 聊天 -----

    def _send_chat_message(self, message: str) -> None:
        """提交用户输入的聊天消息：显示在对话窗口，并在后台线程调用 AIService。

        LLM 请求可能耗时（网络延迟/超时），在独立线程中执行以避免
        阻塞主循环；意外异常兜底，避免对话窗口永久卡在"正在输入"。
        """
        self.chat_window.add_message("user", message)
        self.chat_window.set_pending(True)

        def worker() -> None:
            try:
                reply = self.ai_service.chat(self.pet, message)
            except Exception as exc:
                log_exception(AIServiceError(f"聊天处理出现意外异常: {exc}"))
                reply = _CHAT_FALLBACK_REPLY
            self._ai_replies.put(reply)

        threading.Thread(target=worker, daemon=True).start()

    # ----- 逐帧更新 -----

    def update(self, dt: float) -> None:
        """处理后台线程结果回传，并推进属性变化提示的显示时间。"""
        self._process_ai_replies()
        self._process_ai_test_results()
        self._update_attr_deltas(dt)

    def _process_ai_replies(self) -> None:
        """将后台线程中 AIService.chat() 返回的回复写回对话窗口。"""
        while not self._ai_replies.empty():
            reply = self._ai_replies.get_nowait()
            self.chat_window.set_pending(False)
            self.chat_window.add_message("pet", reply)

    def _process_ai_test_results(self) -> None:
        """将后台线程的连接测试结果写回设置窗口状态行。"""
        while not self._ai_test_results.empty():
            ok, message = self._ai_test_results.get_nowait()
            self.settings_window.set_status(message, ok)

    # ----- 属性变化提示 -----

    def record_attr_deltas(self, before: tuple) -> None:
        """对比交互前后的属性值，记录非零变化量供数值面板显示。

        before: 交互前的 (hunger, mood, energy) 快照，after 从 pet 读取。
        """
        for name, old_value, new_value in (
            ("hunger", before[0], self.pet.hunger),
            ("mood", before[1], self.pet.mood),
            ("energy", before[2], self.pet.energy),
        ):
            delta = new_value - old_value
            if delta:
                self._attr_deltas[name] = [delta, settings.ATTR_DELTA_DURATION]

    def _attr_delta_suffix(self, name: str) -> str:
        """生成属性行的变化量后缀（如 " +20"），无变化时返回空字符串。"""
        entry = self._attr_deltas.get(name)
        if entry is None:
            return ""
        return f"  {entry[0]:+.0f}"

    def _update_attr_deltas(self, dt: float) -> None:
        """推进属性变化提示的剩余显示时间，移除已过期的条目。"""
        expired = []
        for name, entry in self._attr_deltas.items():
            entry[1] -= dt
            if entry[1] <= 0:
                expired.append(name)
        for name in expired:
            del self._attr_deltas[name]

    # ----- 渲染 -----

    def draw(self, screen: pygame.Surface) -> None:
        """绘制数值面板 / 聊天窗口 / 设置窗口（在宠物精灵之上）。"""
        self.stats_panel.draw(screen, self.pet_sprite.rect, self._stats_lines())
        self.chat_window.draw(screen)
        self.settings_window.draw(screen)

    def _stats_lines(self) -> List[str]:
        """生成数值信息面板的内容（右键点击宠物弹出）。

        只展示名称、各属性数值与时间；行为、情绪、最近动作等
        通过宠物动画直接呈现，不再以文字罗列。喂食/玩耍等交互引起的
        属性变化以 +xx/-xx 后缀短暂显示（见 record_attr_deltas）。
        """
        return [
            f"名称: {self.pet.name}",
            f"饥饿: {self.pet.hunger:.1f}{self._attr_delta_suffix('hunger')}",
            f"心情: {self.pet.mood:.1f}{self._attr_delta_suffix('mood')}",
            f"体力: {self.pet.energy:.1f}{self._attr_delta_suffix('energy')}",
            f"时间: {self.autonomous_manager.schedule.time_of_day()}"
            f" (第 {self.autonomous_manager.schedule.day_count} 天)",
        ]


def save_ai_config(ai_config: dict) -> None:
    """将 AI 配置写回 config/ai_config.json（独立函数便于测试替换）。"""
    from utils.helper import save_json

    save_json(settings.AI_CONFIG_FILE, ai_config)
