"""皮肤构建引擎 core/skin_builder 的回归测试（用 PIL 合成图，不依赖真实素材）。"""

import json
import os

import numpy as np
import pytest
from PIL import Image

from core import skin_builder
from config import settings

BG = (170, 237, 224)
FG = (200, 80, 60)


def _make_sheet(rows, cols, cell=60, blob=30):
    img = Image.new("RGB", (cols * cell, rows * cell), BG)
    for r in range(rows):
        for c in range(cols):
            cx, cy = c * cell + cell // 2, r * cell + cell // 2
            h = blob // 2
            for x in range(cx - h, cx + h):
                for y in range(cy - h, cy + h):
                    img.putpixel((x, y), FG)
    return img


def _save(img, path):
    img.save(path)
    return str(path)


def _redirect_skins(tmp_path, monkeypatch):
    skins_dir = tmp_path / "skins"
    skins_dir.mkdir()
    monkeypatch.setattr(settings, "SKINS_DIR", str(skins_dir))
    return skins_dir


def test_chroma_key_makes_background_transparent():
    img = _make_sheet(1, 1)
    out = skin_builder.chroma_key(img, BG)
    assert out.mode == "RGBA"
    arr = np.asarray(out)
    assert arr[0, 0, 3] == 0  # 角落背景透明
    assert arr[arr.shape[0] // 2, arr.shape[1] // 2, 3] == 255  # 中心前景不透明


def test_mirror_frames_flips():
    img = Image.new("RGBA", (4, 2), (0, 0, 0, 0))
    img.putpixel((0, 0), (255, 0, 0, 255))
    flipped = skin_builder.mirror_frames([img])[0]
    assert flipped.getpixel((3, 0)) == (255, 0, 0, 255)


def _save_gif(path, n_frames=4, size=(40, 40)):
    """合成一张多帧 GIF（每帧一个不同位置的色块），返回路径。"""
    frames = []
    for i in range(n_frames):
        im = Image.new("RGB", size, BG)
        im.putpixel((2 + i, 2 + i), FG)
        frames.append(im)
    frames[0].save(
        path, save_all=True, append_images=frames[1:], duration=80, loop=0
    )
    return str(path)


def test_load_image_frames_static_single(tmp_path):
    path = _save(_make_sheet(1, 1), tmp_path / "one.png")
    frames = skin_builder.load_image_frames(path)
    assert len(frames) == 1
    assert frames[0].mode == "RGBA"


def test_load_image_frames_gif_expands(tmp_path):
    path = _save_gif(tmp_path / "anim.gif", n_frames=5)
    frames = skin_builder.load_image_frames(path)
    assert len(frames) == 5
    assert all(f.mode == "RGBA" for f in frames)


def test_grouped_from_state_images_expands_gif(tmp_path):
    gif = _save_gif(tmp_path / "walk.gif", n_frames=6)
    png = _save(_make_sheet(1, 1), tmp_path / "idle.png")
    grouped = skin_builder.grouped_from_state_images({"walk": [gif], "idle": [png]})
    assert len(grouped["walk"]) == 6  # GIF 展开为多帧
    assert len(grouped["idle"]) == 1  # 静图仍为单帧
    # 归一化后同尺寸
    assert grouped["walk"][0].size == grouped["idle"][0].size


def test_build_from_spritesheet_rows(tmp_path, monkeypatch):
    skins = _redirect_skins(tmp_path, monkeypatch)
    path = _save(_make_sheet(2, 3), tmp_path / "sheet.png")
    manifest = skin_builder.build_from_spritesheet(
        "t", path, states=["idle", "happy"], frame_durations={"idle": 0.3}
    )
    assert manifest["states"] == {"idle": 3, "happy": 3}
    assert manifest["frame_durations"]["idle"] == 0.3
    # 帧文件确实写入，且尺寸为统一画布
    idle0 = skins / "t" / "idle" / "frame_00.png"
    assert idle0.is_file()
    assert Image.open(idle0).size == settings.SKIN_FRAME_SIZE


def test_build_from_state_images(tmp_path, monkeypatch):
    skins = _redirect_skins(tmp_path, monkeypatch)
    p_idle = _save(_make_sheet(1, 1), tmp_path / "i.png")
    p_happy = _save(_make_sheet(1, 1), tmp_path / "h.png")
    manifest = skin_builder.build_from_state_images(
        "s", {"idle": [p_idle], "happy": [p_happy]}, frame_durations={"happy": 0.12}
    )
    assert manifest["states"] == {"idle": 1, "happy": 1}
    assert manifest["frame_durations"]["happy"] == 0.12
    assert (skins / "s" / "idle" / "frame_00.png").is_file()


def test_set_frame_durations_only(tmp_path, monkeypatch):
    skins = _redirect_skins(tmp_path, monkeypatch)
    path = _save(_make_sheet(1, 2), tmp_path / "sheet.png")
    skin_builder.build_from_spritesheet("t", path, states=["idle"])
    skin_builder.set_frame_durations("t", {"idle": 0.5})
    manifest = json.load(open(skins / "t" / "skin.json", encoding="utf-8"))
    assert manifest["frame_durations"]["idle"] == 0.5
    assert manifest["states"]["idle"] == 2  # 帧未被改动


def test_spritesheet_custom_states_with_skip(tmp_path, monkeypatch):
    skins = _redirect_skins(tmp_path, monkeypatch)
    path = _save(_make_sheet(3, 2), tmp_path / "sheet.png")
    # 3 行：第 1 行 idle，第 2 行跳过，第 3 行 walk
    manifest = skin_builder.build_from_spritesheet(
        "t", path, states=["idle", "skip", "walk"]
    )
    assert set(manifest["states"].keys()) == {"idle", "walk"}
    assert (skins / "t" / "idle").is_dir()
    assert not (skins / "t" / "skip").exists()


def test_supplement_merges_states(tmp_path, monkeypatch):
    skins = _redirect_skins(tmp_path, monkeypatch)
    sheet = _save(_make_sheet(1, 2), tmp_path / "sheet.png")
    skin_builder.build_from_spritesheet("t", sheet, states=["idle"])
    # 补充：按状态加入 happy，应合并保留 idle
    img = _save(_make_sheet(1, 1), tmp_path / "h.png")
    manifest = skin_builder.build_from_state_images("t", {"happy": [img]})
    assert set(manifest["states"].keys()) == {"idle", "happy"}


def test_slice_frames_flattens(tmp_path):
    from utils import spritesheet
    img = _make_sheet(2, 3)
    alpha = spritesheet.build_alpha_mask(img, BG)
    frames = skin_builder.slice_frames(img, alpha)
    assert len(frames) == 6  # 2x3 展平为 6 帧


def test_build_from_sheets_per_frame_states(tmp_path, monkeypatch):
    skins = _redirect_skins(tmp_path, monkeypatch)
    p1 = _save(_make_sheet(1, 4), tmp_path / "s1.png")  # 4 帧
    p2 = _save(_make_sheet(1, 2), tmp_path / "s2.png")  # 2 帧
    sheets = [
        # 第1张：前2帧给 walk，后2帧跳过
        {"path": p1, "frame_states": ["walk", "walk", "skip", "skip"]},
        # 第2张：2帧给 idle（不同资源拼到同一皮肤）
        {"path": p2, "frame_states": ["idle", "idle"]},
    ]
    manifest = skin_builder.build_from_sheets("multi", sheets)
    assert manifest["states"] == {"walk": 2, "idle": 2}
    assert (skins / "multi" / "walk" / "frame_01.png").is_file()


def test_build_from_sheets_requires_assignment(tmp_path, monkeypatch):
    _redirect_skins(tmp_path, monkeypatch)
    p = _save(_make_sheet(1, 2), tmp_path / "s.png")
    with pytest.raises(ValueError):
        skin_builder.build_from_sheets("x", [{"path": p, "frame_states": ["skip", "skip"]}])


def test_mirror_build(tmp_path, monkeypatch):
    _redirect_skins(tmp_path, monkeypatch)
    path = _save(_make_sheet(1, 2), tmp_path / "sheet.png")
    # 仅验证带镜像构建不报错且帧数正确
    manifest = skin_builder.build_from_spritesheet("m", path, states=["idle"], mirror=True)
    assert manifest["states"]["idle"] == 2


def test_binary_alpha_mask_no_partial_pixels():
    """feather=0 时 alpha 仅 0/255（消除洋红色键下的紫色半透明描边）。"""
    from utils.spritesheet import build_alpha_mask
    img = _make_sheet(1, 1)  # 纯背景 BG + 中心前景 FG 块
    soft = build_alpha_mask(img, BG, tolerance=40, feather=30)
    hard = build_alpha_mask(img, BG, tolerance=40, feather=0)
    assert set(np.unique(hard)).issubset({0, 255})       # 二值，无半透明
    assert hard.max() == 255 and hard.min() == 0          # 既有前景也有背景
    # 软边模式通常会产生中间过渡值（半透明）
    assert (soft > 0).any() and (soft < 255).any()


def test_ai_skin_frames_binary_alpha_after_resize(tmp_path):
    """feather=0 的整套构建：缩放后帧 alpha 仍为二值（不会重新出现半透明->紫边）。"""
    big = _save(_make_sheet(1, 1, cell=300, blob=160), tmp_path / "big.png")  # 大图触发缩放
    grouped = skin_builder.grouped_from_state_images(
        {"idle": [big]}, tolerance=60, feather=0,
    )
    alpha = np.asarray(grouped["idle"][0])[:, :, 3]
    assert set(np.unique(alpha)).issubset({0, 255})  # 缩放后仍二值
    assert alpha.max() == 255  # 仍保留前景
