"""SkinManager 皮肤列举与切换的回归测试。"""

import json
import os

from core.skin import DEFAULT_SKIN, SkinManager


def _write_config(path, skin):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"active_skin": skin}, f)


def test_default_when_no_config(tmp_path):
    sm = SkinManager(str(tmp_path / "skin_config.json"))
    assert sm.active_skin == DEFAULT_SKIN
    assert sm.is_default


def test_set_active_persists(tmp_path):
    path = str(tmp_path / "skin_config.json")
    sm = SkinManager(path)
    sm.set_active("cat")
    assert sm.active_skin == "cat"
    assert not sm.is_default

    # 写回配置文件，重新加载应保持
    reloaded = SkinManager(path)
    assert reloaded.active_skin == "cat"


def test_available_skins_includes_default_first():
    sm = SkinManager()
    skins = sm.available_skins()
    assert skins[0] == DEFAULT_SKIN
    # 项目已内置 cat 皮肤
    assert "cat" in skins
    # 无重复、default 唯一
    assert skins.count(DEFAULT_SKIN) == 1


def test_animation_dir_none_for_default(tmp_path):
    sm = SkinManager(str(tmp_path / "skin_config.json"))
    assert sm.animation_dir("idle") is None  # 默认皮肤回退内置动画


def test_preview_path_returns_existing_frame():
    sm = SkinManager()
    # 内置默认皮肤的代表帧应存在（assets/animations/idle/）
    default_preview = sm.preview_path("default")
    assert default_preview is not None and os.path.isfile(default_preview)
    # cat 皮肤的代表帧应存在
    cat_preview = sm.preview_path("cat")
    assert cat_preview is not None and os.path.isfile(cat_preview)


def test_preview_path_none_for_unknown_skin():
    assert SkinManager().preview_path("__nonexistent__") is None
