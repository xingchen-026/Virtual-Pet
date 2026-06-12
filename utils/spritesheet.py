"""精灵图切分工具模块。

将用户上传的整张精灵图（sprite sheet，背景不一定透明）切分为
逐帧贴图，供皮肤导入工具（tools/import_skin.py）使用：

1. 自动检测背景色（取四角像素的众数）
2. 按颜色距离生成"非背景"掩码，去除背景（输出 RGBA 透明背景）
3. 按掩码的行/列投影自动定位每一行精灵与行内每一帧
   （支持行内有空缺、间距不均匀的精灵图）
4. 将所有帧归一化到同一尺寸的方形画布（底部居中对齐，
   避免动画播放时上下跳动），再缩放到目标尺寸

本模块只依赖 PIL 与 numpy，不依赖 pygame，可独立测试。
"""

from __future__ import annotations

from collections import Counter
from typing import List, Tuple

import numpy as np
from PIL import Image

# 行/列投影中，小于该像素数的空隙视为同一精灵内部的间隙（合并）
_MIN_GAP = 4

# 小于该尺寸（宽或高）的色块视为噪点，不作为帧输出
_MIN_CELL_SIZE = 12

# 背景去除的默认颜色距离阈值与边缘羽化宽度
DEFAULT_TOLERANCE = 40.0
DEFAULT_FEATHER = 30.0

# 网格模式中，贴着单元格边缘且面积小于最大色块该比例的连通块
# 视为相邻单元格精灵越界产生的碎片，予以剔除
# （主体精灵即使贴边也是最大连通块，不会被误删）
_BORDER_DEBRIS_RATIO = 0.3


def detect_background_color(image: Image.Image) -> Tuple[int, int, int]:
    """检测精灵图背景色：取四个角落小块像素的众数。"""
    rgb = image.convert("RGB")
    width, height = rgb.size
    sample = 5

    pixels: List[Tuple[int, int, int]] = []
    for x0, y0 in ((0, 0), (width - sample, 0), (0, height - sample), (width - sample, height - sample)):
        for dx in range(sample):
            for dy in range(sample):
                pixels.append(rgb.getpixel((x0 + dx, y0 + dy)))

    return Counter(pixels).most_common(1)[0][0]


