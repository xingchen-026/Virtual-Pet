"""宠物行为逻辑模块。

负责：

* 基于计时器的属性随时间自然变化（饥饿 / 体力衰减，心情波动）
* 调用 StateMachine 计算当前状态
* 状态发生变化时同步 Pet.current_state 并驱动动画切换

属性系统与动画系统通过本模块解耦：
PetBehavior 只在状态变化时调用 pet.change_animation()，
Pet 与 AnimationManager 互不直接依赖。
"""

from config import settings
from core.pet import Pet
from core.pet_state import PetState
from core.state_machine import StateMachine

# PetState -> 动画状态名称（对应 core.animation.AnimationState 的值）
# 尚未拥有专属动画的状态（如 SAD）暂时回退到 idle 动画，
# 待后续阶段补充对应动画资源后在此扩展。
STATE_ANIMATION_MAP = {
    PetState.IDLE: "idle",
    PetState.HAPPY: "happy",
    PetState.HUNGRY: "hungry",
    PetState.TIRED: "tired",
    PetState.SAD: "idle",
}


class PetBehavior:
    """管理宠物属性随时间的自然变化，以及状态与动画的同步。"""

    def __init__(self, pet: Pet) -> None:
        self.pet = pet
        self._elapsed = 0.0

        # 启动时按 pet.current_state（可能来自存档）同步一次动画
        self._sync_animation()

    def update(self, dt: float) -> None:
        """累计时间，每达到一个 tick 间隔执行一次属性衰减与状态刷新。

        dt: 距离上一次更新的时间间隔（秒）。
        """
        self._elapsed += dt

        while self._elapsed >= settings.ATTRIBUTE_DECAY_INTERVAL:
            self._elapsed -= settings.ATTRIBUTE_DECAY_INTERVAL
            self._tick()

    def _tick(self) -> None:
        """单次属性自然变化，并在状态变化时刷新动画。"""
        self.pet.decrease_hunger(settings.HUNGER_DECAY_PER_TICK)
        self.pet.decrease_energy(settings.ENERGY_DECAY_PER_TICK)

        # 开心状态下心情保持不变，其余状态正常衰减
        if StateMachine.evaluate(self.pet.hunger, self.pet.mood, self.pet.energy) != PetState.HAPPY:
            self.pet.decrease_mood(settings.MOOD_DECAY_PER_TICK)

        new_state = StateMachine.evaluate(self.pet.hunger, self.pet.mood, self.pet.energy)
        if new_state != self.pet.current_state:
            self.pet.current_state = new_state
            self._sync_animation()

    def _sync_animation(self) -> None:
        """将动画切换为 pet.current_state 对应的动画。"""
        self.pet.change_animation(STATE_ANIMATION_MAP[self.pet.current_state])
