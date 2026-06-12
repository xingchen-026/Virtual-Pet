"""宠物 Sprite 渲染模块。

将 Pet 数据对象与 AnimationManager 关联起来：
根据 Pet.current_animation 驱动动画状态切换，
并将当前动画帧渲染到窗口中宠物所在位置。

桌面窗口跟随模式下（窗口随宠物移动、宠物固定在窗口中心），
Game 会设置 render_center 覆盖渲染位置：Pet.position 表示
宠物在屏幕坐标系下的位置，窗口内渲染位置恒为窗口中心。

镜像皮肤：素材帧默认朝右，Pet.facing_left 为真时
当前帧水平翻转后渲染（翻转结果按帧缓存，避免每帧重复变换）。
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

from core.animation import AnimationManager
from core.pet import Pet


class PetSprite(pygame.sprite.Sprite):
    """宠物精灵：关联 Pet 数据对象与动画管理器，负责动画更新与绘制。"""

    def __init__(self, pet: Pet, animation_manager: AnimationManager) -> None:
        super().__init__()

        self.pet = pet
        self.animation_manager = animation_manager

        # 渲染位置覆盖：为 None 时按 Pet.position 渲染（窗口内移动模式）；
        # 桌面窗口跟随模式下由 Game 固定为窗口中心
        self.render_center: Optional[Tuple[int, int]] = None

        # 宠物缩放倍数（设置窗口可调，1.0 为素材原始大小）
        self.scale: float = 1.0

        # 变换帧缓存：(原始帧 id, 是否镜像, 缩放倍数) -> 处理后的帧
        self._transform_cache: Dict[tuple, pygame.Surface] = {}

        self.image = self._current_image()
        self.rect = self.image.get_rect(center=self._center())

    def update(self, dt: float = 0.0) -> None:
        """更新动画状态与当前帧。

        若 Pet.current_animation 与动画管理器当前状态不一致
        （即通过 pet.change_animation() 切换了状态），
        先同步动画管理器的状态，再推进动画播放进度。
        """
        if self.pet.current_animation != self.animation_manager.current_state.value:
            self.animation_manager.set_state(self.pet.current_animation)

        self.animation_manager.update(dt)

        self.image = self._current_image()
        self.rect = self.image.get_rect(center=self._center())

    def draw(self, screen: pygame.Surface) -> None:
        """将宠物当前帧绘制到指定窗口表面上。"""
        screen.blit(self.image, self.rect)

    def _center(self) -> Tuple[int, int]:
        """当前帧的渲染中心坐标。"""
        return self.render_center if self.render_center is not None else self.pet.position

    def _current_image(self) -> pygame.Surface:
        """获取当前帧：按需应用缩放与镜像翻转（结果按帧缓存）。"""
        frame = self.animation_manager.get_current_frame()
        scale = round(self.scale, 2)
        if not self.pet.facing_left and scale == 1.0:
            return frame

        key = (id(frame), self.pet.facing_left, scale)
        if key not in self._transform_cache:
            image = frame
            if scale != 1.0:
                size = (int(frame.get_width() * scale), int(frame.get_height() * scale))
                image = pygame.transform.smoothscale(image, size)
            if self.pet.facing_left:
                image = pygame.transform.flip(image, True, False)
            self._transform_cache[key] = image
        return self._transform_cache[key]
