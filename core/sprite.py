"""宠物 Sprite 渲染模块。

将 Pet 数据对象与 AnimationManager 关联起来：
根据 Pet.current_animation 驱动动画状态切换，
并将当前动画帧渲染到窗口中宠物所在位置。
"""

from __future__ import annotations

import pygame

from core.animation import AnimationManager
from core.pet import Pet


class PetSprite(pygame.sprite.Sprite):
    """宠物精灵：关联 Pet 数据对象与动画管理器，负责动画更新与绘制。"""

    def __init__(self, pet: Pet, animation_manager: AnimationManager) -> None:
        super().__init__()

        self.pet = pet
        self.animation_manager = animation_manager

        self.image = self.animation_manager.get_current_frame()
        self.rect = self.image.get_rect(center=self.pet.position)

    def update(self, dt: float = 0.0) -> None:
        """更新动画状态与当前帧。

        若 Pet.current_animation 与动画管理器当前状态不一致
        （即通过 pet.change_animation() 切换了状态），
        先同步动画管理器的状态，再推进动画播放进度。
        """
        if self.pet.current_animation != self.animation_manager.current_state.value:
            self.animation_manager.set_state(self.pet.current_animation)

        self.animation_manager.update(dt)

        self.image = self.animation_manager.get_current_frame()
        self.rect = self.image.get_rect(center=self.pet.position)

    def draw(self, screen: pygame.Surface) -> None:
        """将宠物当前帧绘制到指定窗口表面上。"""
        screen.blit(self.image, self.rect)
