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

import datetime
import queue
import random
import threading
from typing import Callable, List, Optional, Tuple

import pygame

from config import settings
from core.ai.ai_service import AIService
from core.event import InteractionEvent, InteractionEventType
from ui.chat_window import ChatWindow
from ui.settings_window import SettingsWindow
from ui.skin_creator import SkinCreator
from ui.skin_window import SkinWindow
from ui.speech_bubble import SpeechBubble
from ui.stats_panel import StatsPanel
from utils.exception import AIServiceError, log_exception
from utils.helper import load_json, save_json
from utils.timer import IntervalTimer

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
        skin_manager=None,
        on_skin_change: Callable[[str], None] = None,
        on_skin_create: Callable[[dict], tuple] = None,
        reminder_interval_minutes: float = settings.REST_REMINDER_INTERVAL_MINUTES,
        proactive_enabled: bool = settings.PROACTIVE_CHAT_ENABLED,
        proactive_interval_minutes: float = settings.PROACTIVE_CHAT_INTERVAL_MINUTES,
        sound_enabled: bool = settings.SOUND_ENABLED,
        tts=None,
        tts_enabled: bool = settings.TTS_ENABLED,
        on_feed_place_start: Callable[[], None] = None,
        on_fence_toggle: Callable[[], None] = None,
        on_fence_view_toggle: Callable[[], None] = None,
        fence_view_label: Callable[[], str] = None,
        on_quit: Callable[[], None] = None,
        popup_anchor: Callable[[Tuple[int, int]], Optional[Tuple[int, int]]] = None,
    ) -> None:
        self.font = font
        self.pet = pet
        self.pet_sprite = pet_sprite
        self.autonomous_manager = autonomous_manager
        self.ai_service = ai_service
        self.desktop_manager = desktop_manager
        self.ai_config = ai_config
        self.skin_manager = skin_manager
        self._on_interaction = on_interaction
        self._on_user_prefs_changed = on_user_prefs_changed
        self._on_skin_change = on_skin_change
        self._on_skin_create = on_skin_create
        self._on_feed_place_start = on_feed_place_start
        self._on_fence_toggle = on_fence_toggle
        self._on_fence_view_toggle = on_fence_view_toggle
        self._fence_view_label = fence_view_label
        self._on_quit = on_quit
        self._popup_anchor = popup_anchor

        # 数值信息面板：右键点击宠物弹出/关闭
        self.stats_panel = StatsPanel(font)

        # 休息提醒：每隔 reminder_interval_minutes 分钟在宠物头顶弹出提示气泡。
        # 气泡不拦截事件、不计入 is_active，不影响帧率与自主行为。
        self.reminder_interval_minutes = reminder_interval_minutes
        self.speech_bubble = SpeechBubble(font)
        self._rest_timer = IntervalTimer(
            self._reminder_seconds(), self._show_rest_reminder
        )

        # AI 主动互动：每隔一段时间让宠物结合状态/记忆/时段主动冒泡说一句。
        # 开关与间隔可在设置窗口调整（存 user_config）。LLM 请求在后台线程进行，
        # 结果经队列回主循环显示；离线则用状态化文案降级。
        self.proactive_enabled = proactive_enabled
        self.proactive_interval_minutes = proactive_interval_minutes
        # 音效开关（实际播放在 Game 的 SoundManager；此处仅承载设置窗口的编辑值，
        # 保存后经 on_user_prefs_changed 让 Game 应用并持久化）
        self.sound_enabled = sound_enabled
        # 语音朗读：tts 为 Game 创建的 TTSManager（可能为 None，如测试），在主动发言/
        # 聊天回复处调用 speak；tts_enabled 为设置窗口编辑值，保存后由 Game 应用并持久化
        self._tts = tts
        self.tts_enabled = tts_enabled
        self._proactive_timer = IntervalTimer(
            self._proactive_seconds(), self._trigger_proactive
        )
        self._proactive_queue: "queue.Queue[str]" = queue.Queue()
        self._proactive_pending = False

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

        # 皮肤选择窗口：顶级弹窗，缩略图预览选择，靠右侧停靠、垂直居中
        skin_rect = pygame.Rect(
            window_size[0] - settings.SKIN_WINDOW_WIDTH - settings.CHAT_WINDOW_MARGIN,
            (window_size[1] - settings.SKIN_WINDOW_HEIGHT) // 2,
            settings.SKIN_WINDOW_WIDTH,
            settings.SKIN_WINDOW_HEIGHT,
        )
        self.skin_window = SkinWindow(font, skin_rect)

        # 创建皮肤窗口：内容较多，居中显示（创建为一次性模态任务，临时遮挡可接受）
        creator_size = (500, 600)
        self._creator_size = creator_size
        creator_rect = pygame.Rect(
            (window_size[0] - creator_size[0]) // 2,
            (window_size[1] - creator_size[1]) // 2,
            *creator_size,
        )
        self.skin_creator = SkinCreator(font, creator_rect)

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

        # 各弹窗的默认停靠矩形。设围栏后弹窗统一锚定到围栏上边（见 _anchored_rect），
        # 无围栏时回退到这些默认位置。
        self._default_settings_rect = settings_rect.copy()
        self._default_skin_rect = skin_rect.copy()
        self._default_creator_rect = creator_rect.copy()
        self._default_chat_rect = chat_rect.copy()

        # 聊天历史持久化：启动时把上次的可见对话回填到聊天窗口（与 AI 记忆分离）
        self._chat_history: list = load_json(settings.CHAT_HISTORY_FILE) or []
        for item in self._chat_history:
            self.chat_window.add_message(item.get("sender", "pet"), item.get("text", ""))

    def pet_name(self) -> str:
        """对话窗口标题使用的宠物名（取自人格服务）。"""
        return self.ai_service.personality.name

    def set_canvas_size(self, window_size) -> None:
        """窗口画布尺寸变化（围栏模式缩放/恢复）后，重算各弹窗默认停靠矩形。

        设置/皮肤窗口靠右侧停靠、垂直居中，创建窗口居中，均依赖画布尺寸；
        聊天窗口固定停靠左上角，不随尺寸变化。下次打开弹窗时即用新默认位置
        （设围栏时仍优先经 _anchored_rect 锚定到围栏上边）。
        """
        w, h = window_size
        self._default_settings_rect = pygame.Rect(
            w - settings.SETTINGS_WINDOW_WIDTH - settings.CHAT_WINDOW_MARGIN,
            (h - settings.SETTINGS_WINDOW_HEIGHT) // 2,
            settings.SETTINGS_WINDOW_WIDTH,
            settings.SETTINGS_WINDOW_HEIGHT,
        )
        self._default_skin_rect = pygame.Rect(
            w - settings.SKIN_WINDOW_WIDTH - settings.CHAT_WINDOW_MARGIN,
            (h - settings.SKIN_WINDOW_HEIGHT) // 2,
            settings.SKIN_WINDOW_WIDTH,
            settings.SKIN_WINDOW_HEIGHT,
        )
        cw, ch = self._creator_size
        self._default_creator_rect = pygame.Rect(
            (w - cw) // 2, (h - ch) // 2, cw, ch
        )

    # ----- 状态查询（供 Game 决定帧率/暂停自主行为） -----

    @property
    def is_active(self) -> bool:
        """是否有界面窗口/面板正在显示（活跃态，需要高帧率）。"""
        return (
            self.chat_window.visible
            or self.settings_window.visible
            or self.skin_window.visible
            or self.skin_creator.visible
            or self.stats_panel.visible
        )

    @property
    def blocks_autonomous(self) -> bool:
        """是否应暂停自主行为（聊天/设置/皮肤/创建窗口打开时窗口需保持静止）。"""
        return (
            self.chat_window.visible
            or self.settings_window.visible
            or self.skin_window.visible
            or self.skin_creator.visible
        )

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

        # 创建皮肤窗口为模态：打开期间吞掉全部事件（优先于皮肤选择窗口）
        if self.skin_creator.visible:
            if event.type in (
                pygame.KEYDOWN, pygame.TEXTINPUT, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL,
            ):
                result = self.skin_creator.handle_event(event)
                if result is not None:
                    self._handle_creator_result(result)
            return True

        # 皮肤选择窗口为模态：打开期间吞掉全部事件
        if self.skin_window.visible:
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                result = self.skin_window.handle_event(event)
                if result is not None:
                    self._handle_skin_result(result)
            return True

        # 聊天开关键（仅在聊天窗口关闭时响应）
        if event.type == pygame.KEYDOWN and not self.chat_window.visible:
            if pygame.key.name(event.key) == settings.CHAT_TOGGLE_KEY:
                self.chat_window.rect = self._anchored_rect(self._default_chat_rect)
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
        # 喂食改为放置模式：进入后由 Game 处理鼠标放置/取消（见 _handle_feed_placement）
        if action == "feed":
            self.stats_panel.hide()
            if self._on_feed_place_start is not None:
                self._on_feed_place_start()
            return

        # 围栏：取点/设定/清除由 Game 编排，状态用头顶气泡反馈
        if action == "fence":
            self.stats_panel.hide()
            if self._on_fence_toggle is not None:
                self._on_fence_toggle()
            return

        # 围栏显隐：一键隐藏/显示围栏边框。保持面板打开，便于即时看到效果并连续切换
        if action == "fence_view":
            if self._on_fence_view_toggle is not None:
                self._on_fence_view_toggle()
            return

        event_type = _PANEL_INTERACTION_TYPES.get(action)
        if event_type is not None:
            self._on_interaction(InteractionEvent(type=event_type))
            return

        if action == "chat":
            if not self.chat_window.visible:
                self.chat_window.rect = self._anchored_rect(self._default_chat_rect)
            self.chat_window.toggle()
            self.stats_panel.hide()
            if self.chat_window.visible:
                self.desktop_manager.focus()
        elif action == "skin":
            self._open_skin_window()
        elif action == "settings":
            personality = self.ai_service.personality
            self.settings_window.rect = self._anchored_rect(self._default_settings_rect)
            self.settings_window.open(
                self.pet_sprite.scale, personality.name,
                personality.character, personality.tone, self.ai_config,
                reminder_interval=self.reminder_interval_minutes,
                proactive_enabled=self.proactive_enabled,
                proactive_interval=self.proactive_interval_minutes,
                sound_enabled=self.sound_enabled,
                tts_enabled=self.tts_enabled,
            )
            self.stats_panel.hide()
            self.desktop_manager.focus()

    # ----- 皮肤窗口结果 -----

    def _open_skin_window(self) -> None:
        """打开皮肤选择窗口，附带每个皮肤的缺失状态信息。"""
        skins = self.skin_manager.available_skins()
        items = [(name, self.skin_manager.preview_path(name)) for name in skins]
        missing_map = {name: self.skin_manager.missing_states(name) for name in skins}
        self.skin_window.rect = self._anchored_rect(self._default_skin_rect)
        self.skin_window.open(items, self.skin_manager.active_skin, missing_map)
        self.stats_panel.hide()
        self.desktop_manager.focus()

    def show_bubble(self, text: str) -> None:
        """在宠物头顶弹出一条提示气泡（围栏取点/设定等状态反馈）。"""
        self.speech_bubble.show(text, settings.REST_REMINDER_BUBBLE_DURATION)

    def _anchored_rect(self, default_rect: pygame.Rect) -> pygame.Rect:
        """弹窗矩形：设围栏时锚定到围栏上边统一基点，否则用默认停靠位置。"""
        if self._popup_anchor is None:
            return default_rect.copy()
        anchor = self._popup_anchor((default_rect.width, default_rect.height))
        if anchor is None:
            return default_rect.copy()
        return pygame.Rect(anchor[0], anchor[1], default_rect.width, default_rect.height)

    def _handle_skin_result(self, result: tuple) -> None:
        """处理皮肤选择窗口的结果：选择切换 / 创建 / 补充缺失动画。"""
        action, value = result
        if action == "select":
            if self._on_skin_change is not None:
                self._on_skin_change(value)
            self.skin_window.set_active(value)
        elif action == "create":
            # 打开创建皮肤窗口（皮肤选择窗口暂时关闭，创建完成后可重新打开查看）
            self.skin_window.close()
            self.skin_creator.rect = self._anchored_rect(self._default_creator_rect)
            self.skin_creator.open()
            self.desktop_manager.focus()
        elif action == "supplement":
            # 补充已有皮肤的缺失动画：按状态上传，高亮缺失项
            self.skin_window.close()
            self.skin_creator.rect = self._anchored_rect(self._default_creator_rect)
            self.skin_creator.open(
                name=value, mode="states", highlight_states=self.skin_manager.missing_states(value)
            )
            self.desktop_manager.focus()
        # ("close", None)：窗口已自行关闭，无需额外处理

    def _handle_creator_result(self, result: tuple) -> None:
        """处理创建皮肤窗口的结果：生成皮肤（经回调）或关闭。"""
        action, value = result
        if action == "generate":
            if self._on_skin_create is None:
                return
            ok, message = self._on_skin_create(value)
            if ok:
                self.skin_creator.close()
            else:
                self.skin_creator.set_status(message)
        # ("close", None)：窗口已自行关闭

    # ----- 设置窗口结果 -----

    def _handle_settings_result(self, result: dict) -> None:
        """应用设置窗口的保存/测试/保存退出结果。"""
        action = result.get("action")
        if action == "test":
            self._test_ai_config(result["ai_config"])
            return

        if action in ("save", "save_exit"):
            self._apply_save(result)

        # 设置窗口已关闭：聊天窗口未打开时停用文本输入
        if not self.chat_window.visible:
            pygame.key.stop_text_input()

        # 保存并退出：应用保存后请求 Game 退出（退出时统一存档宠物数据/偏好）
        if action == "save_exit" and self._on_quit is not None:
            self._on_quit()

    def _apply_save(self, result: dict) -> None:
        """应用设置窗口「保存」的各项编辑值并持久化（save / save_exit 共用）。"""
        self.pet_sprite.scale = result["pet_scale"]
        self.reminder_interval_minutes = result["reminder_interval"]
        # 间隔变更后按新间隔重新计时
        self._rest_timer.interval = self._reminder_seconds()
        self._rest_timer.reset()
        # 主动互动开关 / 间隔
        self.proactive_enabled = result["proactive_enabled"]
        self.proactive_interval_minutes = result["proactive_interval"]
        self._proactive_timer.interval = self._proactive_seconds()
        self._proactive_timer.reset()
        # 音效 / 语音朗读开关（实际应用与持久化在 Game._save_user_config，经下面回调触发）
        self.sound_enabled = result["sound_enabled"]
        self.tts_enabled = result["tts_enabled"]
        self._on_user_prefs_changed()  # 由 Game 合并写回 user_config（含窗口位置/提醒/主动互动）

        # 统一宠物名称：同时更新 Pet、人格服务与聊天窗口标题，并持久化人格
        personality = self.ai_service.personality
        name = result["name"] or personality.name
        self.pet.set_name(name)
        personality.name = name
        personality.character = result["character"]
        personality.tone = result["tone"]
        personality.save()
        self.chat_window.pet_name = name

        self.ai_config.update(result["ai_config"])
        save_ai_config(self.ai_config)
        self.ai_service.apply_config(self.ai_config)

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
        self._record_chat("user", message)
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
        """处理后台线程结果回传，推进属性变化提示与创建窗口的实时预览。"""
        self._process_ai_replies()
        self._process_ai_test_results()
        self._process_proactive()
        self._update_attr_deltas(dt)
        self._update_rest_reminder(dt)
        self._proactive_timer.update(dt)
        self.speech_bubble.update(dt)
        if self.skin_creator.visible:
            self.skin_creator.update(dt)

    def _reminder_seconds(self) -> float:
        """当前提醒间隔（秒），下限 1 秒避免间隔为 0 时每帧触发。"""
        return max(1.0, self.reminder_interval_minutes * 60.0)

    def _proactive_seconds(self) -> float:
        """当前主动互动间隔（秒），下限 1 秒避免间隔为 0 时每帧触发。"""
        return max(1.0, self.proactive_interval_minutes * 60.0)

    def _update_rest_reminder(self, dt: float) -> None:
        """累计计时，到达提醒间隔时弹出休息提醒气泡（由计时器回调触发）。"""
        self._rest_timer.update(dt)

    def _show_rest_reminder(self) -> None:
        """弹出一条随机休息提醒气泡。"""
        self.speech_bubble.show(
            random.choice(settings.REST_REMINDER_MESSAGES),
            settings.REST_REMINDER_BUBBLE_DURATION,
        )

    def _trigger_proactive(self) -> None:
        """到点尝试让宠物主动说一句：满足条件时后台请求，否则跳过本次。

        跳过条件：已有请求在途、聊天/设置等窗口打开、当前已有气泡显示、
        宠物已隐藏到托盘、或宠物正在睡觉（让它安静睡）。
        """
        if (
            not self.proactive_enabled
            or self._proactive_pending
            or self.blocks_autonomous
            or self.speech_bubble.visible
            or not self.desktop_manager.visible
            or self.pet.current_animation == "sleep"
        ):
            return

        self._proactive_pending = True

        def worker() -> None:
            try:
                text = self.ai_service.proactive_message(self.pet)
            except Exception as exc:
                log_exception(AIServiceError(f"主动互动生成异常: {exc}"))
                text = ""
            self._proactive_queue.put(text)

        threading.Thread(target=worker, daemon=True).start()

    def _process_proactive(self) -> None:
        """把后台生成的主动发言显示为头顶气泡（若期间没被其它气泡占用）。"""
        while not self._proactive_queue.empty():
            text = self._proactive_queue.get_nowait()
            self._proactive_pending = False
            if text and not self.speech_bubble.visible:
                self.speech_bubble.show(text, settings.PROACTIVE_BUBBLE_DURATION)
                if self._tts is not None:
                    self._tts.speak(text)

    def _process_ai_replies(self) -> None:
        """将后台线程中 AIService.chat() 返回的回复写回对话窗口。"""
        while not self._ai_replies.empty():
            reply = self._ai_replies.get_nowait()
            self.chat_window.set_pending(False)
            self.chat_window.add_message("pet", reply)
            self._record_chat("pet", reply)
            if self._tts is not None:
                self._tts.speak(reply)

    def _record_chat(self, sender: str, text: str) -> None:
        """把一条可见对话写入聊天历史并持久化（超上限丢弃最旧）。"""
        self._chat_history.append({"sender": sender, "text": text})
        if len(self._chat_history) > settings.CHAT_HISTORY_LIMIT:
            self._chat_history = self._chat_history[-settings.CHAT_HISTORY_LIMIT:]
        save_json(settings.CHAT_HISTORY_FILE, self._chat_history)

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
        # 设围栏后数值面板也走统一基点（左上角对齐围栏上边），否则贴宠物显示
        force = None
        if self._popup_anchor is not None:
            force = self._popup_anchor((settings.STATS_PANEL_WIDTH, settings.STATS_PANEL_WIDTH))
        # 围栏显隐按钮的动态文案（隐藏围栏 / 显示围栏）
        button_labels = None
        if self._fence_view_label is not None:
            button_labels = {"fence_view": self._fence_view_label()}
        self.stats_panel.draw(
            screen, self.pet_sprite.rect, self._stats_lines(),
            force_topleft=force, button_labels=button_labels,
        )
        self.speech_bubble.draw(screen, self.pet_sprite.rect)
        self.chat_window.draw(screen)
        self.settings_window.draw(screen)
        self.skin_window.draw(screen)
        self.skin_creator.draw(screen)

    def _stats_lines(self) -> List[str]:
        """生成数值信息面板的内容（右键点击宠物弹出）。

        只展示名称、各属性数值与时间；时间为系统真实时间。行为、情绪、
        最近动作等通过宠物动画直接呈现，不再以文字罗列。喂食/玩耍等交互
        引起的属性变化以 +xx/-xx 后缀短暂显示（见 record_attr_deltas）。
        """
        return [
            f"名称: {self.pet.name}",
            f"等级: Lv.{self.pet.level} {self.pet.title()}  ({self.pet.exp:g}/{self.pet.exp_to_next()})",
            f"饥饿: {self.pet.hunger:.1f}{self._attr_delta_suffix('hunger')}",
            f"心情: {self.pet.mood:.1f}{self._attr_delta_suffix('mood')}",
            f"体力: {self.pet.energy:.1f}{self._attr_delta_suffix('energy')}",
            f"时间: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
        ]


def save_ai_config(ai_config: dict) -> None:
    """将 AI 配置写回 config/ai_config.json（独立函数便于测试替换）。"""
    from utils.helper import save_json

    save_json(settings.AI_CONFIG_FILE, ai_config)
