"""动画系统核心模块。

提供：

* AnimationState  —— 动画状态枚举，集中管理状态名称
* Animation       —— 单组动画帧序列的播放控制
* AnimationManager —— 管理多组状态动画并支持状态切换

后续阶段如需新增宠物动作，只需：

1. 在 AnimationState 中新增枚举值
2. 在 assets/animations 下新增对应资源目录
3. 在 config/settings.py 的动画配置中注册目录与播放速度

无需修改本模块的核心逻辑。
"""

from __future__ import annotations

import enum
from typing import Dict, List, Union

import pygame


class AnimationState(enum.Enum):
    """宠物动画状态枚举。

    使用枚举而非裸字符串管理状态，避免状态名称在代码中被硬编码、写错。
    """

    IDLE = "idle"
    HAPPY = "happy"
    HUNGRY = "hungry"
    TIRED = "tired"
    INTERACT = "interact"
    EXCITED = "excited"
    EATING = "eating"
    PLAYING = "playing"
    WALK = "walk"
    RUN = "run"
    LOOK_AROUND = "look_around"
    SLEEP = "sleep"


class Animation:
    """单组动画：管理一段帧图像序列的播放进度。"""

    def __init__(
        self,
        frames: List[pygame.Surface],
        frame_duration: float = 0.15,
        loop: bool = True,
    ) -> None:
        if not frames:
            raise ValueError("动画至少需要包含一帧图像")
        if frame_duration <= 0:
            raise ValueError("frame_duration 必须为正数")

        self.frames = frames
        self.frame_duration = frame_duration
        self.loop = loop

        self._elapsed = 0.0
        self._frame_index = 0
        self._finished = False

    def reset(self) -> None:
        """重置动画到第一帧，重新开始播放进度计时。"""
        self._elapsed = 0.0
        self._frame_index = 0
        self._finished = False

    def update(self, dt: float) -> None:
        """根据时间增量推进动画帧。

        dt: 距离上一次更新的时间间隔（秒）。
        """
        if self._finished:
            return

        self._elapsed += dt
        while self._elapsed >= self.frame_duration:
            self._elapsed -= self.frame_duration
            self._frame_index += 1

            if self._frame_index >= len(self.frames):
                if self.loop:
                    self._frame_index = 0
                else:
                    self._frame_index = len(self.frames) - 1
                    self._finished = True
                    break

    @property
    def current_frame(self) -> pygame.Surface:
        """返回当前应显示的帧图像。"""
        return self.frames[self._frame_index]


class AnimationManager:
    """动画管理器：持有多组状态动画，并管理当前播放状态与速度。"""

    def __init__(
        self,
        animations: Dict[AnimationState, Animation],
        default_state: AnimationState = AnimationState.IDLE,
    ) -> None:
        if default_state not in animations:
            raise ValueError(f"缺少默认动画状态对应的动画数据: {default_state}")

        self._animations = animations
        self._current_state = default_state
        self._speed = 1.0

        self._current_animation.reset()

    @property
    def _current_animation(self) -> Animation:
        return self._animations[self._current_state]

    @property
    def current_state(self) -> AnimationState:
        """当前播放中的动画状态。"""
        return self._current_state

    def set_speed(self, speed: float) -> None:
        """设置全局播放速度倍率（1.0 为正常速度）。"""
        if speed <= 0:
            raise ValueError("播放速度必须为正数")
        self._speed = speed

    def set_state(self, state: Union[AnimationState, str]) -> None:
        """切换当前动画状态。

        state 可以是 AnimationState 枚举值，也可以是其字符串值（如 "happy"）。
        切换到不同状态时会重置该动画的播放进度；若状态未变化则不做任何操作。
        """
        if isinstance(state, str):
            state = AnimationState(state)

        if state not in self._animations:
            raise ValueError(f"未注册的动画状态: {state}")

        if state == self._current_state:
            return

        self._current_state = state
        self._current_animation.reset()

    def update(self, dt: float) -> None:
        """推进当前动画的播放进度。"""
        self._current_animation.update(dt * self._speed)

    def get_current_frame(self) -> pygame.Surface:
        """获取当前动画状态下应显示的帧图像。"""
        return self._current_animation.current_frame
