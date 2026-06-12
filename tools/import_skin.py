"""皮肤导入工具（命令行）。

将用户提供的精灵图（背景不要求透明）切分为桌宠可加载的皮肤贴图，
支持两种切分模式：

1. 行模式（默认）：每行是一个动作的多帧动画，自动投影切分

       python tools/import_skin.py 精灵图.png --name cat \
           --states idle,happy,walk

   --states 按从上到下的行顺序指定每行对应的动画状态，
   数量需与检测到的行数一致；省略时按 settings.ANIMATION_FOLDERS
   中的状态顺序取前 N 个。

2. 网格模式（--grid 行x列）：每个单元格是一个独立姿势/表情，
   按固定网格均匀切分（单元格内与主体分离的装饰元素不会被误切）

       python tools/import_skin.py 表情图.png --name cat --grid 3x6 \
           --states excited,look_around,tired,skip,...,hungry,hungry,eating

   --states 按行优先顺序为每个单元格指定状态，数量需等于 行*列；
   写 skip（或 -）跳过该单元格；同一状态出现多次时，
   对应单元格按顺序成为该状态的多帧动画。

处理流程：

    精灵图 -> 检测背景色 -> 去除背景（RGBA 透明） -> 切分
        -> 帧归一化（方形画布、底部对齐、统一尺寸）
        -> 写入 assets/skins/<皮肤名>/<状态名>/frame_XX.png

向已存在的皮肤导入时按状态合并：本次涉及的状态会清空重写，
未涉及的状态保留；皮肤未提供的状态运行时自动回退到默认动画。
导入成功后默认将该皮肤设为当前皮肤（写入 config/skin_config.json），
使用 --no-activate 可只导入不启用。
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

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

# --states 中表示"跳过该单元格"的占位写法
_SKIP_TOKENS = ("skip", "-")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将精灵图导入为桌宠皮肤")
    parser.add_argument("image", help="精灵图文件路径")
    parser.add_argument("--name", required=True, help="皮肤名称（用作 assets/skins/ 下的目录名）")
    parser.add_argument(
        "--states",
        default="",
        help="逗号分隔的动画状态列表：行模式按行对应；网格模式按行优先逐格对应（skip 跳过）",
    )
    parser.add_argument(
        "--grid",
        default="",
        help="网格模式：固定行列数均匀切分，格式如 3x6（每个单元格一个姿势/表情）",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"背景色判定的颜色距离阈值（默认 {DEFAULT_TOLERANCE:.0f}，背景与主体颜色接近时调小）",
    )
    parser.add_argument(
        "--no-activate",
        action="store_true",
        help="仅导入皮肤，不设为当前使用的皮肤",
    )
    return parser.parse_args()


def validate_states(states: List[str]) -> None:
    """校验状态名是否均为已知动画状态。"""
    known_states = set(settings.ANIMATION_FOLDERS.keys())
    unknown = [s for s in states if s not in known_states]
    if unknown:
        raise SystemExit(
            f"未知的动画状态: {', '.join(unknown)}"
            f"（可用: {', '.join(settings.ANIMATION_FOLDERS.keys())}）"
        )


def collect_row_mode(image: Image.Image, alpha, states_arg: str) -> Dict[str, List[Image.Image]]:
    """行模式：自动投影切分，每行映射为一个动画状态的多帧。"""
    rows = slice_sheet(image, alpha)
    if not rows:
        raise SystemExit("未能从精灵图中切分出任何帧，请检查图片内容或调整 --tolerance")

    print(f"切分结果: {len(rows)} 行，每行帧数: {[len(row) for row in rows]}")

    if states_arg:
        states = [s.strip() for s in states_arg.split(",") if s.strip()]
        validate_states(states)
        if len(states) != len(rows):
            raise SystemExit(
                f"--states 数量（{len(states)}）与精灵图检测到的行数（{len(rows)}）不一致"
            )
    else:
        known_states = list(settings.ANIMATION_FOLDERS.keys())
        if len(rows) > len(known_states):
            raise SystemExit(f"精灵图行数（{len(rows)}）超过支持的动画状态数（{len(known_states)}）")
        states = known_states[:len(rows)]

    return {state: frames for state, frames in zip(states, rows)}


def collect_grid_mode(
    image: Image.Image, alpha, grid_arg: str, states_arg: str
) -> Dict[str, List[Image.Image]]:
    """网格模式：固定行列均匀切分，每个单元格按 --states 逐格映射。"""
    match = re.fullmatch(r"(\d+)x(\d+)", grid_arg.strip().lower())
    if not match:
        raise SystemExit(f"--grid 格式错误: {grid_arg}（应为 行x列，如 3x6）")
    grid_rows, grid_cols = int(match.group(1)), int(match.group(2))

    if not states_arg:
        raise SystemExit("网格模式必须通过 --states 为每个单元格指定状态（skip 跳过）")

    states = [s.strip() for s in states_arg.split(",")]
    if len(states) != grid_rows * grid_cols:
        raise SystemExit(
            f"--states 数量（{len(states)}）应等于网格单元格数（{grid_rows}x{grid_cols}"
            f"={grid_rows * grid_cols}），跳过的单元格请写 skip"
        )
    validate_states([s for s in states if s not in _SKIP_TOKENS])

    cells = slice_grid(image, alpha, grid_rows, grid_cols)

    grouped: Dict[str, List[Image.Image]] = {}
    for index, (state, cell) in enumerate(zip(states, cells)):
        position = f"({index // grid_cols + 1},{index % grid_cols + 1})"
        if state in _SKIP_TOKENS:
            continue
        if cell is None:
            print(f"  警告: 单元格{position} 无内容，已跳过（原计划 -> {state}）")
            continue
        grouped.setdefault(state, []).append(cell)

    if not grouped:
        raise SystemExit("没有任何单元格被映射到动画状态，请检查 --states")

    return grouped


def write_skin(skin_dir: str, grouped: Dict[str, List[Image.Image]], source: str) -> None:
    """将各状态帧写入皮肤目录（涉及的状态清空重写），并合并更新 skin.json。"""
    manifest_path = os.path.join(skin_dir, "skin.json")
    manifest = load_json(manifest_path) or {"name": os.path.basename(skin_dir), "states": {}}
    manifest.setdefault("states", {})
    manifest["source"] = source

    for state, frames in grouped.items():
        state_dir = os.path.join(skin_dir, state)
        os.makedirs(state_dir, exist_ok=True)

        for name in os.listdir(state_dir):
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                os.remove(os.path.join(state_dir, name))

        for index, frame in enumerate(frames):
            frame.save(os.path.join(state_dir, f"frame_{index:02d}.png"))

        manifest["states"][state] = len(frames)
        print(f"  {state}: {len(frames)} 帧 -> {state_dir}")

    save_json(manifest_path, manifest)


def main() -> None:
    args = parse_args()

    if not os.path.exists(args.image):
        raise SystemExit(f"找不到精灵图文件: {args.image}")

    image = Image.open(args.image)
    bg_color = detect_background_color(image)
    print(f"检测到背景色: RGB{bg_color}")

    alpha = build_alpha_mask(image, bg_color, tolerance=args.tolerance, feather=DEFAULT_FEATHER)

    if args.grid:
        grouped = collect_grid_mode(image, alpha, args.grid, args.states)
    else:
        grouped = collect_row_mode(image, alpha, args.states)

    # 归一化时合并全部帧统一画布，保证同一次导入的各状态尺寸一致
    state_names = list(grouped.keys())
    normalized = normalize_frames([grouped[s] for s in state_names], settings.SKIN_FRAME_SIZE)
    grouped = {state: frames for state, frames in zip(state_names, normalized)}

    skin_dir = os.path.join(settings.SKINS_DIR, args.name)
    write_skin(skin_dir, grouped, os.path.basename(args.image))

    if not args.no_activate:
        config = load_json(settings.SKIN_CONFIG_FILE) or {}
        config["active_skin"] = args.name
        save_json(settings.SKIN_CONFIG_FILE, config)
        print(f"已将当前皮肤设置为: {args.name}（重启桌宠生效）")
    else:
        print(f"皮肤已导入（未启用），可在 {settings.SKIN_CONFIG_FILE} 中设置 active_skin 启用")


if __name__ == "__main__":
    main()
