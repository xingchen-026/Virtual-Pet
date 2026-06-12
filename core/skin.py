"""宠物皮肤管理模块。

SkinManager 根据 config/skin_config.json 中的 active_skin 决定
各动画状态的帧资源目录：

* active_skin 为 "default"（或皮肤目录不存在）时，
  使用内置动画目录 assets/animations/<state>/
* 否则优先使用 assets/skins/<皮肤名>/<state>/，
  皮肤中未提供的状态自动回退到内置动画目录，
  保证任何皮肤下全部动画状态均可加载。

皮肤由 tools/import_skin.py 从用户精灵图导入生成。
"""

from __future__ import annotations

import os
from typing import Optional

from config import settings
from utils.helper import load_json

DEFAULT_SKIN = "default"


class SkinManager:
    """解析当前皮肤下各动画状态对应的帧资源目录。"""

    def __init__(self, config_path: Optional[str] = None) -> None:
        config = load_json(config_path or settings.SKIN_CONFIG_FILE) or {}
        self.active_skin: str = config.get("active_skin", DEFAULT_SKIN)

    @property
    def is_default(self) -> bool:
        """当前是否使用内置默认皮肤。"""
        return self.active_skin == DEFAULT_SKIN

    def animation_dir(self, state_name: str) -> Optional[str]:
        """返回当前皮肤下该状态的帧目录（绝对路径）。

        皮肤未启用、皮肤目录不存在或该状态在皮肤中缺帧时返回 None，
        调用方应回退到内置动画目录。
        """
        if self.is_default:
            return None

        state_dir = os.path.join(settings.SKINS_DIR, self.active_skin, state_name)
        if not os.path.isdir(state_dir):
            return None

        has_frames = any(
            name.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))
            for name in os.listdir(state_dir)
        )
        return state_dir if has_frames else None
