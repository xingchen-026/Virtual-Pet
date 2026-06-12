"""资源管理模块。

统一管理图片、动画、音频等素材的加载与缓存。
当前阶段尚未引入具体素材文件，仅提供基础的图片加载框架，
后续阶段可在此基础上扩展动画帧序列、音效等资源类型。
"""

import os

import pygame

from config import settings


class ResourceManager:
    """资源加载与缓存管理器。"""

    def __init__(self):
        self._image_cache = {}

    def load_image(self, relative_path, convert_alpha=True):
        """加载 assets/images 目录下的图片并缓存结果。

        relative_path: 相对于 assets/images 的路径。
        convert_alpha: 是否保留透明通道（用于带透明背景的素材）。
        """
        if relative_path in self._image_cache:
            return self._image_cache[relative_path]

        full_path = os.path.join(settings.ASSETS_DIR, "images", relative_path)
        image = pygame.image.load(full_path)
        image = image.convert_alpha() if convert_alpha else image.convert()

        self._image_cache[relative_path] = image
        return image
