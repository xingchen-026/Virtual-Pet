"""游戏主循环模块。

负责 Pygame 的初始化、窗口创建以及主循环的运行与退出控制。
当前阶段仅渲染一个空白窗口，结构上为后续接入桌宠透明窗口、
置顶显示、动画渲染等功能预留空间。
"""

import sys

import pygame

from config import settings
from core.pet import Pet


class Game:
    """游戏主控制类，管理窗口、主循环与生命周期。"""

    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((settings.WINDOW_WIDTH, settings.WINDOW_HEIGHT))
        pygame.display.set_caption(settings.WINDOW_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True

        # 当前阶段使用默认属性创建宠物对象，后续阶段将接入数据持久化
        self.pet = Pet()

    def run(self):
        """启动主循环，直到用户关闭窗口或主动退出。"""
        while self.running:
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(settings.FPS)

        self._quit()

    def _handle_events(self):
        """处理窗口事件，目前仅响应关闭窗口事件。"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def _update(self):
        """逐帧更新逻辑。当前阶段暂无内容，预留给状态机与动画系统。"""
        pass

    def _render(self):
        """渲染当前帧。当前阶段仅填充背景色。"""
        self.screen.fill((255, 255, 255))
        pygame.display.flip()

    def _quit(self):
        """安全退出 Pygame 与程序。"""
        pygame.quit()
        sys.exit()
