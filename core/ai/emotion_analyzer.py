"""情绪分析模块。

EmotionAnalyzer 将一段文本映射为宠物属性的变化量
（mood_delta / energy_delta）与建议触发的动画状态，
用于实现"对话影响宠物情绪"以及"AI 判断影响桌宠状态"。

初期方案：规则（关键词）匹配 + 对 AI 回复中情绪标签的解析，
不强制依赖额外模型：

* 用户输入命中正向关键词（可爱/喜欢/谢谢...） -> mood +10
* 用户输入命中负向关键词（笨/讨厌/生气...）   -> mood -5
* 用户输入命中疲劳关键词（累/睡觉/休息...）   -> energy -5，
  建议动画 sleep
* AI 回复若携带「[情绪:开心]」「[情绪:生气]」「[情绪:疲惫]」等
  标签，则优先按标签结果应用（标签会从最终展示文本中移除）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# 关键词规则：命中即触发对应的属性变化
_POSITIVE_KEYWORDS = ("可爱", "喜欢", "谢谢", "真棒", "开心", "爱你", "真好")
_NEGATIVE_KEYWORDS = ("笨", "讨厌", "生气", "烦", "丑", "滚")
_TIRED_KEYWORDS = ("累", "睡觉", "休息", "困")

_POSITIVE_MOOD_DELTA = 10.0
_NEGATIVE_MOOD_DELTA = -5.0
_TIRED_ENERGY_DELTA = -5.0

# AI 回复情绪标签格式：[情绪:开心] / [情绪：生气] 等
_EMOTION_TAG_PATTERN = re.compile(r"\[情绪[:：]\s*(\S+?)\]")

# 情绪标签 -> 属性变化映射
_TAG_MOOD_EFFECTS = {
    "开心": _POSITIVE_MOOD_DELTA,
    "高兴": _POSITIVE_MOOD_DELTA,
    "兴奋": _POSITIVE_MOOD_DELTA,
    "生气": _NEGATIVE_MOOD_DELTA,
    "难过": _NEGATIVE_MOOD_DELTA,
    "委屈": _NEGATIVE_MOOD_DELTA,
}
_TAG_TIRED_LABELS = ("疲惫", "困倦", "疲劳")


@dataclass
class EmotionEffect:
    """一次对话对宠物属性的影响，以及建议触发的动画状态。"""

    mood_delta: float = 0.0
    energy_delta: float = 0.0
    suggested_animation: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        """是否不包含任何属性变化或动画建议。"""
        return self.mood_delta == 0 and self.energy_delta == 0 and self.suggested_animation is None


class EmotionAnalyzer:
    """基于关键词规则与情绪标签的文本情绪分析器。"""

    def analyze(self, text: str) -> EmotionEffect:
        """分析一段文本（通常是用户输入），返回属性变化量与建议动画。"""
        effect = EmotionEffect()

        if any(keyword in text for keyword in _POSITIVE_KEYWORDS):
            effect.mood_delta += _POSITIVE_MOOD_DELTA

        if any(keyword in text for keyword in _NEGATIVE_KEYWORDS):
            effect.mood_delta += _NEGATIVE_MOOD_DELTA

        if any(keyword in text for keyword in _TIRED_KEYWORDS):
            effect.energy_delta += _TIRED_ENERGY_DELTA
            effect.suggested_animation = "sleep"

        return effect

    def from_tag(self, reply: str) -> EmotionEffect:
        """解析 AI 回复中可能携带的情绪标签，如「[情绪:开心]」。"""
        match = _EMOTION_TAG_PATTERN.search(reply)
        if not match:
            return EmotionEffect()

        tag = match.group(1)

        if tag in _TAG_MOOD_EFFECTS:
            return EmotionEffect(mood_delta=_TAG_MOOD_EFFECTS[tag])

        if tag in _TAG_TIRED_LABELS:
            return EmotionEffect(energy_delta=_TIRED_ENERGY_DELTA, suggested_animation="sleep")

        return EmotionEffect()

    @staticmethod
    def strip_tag(reply: str) -> str:
        """从回复文本中移除情绪标签，得到展示给用户的纯文本。"""
        return _EMOTION_TAG_PATTERN.sub("", reply).strip()
