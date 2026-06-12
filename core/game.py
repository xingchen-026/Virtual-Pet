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

拖拽宠物时区分两种模式：

* 支持桌面窗口能力（Windows）：DRAG_MOVE 转换为"窗口移动拖拽"——
  整个窗口跟随鼠标移动，宠物在窗口内的位置保持不变。
* 不支持时（如非 Windows 平台）：退化为已有的"宠物在窗口内移动"
  拖拽方式，保证基础可运行。

系统托盘（utils.tray.TrayIcon）运行在独立线程，菜单回调仅将动作
放入队列，由主循环在 _process_tray_actions() 中统一处理，
避免跨线程操作 Pygame / 窗口对象。
"""

import queue
import sys

import pygame

from config import settings
from core.action import BehaviorManager
from core.animation import Animation, AnimationManager, AnimationState
from core.autonomous import AutonomousManager
from core.behavior import PetBehavior
from core.desktop import DesktopManager
from core.event import InteractionEvent, InteractionEventType
from core.feedback import FeedbackOverlay
from core.interaction import InteractionManager
from core.pet import Pet
from core.resource import ResourceManager
from core.sprite import PetSprite
from utils.behavior_logger import BehaviorLogger
from utils.helper import load_json, save_json
from utils.tray import TrayIcon

# 用户交互事件 -> 行为日志文案
INTERACTION_LOG_MESSAGES = {
    InteractionEventType.CLICK: "User clicked pet",
    InteractionEventType.EXCITED: "User excited pet with repeated clicks",
    InteractionEventType.FEED: "User fed pet",
    InteractionEventType.PLAY: "User played with pet",
}

# 调试信息文字颜色与起始绘制位置
DEBUG_TEXT_COLOR = (30, 30, 30)
DEBUG_TEXT_POS = (10, 10)
DEBUG_LINE_HEIGHT = 20

# 交互提示文字起始绘制位置
FEEDBACK_TEXT_POS = (10, 220)


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

        self.debug_font = pygame.font.SysFont(None, 20)
        self.feedback_overlay = FeedbackOverlay(self.debug_font)

        # 系统托盘：菜单回调在后台线程执行，仅将动作放入队列，主循环统一处理
        self._tray_actions: "queue.Queue[str]" = queue.Queue()
        self.tray_icon = TrayIcon(
            on_show=lambda: self._tray_actions.put("show"),
            on_hide=lambda: self._tray_actions.put("hide"),
            on_save=lambda: self._tray_actions.put("save"),
            on_exit=lambda: self._tray_actions.put("exit"),
        )

    def _build_animation_manager(self) -> AnimationManager:
        """根据配置加载各动画状态的帧资源，构建 AnimationManager。"""
        animations = {}
        for state in AnimationState:
            folder = settings.ANIMATION_FOLDERS[state.value]
            frame_duration = settings.ANIMATION_FRAME_DURATIONS[state.value]
            frames = self.resource_manager.load_animation(folder)
            animations[state] = Animation(frames, frame_duration=frame_duration)

        default_state = AnimationState(settings.DEFAULT_ANIMATION_STATE)
        return AnimationManager(animations, default_state=default_state)

    def run(self):
        """启动主循环，直到用户关闭窗口或主动退出。

        窗口隐藏到系统托盘期间使用 settings.BACKGROUND_FPS 降低帧率，
        减少后台运行时的 CPU 占用。
        """
        self.tray_icon.run_detached()

        while self.running:
            fps = settings.FPS if self.desktop_manager.visible else settings.BACKGROUND_FPS
            dt = self.clock.tick(fps) / 1000.0
            self._handle_events()
            self._update(dt)
            self._render()

        self._quit()

    def _handle_events(self):
        """处理窗口事件：关闭窗口，以及鼠标/键盘交互事件。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue

            interaction_event = self.interaction_manager.handle_event(event)
            if interaction_event is not None:
                self._dispatch_interaction(interaction_event)

    def _dispatch_interaction(self, interaction_event: InteractionEvent):
        """将交互事件交给 BehaviorManager 处理，并应用其结果。

        拖拽开始/移动/结束属于位置更新，不经过 BehaviorManager；
        其余事件统一走 BehaviorManager -> Pet Attribute -> 临时动画。
        """
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

        result = self.behavior_manager.handle(interaction_event, self.pet)
        if result is None:
            return

        self.behavior.trigger_temporary_animation(result.animation, result.duration)
        self.feedback_overlay.show(result.message)

        log_message = INTERACTION_LOG_MESSAGES.get(interaction_event.type)
        if log_message is not None:
            self.behavior_logger.log(log_message)

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
        """根据鼠标在屏幕坐标系下的位移，移动整个桌宠窗口（窗口移动拖拽）。"""
        start_cursor, start_window = self._drag_anchor
        cursor_x, cursor_y = self.desktop_manager.get_cursor_position()
        dx = cursor_x - start_cursor[0]
        dy = cursor_y - start_cursor[1]
        self.desktop_manager.set_position(start_window[0] + dx, start_window[1] + dy)

    def _update(self, dt: float):
        """逐帧更新逻辑：处理托盘动作、推进宠物行为/自主行为决策/动画与交互提示。"""
        self._process_tray_actions()

        self.behavior.update(dt)
        self.autonomous_manager.update(dt, self.interaction_manager.dragging)
        self.pet_sprite.update(dt)
        self.feedback_overlay.update(dt)

        self._refresh_topmost(dt)

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
        """渲染当前帧：填充背景（透明色键或白色）、绘制宠物精灵、调试信息与交互提示。"""
        if self.desktop_manager.supported and self.desktop_config.get("transparent", False):
            background_color = settings.TRANSPARENT_COLOR_KEY
        else:
            background_color = (255, 255, 255)

        self.screen.fill(background_color)
        self.pet_sprite.draw(self.screen)
        self._render_debug_info()
        self.feedback_overlay.draw(self.screen, FEEDBACK_TEXT_POS)
        pygame.display.flip()

    def _render_debug_info(self):
        """在窗口左上角绘制宠物名称、状态、各属性数值与桌面窗口状态，便于开发调试。"""
        lines = [
            f"Name: {self.pet.name}  Age: {self.pet.age}",
            f"State: {self.pet.current_state.name}",
            f"Hunger: {self.pet.hunger:.1f}",
            f"Mood: {self.pet.mood:.1f}",
            f"Energy: {self.pet.energy:.1f}",
            f"Last action: {self.pet.last_action}",
            f"Interactions: {self.pet.interaction_count}",
            f"Behavior: {self.autonomous_manager.current_behavior.name}",
            f"Emotion: {self.autonomous_manager.emotion.name}",
            f"Time: {self.autonomous_manager.schedule.time_of_day()}"
            f" (day {self.autonomous_manager.schedule.day_count})",
            f"Desktop: {'on' if self.desktop_manager.supported else 'off'}"
            f" ({'visible' if self.desktop_manager.visible else 'hidden'})",
        ]

        x, y = DEBUG_TEXT_POS
        for line in lines:
            text_surface = self.debug_font.render(line, True, DEBUG_TEXT_COLOR)
            self.screen.blit(text_surface, (x, y))
            y += DEBUG_LINE_HEIGHT

    def _quit(self):
        """停止系统托盘、保存宠物数据并安全退出 Pygame 与程序。"""
        self.tray_icon.stop()
        save_json(settings.PET_DATA_FILE, self.pet.to_dict())
        pygame.quit()
        sys.exit()
