"""宠物行为逻辑模块。

负责：

* 基于计时器的属性随时间自然变化（饥饿 / 体力衰减，心情波动）
* 调用 StateMachine 计算当前状态
* 状态发生变化时同步 Pet.current_state 并驱动动画切换
* 管理交互行为触发的临时动画（如 happy / eating / playing），
  播放结束后自动恢复为当前状态对应的动画

属性系统与动画系统通过本模块解耦：
PetBehavior 只在状态变化或临时动画结束时调用 pet.change_animation()，
Pet 与 AnimationManager 互不直接依赖。
"""

from config import settings
from core.pet import Pet
from core.pet_state import PetState
from core.state_machine import StateMachine

# PetState -> 动画状态名称（对应 core.animation.AnimationState 的值）
STATE_ANIMATION_MAP = {
    PetState.IDLE: "idle",
    PetState.HAPPY: "happy",
    PetState.HUNGRY: "hungry",
    PetState.TIRED: "tired",
    PetState.SAD: "sad",
}


class PetBehavior:
    """管理宠物属性随时间的自然变化，以及状态与动画的同步。"""

    def __init__(self, pet: Pet) -> None:
        self.pet = pet
        self._elapsed = 0.0

        # 临时动画剩余播放时间。大于 0 时，状态驱动的动画同步会被暂时跳过，
        # 计时结束后自动恢复为 pet.current_state 对应的动画。
        self._temp_animation_timer = 0.0

        # 睡眠模式：点击「睡觉」后停在原地、持续播放 sleep 动画、
        # 按时间缓慢恢复体力，体力回满或被交互打断后醒来。
        self._sleeping = False

        # 启动时按 pet.current_state（可能来自存档）同步一次动画
        self._sync_animation()

    @property
    def is_sleeping(self) -> bool:
        """当前是否处于睡眠模式（供 Game 暂停自主漫游、保持窗口静止）。"""
        return self._sleeping

    @property
    def is_critical(self) -> bool:
        """是否处于危急状态（饥饿或体力归零）。

        供 Game 暂停自主漫游，使宠物停在原地、持续显示饥饿/疲劳动画。
        """
        threshold = settings.CRITICAL_ATTRIBUTE_THRESHOLD
        return self.pet.hunger <= threshold or self.pet.energy <= threshold

    def start_sleep(self) -> None:
        """进入睡眠模式：切换为 sleep 动画并清除临时动画计时。"""
        self._sleeping = True
        self._temp_animation_timer = 0.0
        self._elapsed = 0.0
        self.pet.change_animation("sleep")

    def stop_sleep(self) -> None:
        """退出睡眠模式，恢复为当前状态对应的动画。"""
        if not self._sleeping:
            return
        self._sleeping = False
        self._sync_animation()

    def update(self, dt: float) -> None:
        """累计时间，每达到一个 tick 间隔执行一次属性变化与状态刷新。

        dt: 距离上一次更新的时间间隔（秒）。
        """
        if self._sleeping:
            self._update_sleep(dt)
            return

        if self._temp_animation_timer > 0:
            self._temp_animation_timer -= dt
            if self._temp_animation_timer <= 0:
                self._temp_animation_timer = 0.0
                self._sync_animation()

        self._elapsed += dt

        while self._elapsed >= settings.ATTRIBUTE_DECAY_INTERVAL:
            self._elapsed -= settings.ATTRIBUTE_DECAY_INTERVAL
            self._tick()

        # 危急状态（饥饿/体力归零）：持续强制显示状态动画，
        # 避免被暂停前残留的漫游动画（walk/run）盖住，给出明确反馈。
        if self.is_critical and self._temp_animation_timer <= 0:
            self._sync_animation()

    def _update_sleep(self, dt: float) -> None:
        """睡眠模式逐帧更新：保持 sleep 动画，按 tick 缓慢恢复体力。

        体力恢复到上限后自动醒来。睡眠期间饥饿仍缓慢下降。
        """
        self.pet.change_animation("sleep")

        self._elapsed += dt
        while self._elapsed >= settings.ATTRIBUTE_DECAY_INTERVAL:
            self._elapsed -= settings.ATTRIBUTE_DECAY_INTERVAL
            self.pet.increase_energy(settings.SLEEP_ENERGY_RECOVER_PER_TICK)
            self.pet.decrease_hunger(settings.HUNGER_DECAY_PER_TICK)

        if self.pet.energy >= settings.ATTRIBUTE_MAX:
            self.stop_sleep()

    def trigger_temporary_animation(self, animation: str, duration: float) -> None:
        """播放一段交互行为触发的临时动画（如 happy / eating / playing）。

        animation: 对应 AnimationState 的字符串值。
        duration: 播放时长（秒），结束后自动恢复为状态对应动画。
        """
        self.pet.change_animation(animation)
        self._temp_animation_timer = duration

    def sync_to_state_animation(self) -> None:
        """立即恢复为 pet.current_state 对应的动画，并清除临时动画计时。

        供持续时长不固定的行为（如自主漫游 walk/run）使用：
        行为开始时直接调用 pet.change_animation() 切换动画，
        行为结束时调用本方法立即恢复为状态对应动画。
        """
        self._temp_animation_timer = 0.0
        self._sync_animation()

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
            # 临时动画播放期间，状态切换不打断当前的交互反馈动画，
            # 待临时动画结束后会自动按最新状态同步。
            if self._temp_animation_timer <= 0:
                self._sync_animation()

    def _sync_animation(self) -> None:
        """将动画切换为 pet.current_state 对应的动画。"""
        self.pet.change_animation(STATE_ANIMATION_MAP[self.pet.current_state])
