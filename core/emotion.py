"""宠物表情系统模块。

EmotionManager 根据宠物的属性数值与最近一次交互行为
（Pet.last_action），综合判断当前应展示的表情。

表情系统只产生「展示信息」，不修改 Pet 的属性、
不直接操作动画系统，避免与状态机 / 动画系统耦合。
所有阈值均来自 behavior_config，不硬编码。
"""

from __future__ import annotations

import enum

from core.pet import Pet

# 用户主动交互后，会让宠物显得开心的行为名称
# （对应 core.event.InteractionEventType 的字符串值）
_POSITIVE_USER_ACTIONS = {"feed", "play", "click"}


class Emotion(enum.Enum):
    """宠物表情。"""

    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    HUNGRY = "hungry"
    SLEEPY = "sleepy"
    EXCITED = "excited"
    NEUTRAL = "neutral"


class EmotionManager:
    """根据属性、行为与用户操作综合判断宠物当前表情。"""

    def __init__(self, behavior_config: dict) -> None:
        self.config = behavior_config
        self.current_emotion = Emotion.NEUTRAL

    def update(self, pet: Pet) -> Emotion:
        """根据宠物当前数据刷新并返回当前表情。"""
        self.current_emotion = self._derive(pet)
        return self.current_emotion

    def _derive(self, pet: Pet) -> Emotion:
        # 长期严重饥饿且心情低落：愤怒
        if (
            pet.hunger < self.config["angry_hunger_threshold"]
            and pet.mood < self.config["sad_threshold"]
        ):
            return Emotion.ANGRY

        # 饥饿
        if pet.hunger < self.config["hunger_threshold"]:
            return Emotion.HUNGRY

        # 疲劳欲睡
        if pet.energy < self.config["sleep_threshold"]:
            return Emotion.SLEEPY

        # 用户刚触发连续点击：兴奋
        if pet.last_action == "excited":
            return Emotion.EXCITED

        # 心情愉悦，或用户刚进行了正向互动：开心
        if pet.mood > self.config["happy_threshold"] or pet.last_action in _POSITIVE_USER_ACTIONS:
            return Emotion.HAPPY

        # 心情低落：难过
        if pet.mood < self.config["sad_threshold"]:
            return Emotion.SAD

        return Emotion.NEUTRAL
