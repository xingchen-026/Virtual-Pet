"""游戏主循环模块。

负责 Pygame 的初始化、窗口创建、资源/动画/精灵/行为系统的组装，
宠物数据的读取与保存，以及主循环的运行与退出控制。

交互系统集成方式：

    User Input -> InteractionManager -> BehaviorManager
        -> Pet Attribute -> StateMachine -> AnimationManager

结构上为后续接入桌宠透明窗口、置顶显示等功能预留空间。
"""

import sys

import pygame

from config import settings
from core.action import BehaviorManager
from core.animation import Animation, AnimationManager, AnimationState
from core.behavior import PetBehavior
from core.event import InteractionEvent, InteractionEventType
from core.feedback import FeedbackOverlay
from core.interaction import InteractionManager
from core.pet import Pet
from core.resource import ResourceManager
from core.sprite import PetSprite
from utils.helper import load_json, save_json

# 调试信息文字颜色与起始绘制位置
DEBUG_TEXT_COLOR = (30, 30, 30)
DEBUG_TEXT_POS = (10, 10)
DEBUG_LINE_HEIGHT = 20

# 交互提示文字起始绘制位置
FEEDBACK_TEXT_POS = (10, 160)


class Game:
    """游戏主控制类，管理窗口、资源、宠物状态/精灵与主循环生命周期。"""

    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
        pygame.display.set_caption(settings.WINDOW_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True

        self.resource_manager = ResourceManager()

        # 启动时尝试从 JSON 存档读取宠物数据，不存在则使用默认属性
        pet_data = load_json(settings.PET_DATA_FILE)
        self.pet = Pet.from_dict(pet_data) if pet_data else Pet()

        self.behavior = PetBehavior(self.pet)
        self.pet_sprite = PetSprite(self.pet, self._build_animation_manager())

        # 交互系统：用户输入 -> InteractionManager -> BehaviorManager
        self.interaction_manager = InteractionManager(self.pet_sprite)
        self.behavior_manager = BehaviorManager()

        self.debug_font = pygame.font.SysFont(None, 20)
        self.feedback_overlay = FeedbackOverlay(self.debug_font)

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
        """启动主循环，直到用户关闭窗口或主动退出。"""
        while self.running:
            dt = self.clock.tick(settings.FPS) / 1000.0
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

        拖拽移动/结束属于位置更新，不经过 BehaviorManager；
        其余事件统一走 BehaviorManager -> Pet Attribute -> 临时动画。
        """
        if interaction_event.type == InteractionEventType.DRAG_MOVE:
            self.pet.set_position(*interaction_event.position)
            return

        if interaction_event.type == InteractionEventType.DRAG_END:
            return

        result = self.behavior_manager.handle(interaction_event, self.pet)
        if result is None:
            return

        self.behavior.trigger_temporary_animation(result.animation, result.duration)
        self.feedback_overlay.show(result.message)

    def _update(self, dt: float):
        """逐帧更新逻辑：推进宠物行为（属性衰减/状态切换）、动画播放进度与交互提示。"""
        self.behavior.update(dt)
        self.pet_sprite.update(dt)
        self.feedback_overlay.update(dt)

    def _render(self):
        """渲染当前帧：填充背景、绘制宠物精灵、调试信息与交互提示。"""
        self.screen.fill((255, 255, 255))
        self.pet_sprite.draw(self.screen)
        self._render_debug_info()
        self.feedback_overlay.draw(self.screen, FEEDBACK_TEXT_POS)
        pygame.display.flip()

    def _render_debug_info(self):
        """在窗口左上角绘制宠物名称、状态与各属性数值，便于开发调试。"""
        lines = [
            f"Name: {self.pet.name}",
            f"State: {self.pet.current_state.name}",
            f"Hunger: {self.pet.hunger:.1f}",
            f"Mood: {self.pet.mood:.1f}",
            f"Energy: {self.pet.energy:.1f}",
            f"Last action: {self.pet.last_action}",
            f"Interactions: {self.pet.interaction_count}",
        ]

        x, y = DEBUG_TEXT_POS
        for line in lines:
            text_surface = self.debug_font.render(line, True, DEBUG_TEXT_COLOR)
            self.screen.blit(text_surface, (x, y))
            y += DEBUG_LINE_HEIGHT

    def _quit(self):
        """保存宠物数据并安全退出 Pygame 与程序。"""
        save_json(settings.PET_DATA_FILE, self.pet.to_dict())
        pygame.quit()
        sys.exit()
