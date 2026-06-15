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
* 坐标换算与窗口移动由 core.window_controller.WindowController
  统一维护（"窗口中心 = 宠物屏幕坐标"不变式），Game 不直接
  操作窗口位置 / 拖拽锚点。

系统托盘（utils.tray.TrayIcon）运行在独立线程，菜单回调仅将动作
放入队列，由主循环在 _process_tray_actions() 中统一处理，
避免跨线程操作 Pygame / 窗口对象。

界面窗口（聊天 / 数值面板 / 设置）由 ui.ui_manager.UIManager 统一
管理：界面相关事件由 UIManager 优先消化，未消化的事件再交给
InteractionManager 产出宠物交互。聊天与连接测试在独立线程中调用
AIService（避免阻塞主循环），结果经 queue.Queue 回传，由
UIManager.update() 在主循环中写回界面。喂食/玩耍按钮经回调回到
Game._dispatch_interaction 走完整交互管线：

    Pet -> AIService -> LLM

AIService 内部根据 EmotionAnalyzer 的分析结果调整 Pet 属性，
并通过 PetBehavior 触发对应的临时动画
（如"你累了吗？" -> energy-5、播放 sleep 动画）。
"""

import queue
import sys

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
from core.feeding import FeedingController
from core.fence import FenceController, popup_topleft
from core.sound import SoundManager
from core.interaction import InteractionManager
from core.pet import Pet
from core.resource import ResourceManager
from core.skin import SkinManager
from core.sprite import PetSprite
from core.window_controller import WindowController
from ui import food_icon
from ui.ui_manager import UIManager
from utils.behavior_logger import BehaviorLogger
from utils.exception import AIServiceError, log_exception
from utils.helper import load_json, save_json
from utils.timer import IntervalTimer
from utils.tray import TrayIcon

# 用户交互事件 -> 行为日志文案
INTERACTION_LOG_MESSAGES = {
    InteractionEventType.CLICK: "User clicked pet",
    InteractionEventType.EXCITED: "User excited pet with repeated clicks",
    InteractionEventType.FEED: "User fed pet",
    InteractionEventType.PLAY: "User played with pet",
    InteractionEventType.BATH: "User bathed pet",
    InteractionEventType.SLEEP: "User put pet to sleep",
    InteractionEventType.GIFT: "User gave pet a gift",
}

# 交互类型 -> 音效名（core/sound.py 的 EVENT_NOTES 键）；未列出的交互不发声
INTERACTION_SOUNDS = {
    InteractionEventType.CLICK: "click",
    InteractionEventType.EXCITED: "excited",
    InteractionEventType.FEED: "feed",
    InteractionEventType.PLAY: "play",
    InteractionEventType.BATH: "bath",
    InteractionEventType.GIFT: "gift",
}


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
        # 周期性维持窗口置顶（避免每帧调用系统 API），到点触发 keep_on_top
        self._topmost_timer = IntervalTimer(
            settings.TOPMOST_REFRESH_INTERVAL, self.desktop_manager.keep_on_top
        )

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

        # 电子围栏与喂食放置控制器（纯状态机），由 Game 编排接入移动/事件/渲染
        self.fence_controller = FenceController()
        self.feeding = FeedingController()
        self.autonomous_manager.on_food_reached = self._on_food_reached

        # 用户偏好（宠物大小、窗口位置等），整局共用一份，退出时合并写回
        self.user_config = load_json(settings.USER_CONFIG_FILE) or {}

        # 互动音效（程序化合成，离线自包含；音频不可用时静默降级）
        self.sound = SoundManager(
            enabled=self.user_config.get("sound_enabled", settings.SOUND_ENABLED),
            volume=settings.SOUND_VOLUME,
        )

        # 窗口跟随控制器：维护"窗口中心 = 宠物屏幕坐标"，集中处理窗口移动/拖拽。
        # 优先使用上次退出时保存的窗口位置，否则用 desktop_manager 的初始位置
        self.window = WindowController(
            self.desktop_manager, self.pet, self.pet_sprite,
            (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT),
        )
        self.window.initialize(self.user_config.get("window_position"))
        if self.desktop_manager.supported:
            # 漫游范围用整个虚拟桌面（多显示器并集），宠物可跨屏漫游；
            # 内缩半个窗口，确保窗口（及右键面板）始终留在桌面内。
            vx, vy, vw, vh = self.desktop_manager.get_virtual_screen()
            self.autonomous_manager.movement.set_bounds(
                vw, vh, inset=self.window.center, origin=(vx, vy)
            )

        # 恢复上次保存的电子围栏（窗口模式切换需 UI 就绪，故延后到 __init__ 末尾）。
        # 退化（过小）的存档围栏直接忽略，避免窗口缩成一个点导致无法操作。
        saved_fence = self.user_config.get("fence")
        if saved_fence and not self._fence_too_small(tuple(saved_fence)):
            self.fence_controller.fence = tuple(saved_fence)
        # 围栏边框是否显示（可一键隐藏，持久化）
        self._fence_visible = self.user_config.get("fence_visible", True)
        # 是否处于围栏「全屏取点态」（点两个对角定围栏）
        self._fence_selecting = False
        # 喂食放置是否借用了全屏遮罩（无围栏时铺满全屏，结束后恢复跟随窗口）
        self._feed_overlay = False

        # 界面字体：必须使用含中文字形的系统字体（settings.UI_FONT_NAMES），
        # 否则聊天窗口/面板中的中文会渲染为方块乱码
        self.ui_font = pygame.font.SysFont(settings.UI_FONT_NAMES, settings.UI_FONT_SIZE)

        # 宠物大小读取自上面加载的 user_config
        self.pet_sprite.scale = self.user_config.get("pet_scale", settings.PET_SCALE_DEFAULT)

        # 宠物数据自动存档计时器（settings.AUTOSAVE_INTERVAL 秒一次）
        self._autosave_timer = IntervalTimer(settings.AUTOSAVE_INTERVAL, self._save_pet_data)

        # AI 服务：Pet -> AIService -> LLM，人格/记忆数据持久化到 data/ 下的 JSON 文件
        # ai_config 保留引用，供设置窗口读取/更新后写回
        self.ai_config = load_json(settings.AI_CONFIG_FILE) or {}
        self.personality = PersonalityManager()
        self.memory = MemoryManager()
        self.ai_service = AIService(self.ai_config, self.personality, self.memory, self.behavior)

        # 统一宠物名称：以人格服务的名称为准，同步到 Pet（数值面板与聊天窗口共用同一名称）
        self.pet.set_name(self.personality.name)

        # 界面管理器：聊天窗口 / 数值面板 / 设置窗口及其事件路由与异步结果回传。
        # 喂食/玩耍按钮经 on_interaction 回到交互分发管线；
        # 保存设置后经 on_user_prefs_changed 让 Game 合并持久化用户偏好。
        self.ui = UIManager(
            self.ui_font, self.pet, self.pet_sprite, self.autonomous_manager,
            self.ai_service, self.desktop_manager, self.ai_config,
            (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT),
            on_interaction=self._dispatch_interaction,
            on_user_prefs_changed=self._save_user_config,
            skin_manager=self.skin_manager,
            on_skin_change=self._apply_skin,
            on_skin_create=self.create_skin,
            reminder_interval_minutes=self.user_config.get(
                "reminder_interval_minutes", settings.REST_REMINDER_INTERVAL_MINUTES
            ),
            proactive_enabled=self.user_config.get(
                "proactive_enabled", settings.PROACTIVE_CHAT_ENABLED
            ),
            proactive_interval_minutes=self.user_config.get(
                "proactive_interval_minutes", settings.PROACTIVE_CHAT_INTERVAL_MINUTES
            ),
            sound_enabled=self.user_config.get("sound_enabled", settings.SOUND_ENABLED),
            on_feed_place_start=self._start_feed_placement,
            on_fence_toggle=self._toggle_fence,
            on_fence_view_toggle=self._toggle_fence_view,
            fence_view_label=self._fence_view_label,
            on_quit=self._request_quit,
            popup_anchor=self._popup_topleft,
        )

        # 系统托盘：菜单回调在后台线程执行，仅将动作放入队列，主循环统一处理
        self._tray_actions: "queue.Queue[str]" = queue.Queue()
        self.tray_icon = TrayIcon(
            on_show=lambda: self._tray_actions.put("show"),
            on_hide=lambda: self._tray_actions.put("hide"),
            on_save=lambda: self._tray_actions.put("save"),
            on_exit=lambda: self._tray_actions.put("exit"),
        )

        # 启动时若已存有围栏，直接进入围栏窗口模式（窗口=围栏矩形、固定、宠物在内漫游）。
        # 须在 self.window / self.ui 构造完成之后进行（依赖窗口几何与 UI 画布尺寸联动）。
        if self.fence_controller.fence is not None:
            self._enter_fence_mode(self.fence_controller.fence)

    def _build_animation_manager(self) -> AnimationManager:
        """根据配置加载各动画状态的帧资源，构建 AnimationManager。

        优先使用当前皮肤（SkinManager）提供的帧目录，
        皮肤未覆盖的状态回退到内置动画目录。
        """
        animations = {}
        skin_durations = self.skin_manager.frame_durations()
        for state in AnimationState:
            folder = (
                self.skin_manager.animation_dir(state.value)
                or settings.ANIMATION_FOLDERS[state.value]
            )
            # 优先使用皮肤自定义的播放速度，否则用内置默认速度
            frame_duration = skin_durations.get(
                state.value, settings.ANIMATION_FRAME_DURATIONS[state.value]
            )
            frames = self.resource_manager.load_animation(folder)
            animations[state] = Animation(frames, frame_duration=frame_duration)

        default_state = AnimationState(settings.DEFAULT_ANIMATION_STATE)
        return AnimationManager(animations, default_state=default_state)

    def _apply_skin(self, skin_name: str) -> None:
        """切换皮肤并即时生效（无需重启）：持久化选择并重建动画管理器。"""
        if skin_name == self.skin_manager.active_skin:
            return

        self.skin_manager.set_active(skin_name)
        self.pet_sprite.animation_manager = self._build_animation_manager()
        # 旧皮肤的镜像/缩放变换缓存按帧 id 缓存，换皮肤后失效，清空避免占用
        self.pet_sprite._transform_cache.clear()

    def _reload_skin(self, skin_name: str) -> None:
        """强制重载皮肤（用于新建/重建皮肤后）：清资源缓存并重建动画。

        与 _apply_skin 不同，本方法不做"已是当前皮肤就跳过"的优化，
        且清空 ResourceManager 的动画缓存，确保读到磁盘上的新帧。
        """
        self.resource_manager._animation_cache.clear()
        self.skin_manager.set_active(skin_name)
        self.pet_sprite.animation_manager = self._build_animation_manager()
        self.pet_sprite._transform_cache.clear()

    def create_skin(self, config: dict):
        """根据创建皮肤窗口的配置构建皮肤并即时启用，返回 (成功, 提示文案)。"""
        from core import skin_builder

        name = (config.get("name") or "").strip()
        if not name:
            return False, "请先填写皮肤名称"

        try:
            if config["mode"] == "sheet":
                sheets = [s for s in config.get("sheets", []) if s.get("path")]
                if not sheets:
                    return False, "请先添加精灵图"
                if not any(
                    st and st not in skin_builder.SKIP_TOKENS
                    for s in sheets for st in (s.get("frame_states") or [])
                ):
                    return False, "请为至少一帧指定动画状态"
                skin_builder.build_from_sheets(
                    name, sheets, frame_durations=config.get("speeds")
                )
            else:
                state_paths = {s: [p] for s, p in config.get("state_paths", {}).items() if p}
                if not state_paths:
                    return False, "请至少为一个状态选择图片"
                skin_builder.build_from_state_images(
                    name, state_paths,
                    chroma_color=config.get("chroma_color"),
                    mirror=config.get("mirror", False),
                    frame_durations=config.get("speeds"),
                )
        except Exception as exc:
            log_exception(AIServiceError(f"创建皮肤失败: {exc}"))
            return False, f"创建失败：{exc}"

        self._reload_skin(name)
        return True, f"皮肤「{name}」已创建并启用"

    def run(self):
        """启动主循环，直到用户关闭窗口或主动退出。

        帧率分三档：窗口隐藏时 BACKGROUND_FPS；活跃（移动/拖拽/
        UI 窗口打开）时 FPS；其余空闲时 IDLE_FPS，降低常驻开销。
        """
        self.tray_icon.run_detached()

        while self.running:
            # 钳制单帧时间步长：进程被系统挂起/降频后下一帧 dt 可能极大，
            # 不钳制会导致移动一步跳变（"闪现"）与属性瞬间大幅衰减。
            dt = min(self.clock.tick(self._target_fps()) / 1000.0, settings.MAX_FRAME_DT)
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
            or self._fence_selecting
            or self.ui.is_active
            or self.autonomous_manager.movement.has_target()
            or self.feeding.placing
            or self.feeding.has_food
        )
        return settings.FPS if active else settings.IDLE_FPS

    def _handle_events(self):
        """处理窗口事件：关闭窗口、界面窗口输入，以及鼠标/键盘交互事件。

        界面相关事件（设置窗口模态、聊天输入、面板按钮）由 UIManager
        优先消化；未被消化的事件再交给 InteractionManager 产出交互事件，
        避免输入聊天内容/点击面板按钮时误触发宠物交互。
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            # 围栏全屏取点态：左键点两个对角/右键或 Esc 取消，优先消化
            if self._fence_selecting and self._handle_fence_selection(event):
                continue

            # 喂食放置模式：左键放下/右键取消/移出围栏自动取消，优先消化
            if self.feeding.placing and self._handle_feed_placement(event):
                continue

            if self.ui.handle_event(event):
                continue

            interaction_event = self.interaction_manager.handle_event(event)
            if interaction_event is not None:
                self._dispatch_interaction(interaction_event)

    def _dispatch_interaction(self, interaction_event: InteractionEvent):
        """将交互事件交给 BehaviorManager 处理，并应用其结果。

        拖拽开始/移动/结束属于位置更新，不经过 BehaviorManager；
        睡觉是持续模式，单独拦截；查看面板不唤醒；其余交互会唤醒
        正在睡觉的宠物，再统一走 BehaviorManager -> Pet Attribute -> 临时动画。
        """
        if interaction_event.type == InteractionEventType.STATS_TOGGLE:
            self.ui.toggle_stats_panel()
            return

        # 睡觉：进入持续睡眠模式（停在原地、随时间缓慢回体力），
        # 不走一次性行为管线
        if interaction_event.type == InteractionEventType.SLEEP:
            self.behavior.start_sleep()
            self.pet.record_interaction(interaction_event.type.value)
            self.behavior_logger.log(INTERACTION_LOG_MESSAGES[InteractionEventType.SLEEP])
            return

        # 其余任何交互（点击/拖拽/喂食/玩耍/洗澡/送礼）都唤醒睡觉中的宠物
        if self.behavior.is_sleeping:
            self.behavior.stop_sleep()

        if interaction_event.type == InteractionEventType.DRAG_START:
            self.window.begin_drag()
            return

        if interaction_event.type == InteractionEventType.DRAG_MOVE:
            if self.window.dragging_window:
                self.window.update_drag()
            elif self.window.supported and not self.window.follow:
                # 围栏模式：窗口固定，拖拽移动宠物本身；
                # 交互事件的位置是画布坐标，需换算回宠物所用的屏幕坐标。
                self.pet.set_position(*self._to_screen(interaction_event.position))
            else:
                self.pet.set_position(*interaction_event.position)
            return

        if interaction_event.type == InteractionEventType.DRAG_END:
            self.window.end_drag()
            return

        # 记录行为前后的属性变化，在数值面板对应行后以 +xx/-xx 显示
        before = (self.pet.hunger, self.pet.mood, self.pet.energy)

        result = self.behavior_manager.handle(interaction_event, self.pet)
        if result is None:
            return

        self.behavior.trigger_temporary_animation(result.animation, result.duration)
        self.ui.record_attr_deltas(before)
        self.sound.play(INTERACTION_SOUNDS.get(interaction_event.type))

        log_message = INTERACTION_LOG_MESSAGES.get(interaction_event.type)
        if log_message is not None:
            self.behavior_logger.log(log_message)

        self.ai_service.notify_interaction(self.pet, interaction_event.type.value)

    # ----- 喂食放置 -----

    def _to_screen(self, pos):
        """把窗口内坐标换算为与 Pet.position 一致的坐标（跟随模式下为屏幕坐标）。"""
        return (self.window.window_pos[0] + pos[0], self.window.window_pos[1] + pos[1])

    def _start_feed_placement(self) -> None:
        """进入喂食放置模式（食物图标开始跟随鼠标）。

        放置范围 = 围栏内（已设围栏，此时窗口本就是围栏矩形）或全屏（无围栏，
        借用全屏遮罩，使食物可放在桌面任意处，而不局限于宠物周围的小窗口）。
        """
        self.feeding.start_placing()
        if self.fence_controller.fence is None:
            self._feed_overlay = True
            self._enter_fullscreen_overlay()

    def _end_feed_placement(self) -> None:
        """退出喂食放置：已放下的食物保留；若借用了全屏遮罩则恢复跟随窗口。"""
        self.feeding.cancel_placing()
        if self._feed_overlay:
            self._feed_overlay = False
            self._enter_follow_mode()

    def _handle_feed_placement(self, event) -> bool:
        """放置模式下的鼠标事件：左键放下（可连续放多个）、右键退出、移出围栏退出。

        返回 True 表示已消化（主循环不再交给界面/交互系统处理）。
        """
        if event.type == pygame.MOUSEMOTION:
            if not self.fence_controller.contains(self._to_screen(event.pos)):
                self._end_feed_placement()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            screen = self._to_screen(event.pos)
            if not self.fence_controller.contains(screen):
                self._end_feed_placement()
                return True
            if self.feeding.is_full(settings.FOOD_MAX_COUNT):
                # 达到食物上限：忽略本次放置但保持放置模式，给气泡提示
                self.ui.show_bubble("我已经有好多吃的啦，先吃完这些再喂吧~")
                return True
            self.feeding.add(screen, settings.FOOD_MAX_COUNT)  # 保持放置模式，可继续放下一个
            # 当前没有正在走向的食物时，立即以这份为目标
            if self.autonomous_manager.food_target is None:
                self.autonomous_manager.food_target = screen
            if self.behavior.is_sleeping:
                self.behavior.stop_sleep()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._end_feed_placement()
            return True

        return False

    def _on_food_reached(self, point) -> None:
        """宠物走到一份食物处：移除该份、复用喂食管线吃掉，还有剩余则走向下一个。"""
        self.feeding.remove(point)
        self._dispatch_interaction(InteractionEvent(type=InteractionEventType.FEED))
        if self.feeding.foods:
            self.autonomous_manager.food_target = self.feeding.foods[0]

    # ----- 电子围栏 -----

    def _toggle_fence(self) -> None:
        """处理面板「围栏」点击：已有围栏则清除并恢复跟随窗口；否则进入全屏取点态。"""
        if self.fence_controller.fence is not None:
            self.fence_controller.clear()
            self._enter_follow_mode()
            self._save_user_config()
            self.ui.show_bubble(settings.FENCE_MESSAGES["cleared"])
            return

        self._fence_selecting = True
        self.fence_controller.clear()  # 清掉可能残留的待定取点
        self._enter_fullscreen_overlay()
        self.ui.show_bubble(settings.FENCE_MESSAGES["start"])

    def _handle_fence_selection(self, event) -> bool:
        """全屏取点态下的事件：左键点两个对角定围栏、右键 / Esc 取消。

        返回 True 表示已消化（主循环不再交给界面/交互系统处理）。
        """
        if event.type == pygame.MOUSEMOTION:
            return True  # 橡皮筋预览终点用实时鼠标位置，无需存储

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            status = self.fence_controller.toggle(self._to_screen(event.pos))
            if status == "set":
                # 两角太近（如误双击）得到的极小围栏直接拒绝，留在取点态重选
                if self._fence_too_small(self.fence_controller.fence):
                    self.fence_controller.clear()
                    self.ui.show_bubble(settings.FENCE_MESSAGES["too_small"])
                    return True
                self._fence_selecting = False
                self._enter_fence_mode(self.fence_controller.fence)
                self._save_user_config()
            self.ui.show_bubble(settings.FENCE_MESSAGES[status])
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._cancel_fence_selection()
            return True

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._cancel_fence_selection()
            return True

        return False

    def _cancel_fence_selection(self) -> None:
        """取消全屏取点：清空待定取点、恢复跟随窗口、提示。"""
        self._fence_selecting = False
        self.fence_controller.clear()
        self._enter_follow_mode()
        self.ui.show_bubble(settings.FENCE_MESSAGES["cancelled"])

    # ----- 窗口三态切换（跟随 / 全屏遮罩 / 围栏固定） -----

    @staticmethod
    def _fence_too_small(fence) -> bool:
        """围栏任一边长是否小于最小值（拒绝误双击产生的退化围栏）。"""
        x1, y1, x2, y2 = fence
        return (x2 - x1) < settings.FENCE_MIN_SIZE or (y2 - y1) < settings.FENCE_MIN_SIZE

    def _apply_window_geometry(self, width: int, height: int, x: int, y: int) -> None:
        """运行时把游戏窗口缩放为 (width, height) 并移动到屏幕 (x, y)。

        pygame.display.set_mode 重建显示表面后，分层透明/置顶/句柄可能变化，
        交由 DesktopManager.reapply_after_resize 统一重新应用。
        """
        self.screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
        self.desktop_manager.reapply_after_resize(x, y)

    def _enter_fullscreen_overlay(self) -> None:
        """铺满整个虚拟桌面（所有显示器）的遮罩：围栏取点 / 无围栏喂食放置共用，
        可在任意屏幕的任意处交互。

        改用统一半透明（LWA_ALPHA）而非颜色键透明，否则空白处的点击会穿透到桌面、
        无法取点/放置（颜色键透明的像素是"点击穿透"的）。
        """
        vx, vy, vw, vh = self.desktop_manager.get_virtual_screen()
        self._apply_window_geometry(vw, vh, vx, vy)
        self.window.set_geometry((vw, vh), (vx, vy), follow=False)
        self.desktop_manager.set_overlay_alpha(settings.OVERLAY_ALPHA)
        self.ui.set_canvas_size((vw, vh))

    def _enter_fence_mode(self, fence) -> None:
        """进入围栏固定模式：窗口缩成围栏矩形、定位在围栏左上角、不再跟随。

        漫游范围用半个精灵尺寸内缩的围栏夹取，保证宠物精灵始终完整落在窗口内；
        宠物若不在围栏内（如刚框在别处或重启恢复）则移动到围栏中心。
        """
        x1, y1, x2, y2 = fence
        w, h = x2 - x1, y2 - y1
        self._apply_window_geometry(w, h, x1, y1)
        self.window.set_geometry((w, h), (x1, y1), follow=False)

        vx, vy, vw, vh = self.desktop_manager.get_virtual_screen()
        spr_w, spr_h = self.pet_sprite.image.get_size()
        hw, hh = min(spr_w // 2, w // 2), min(spr_h // 2, h // 2)
        # 漫游边界用虚拟桌面（支持围栏落在任意屏、含负原点），实际范围由下面的围栏夹取
        self.autonomous_manager.movement.set_bounds(vw, vh, inset=(0, 0), origin=(vx, vy))
        self.autonomous_manager.movement.set_fence((x1 + hw, y1 + hh, x2 - hw, y2 - hh))
        self.ui.set_canvas_size((w, h))

        if not self.fence_controller.contains(self.pet.position):
            self.pet.set_position((x1 + x2) // 2, (y1 + y2) // 2)

    def _enter_follow_mode(self) -> None:
        """恢复跟随窗口模式：窗口回到 800×600、以宠物为中心、重新跟随漫游。"""
        w, h = settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT
        cx, cy = w // 2, h // 2
        px, py = self.pet.position
        pos = (int(px - cx), int(py - cy))
        self._apply_window_geometry(w, h, pos[0], pos[1])
        self.window.set_geometry((w, h), pos, follow=True)
        self.pet_sprite.render_center = (cx, cy)
        self.pet.set_position(pos[0] + cx, pos[1] + cy)

        vx, vy, vw, vh = self.desktop_manager.get_virtual_screen()
        self.autonomous_manager.movement.set_bounds(
            vw, vh, inset=self.window.center, origin=(vx, vy)
        )
        self.autonomous_manager.movement.clear_fence()
        self.ui.set_canvas_size((w, h))

    def _toggle_fence_view(self) -> None:
        """一键隐藏/显示围栏边框（不影响围栏对漫游/喂食的约束），并持久化。"""
        self._fence_visible = not self._fence_visible
        self._save_user_config()

    def _fence_view_label(self) -> str:
        """围栏显隐按钮的动态文案。"""
        return "隐藏围栏" if self._fence_visible else "显示围栏"

    def _popup_topleft(self, popup_size):
        """设围栏后弹窗统一锚点（窗口画布坐标）；无围栏返回 None 沿用默认停靠。"""
        return popup_topleft(
            self.fence_controller.fence,
            self.window.window_pos,
            self.screen.get_size(),
            popup_size,
        )

    def _request_quit(self) -> None:
        """请求退出主循环（设置窗口「保存并退出」触发，退出时统一存档）。"""
        self.running = False

    def _update(self, dt: float):
        """逐帧更新逻辑：处理托盘动作、界面异步结果、宠物行为/自主行为/动画。"""
        self._process_tray_actions()
        self.ui.update(dt)

        # 体力消耗/恢复取决于宠物是否在移动：有移动目标即视为移动中
        moving = self.autonomous_manager.movement.has_target()
        self.behavior.update(dt, moving)
        # 以下情况暂停自主行为（宠物停在原地，窗口保持静止）：
        # 拖拽中、聊天/设置窗口打开、睡眠模式、危急状态（饥饿/体力归零）。
        # 例外：已放下食物时即使危急也要让宠物走过去吃，故危急豁免。
        interaction_active = (
            self.interaction_manager.dragging
            or self._fence_selecting
            or self.ui.blocks_autonomous
            or self.behavior.is_sleeping
            or (self.behavior.is_critical and not self.feeding.has_food)
        )
        self.autonomous_manager.update(dt, interaction_active)
        self.window.sync_to_pet()
        self.pet_sprite.update(dt)

        self._refresh_topmost(dt)
        self._autosave(dt)

    def _autosave(self, dt: float) -> None:
        """定期自动保存宠物数据，避免进程异常退出丢失进度。"""
        self._autosave_timer.update(dt)

    def _save_pet_data(self) -> None:
        """将宠物当前数据写入存档（自动存档 / 托盘保存 / 退出共用同一出口）。"""
        save_json(settings.PET_DATA_FILE, self.pet.to_dict())

    def _save_user_config(self) -> None:
        """将用户偏好（宠物大小、当前窗口位置等）合并写回 user_config.json。

        从存活对象读取当前值（宠物大小取自精灵、窗口位置取自窗口控制器），
        设置保存与退出时统一调用，保证两类偏好不会互相覆盖。
        """
        self.user_config["pet_scale"] = self.pet_sprite.scale
        self.user_config["reminder_interval_minutes"] = self.ui.reminder_interval_minutes
        self.user_config["proactive_enabled"] = self.ui.proactive_enabled
        self.user_config["proactive_interval_minutes"] = self.ui.proactive_interval_minutes
        # 音效开关：从 UI 读回当前值、持久化，并即时应用到 SoundManager
        self.user_config["sound_enabled"] = self.ui.sound_enabled
        self.sound.set_enabled(self.ui.sound_enabled)
        fence = self.fence_controller.fence
        self.user_config["fence"] = list(fence) if fence else None
        self.user_config["fence_visible"] = self._fence_visible
        if self.window.supported:
            self.user_config["window_position"] = list(self.window.window_pos)
        save_json(settings.USER_CONFIG_FILE, self.user_config)

    def _process_tray_actions(self):
        """处理系统托盘菜单产生的动作（显示/隐藏/保存/退出）。"""
        while not self._tray_actions.empty():
            action = self._tray_actions.get_nowait()

            if action == "show":
                self.desktop_manager.show()
            elif action == "hide":
                self.desktop_manager.hide()
            elif action == "save":
                self._save_pet_data()
            elif action == "exit":
                self.running = False

    def _refresh_topmost(self, dt: float):
        """周期性维持窗口置顶状态，避免每帧调用系统 API 影响性能。"""
        if not self.desktop_config.get("always_on_top", False):
            return
        self._topmost_timer.update(dt)

    def _render(self):
        """渲染当前帧：填充背景（遮罩压暗色 / 透明色键 / 白色）、绘制宠物精灵与界面窗口。"""
        if self._fence_selecting or self._feed_overlay:
            # 全屏遮罩态：窗口为统一半透明，填非色键的压暗色（否则色键会扣成透明）
            background_color = settings.OVERLAY_BG_COLOR
        elif self.desktop_manager.supported and self.desktop_config.get("transparent", False):
            background_color = settings.TRANSPARENT_COLOR_KEY
        else:
            background_color = (255, 255, 255)

        self.screen.fill(background_color)
        self._draw_fence(self.screen)
        self.pet_sprite.draw(self.screen)
        self._draw_food(self.screen)
        self.ui.draw(self.screen)
        pygame.display.flip()

    def _draw_fence(self, screen) -> None:
        """绘制围栏边框（仅边框，内部保持透明色键以透出桌面）。

        取点态下画从第一个角到当前鼠标的橡皮筋预览框；已设围栏时画其边框。
        围栏为屏幕坐标，转换到窗口画布坐标后绘制（取点态窗口左上角为 (0,0)）。
        """
        wx, wy = self.window.window_pos

        if self._fence_selecting:
            # 沿整块画布（=全屏遮罩）画一圈边框，直观提示"可在整个屏幕范围内框选"
            cw, ch = screen.get_size()
            pygame.draw.rect(
                screen, settings.FENCE_BORDER_COLOR, pygame.Rect(0, 0, cw, ch), 1
            )
            pending = self.fence_controller.pending
            if pending is not None:
                px, py = pending[0] - wx, pending[1] - wy
                mx, my = pygame.mouse.get_pos()
                rect = pygame.Rect(min(px, mx), min(py, my), abs(mx - px), abs(my - py))
                pygame.draw.rect(
                    screen, settings.FENCE_BORDER_COLOR, rect, settings.FENCE_BORDER_WIDTH
                )
            return

        fence = self.fence_controller.fence
        if not fence or not self._fence_visible:
            return
        x1, y1, x2, y2 = fence
        rect = pygame.Rect(x1 - wx, y1 - wy, x2 - x1, y2 - y1)
        pygame.draw.rect(
            screen, settings.FENCE_BORDER_COLOR, rect, settings.FENCE_BORDER_WIDTH
        )

    def _draw_food(self, screen) -> None:
        """绘制食物图标：已放下的每一份固定在其屏幕位置；放置模式下另画跟随鼠标的一份。"""
        wx, wy = self.window.window_pos
        for fx, fy in self.feeding.foods:
            food_icon.draw_food(screen, (fx - wx, fy - wy))
        if self.feeding.placing:
            food_icon.draw_food(screen, pygame.mouse.get_pos())

    def _quit(self):
        """停止系统托盘、保存宠物数据与用户偏好并安全退出 Pygame 与程序。"""
        self.tray_icon.stop()
        self._save_pet_data()
        self._save_user_config()
        pygame.quit()
        sys.exit()
