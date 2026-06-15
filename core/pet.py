"""宠物核心类模块。

定义虚拟宠物的基础属性、当前行为状态与当前动画状态，
并提供属性读写、状态切换与数据序列化接口。

Pet 本身不包含状态判断逻辑与动画播放逻辑：
* 状态判断由 core.state_machine.StateMachine 完成
* 属性随时间变化与状态/动画同步由 core.behavior.PetBehavior 完成
* 动画播放由 core.animation / core.sprite 完成
"""

from typing import Any, Dict, Optional, Tuple, Union

from config import settings
from core.animation import AnimationState
from core.pet_state import PetState


class Pet:
    """虚拟宠物核心类。

    current_state 记录宠物当前的行为状态（由 StateMachine 计算）。
    current_animation 记录当前动画状态（字符串值，对应 AnimationState）。
    behavior_state 字段在本阶段不会被使用，仅作为未来扩展点保留。
    last_action / interaction_count 记录最近一次交互行为及累计交互次数，
    由 core.action.BehaviorManager 在执行行为后更新。
    """

    def __init__(
        self,
        name: str = settings.DEFAULT_PET_NAME,
        age: int = settings.DEFAULT_PET_AGE,
        hunger: float = settings.DEFAULT_PET_HUNGER,
        mood: float = settings.DEFAULT_PET_MOOD,
        energy: float = settings.DEFAULT_PET_ENERGY,
        position: Optional[Tuple[int, int]] = None,
    ) -> None:
        self.name = name
        self.age = age
        self.hunger = self._clamp(hunger)
        self.mood = self._clamp(mood)
        self.energy = self._clamp(energy)
        self.position = position if position is not None else settings.DEFAULT_PET_POSITION

        # 当前朝向：素材帧默认朝右，向左移动时由 Sprite 镜像翻转渲染。
        # 运行时状态，不持久化。
        self.facing_left = False

        # 当前行为状态（由 StateMachine 计算，core.behavior 负责同步）
        self.current_state = PetState.IDLE

        # 当前动画状态（字符串值，对应 AnimationState 枚举）
        self.current_animation = settings.DEFAULT_ANIMATION_STATE

        # 预留扩展字段：后续阶段将用于更多行为相关数据
        self.behavior_state = None

        # 最近一次交互行为名称（对应 InteractionEventType 的值，如 "feed"）
        self.last_action: Optional[str] = None

        # 累计交互次数，由 BehaviorManager 在每次执行行为后更新
        self.interaction_count = 0

        # 成长系统：等级与当前等级内的经验值。正向养成动作积累经验，满则升级
        # （升级阈值随等级增长，见 exp_to_next / add_exp）。由 Game 在交互后调用。
        self.level = 1
        self.exp = 0

    # ----- 属性修改接口（绝对赋值，自动限制范围） -----
    def set_name(self, name: str) -> None:
        self.name = name

    def set_age(self, age: int) -> None:
        self.age = age

    def set_position(self, x: int, y: int) -> None:
        self.position = (x, y)

    def set_hunger(self, value: float) -> None:
        self.hunger = self._clamp(value)

    def set_mood(self, value: float) -> None:
        self.mood = self._clamp(value)

    def set_energy(self, value: float) -> None:
        self.energy = self._clamp(value)

    # ----- 属性增减接口（相对修改，自动限制在 0~100） -----
    def increase_hunger(self, amount: float = 1) -> None:
        self.set_hunger(self.hunger + amount)

    def decrease_hunger(self, amount: float = 1) -> None:
        self.set_hunger(self.hunger - amount)

    def increase_mood(self, amount: float = 1) -> None:
        self.set_mood(self.mood + amount)

    def decrease_mood(self, amount: float = 1) -> None:
        self.set_mood(self.mood - amount)

    def increase_energy(self, amount: float = 1) -> None:
        self.set_energy(self.energy + amount)

    def decrease_energy(self, amount: float = 1) -> None:
        self.set_energy(self.energy - amount)

    def exp_to_next(self) -> int:
        """升到下一级所需的经验值（随等级线性增长）。"""
        return settings.LEVEL_BASE_EXP * self.level

    def title(self) -> str:
        """当前等级对应的成长称号（取 settings.LEVEL_TITLES 中 <= 等级的最高一档）。"""
        name = settings.LEVEL_TITLES[0][1]
        for min_level, label in settings.LEVEL_TITLES:
            if self.level >= min_level:
                name = label
            else:
                break
        return name

    def add_exp(self, amount: float) -> int:
        """累加经验并结算升级，返回本次升了几级（0 表示未升级）。

        到达 LEVEL_MAX 后不再升级、经验清零。amount<=0 或已满级直接返回 0。
        """
        if amount <= 0 or self.level >= settings.LEVEL_MAX:
            return 0
        self.exp += amount
        levels = 0
        while self.level < settings.LEVEL_MAX and self.exp >= self.exp_to_next():
            self.exp -= self.exp_to_next()
            self.level += 1
            levels += 1
        if self.level >= settings.LEVEL_MAX:
            self.exp = 0
        return levels

    def record_interaction(self, action_name: str) -> None:
        """记录一次交互行为：更新最近行为名称并累加交互次数。"""
        self.last_action = action_name
        self.interaction_count += 1

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
    def _clamp(value: float) -> float:
        """将数值限制在配置的属性范围内。"""
        return max(settings.ATTRIBUTE_MIN, min(settings.ATTRIBUTE_MAX, value))

    # ----- 数据序列化接口（供持久化模块使用） -----
    def to_dict(self) -> Dict[str, Any]:
        """将宠物的基础属性与当前状态转换为字典，用于保存到 JSON。"""
        return {
            "name": self.name,
            "age": self.age,
            "hunger": self.hunger,
            "mood": self.mood,
            "energy": self.energy,
            "state": self.current_state.name,
            "last_action": self.last_action,
            "interaction_count": self.interaction_count,
            "level": self.level,
            "exp": self.exp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Pet":
        """根据字典数据创建宠物实例，缺失字段使用默认值。"""
        pet = cls(
            name=data.get("name", settings.DEFAULT_PET_NAME),
            age=data.get("age", settings.DEFAULT_PET_AGE),
            hunger=data.get("hunger", settings.DEFAULT_PET_HUNGER),
            mood=data.get("mood", settings.DEFAULT_PET_MOOD),
            energy=data.get("energy", settings.DEFAULT_PET_ENERGY),
        )
        pet.current_state = PetState[data.get("state", PetState.IDLE.name)]
        pet.last_action = data.get("last_action")
        pet.interaction_count = data.get("interaction_count", 0)
        pet.level = max(1, int(data.get("level", 1)))
        pet.exp = max(0, data.get("exp", 0))
        return pet

    def __repr__(self) -> str:
        return (
            f"Pet(name={self.name!r}, age={self.age}, hunger={self.hunger}, "
            f"mood={self.mood}, energy={self.energy}, state={self.current_state.name})"
        )
