"""宠物核心类模块。

定义虚拟宠物的基础属性以及读写接口，
为后续阶段的动画状态、行为状态机预留扩展字段。
"""

from typing import Union

from config import settings
from core.animation import AnimationState


class Pet:
    """虚拟宠物核心类。

    包含基础属性（外观、状态数值、位置）以及当前动画状态的存取接口。
    behavior_state 字段在本阶段不会被使用，
    仅作为后续行为状态机的预留扩展点。
    """

    def __init__(
        self,
        name=settings.DEFAULT_PET_NAME,
        age=settings.DEFAULT_PET_AGE,
        hunger=settings.DEFAULT_PET_HUNGER,
        mood=settings.DEFAULT_PET_MOOD,
        energy=settings.DEFAULT_PET_ENERGY,
        position=None,
    ):
        self.name = name
        self.age = age
        self.hunger = self._clamp(hunger)
        self.mood = self._clamp(mood)
        self.energy = self._clamp(energy)
        self.position = position if position is not None else settings.DEFAULT_PET_POSITION

        # 当前动画状态（字符串值，对应 AnimationState 枚举）
        self.current_animation = settings.DEFAULT_ANIMATION_STATE

        # 预留扩展字段：后续阶段将用于行为状态机
        self.behavior_state = None

    # ----- 属性修改接口 -----
    def set_name(self, name):
        self.name = name

    def set_age(self, age):
        self.age = age

    def set_position(self, x, y):
        self.position = (x, y)

    def set_hunger(self, value):
        self.hunger = self._clamp(value)

    def set_mood(self, value):
        self.mood = self._clamp(value)

    def set_energy(self, value):
        self.energy = self._clamp(value)

    def change_animation(self, state: Union[AnimationState, str]) -> None:
        """切换宠物当前动画状态。

        state 可以是 AnimationState 枚举值，也可以是其字符串值（如 "happy"）。
        传入无效状态名称时会抛出 ValueError。
        """
        if isinstance(state, AnimationState):
            state = state.value
        else:
            state = AnimationState(state).value

        self.current_animation = state

    @staticmethod
    def _clamp(value):
        """将数值限制在配置的属性范围内。"""
        return max(settings.ATTRIBUTE_MIN, min(settings.ATTRIBUTE_MAX, value))

    # ----- 数据序列化接口（供持久化模块使用） -----
    def to_dict(self):
        """将宠物的基础数值属性转换为字典，用于保存到 JSON。"""
        return {
            "name": self.name,
            "age": self.age,
            "hunger": self.hunger,
            "mood": self.mood,
            "energy": self.energy,
        }

    @classmethod
    def from_dict(cls, data):
        """根据字典数据创建宠物实例，缺失字段使用默认值。"""
        return cls(
            name=data.get("name", settings.DEFAULT_PET_NAME),
            age=data.get("age", settings.DEFAULT_PET_AGE),
            hunger=data.get("hunger", settings.DEFAULT_PET_HUNGER),
            mood=data.get("mood", settings.DEFAULT_PET_MOOD),
            energy=data.get("energy", settings.DEFAULT_PET_ENERGY),
        )

    def __repr__(self):
        return (
            f"Pet(name={self.name!r}, age={self.age}, hunger={self.hunger}, "
            f"mood={self.mood}, energy={self.energy}, position={self.position})"
        )
