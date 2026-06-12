"""Lottie 动画加载接口模块。

设计目标：

* 提供 Lottie（.json）动画文件的加载与帧序列转换接口，
  转换结果与 core.animation.Animation 所需的
  ``List[pygame.Surface]`` 格式一致，可直接接入现有动画系统。
* 当前环境若未安装 python-lottie（或其渲染依赖），
  is_lottie_available() 返回 False，
  load_lottie_frames() 返回 None。
  调用方应在 None 时回退到 assets/animations 下的图片帧方案
  （见 ResourceManager.load_animation）。

这样后续接入正式 Lottie 资源时，只需安装依赖并将动画目录中的
图片帧替换为 load_lottie_frames() 的输出，
无需改动 AnimationManager / PetSprite 的接口。
"""

from __future__ import annotations

import io
import os
from typing import List, Optional

import pygame

try:
    from lottie import objects as _lottie_objects
    from lottie.exporters.cairo import export_png as _export_png

    LOTTIE_AVAILABLE = True
except ImportError:
    _lottie_objects = None
    _export_png = None
    LOTTIE_AVAILABLE = False


def is_lottie_available() -> bool:
    """返回当前环境是否具备渲染 Lottie 动画的能力。"""
    return LOTTIE_AVAILABLE


def load_lottie_frames(file_path: str) -> Optional[List[pygame.Surface]]:
    """加载 Lottie (.json) 动画文件并转换为 pygame 帧图像序列。

    若文件不存在，或当前环境不支持 Lottie 渲染，返回 None，
    调用方需回退到基于图片序列的动画方案。
    """
    if not LOTTIE_AVAILABLE or not os.path.exists(file_path):
        return None

    animation = _lottie_objects.Animation.load(file_path)
    frames: List[pygame.Surface] = []

    for frame_no in range(int(animation.in_point), int(animation.out_point) + 1):
        buffer = io.BytesIO()
        _export_png(animation, buffer, frame_no)
        buffer.seek(0)
        frames.append(pygame.image.load(buffer, "frame.png").convert_alpha())

    return frames or None
