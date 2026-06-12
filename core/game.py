"""游戏主循环模块。

负责 Pygame 的初始化、窗口创建、资源/动画/精灵/行为系统的组装，
宠物数据的读取与保存，以及主循环的运行与退出控制。

交互系统集成方式：

    User Input -> InteractionManager -> BehaviorManager
        -> Pet Attribute -> StateMachine -> AnimationManager

自主行为系统集成方式：

    Pet State -> AutonomousManager -> Behavior Decision
        -> Action Execute -> Animation Update

用户交互优先：拖拽宠物时自主行为暂停，避免两套系统争夺位置/动画。

桌面窗口集成方式：

    Game -> DesktopManager -> OS API（无边框 / 透明 / 置顶 / 隐藏 / 移动）

窗口本身使用 pygame.NOFRAME 创建为无边框窗口；背景填充
settings.TRANSPARENT_COLOR_KEY 后由 DesktopManager 设为透明色键，
使窗口看起来只显示宠物本体，悬浮于桌面之上。

窗口跟随模式（支持桌面窗口能力时，Windows）：

* 宠物固定渲染在窗口中心，Pet.position 表示宠物在屏幕坐标系
  下的位置；自主移动/拖拽统一通过移动整个窗口实现，
  宠物漫游范围为整个屏幕。
* 不支持时（如非 Windows 平台）：退化为"宠物在窗口内移动"
  模式，保证基础可运行。

系统托盘（utils.tray.TrayIcon）运行在独立线程，菜单回调仅将动作
放入队列，由主循环在 _process_tray_actions() 中统一处理，
避免跨线程操作 Pygame / 窗口对象。

AI 对话集成方式：

    Pet -> AIService -> LLM

ChatWindow 仅负责输入框/消息历史的渲染与按键解析；用户提交消息后，
Game 在独立线程中调用 AIService.chat()（避免阻塞主循环/动画），
结果通过 queue.Queue 回传，由 _process_ai_replies() 在主循环中
统一写回 ChatWindow 与宠物记忆。AIService 内部根据
EmotionAnalyzer 的分析结果调整 Pet 属性，并通过 PetBehavior
触发对应的临时动画（如"你累了吗？" -> energy-5、播放 sleep 动画）。
"""

import queue
import sys
import threading

import pygame

from config import settings
from core.action import BehaviorManager
from core.ai.ai_service import AIService
from core.ai.memory import MemoryManager
from core.ai.personality import PersonalityManager
from core.animation import Animation, AnimationManager, AnimationState
from core.autonomous import AutonomousManager
from core.behavior import PetBehavior
from core.desktop import DesktopManager
from core.event import InteractionEvent, InteractionEventType
from core.interaction import InteractionManager
from core.pet import Pet
from core.resource import ResourceManager
from core.skin import SkinManager
from core.sprite import PetSprite
from ui.chat_window import ChatWindow
from ui.settings_window import SettingsWindow
from ui.stats_panel import StatsPanel
from utils.behavior_logger import BehaviorLogger
from utils.exception import AIServiceError, log_exception
from utils.helper import load_json, save_json
from utils.tray import TrayIcon

# 用户交互事件 -> 行为日志文案
INTERACTION_LOG_MESSAGES = {
    InteractionEventType.CLICK: "User clicked pet",
    InteractionEventType.EXCITED: "User excited pet with repeated clicks",
    InteractionEventType.FEED: "User fed pet",
    InteractionEventType.PLAY: "User played with pet",
}

# 设置窗口尺寸（居中显示）
SETTINGS_WINDOW_SIZE = (380, 310)