def build_alpha_mask(
    image: Image.Image,
    bg_color: Tuple[int, int, int],
    tolerance: float = DEFAULT_TOLERANCE,
    feather: float = DEFAULT_FEATHER,
) -> np.ndarray:
    """根据与背景色的颜色距离生成 alpha 通道（0-255 的 uint8 数组）。

    距离 <= tolerance 的像素视为背景（alpha=0）；
    距离在 tolerance ~ tolerance+feather 之间的像素线性过渡，
    使抗锯齿边缘平滑，避免出现硬边/背景色描边。
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    distance = np.sqrt(((rgb - np.array(bg_color, dtype=np.float32)) ** 2).sum(axis=2))

    alpha = (distance - tolerance) / max(feather, 1.0)
    return (alpha.clip(0.0, 1.0) * 255).astype(np.uint8)


def _find_runs(flags: np.ndarray, min_gap: int, min_size: int) -> List[Tuple[int, int]]:
    """在一维布尔数组中查找连续 True 区段（起止下标，含合并与去噪）。"""
    indices = np.flatnonzero(flags)
    if indices.size == 0:
        return []

    runs: List[Tuple[int, int]] = []
    start = prev = int(indices[0])
    for index in indices[1:]:
        index = int(index)
        if index - prev > min_gap:
            runs.append((start, prev + 1))
            start = index
        prev = index
    runs.append((start, prev + 1))

    return [(s, e) for s, e in runs if e - s >= min_size]


def slice_sheet(
    image: Image.Image,
    alpha: np.ndarray,
) -> List[List[Image.Image]]:
    """按 alpha 掩码将精灵图切分为按行分组的 RGBA 帧列表。

    返回值：rows[i][j] 为第 i 行（从上到下）第 j 帧（从左到右），
    每帧已去除背景并裁剪到内容的紧致包围盒。
    """
    rgba = np.dstack([np.asarray(image.convert("RGB"), dtype=np.uint8), alpha])
    mask = alpha > 0

    rows: List[List[Image.Image]] = []
    for top, bottom in _find_runs(mask.any(axis=1), _MIN_GAP, _MIN_CELL_SIZE):
        band = mask[top:bottom]
        row_frames: List[Image.Image] = []

        for left, right in _find_runs(band.any(axis=0), _MIN_GAP, _MIN_CELL_SIZE):
            cell = band[:, left:right]
            cell_rows = np.flatnonzero(cell.any(axis=1))
            cell_top, cell_bottom = top + int(cell_rows[0]), top + int(cell_rows[-1]) + 1

            frame = rgba[cell_top:cell_bottom, left:right]
            row_frames.append(Image.fromarray(frame, mode="RGBA"))

        if row_frames:
            rows.append(row_frames)

    return rows


def _remove_border_debris(cell_mask: np.ndarray) -> np.ndarray:
    """剔除单元格内贴边的小连通块（相邻单元格精灵越界的碎片）。

    均匀网格切分时，相邻单元格的精灵（耳朵/尾巴/装饰）可能越过
    分界线漏进本单元格，表现为贴着单元格边缘的小碎片。
    规则：连通块同时满足「接触单元格边缘」且「面积小于最大连通块
    的 _BORDER_DEBRIS_RATIO 倍」时剔除；不贴边的小装饰
    （星星 / zZ / 气泡等）不受影响。
    """
    from scipy import ndimage

    labels, count = ndimage.label(cell_mask)
    if count <= 1:
        return cell_mask

    areas = ndimage.sum_labels(cell_mask, labels, index=range(1, count + 1))
    max_area = areas.max()

    border_labels = set(np.unique(labels[0, :])) | set(np.unique(labels[-1, :])) \
        | set(np.unique(labels[:, 0])) | set(np.unique(labels[:, -1]))

    cleaned = cell_mask.copy()
    for label_id in range(1, count + 1):
        if label_id in border_labels and areas[label_id - 1] < max_area * _BORDER_DEBRIS_RATIO:
            cleaned[labels == label_id] = False

    return cleaned


def slice_grid(
    image: Image.Image,
    alpha: np.ndarray,
    grid_rows: int,
    grid_cols: int,
) -> List[Image.Image]:
    """按固定行列数将精灵图均匀切分为单元格（按行优先顺序返回）。

    与 slice_sheet 的自动投影切分不同，本方法适用于
    "每个单元格是一个独立姿势/表情"的素材（如情绪表情图），
    单元格内可能存在与主体分离的装饰元素（星星/气泡等），
    投影法会将其误判为独立帧，固定网格则将其保留在同一帧内。

    每个单元格内按掩码裁剪到内容紧致包围盒；
    无内容的单元格返回 None 占位，保持行优先索引与网格一致。
    """
    rgba = np.dstack([np.asarray(image.convert("RGB"), dtype=np.uint8), alpha])
    mask = alpha > 0
    height, width = mask.shape

    cells: List[Image.Image] = []
    for row in range(grid_rows):
        top = row * height // grid_rows
        bottom = (row + 1) * height // grid_rows
        for col in range(grid_cols):
            left = col * width // grid_cols
            right = (col + 1) * width // grid_cols

            cell_mask = _remove_border_debris(mask[top:bottom, left:right])
            ys = np.flatnonzero(cell_mask.any(axis=1))
            xs = np.flatnonzero(cell_mask.any(axis=0))
            if ys.size == 0 or xs.size == 0:
                cells.append(None)
                continue

            # 应用剔除碎片后的掩码，再裁剪到内容包围盒
            cell = rgba[top:bottom, left:right].copy()
            cell[:, :, 3] = np.where(cell_mask, cell[:, :, 3], 0)
            frame = cell[int(ys[0]): int(ys[-1]) + 1, int(xs[0]): int(xs[-1]) + 1]
            cells.append(Image.fromarray(frame, mode="RGBA"))

    return cells


def normalize_frames(
    rows: List[List[Image.Image]],
    target_size: Tuple[int, int],
) -> List[List[Image.Image]]:
    """将所有帧归一化到同一尺寸。

    先以全部帧的最大宽/高确定方形画布，每帧底部居中粘贴
    （宠物站立类素材底部对齐，动画播放不跳动），
    再整体缩放到 target_size。
    """
    all_frames = [frame for row in rows for frame in row]
    if not all_frames:
        return rows

    side = max(max(f.width for f in all_frames), max(f.height for f in all_frames))

    normalized: List[List[Image.Image]] = []
    for row in rows:
        new_row: List[Image.Image] = []
        for frame in row:
            canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            canvas.paste(frame, ((side - frame.width) // 2, side - frame.height))
            new_row.append(canvas.resize(target_size, Image.LANCZOS))
        normalized.append(new_row)

    return normalized
