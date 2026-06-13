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
from core.interaction import InteractionManager
from core.pet import Pet
from core.resource import ResourceManager
from core.skin import SkinManager
from core.sprite import PetSprite
from core.window_controller import WindowController
from ui.ui_manager import UIManager
from utils.behavior_logger import BehaviorLogger
from utils.helper import load_json, save_json
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

        # 用户偏好（宠物大小、窗口位置等），整局共用一份，退出时合并写回
        self.user_config = load_json(settings.USER_CONFIG_FILE) or {}

        # 窗口跟随控制器：维护"窗口中心 = 宠物屏幕坐标"，集中处理窗口移动/拖拽。
        # 优先使用上次退出时保存的窗口位置，否则用 desktop_manager 的初始位置
        self.window = WindowController(
            self.desktop_manager, self.pet, self.pet_sprite,
            (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT),
        )
        self.window.initialize(self.user_config.get("window_position"))
        if self.desktop_manager.supported:
            # 漫游目标内缩半个窗口，确保窗口（及右键面板）始终留在屏幕内
            self.autonomous_manager.movement.set_bounds(
                *self.desktop_manager.get_screen_size(), inset=self.window.center
            )

        # 界面字体：必须使用含中文字形的系统字体（settings.UI_FONT_NAMES），
        # 否则聊天窗口/面板中的中文会渲染为方块乱码
        self.ui_font = pygame.font.SysFont(settings.UI_FONT_NAMES, settings.UI_FONT_SIZE)

        # 宠物大小读取自上面加载的 user_config
        self.pet_sprite.scale = self.user_config.get("pet_scale", settings.PET_SCALE_DEFAULT)

        # 宠物数据自动存档计时器（settings.AUTOSAVE_INTERVAL 秒一次）
        self._autosave_timer = 0.0

        # AI 服务：Pet -> AIService -> LLM，人格/记忆数据持久化到 data/ 下的 JSON 文件
        # ai_config 保留引用，供设置窗口读取/更新后写回
        self.ai_config = load_json(settings.AI_CONFIG_FILE) or {}
        self.personality = PersonalityManager()
        self.memory = MemoryManager()
        self.ai_service = AIService(self.ai_config, self.personality, self.memory, self.behavior)

        # 界面管理器：聊天窗口 / 数值面板 / 设置窗口及其事件路由与异步结果回传。
        # 喂食/玩耍按钮经 on_interaction 回到交互分发管线；
        # 保存设置后经 on_user_prefs_changed 让 Game 合并持久化用户偏好。
        self.ui = UIManager(
            self.ui_font, self.pet, self.pet_sprite, self.autonomous_manager,
            self.ai_service, self.desktop_manager, self.ai_config,
            (settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT),
            on_interaction=self._dispatch_interaction,
            on_user_prefs_changed=self._save_user_config,
        )

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
            or self.ui.is_active
            or self.autonomous_manager.movement.has_target()
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

        log_message = INTERACTION_LOG_MESSAGES.get(interaction_event.type)
        if log_message is not None:
            self.behavior_logger.log(log_message)

        self.ai_service.notify_interaction(self.pet, interaction_event.type.value)

    def _update(self, dt: float):
        """逐帧更新逻辑：处理托盘动作、界面异步结果、宠物行为/自主行为/动画。"""
        self._process_tray_actions()
        self.ui.update(dt)

        self.behavior.update(dt)
        # 以下情况暂停自主行为（宠物停在原地，窗口保持静止）：
        # 拖拽中、聊天/设置窗口打开、睡眠模式、危急状态（饥饿/体力归零）。
        interaction_active = (
            self.interaction_manager.dragging
            or self.ui.blocks_autonomous
            or self.behavior.is_sleeping
            or self.behavior.is_critical
        )
        self.autonomous_manager.update(dt, interaction_active)
        self.window.sync_to_pet()
        self.pet_sprite.update(dt)

        self._refresh_topmost(dt)
        self._autosave(dt)

    def _autosave(self, dt: float) -> None:
        """定期自动保存宠物数据，避免进程异常退出丢失进度。"""
        self._autosave_timer += dt
        if self._autosave_timer >= settings.AUTOSAVE_INTERVAL:
            self._autosave_timer = 0.0
            save_json(settings.PET_DATA_FILE, self.pet.to_dict())

    def _save_user_config(self) -> None:
        """将用户偏好（宠物大小、当前窗口位置等）合并写回 user_config.json。

        从存活对象读取当前值（宠物大小取自精灵、窗口位置取自窗口控制器），
        设置保存与退出时统一调用，保证两类偏好不会互相覆盖。
        """
        self.user_config["pet_scale"] = self.pet_sprite.scale
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
        """渲染当前帧：填充背景（透明色键或白色）、绘制宠物精灵与界面窗口。"""
        if self.desktop_manager.supported and self.desktop_config.get("transparent", False):
            background_color = settings.TRANSPARENT_COLOR_KEY
        else:
            background_color = (255, 255, 255)

        self.screen.fill(background_color)
        self.pet_sprite.draw(self.screen)
        self.ui.draw(self.screen)
        pygame.display.flip()

    def _quit(self):
        """停止系统托盘、保存宠物数据与用户偏好并安全退出 Pygame 与程序。"""
        self.tray_icon.stop()
        save_json(settings.PET_DATA_FILE, self.pet.to_dict())
        self._save_user_config()
        pygame.quit()
        sys.exit()
