"""精灵图切分工具（背景检测/去除/切分/归一化）的回归测试。

使用 PIL 合成的精灵图，不依赖真实素材，便于离线回归。
"""

from PIL import Image

from utils.spritesheet import (
    build_alpha_mask,
    detect_background_color,
    normalize_frames,
    slice_grid,
    slice_sheet,
)

BG = (170, 237, 224)  # 与项目素材接近的薄荷绿背景
FG = (200, 80, 60)    # 前景方块颜色


def _make_sheet(rows, cols, cell=60, blob=30):
    """合成 rows x cols 的精灵图：每个单元格中央一个前景方块。"""
    img = Image.new("RGB", (cols * cell, rows * cell), BG)
    for r in range(rows):
        for c in range(cols):
            cx, cy = c * cell + cell // 2, r * cell + cell // 2
            half = blob // 2
            for x in range(cx - half, cx + half):
                for y in range(cy - half, cy + half):
                    img.putpixel((x, y), FG)
    return img


def test_detect_background_color():
    img = _make_sheet(2, 3)
    assert detect_background_color(img) == BG


def test_alpha_mask_marks_foreground_opaque_background_transparent():
    img = _make_sheet(1, 1)
    alpha = build_alpha_mask(img, BG)
    # 角落是背景 -> 透明
    assert alpha[0, 0] == 0
    # 中心是前景 -> 不透明
    assert alpha[alpha.shape[0] // 2, alpha.shape[1] // 2] == 255


def test_slice_sheet_detects_rows_and_frames():
    img = _make_sheet(3, 4)
    alpha = build_alpha_mask(img, BG)
    rows = slice_sheet(img, alpha)
    assert len(rows) == 3
    assert [len(r) for r in rows] == [4, 4, 4]


def test_slice_sheet_handles_empty_cell():
    # 第二行只有 2 个方块（中间留空），投影切分应得到该行 2 帧
    img = _make_sheet(2, 3)
    # 抹掉第二行第二个方块（恢复为背景）
    cell = 60
    for x in range(cell, 2 * cell):
        for y in range(cell, 2 * cell):
            img.putpixel((x, y), BG)
    alpha = build_alpha_mask(img, BG)
    rows = slice_sheet(img, alpha)
    assert len(rows) == 2
    assert len(rows[1]) == 2


def test_slice_grid_returns_fixed_cells_with_transparent_frames():
    img = _make_sheet(2, 3)
    alpha = build_alpha_mask(img, BG)
    cells = slice_grid(img, alpha, 2, 3)
    assert len(cells) == 6
    assert all(c is not None for c in cells)
    # 每个单元格帧均为 RGBA，含透明像素
    assert cells[0].mode == "RGBA"


def test_normalize_frames_uniform_square_size():
    img = _make_sheet(2, 2)
    alpha = build_alpha_mask(img, BG)
    rows = slice_sheet(img, alpha)
    target = (128, 128)
    normalized = normalize_frames(rows, target)
    sizes = {frame.size for row in normalized for frame in row}
    assert sizes == {target}
