"""互动音效模块。

SoundManager 用 numpy 程序化合成短促音效（无需任何外部音频素材，离线自包含），
在喂食/玩耍/洗澡/送礼/点击等互动时播放，提升反馈手感。

设计：
* 各事件对应一段「音符序列」（频率, 时长），渲染为带淡入淡出的 int16 立体声波形，
  经 pygame.sndarray.make_sound 得到可播放的 Sound，启动时一次性预渲染缓存。
* 音频设备不可用（无声卡 / CI 无音频 / mixer 初始化失败）时整体静默降级，
  不影响桌宠其它功能。
* 总开关 enabled 可运行时切换（设置窗口），音量 0~1。

render_event_samples 为纯函数，便于在无音频设备的环境下单测波形。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from utils.exception import AppError, log_exception

SAMPLE_RATE = 44100

# 事件 -> 音符序列 [(频率Hz, 时长秒), ...]，依次播放（上行音阶=积极反馈）
EVENT_NOTES: Dict[str, List[Tuple[float, float]]] = {
    "feed": [(660, 0.08), (880, 0.10)],
    "play": [(784, 0.07), (988, 0.07), (1175, 0.09)],
    "bath": [(523, 0.07), (784, 0.11)],
    "gift": [(659, 0.07), (784, 0.07), (1047, 0.13)],
    "click": [(440, 0.05)],
    "excited": [(880, 0.05), (1320, 0.09)],
    "levelup": [(523, 0.10), (659, 0.10), (784, 0.16)],
}


def render_event_samples(
    notes: List[Tuple[float, float]], sample_rate: int = SAMPLE_RATE
) -> np.ndarray:
    """把音符序列渲染为 int16 立体声波形 (N, 2)。

    每个音符为正弦波 + 短淡入淡出包络（避免起止爆音），按顺序拼接。
    幅度归一到接近满量程，播放音量由 Sound.set_volume 控制（不在此烘焙）。
    """
    chunks: List[np.ndarray] = []
    for freq, duration in notes:
        n = max(1, int(sample_rate * duration))
        t = np.linspace(0.0, duration, n, endpoint=False)
        wave = np.sin(2.0 * np.pi * freq * t)

        # 线性淡入淡出包络（各取约 8ms 或四分之一段，取小者）
        fade = min(n // 4, int(sample_rate * 0.008)) or 1
        env = np.ones(n)
        env[:fade] = np.linspace(0.0, 1.0, fade)
        env[-fade:] = np.linspace(1.0, 0.0, fade)
        chunks.append(wave * env)

    mono = np.concatenate(chunks) if chunks else np.zeros(1)
    samples = (mono * 32767 * 0.9).astype(np.int16)
    return np.column_stack([samples, samples])


class SoundManager:
    """合成并播放互动音效；音频不可用时静默降级。"""

    def __init__(self, enabled: bool = True, volume: float = 0.45) -> None:
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self._sounds: Dict[str, "object"] = {}
        self._ok = False

        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2)
            for name, notes in EVENT_NOTES.items():
                sound = pygame.sndarray.make_sound(render_event_samples(notes))
                sound.set_volume(self.volume)
                self._sounds[name] = sound
            self._ok = True
        except Exception as exc:  # 无音频设备 / mixer 失败 -> 静默降级
            log_exception(AppError(f"音效初始化失败，已静音: {exc}"))

    def play(self, name: Optional[str]) -> None:
        """播放某事件音效；name 为 None / 未知 / 关闭 / 不可用时安全跳过。"""
        if not name or not self.enabled or not self._ok:
            return
        sound = self._sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def set_enabled(self, enabled: bool) -> None:
        """运行时切换音效总开关。"""
        self.enabled = enabled
