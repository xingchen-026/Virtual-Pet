"""宠物状态机模块。

根据宠物的属性数值（饥饿 / 心情 / 体力）独立计算宠物当前
应处于的 PetState。

判断逻辑不依赖 Pet 类或动画系统，只接收数值参数，
便于单独测试与后续扩展更多判断规则。
"""

from core.pet_state import PetState

# 状态判断阈值，集中管理，避免魔法数字散落在判断逻辑中
HUNGER_THRESHOLD = 30
ENERGY_THRESHOLD = 30
MOOD_HAPPY_THRESHOLD = 80


class StateMachine:
    """根据属性数值计算宠物应处于的状态。"""

    @staticmethod
    def evaluate(hunger: float, mood: float, energy: float) -> PetState:
        """根据 hunger / mood / energy 计算当前状态。

        判断优先级：饥饿 > 疲劳 > 开心 > 默认（待机）。
        """
        if hunger < HUNGER_THRESHOLD:
            return PetState.HUNGRY

        if energy < ENERGY_THRESHOLD:
            return PetState.TIRED

        if mood > MOOD_HAPPY_THRESHOLD:
            return PetState.HAPPY

        return PetState.IDLE
