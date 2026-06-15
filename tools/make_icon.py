"""从宠物动画帧生成 Windows 应用图标 build/icon.ico。

打包前由构建脚本调用：取内置 cat 皮肤（无则回退默认）的一帧 idle，
缩放并写出多尺寸 .ico，作为 PyInstaller 的 exe 图标。

用法：
    python tools/make_icon.py            # 写出 build/icon.ico
"""

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 候选图标源（按优先级），取第一个存在的 idle 帧
_CANDIDATES = [
    os.path.join(ROOT, "assets", "skins", "cat", "idle", "frame_00.png"),
    os.path.join(ROOT, "assets", "animations", "idle", "frame_00.png"),
]
# 注意：不要放在 build/ 或 dist/，否则会被 PyInstaller 的 --clean 清掉
_OUT = os.path.join(ROOT, "packaging", "app_icon.ico")
_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _source_frame() -> str:
    for path in _CANDIDATES:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"找不到图标源帧，已尝试: {_CANDIDATES}")


def make_icon(out_path: str = _OUT) -> str:
    src = _source_frame()
    img = Image.open(src).convert("RGBA")

    # 贴到正方形透明画布居中，避免非方形帧被拉伸变形
    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path, format="ICO", sizes=_SIZES)
    return out_path


if __name__ == "__main__":
    out = make_icon()
    print(f"图标已生成: {out}  (源: {_source_frame()})")
    sys.exit(0)
