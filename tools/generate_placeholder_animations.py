"""占位动画素材生成脚本（开发辅助工具，非运行时代码）。

在正式美术资源到位前，生成简单的圆形宠物占位动画帧，
写入 assets/animations/<state>/ 目录，
用于联调动画系统、Sprite 渲染与主循环。

后续替换为正式美术资源时，只需替换对应目录下的图片文件，
文件名按 frame_00.png、frame_01.png ... 顺序命名即可，
无需修改动画系统代码。

运行方式：
    python tools/generate_placeholder_animations.py
"""

import os
from typing import List, Sequence, Tuple

import pygame

FRAME_SIZE = (96, 96)
BODY_RADIUS = 36
CENTER = (FRAME_SIZE[0] // 2, FRAME_SIZE[1] // 2)
EYE_COLOR = (40, 40, 40)

ASSETS_ANIMATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "animations",
)


def _new_frame(
    body_color: Tuple[int, int, int],
    eye_offset: int,
    mouth_points: Sequence[Tuple[int, int]],
) -> pygame.Surface:
    """绘制一帧宠物占位图：圆形身体 + 两只眼睛 + 嘴部线条。"""
    surface = pygame.Surface(FRAME_SIZE, pygame.SRCALPHA)
    cx, cy = CENTER

    pygame.draw.circle(surface, body_color, CENTER, BODY_RADIUS)

    eye_y = cy - 8 + eye_offset
    pygame.draw.circle(surface, EYE_COLOR, (cx - 14, eye_y), 4)
    pygame.draw.circle(surface, EYE_COLOR, (cx + 14, eye_y), 4)

    pygame.draw.lines(surface, EYE_COLOR, False, mouth_points, 3)
    return surface


def _build_idle_frames() -> List[pygame.Surface]:
    cx, cy = CENTER
    smile = [(cx - 12, cy + 14), (cx, cy + 18), (cx + 12, cy + 14)]
    color = (120, 180, 255)
    return [
        _new_frame(color, 0, smile),
        _new_frame(color, 0, smile),
        _new_frame(color, 2, smile),
        _new_frame(color, 0, smile),
    ]


def _build_happy_frames() -> List[pygame.Surface]:
    cx, cy = CENTER
    big_smile = [(cx - 14, cy + 12), (cx, cy + 22), (cx + 14, cy + 12)]
    color = (255, 210, 80)
    return [
        _new_frame(color, 0, big_smile),
        _new_frame(color, -4, big_smile),
        _new_frame(color, 0, big_smile),
        _new_frame(color, 4, big_smile),
    ]


def _build_hungry_frames() -> List[pygame.Surface]:
    cx, cy = CENTER
    sad_mouth = [(cx - 12, cy + 18), (cx, cy + 10), (cx + 12, cy + 18)]
    return [
        _new_frame((255, 170, 90), 0, sad_mouth),
        _new_frame((255, 130, 60), 0, sad_mouth),
    ]


def _build_tired_frames() -> List[pygame.Surface]:
    cx, cy = CENTER
    flat_mouth = [(cx - 12, cy + 16), (cx + 12, cy + 16)]
    color = (180, 180, 190)
    return [
        _new_frame(color, 6, flat_mouth),
        _new_frame(color, 8, flat_mouth),
        _new_frame(color, 6, flat_mouth),
        _new_frame(color, 4, flat_mouth),
    ]


ANIMATION_FRAME_BUILDERS = {
    "idle": _build_idle_frames,
    "happy": _build_happy_frames,
    "hungry": _build_hungry_frames,
    "tired": _build_tired_frames,
}


def main() -> None:
    pygame.init()
    # 部分平台需要先创建 display 才能正确保存带 alpha 通道的 Surface
    pygame.display.set_mode((1, 1))

    for state_name, build_frames in ANIMATION_FRAME_BUILDERS.items():
        output_dir = os.path.join(ASSETS_ANIMATIONS_DIR, state_name)
        os.makedirs(output_dir, exist_ok=True)

        for index, frame in enumerate(build_frames()):
            output_path = os.path.join(output_dir, f"frame_{index:02d}.png")
            pygame.image.save(frame, output_path)
            print(f"生成: {output_path}")

    pygame.quit()


if __name__ == "__main__":
    main()
