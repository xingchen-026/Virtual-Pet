"""游戏主循环模块。

负责 Pygame 的初始化、窗口创建、资源/动画/精灵的组装，
以及主循环的运行与退出控制。

结构上为后续接入桌宠透明窗口、置顶显示、
鼠标拖拽等功能预留空间。
"""

import sys

import pygame

from config import settings
from core.animation import Animation, AnimationManager, AnimationState
from core.pet import Pet
from core.resource import ResourceManager
from core.sprite import PetSprite


class Game:
    """游戏主控制类，管理窗口、资源、宠物精灵与主循环生命周期。"""

    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
        pygame.display.set_caption(settings.WINDOW_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True

        self.resource_manager = ResourceManager()

        # 当前阶段使用默认属性创建宠物对象，后续阶段将接入数据持久化
        self.pet = Pet()
        self.pet_sprite = PetSprite(self.pet, self._build_animation_manager())

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
        """处理窗口事件，目前仅响应关闭窗口事件。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def _update(self, dt: float):
        """逐帧更新逻辑：推进宠物动画播放进度。"""
        self.pet_sprite.update(dt)

    def _render(self):
        """渲染当前帧：填充背景并绘制宠物精灵。"""
        self.screen.fill((255, 255, 255))
        self.pet_sprite.draw(self.screen)
        pygame.display.flip()

    def _quit(self):
        """安全退出 Pygame 与程序。"""
        pygame.quit()
        sys.exit()
