"""资源管理模块。

统一管理图片与动画帧序列的加载与缓存，避免重复读取磁盘。
"""

import os
from typing import Dict, List

import pygame

from config import settings

# 动画帧图片支持的文件扩展名
_FRAME_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp")


class ResourceManager:
    """资源加载与缓存管理器。"""

    def __init__(self) -> None:
        self._image_cache: Dict[str, pygame.Surface] = {}
        self._animation_cache: Dict[str, List[pygame.Surface]] = {}

    def load_image(self, relative_path: str, convert_alpha: bool = True) -> pygame.Surface:
        """加载 assets/images 目录下的图片并缓存结果。

        relative_path: 相对于 assets/images 的路径。
        convert_alpha: 是否保留透明通道（用于带透明背景的素材）。
        """
        if relative_path in self._image_cache:
            return self._image_cache[relative_path]

        full_path = os.path.join(settings.ASSETS_DIR, "images", relative_path)
        image = self._load_surface(full_path, convert_alpha)

        self._image_cache[relative_path] = image
        return image

    def load_animation(self, folder_name: str, convert_alpha: bool = True) -> List[pygame.Surface]:
        """加载 assets/animations/<folder_name> 目录下的全部帧图片并缓存。

        目录内的图片按文件名排序后依次作为动画帧，
        因此帧文件建议使用 frame_00.png、frame_01.png ... 的命名方式。
        """
        if folder_name in self._animation_cache:
            return self._animation_cache[folder_name]

        animation_dir = os.path.join(settings.ASSETS_DIR, "animations", folder_name)
        frame_names = sorted(
            name for name in os.listdir(animation_dir)
            if name.lower().endswith(_FRAME_EXTENSIONS)
        )

        if not frame_names:
            raise FileNotFoundError(f"动画目录中未找到帧图片: {animation_dir}")

        frames = [
            self._load_surface(os.path.join(animation_dir, name), convert_alpha)
            for name in frame_names
        ]

        self._animation_cache[folder_name] = frames
        return frames

    @staticmethod
    def _load_surface(full_path: str, convert_alpha: bool) -> pygame.Surface:
        image = pygame.image.load(full_path)
        return image.convert_alpha() if convert_alpha else image.convert()
