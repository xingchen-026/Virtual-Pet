"""皮肤构建引擎。

把「精灵图」或「逐状态图片」处理（去背景 / 抠图 / 镜像 / 归一化）后写入
assets/skins/<name>/，并维护每个皮肤的 skin.json（各状态帧数 states +
每个动画的播放速度 frame_durations）。供 tools/import_skin.py（命令行）
与 ui/skin_creator.py（图形界面）共用，不依赖 pygame，可独立测试。

两种构建方式：

* build_from_spritesheet：同一张图含多个动作，按行/网格切分。
* build_from_state_images：按状态分别上传图片（每状态一张或多张帧）。

通用处理：

* 抠图（chroma_key）：把与指定颜色接近的像素改为透明；颜色为 None 时
  自动取四角背景色。
* 镜像（mirror）：水平翻转所有帧——素材约定朝右，源图朝左时开启镜像即可。
* 归一化：统一到 settings.SKIN_FRAME_SIZE 的方形画布（底部居中对齐）。
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageSequence

from config import settings
from utils.helper import load_json, save_json
from utils.spritesheet import (
    DEFAULT_FEATHER,
    DEFAULT_TOLERANCE,
    build_alpha_mask,
    detect_background_color,
    normalize_frames,
    slice_grid,
    slice_sheet,
)

_FRAME_EXTS = (".png", ".jpg", ".jpeg", ".bmp")

# 网格模式中表示跳过该单元格的占位
SKIP_TOKENS = ("skip", "-", "")


def chroma_key(
    image: Image.Image,
    color: Optional[Tuple[int, int, int]] = None,
    tolerance: float = DEFAULT_TOLERANCE,
    feather: float = DEFAULT_FEATHER,
) -> Image.Image:
    """一键抠图：把与 color 接近的像素改为透明，返回 RGBA 图。

    color 为 None 时自动取四角背景色（适合纯色背景）。
    """
    if color is None:
        color = detect_background_color(image)
    alpha = build_alpha_mask(image, color, tolerance, feather)
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]))


def mirror_frames(frames: List[Image.Image]) -> List[Image.Image]:
    """水平镜像一组帧（源图朝左时翻转为朝右）。"""
    return [frame.transpose(Image.FLIP_LEFT_RIGHT) for frame in frames]


def group_rows(
    image: Image.Image, alpha: np.ndarray, states: Optional[List[str]]
) -> Dict[str, List[Image.Image]]:
    """行模式：自动投影切分，每行映射为一个动画状态的多帧。

    states 为 None 时按 settings.ANIMATION_FOLDERS 顺序取前 N 个状态。
    """
    rows = slice_sheet(image, alpha)
    if not rows:
        raise ValueError("未能从精灵图中切分出任何帧，请检查图片或调整容差")

    if states is None:
        known = list(settings.ANIMATION_FOLDERS.keys())
        if len(rows) > len(known):
            raise ValueError(f"精灵图行数（{len(rows)}）超过支持的状态数（{len(known)}）")
        states = known[: len(rows)]
    elif len(states) != len(rows):
        raise ValueError(f"指定状态数（{len(states)}）与检测到的行数（{len(rows)}）不一致")

    # 支持逐行指定状态，写 skip/空 的行将被忽略；同一状态多行则合并
    grouped: Dict[str, List[Image.Image]] = {}
    for state, frames in zip(states, rows):
        if state in SKIP_TOKENS:
            continue
        grouped.setdefault(state, []).extend(frames)

    if not grouped:
        raise ValueError("未指定任何状态（所有行都被跳过）")
    return grouped


def group_grid(
    image: Image.Image, alpha: np.ndarray, grid_rows: int, grid_cols: int, states: List[str]
) -> Dict[str, List[Image.Image]]:
    """网格模式：固定行列均匀切分，states 按行优先逐格映射（skip 跳过）。"""
    if len(states) != grid_rows * grid_cols:
        raise ValueError(
            f"状态数（{len(states)}）应等于网格单元格数（{grid_rows}x{grid_cols}）"
        )

    cells = slice_grid(image, alpha, grid_rows, grid_cols)
    grouped: Dict[str, List[Image.Image]] = {}
    for state, cell in zip(states, cells):
        if state in SKIP_TOKENS or cell is None:
            continue
        grouped.setdefault(state, []).append(cell)

    if not grouped:
        raise ValueError("没有任何单元格被映射到动画状态")
    return grouped


def slice_frames(image: Image.Image, alpha: np.ndarray) -> List[Image.Image]:
    """把精灵图切成「按阅读顺序」的逐帧列表（行内从左到右、行间从上到下）。

    与 slice_sheet 的区别：展平成单一帧序列，供用户逐帧自由分配状态
    （任选一部分帧作为某状态的动画），不再强制「一行=一个状态」。
    """
    return [frame for row in slice_sheet(image, alpha) for frame in row]


def grouped_from_sheets(sheets: List[dict]) -> Dict[str, List[Image.Image]]:
    """多张精灵图 + 逐帧状态分配 -> 归一化的各状态帧。

    sheets: [{"path", "mirror", "chroma_color", "frame_states": [state|skip, ...]}]
    同一状态的帧按「精灵图顺序 + 帧顺序」拼接，支持不同资源（不同背景/朝向）
    各自抠图与镜像，组合成同一皮肤。
    """
    grouped: Dict[str, List[Image.Image]] = {}
    for sheet in sheets:
        path = sheet.get("path")
        if not path:
            continue
        image = Image.open(path)
        bg = sheet.get("chroma_color") or detect_background_color(image)
        alpha = build_alpha_mask(image, bg, DEFAULT_TOLERANCE, DEFAULT_FEATHER)
        frames = slice_frames(image, alpha)
        frame_states = sheet.get("frame_states") or []
        mirror = sheet.get("mirror", False)

        for index, frame in enumerate(frames):
            state = frame_states[index] if index < len(frame_states) else None
            if not state or state in SKIP_TOKENS:
                continue
            # frame 已是去背景后的 RGBA 帧
            grouped.setdefault(state, []).append(
                frame.transpose(Image.FLIP_LEFT_RIGHT) if mirror else frame
            )

    if not grouped:
        raise ValueError("没有任何帧被指定状态")
    return _normalize_grouped(grouped)


def build_from_sheets(
    name: str, sheets: List[dict], frame_durations: Optional[Dict[str, float]] = None
) -> dict:
    """多张精灵图 + 逐帧状态分配，构建皮肤。"""
    grouped = grouped_from_sheets(sheets)
    source = ", ".join(
        os.path.basename(s["path"]) for s in sheets if s.get("path")
    )
    return write_skin(name, grouped, source, frame_durations)


def write_skin(
    name: str,
    grouped: Dict[str, List[Image.Image]],
    source: str = "",
    frame_durations: Optional[Dict[str, float]] = None,
) -> dict:
    """将各状态帧写入皮肤目录（涉及的状态清空重写），合并更新 skin.json。

    skin.json 记录每个状态的帧数（states）与每个动画的播放速度
    （frame_durations，秒/帧）。返回更新后的 manifest。
    """
    skin_dir = os.path.join(settings.SKINS_DIR, name)
    manifest_path = os.path.join(skin_dir, "skin.json")
    manifest = load_json(manifest_path) or {"name": name, "states": {}}
    manifest.setdefault("states", {})
    manifest.setdefault("frame_durations", {})
    if source:
        manifest["source"] = source

    for state, frames in grouped.items():
        state_dir = os.path.join(skin_dir, state)
        os.makedirs(state_dir, exist_ok=True)
        for fname in os.listdir(state_dir):
            if fname.lower().endswith(_FRAME_EXTS):
                os.remove(os.path.join(state_dir, fname))
        for index, frame in enumerate(frames):
            frame.save(os.path.join(state_dir, f"frame_{index:02d}.png"))
        manifest["states"][state] = len(frames)

    if frame_durations:
        manifest["frame_durations"].update(
            {state: float(value) for state, value in frame_durations.items()}
        )

    save_json(manifest_path, manifest)
    return manifest


def _normalize_grouped(grouped: Dict[str, List[Image.Image]]) -> Dict[str, List[Image.Image]]:
    """把各状态帧统一归一化到 SKIN_FRAME_SIZE（合并计算统一画布）。"""
    state_names = list(grouped.keys())
    normalized = normalize_frames([grouped[s] for s in state_names], settings.SKIN_FRAME_SIZE)
    return {state: frames for state, frames in zip(state_names, normalized)}


def grouped_from_spritesheet(
    image_path: str,
    states: Optional[List[str]] = None,
    grid: Optional[Tuple[int, int]] = None,
    tolerance: float = DEFAULT_TOLERANCE,
    chroma_color: Optional[Tuple[int, int, int]] = None,
    mirror: bool = False,
) -> Dict[str, List[Image.Image]]:
    """从精灵图切分得到归一化的各状态帧（不写文件，供构建与实时预览共用）。"""
    image = Image.open(image_path)
    bg = chroma_color if chroma_color is not None else detect_background_color(image)
    alpha = build_alpha_mask(image, bg, tolerance, DEFAULT_FEATHER)

    if grid is not None:
        grouped = group_grid(image, alpha, grid[0], grid[1], states or [])
    else:
        grouped = group_rows(image, alpha, states)

    if mirror:
        grouped = {state: mirror_frames(frames) for state, frames in grouped.items()}
    return _normalize_grouped(grouped)


def load_image_frames(path: str) -> List[Image.Image]:
    """读取一张图片为帧列表：动图（GIF / APNG）按帧序展开，静图返回单帧。

    GIF/APNG 等动画文件直接作为某动画状态的多帧来源，逐帧合成并转 RGBA
    （PIL 会按帧处置方式合成）。静态图片返回只含一帧的列表。
    """
    img = Image.open(path)
    if getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1:
        return [frame.convert("RGBA").copy() for frame in ImageSequence.Iterator(img)]
    return [img.convert("RGBA")]


def grouped_from_state_images(
    state_to_paths: Dict[str, List[str]],
    tolerance: float = DEFAULT_TOLERANCE,
    chroma_color: Optional[Tuple[int, int, int]] = None,
    mirror: bool = False,
) -> Dict[str, List[Image.Image]]:
    """按状态图片得到归一化的各状态帧（不写文件，供构建与实时预览共用）。

    每个状态可上传：单张静图、多张静图（各为一帧），或一张动图（GIF/APNG，
    自动展开为该状态的多帧动画）；多个来源按上传顺序拼接。
    """
    grouped: Dict[str, List[Image.Image]] = {}
    for state, paths in state_to_paths.items():
        frames: List[Image.Image] = []
        for p in paths:
            for frame in load_image_frames(p):
                frames.append(chroma_key(frame, chroma_color, tolerance))
        if frames:
            grouped[state] = mirror_frames(frames) if mirror else frames

    if not grouped:
        raise ValueError("未提供任何状态图片")
    return _normalize_grouped(grouped)


def preview_grouped(config: dict) -> Dict[str, List[Image.Image]]:
    """按创建配置生成各状态帧（不写文件），供创建窗口实时预览播放。"""
    if config.get("mode") == "sheet":
        sheets = [s for s in config.get("sheets", []) if s.get("path")]
        if not sheets:
            return {}
        try:
            return grouped_from_sheets(sheets)
        except ValueError:
            return {}
    state_paths = {s: [p] for s, p in config.get("state_paths", {}).items() if p}
    if not state_paths:
        return {}
    return grouped_from_state_images(
        state_paths, chroma_color=config.get("chroma_color"), mirror=config.get("mirror", False),
    )


def build_from_spritesheet(
    name: str,
    image_path: str,
    states: Optional[List[str]] = None,
    grid: Optional[Tuple[int, int]] = None,
    tolerance: float = DEFAULT_TOLERANCE,
    chroma_color: Optional[Tuple[int, int, int]] = None,
    mirror: bool = False,
    frame_durations: Optional[Dict[str, float]] = None,
) -> dict:
    """从精灵图构建皮肤。grid 为 (行, 列) 时用网格模式，否则用行模式。"""
    grouped = grouped_from_spritesheet(image_path, states, grid, tolerance, chroma_color, mirror)
    return write_skin(name, grouped, os.path.basename(image_path), frame_durations)


def build_from_state_images(
    name: str,
    state_to_paths: Dict[str, List[str]],
    tolerance: float = DEFAULT_TOLERANCE,
    chroma_color: Optional[Tuple[int, int, int]] = None,
    mirror: bool = False,
    frame_durations: Optional[Dict[str, float]] = None,
) -> dict:
    """按状态上传图片构建皮肤：state_to_paths 为 {状态: [图片路径, ...]}。"""
    grouped = grouped_from_state_images(state_to_paths, tolerance, chroma_color, mirror)
    return write_skin(name, grouped, "", frame_durations)


def set_frame_durations(name: str, frame_durations: Dict[str, float]) -> dict:
    """仅更新某皮肤各动画的播放速度（写入 skin.json，不改帧）。"""
    return write_skin(name, {}, "", frame_durations)