class Game:
    """游戏主控制类，管理窗口、资源、宠物状态/精灵与主循环生命周期。"""

    def __init__(self):
        pygame.init()

        # 加载桌面窗口配置（透明/置顶/初始位置/启动即隐藏），不存在则使用空字典默认值
        self.desktop_config = load_json(settings.DESKTOP_CONFIG_FILE) or {}

        # 无边框窗口：去除标题栏/边框，配合 DesktopManager 实现桌面悬浮效果
        self.screen = pygame.display.set_mode(
            (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT), pygame.NOFRAME
        )
        pygame.display.set_caption(settings.WINDOW_TITLE)

        # 桌面窗口能力：透明 / 置顶 / 隐藏 / 移动，统一通过 DesktopManager 操作 OS API
        self.desktop_manager = DesktopManager(self.desktop_config)
        self._topmost_timer = 0.0
        self._drag_anchor = None

        self.clock = pygame.time.Clock()
        self.running = True

        self.resource_manager = ResourceManager()

        # 皮肤系统：根据 config/skin_config.json 决定动画帧来源，
        # 皮肤未覆盖的状态自动回退到内置动画（assets/animations/）
        self.skin_manager = SkinManager()

        # 启动时尝试从 JSON 存档读取宠物数据，不存在或损坏则使用默认属性
        pet_data = load_json(settings.PET_DATA_FILE)
        self.pet = Pet.from_dict(pet_data) if pet_data else Pet()

        self.behavior = PetBehavior(self.pet)
        self.pet_sprite = PetSprite(self.pet, self._build_animation_manager())

        # 交互系统：用户输入 -> InteractionManager -> BehaviorManager
        self.interaction_manager = InteractionManager(self.pet_sprite)
        self.behavior_manager = BehaviorManager()

        # 自主行为系统：Pet State -> AutonomousManager -> Behavior Decision -> Action
        behavior_config = load_json(settings.BEHAVIOR_CONFIG_FILE)
        self.behavior_logger = BehaviorLogger(settings.PET_BEHAVIOR_LOG_FILE)
        self.autonomous_manager = AutonomousManager(
            self.pet, self.behavior, behavior_config, self.behavior_logger
        )

        # 窗口跟随模式：宠物固定渲染在窗口中心，Pet.position 为屏幕坐标，
        # 移动通过移动整个窗口实现，漫游范围扩展为整个屏幕
        self._window_center = (settings.WINDOW_WIDTH // 2, settings.WINDOW_HEIGHT // 2)
        self._window_pos = self.desktop_manager.get_position()
        if self.desktop_manager.supported:
            self.pet_sprite.render_center = self._window_center
            self.pet.set_position(
                self._window_pos[0] + self._window_center[0],
                self._window_pos[1] + self._window_center[1],
            )
            self.autonomous_manager.movement.set_bounds(
                *self.desktop_manager.get_screen_size()
            )

        # 界面字体：必须使用含中文字形的系统字体（settings.UI_FONT_NAMES），
        # 否则聊天窗口/面板中的中文会渲染为方块乱码
        self.ui_font = pygame.font.SysFont(settings.UI_FONT_NAMES, settings.UI_FONT_SIZE)

        # 宠物数值信息面板：右键点击宠物弹出/关闭
        self.stats_panel = StatsPanel(self.ui_font)

        # 交互引起的属性变化（属性名 -> [变化量, 剩余显示时间]），
        # 在数值面板对应行后以 +xx/-xx 形式短暂显示
        self._attr_deltas: dict = {}

        # 用户偏好（宠物大小等）与设置窗口
        user_config = load_json(settings.USER_CONFIG_FILE) or {}
        self.pet_sprite.scale = user_config.get("pet_scale", settings.PET_SCALE_DEFAULT)
        settings_rect = pygame.Rect(
            (settings.WINDOW_WIDTH - SETTINGS_WINDOW_SIZE[0]) // 2,
            (settings.WINDOW_HEIGHT - SETTINGS_WINDOW_SIZE[1]) // 2,
            *SETTINGS_WINDOW_SIZE,
        )
        self.settings_window = SettingsWindow(self.ui_font, settings_rect)
        self._ai_test_results: "queue.Queue[tuple]" = queue.Queue()

        # 宠物数据自动存档计时器（settings.AUTOSAVE_INTERVAL 秒一次）
        self._autosave_timer = 0.0

        # AI 服务：Pet -> AIService -> LLM，人格/记忆数据持久化到 data/ 下的 JSON 文件
        # ai_config 保留引用，供设置窗口读取/更新后写回
        self.ai_config = load_json(settings.AI_CONFIG_FILE) or {}
        self.personality = PersonalityManager()
        self.memory = MemoryManager()
        self.ai_service = AIService(self.ai_config, self.personality, self.memory, self.behavior)

        # AI 对话窗口：UI 与 AIService 解耦，AI 回复在后台线程获取，经队列回传主循环
        chat_rect = pygame.Rect(
            settings.CHAT_WINDOW_MARGIN,
            settings.CHAT_WINDOW_MARGIN,
            settings.WINDOW_WIDTH - 2 * settings.CHAT_WINDOW_MARGIN,
            settings.CHAT_WINDOW_HEIGHT,
        )
        self.chat_window = ChatWindow(self.ui_font, chat_rect, pet_name=self.personality.name)
        self._ai_replies: "queue.Queue[str]" = queue.Queue()

        # 系统托盘：菜单回调在后台线程执行，仅将动作放入队列，主循环统一处理
        self._tray_actions: "queue.Queue[str]" = queue.Queue()
        self.tray_icon = TrayIcon(
            on_show=lambda: self._tray_actions.put("show"),
            on_hide=lambda: self._tray_actions.put("hide"),
            on_save=lambda: self._tray_actions.put("save"),
            on_exit=lambda: self._tray_actions.put("exit"),
        )

    def _build_animation_manager(self) -> AnimationManager:
        """根据配置加载各动画状态的帧资源，构建 AnimationManager。

        优先使用当前皮肤（SkinManager）提供的帧目录，
        皮肤未覆盖的状态回退到内置动画目录。
        """
        animations = {}
        for state in AnimationState:
            folder = (
                self.skin_manager.animation_dir(state.value)
                or settings.ANIMATION_FOLDERS[state.value]
            )
            frame_duration = settings.ANIMATION_FRAME_DURATIONS[state.value]
            frames = self.resource_manager.load_animation(folder)
            animations[state] = Animation(frames, frame_duration=frame_duration)

        default_state = AnimationState(settings.DEFAULT_ANIMATION_STATE)
        return AnimationManager(animations, default_state=default_state)

    def run(self):
        """启动主循环，直到用户关闭窗口或主动退出。

        帧率分三档：窗口隐藏时 BACKGROUND_FPS；活跃（移动/拖拽/
        UI 窗口打开）时 FPS；其余空闲时 IDLE_FPS，降低常驻开销。
        """
        self.tray_icon.run_detached()

        while self.running:
            dt = self.clock.tick(self._target_fps()) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()

        self._quit()

    def _target_fps(self) -> int:
        """根据当前状态选择主循环帧率档位。"""
        if not self.desktop_manager.visible:
            return settings.BACKGROUND_FPS

        active = (
            self.interaction_manager.dragging
            or self.chat_window.visible
            or self.settings_window.visible
            or self.stats_panel.visible
            or self.autonomous_manager.movement.has_target()
        )
        return settings.FPS if active else settings.IDLE_FPS

    def _handle_events(self):
        """处理窗口事件：关闭窗口，AI 对话窗口输入，以及鼠标/键盘交互事件。

        AI 对话窗口打开时，键盘事件（文本输入/退格/回车/Esc）与鼠标滚轮
        事件由 ChatWindow 处理，不再转发给 InteractionManager，
        避免输入聊天内容时触发喂食/玩耍等功能按键。
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            # 设置窗口为模态：打开期间所有输入事件均由其处理
            if self.settings_window.visible:
                if event.type in (
                    pygame.KEYDOWN, pygame.TEXTINPUT, pygame.MOUSEBUTTONDOWN,
                ):
                    result = self.settings_window.handle_event(event)
                    if result is not None:
                        self._handle_settings_result(result)
                continue

            if event.type == pygame.KEYDOWN and not self.chat_window.visible:
                if pygame.key.name(event.key) == settings.CHAT_TOGGLE_KEY:
                    self.chat_window.toggle()
                    self.desktop_manager.focus()
                    continue

            if self.chat_window.visible and event.type in (
                pygame.KEYDOWN, pygame.TEXTINPUT, pygame.MOUSEWHEEL,
            ):
                message = self.chat_window.handle_event(event)
                if message:
                    self._send_chat_message(message)
                continue

            # 数值面板内的左键点击（功能按钮）优先于宠物交互处理，
            # 避免面板覆盖宠物区域时点按钮被误判为点击/拖拽宠物
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.stats_panel.contains(event.pos)
            ):
                self._handle_panel_action(self.stats_panel.handle_click(event.pos))
                continue

            interaction_event = self.interaction_manager.handle_event(event)
            if interaction_event is not None:
                self._dispatch_interaction(interaction_event)

    def _dispatch_interaction(self, interaction_event: InteractionEvent):
        """将交互事件交给 BehaviorManager 处理，并应用其结果。

        拖拽开始/移动/结束属于位置更新，不经过 BehaviorManager；
        其余事件统一走 BehaviorManager -> Pet Attribute -> 临时动画。
        """
        if interaction_event.type == InteractionEventType.STATS_TOGGLE:
            self.stats_panel.toggle()
            return

        if interaction_event.type == InteractionEventType.DRAG_START:
            self._begin_window_drag()
            return

        if interaction_event.type == InteractionEventType.DRAG_MOVE:
            if self._drag_anchor is not None:
                self._update_window_drag()
            else:
                self.pet.set_position(*interaction_event.position)
            return

        if interaction_event.type == InteractionEventType.DRAG_END:
            self._drag_anchor = None
            return

        # 记录行为前后的属性变化，在数值面板对应行后以 +xx/-xx 显示
        before = (self.pet.hunger, self.pet.mood, self.pet.energy)

        result = self.behavior_manager.handle(interaction_event, self.pet)
        if result is None:
            return

        self.behavior.trigger_temporary_animation(result.animation, result.duration)
        self._record_attr_deltas(before)

        log_message = INTERACTION_LOG_MESSAGES.get(interaction_event.type)
        if log_message is not None:
            self.behavior_logger.log(log_message)

        self.ai_service.notify_interaction(self.pet, interaction_event.type.value)

    def _begin_window_drag(self):
        """开始拖拽：记录窗口移动的起始锚点（窗口移动拖拽）。

        仅在支持桌面窗口能力（Windows）时记录锚点；不支持的平台
        self._drag_anchor 保持 None，DRAG_MOVE 将退化为"宠物在
        窗口内移动"的普通互动拖拽，二者通过 self._drag_anchor 是否
        为 None 区分，互不干扰。
        """
        if not self.desktop_manager.supported:
            return

        self._drag_anchor = (
            self.desktop_manager.get_cursor_position(),
            self.desktop_manager.get_position(),
        )

    def _update_window_drag(self):
        """根据鼠标在屏幕坐标系下的位移，移动整个桌宠窗口（窗口移动拖拽）。

        同步更新 Pet.position（屏幕坐标），保持"窗口中心 = 宠物位置"
        的不变式，避免拖拽结束后窗口被 _sync_window_to_pet() 拉回原位。
        """
        start_cursor, start_window = self._drag_anchor
        cursor_x, cursor_y = self.desktop_manager.get_cursor_position()
        new_x = start_window[0] + cursor_x - start_cursor[0]
        new_y = start_window[1] + cursor_y - start_cursor[1]

        self.desktop_manager.set_position(new_x, new_y)
        self._window_pos = (new_x, new_y)
        self.pet.set_position(
            new_x + self._window_center[0], new_y + self._window_center[1]
        )

    def _sync_window_to_pet(self):
        """窗口跟随宠物：使窗口中心始终对准宠物的屏幕坐标。"""
        if not self.desktop_manager.supported:
            return

        target = (
            self.pet.position[0] - self._window_center[0],
            self.pet.position[1] - self._window_center[1],
        )
        if target != self._window_pos:
            self.desktop_manager.set_position(*target)
            self._window_pos = target

    def _handle_panel_action(self, action) -> None:
        """分发数值面板功能按钮的动作（喂食 / 玩耍 / 聊天 / 设置）。"""
        if action == "feed":
            self._dispatch_interaction(InteractionEvent(type=InteractionEventType.FEED))
        elif action == "play":
            self._dispatch_interaction(InteractionEvent(type=InteractionEventType.PLAY))
        elif action == "chat":
            self.chat_window.toggle()
            self.stats_panel.hide()
            if self.chat_window.visible:
                self.desktop_manager.focus()
        elif action == "settings":
            self.settings_window.open(self.pet_sprite.scale, self.ai_config)
            self.stats_panel.hide()
            self.desktop_manager.focus()

    def _handle_settings_result(self, result: dict) -> None:
        """应用设置窗口的保存/测试结果。"""
        if result.get("action") == "test":
            self._test_ai_config(result["ai_config"])
            return

        if result.get("action") == "save":
            self.pet_sprite.scale = result["pet_scale"]
            save_json(settings.USER_CONFIG_FILE, {"pet_scale": result["pet_scale"]})

            self.ai_config.update(result["ai_config"])
            save_json(settings.AI_CONFIG_FILE, self.ai_config)
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

    def _process_ai_test_results(self) -> None:
        """将后台线程的连接测试结果写回设置窗口状态行。"""
        while not self._ai_test_results.empty():
            ok, message = self._ai_test_results.get_nowait()
            self.settings_window.set_status(message, ok)

    def _record_attr_deltas(self, before: tuple) -> None:
        """对比交互前后的属性值，记录非零变化量供数值面板显示。"""
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

    def _send_chat_message(self, message: str) -> None:
        """提交用户输入的聊天消息：显示在对话窗口，并在后台线程调用 AIService。

        LLM 请求可能耗时（网络延迟/超时），在独立线程中执行以避免
        阻塞主循环（动画刷新、置顶维持、托盘响应等）。
        """
        self.chat_window.add_message("user", message)
        self.chat_window.set_pending(True)

        def worker() -> None:
            # 兜底捕获所有异常：工作线程若意外死亡，回复永远不会入队，
            # 聊天窗口将永久停留在"正在输入"状态（pending 无法复位）
            try:
                reply = self.ai_service.chat(self.pet, message)
            except Exception as exc:
                log_exception(AIServiceError(f"聊天处理出现意外异常: {exc}"))
                reply = "（呜……我刚才走神了，再和我说一遍好吗？）"
            self._ai_replies.put(reply)

        threading.Thread(target=worker, daemon=True).start()

    def _process_ai_replies(self) -> None:
        """将后台线程中 AIService.chat() 返回的回复写回对话窗口。"""
        while not self._ai_replies.empty():
            reply = self._ai_replies.get_nowait()
            self.chat_window.set_pending(False)
            self.chat_window.add_message("pet", reply)

    def _update(self, dt: float):
        """逐帧更新逻辑：处理托盘动作、AI 回复、宠物行为/自主行为决策/动画与交互提示。"""
        self._process_tray_actions()
        self._process_ai_replies()
        self._process_ai_test_results()

        self.behavior.update(dt)
        # 拖拽中或聊天/设置窗口打开时暂停自主行为：
        # 窗口跟随模式下漫游会移动整个窗口，输入期间窗口必须保持静止
        interaction_active = (
            self.interaction_manager.dragging
            or self.chat_window.visible
            or self.settings_window.visible
        )
        self.autonomous_manager.update(dt, interaction_active)
        self._sync_window_to_pet()
        self.pet_sprite.update(dt)
        self._update_attr_deltas(dt)

        self._refresh_topmost(dt)
        self._autosave(dt)

    def _autosave(self, dt: float) -> None:
        """定期自动保存宠物数据，避免进程异常退出丢失进度。"""
        self._autosave_timer += dt
        if self._autosave_timer >= settings.AUTOSAVE_INTERVAL:
            self._autosave_timer = 0.0
            save_json(settings.PET_DATA_FILE, self.pet.to_dict())

    def _update_attr_deltas(self, dt: float) -> None:
        """推进属性变化提示的剩余显示时间，移除已过期的条目。"""
        expired = []
        for name, entry in self._attr_deltas.items():
            entry[1] -= dt
            if entry[1] <= 0:
                expired.append(name)
        for name in expired:
            del self._attr_deltas[name]

    def _process_tray_actions(self):
        """处理系统托盘菜单产生的动作（显示/隐藏/保存/退出）。"""
        while not self._tray_actions.empty():
            action = self._tray_actions.get_nowait()

            if action == "show":
                self.desktop_manager.show()
            elif action == "hide":
                self.desktop_manager.hide()
            elif action == "save":
                save_json(settings.PET_DATA_FILE, self.pet.to_dict())
            elif action == "exit":
                self.running = False

    def _refresh_topmost(self, dt: float):
        """周期性维持窗口置顶状态，避免每帧调用系统 API 影响性能。"""
        if not self.desktop_config.get("always_on_top", False):
            return

        self._topmost_timer += dt
        if self._topmost_timer >= settings.TOPMOST_REFRESH_INTERVAL:
            self._topmost_timer = 0.0
            self.desktop_manager.keep_on_top()

    def _render(self):
        """渲染当前帧：填充背景（透明色键或白色）、绘制宠物精灵、数值面板与交互提示。"""
        if self.desktop_manager.supported and self.desktop_config.get("transparent", False):
            background_color = settings.TRANSPARENT_COLOR_KEY
        else:
            background_color = (255, 255, 255)

        self.screen.fill(background_color)
        self.pet_sprite.draw(self.screen)
        self.stats_panel.draw(self.screen, self.pet_sprite.rect, self._stats_lines())
        self.chat_window.draw(self.screen)
        self.settings_window.draw(self.screen)
        pygame.display.flip()

    def _stats_lines(self):
        """生成数值信息面板的内容（右键点击宠物弹出）。

        喂食/玩耍等交互引起的属性变化以 +xx/-xx 后缀短暂显示在
        对应属性行后（见 _record_attr_deltas / _attr_delta_suffix）。
        """
        return [
            f"名称: {self.pet.name}  年龄: {self.pet.age}",
            f"状态: {self.pet.current_state.name}",
            f"饥饿: {self.pet.hunger:.1f}{self._attr_delta_suffix('hunger')}",
            f"心情: {self.pet.mood:.1f}{self._attr_delta_suffix('mood')}",
            f"体力: {self.pet.energy:.1f}{self._attr_delta_suffix('energy')}",
            f"最近动作: {self.pet.last_action or '无'}",
            f"互动次数: {self.pet.interaction_count}",
            f"行为: {self.autonomous_manager.current_behavior.name}",
            f"情绪: {self.autonomous_manager.emotion.name}",
            f"时间: {self.autonomous_manager.schedule.time_of_day()}"
            f" (第 {self.autonomous_manager.schedule.day_count} 天)",
        ]

    def _quit(self):
        """停止系统托盘、保存宠物数据并安全退出 Pygame 与程序。"""
        self.tray_icon.stop()
        save_json(settings.PET_DATA_FILE, self.pet.to_dict())
        pygame.quit()
        sys.exit()
