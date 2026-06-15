"""AI 服务层模块（对外统一入口）。

AIService 是 AI 模块与游戏核心逻辑之间的唯一接口：

    Pet -> AIService -> LLM

职责：

* 调用 PromptManager 拼接完整 Prompt（System Prompt + Pet State +
  Memory + User Message）
* 调用 LLMClient 获取回复
* 调用 EmotionAnalyzer 分析对话对宠物情绪/体力的影响，
  并在需要时通过 PetBehavior 触发对应的临时动画
  （例如"你累了吗？" -> energy -5，animation=sleep）
* 调用 MemoryManager 记录短期对话与长期重要事件
* 统一处理 LLM 调用异常（API失败/网络异常/模型不可用/返回格式
  错误），AI 不可用时返回离线回复，桌宠核心功能不受影响

core.pet.Pet 不直接依赖 LLMClient，所有 AI 能力均通过 AIService
暴露；游戏主循环（core.game.Game）只与 AIService 交互。
"""

from __future__ import annotations

import datetime
import random
from typing import Optional

from config import settings
from core.ai.emotion_analyzer import EmotionAnalyzer, EmotionEffect
from core.ai.llm_client import LLMClient
from core.ai.memory import MemoryManager
from core.ai.moderation import load_moderator
from core.ai.personality import PersonalityManager
from core.ai.prompt_manager import PromptManager
from core.behavior import PetBehavior
from utils.exception import AIServiceError, log_exception

# LLM 不可用时返回给用户的离线提示
_OFFLINE_REPLY = "（暂时联系不到我的大脑，不过我还在这里陪着你哦~）"

# 首次喂食事件的记忆文案
_FIRST_FEED_EVENT = "用户第一次喂食"

# 每累计多少轮对话，用 LLM 总结一次主人习惯并写入长期记忆
_SUMMARY_EVERY = 3


def _time_of_day_hint(hour: Optional[int] = None) -> str:
    """把当前小时映射为时段提示词，供主动发言的 Prompt 使用。"""
    h = datetime.datetime.now().hour if hour is None else hour
    if 5 <= h < 11:
        return "早上"
    if 11 <= h < 13:
        return "中午"
    if 13 <= h < 18:
        return "下午"
    if 18 <= h < 23:
        return "晚上"
    return "深夜"


def _offline_proactive_line(pet) -> str:
    """AI 不可用时，按宠物当前动画状态随机选一句主动发言（离线降级）。"""
    pool = settings.PROACTIVE_OFFLINE_MESSAGES
    options = pool.get(pet.current_animation) or pool["default"]
    return random.choice(options)


class AIService:
    """AI 能力统一入口：对话、人格、记忆、情绪与行为联动。"""

    def __init__(
        self,
        ai_config: dict,
        personality: PersonalityManager,
        memory: MemoryManager,
        behavior: Optional[PetBehavior] = None,
    ) -> None:
        self.llm_client = LLMClient(ai_config)
        self.personality = personality
        self.memory = memory
        self.behavior = behavior
        self.prompt_manager = PromptManager(personality, memory)
        self.emotion_analyzer = EmotionAnalyzer()

        # 内容审查：过滤违规的用户输入与 AI 回复（系统提示词约束之外的第二道防线）
        self.moderator = load_moderator()

        # 习惯总结缓冲：累计若干轮后用 LLM 总结成长期记忆（不持久化，仅运行时计数）
        self._summary_buffer: list = []

        # AI 服务当前是否可用（最近一次 LLM 调用是否成功）
        self.available = True

    def apply_config(self, ai_config: dict) -> None:
        """应用新的 LLM 配置（设置窗口保存后调用），并重置可用状态。"""
        self.llm_client = LLMClient(ai_config)
        self.available = True

    @staticmethod
    def test_connection(ai_config: dict) -> tuple:
        """用给定配置发送一次测试请求，返回 (是否成功, 结果描述)。

        供设置窗口的"测试"按钮验证 API Key / 模型名是否有效，
        会产生一次真实的 LLM 调用，应在后台线程中执行。
        """
        client = LLMClient(ai_config)
        try:
            reply = client.chat([{"role": "user", "content": "你好"}])
            return True, f"连接成功：{reply[:24]}"
        except AIServiceError as exc:
            # 完整错误写入 logs/error.log，状态行显示精简版本
            log_exception(exc)
            brief = str(exc).replace("LLM 请求失败: ", "")
            return False, f"连接失败：{brief}"

    def chat(self, pet, user_message: str) -> str:
        """处理一轮用户对话：审查 -> 获取回复 -> 审查 -> 情绪/行为联动 -> 记忆。

        AI 不可用（API失败/网络异常/模型不可用/返回格式错误）时返回
        离线回复，并仍然基于规则记录情绪联动，保证核心体验连续。
        本方法会阻塞至 LLM 调用返回或失败，调用方（UI 层）应在
        独立线程中调用，避免阻塞主循环。
        """
        # 第一道审查：违规用户输入不送入 LLM，也不写入记忆，直接温和岔开
        if not self.moderator.is_safe(user_message):
            return self.moderator.fallback_reply

        messages = self.prompt_manager.build_messages(pet, user_message)

        try:
            raw_reply = self.llm_client.chat(messages)
            self.available = True
        except AIServiceError as exc:
            log_exception(exc)
            self.available = False
            raw_reply = _OFFLINE_REPLY

        # 第二道审查：违规 AI 回复替换为岔开回复，不展示原文、不联动情绪
        if not self.moderator.is_safe(raw_reply):
            reply = self.moderator.fallback_reply
            self.memory.add_dialogue(user_message, reply)
            return reply

        effect = self.emotion_analyzer.from_tag(raw_reply)
        if effect.is_empty:
            effect = self.emotion_analyzer.analyze(user_message)

        reply = self.emotion_analyzer.strip_tag(raw_reply)
        self._apply_effect(pet, effect)

        self.memory.add_dialogue(user_message, reply)

        # 累计若干轮后总结主人习惯，写入长期记忆（仅 LLM 可用时尝试，最佳努力）
        if self.available:
            self._summary_buffer.append({"user": user_message, "pet": reply})
            if len(self._summary_buffer) >= _SUMMARY_EVERY:
                self._update_long_term_summary()

        return reply

    def proactive_message(self, pet) -> str:
        """生成一句宠物「主动说」的话（供 UI 在头顶气泡显示），不针对用户输入。

        结合宠物状态/记忆/时段请求 LLM；AI 不可用时按当前状态返回离线随机文案，
        保证离线也能主动互动。会阻塞至 LLM 返回或失败，调用方应在后台线程调用。
        不写入对话记忆（非用户对话），避免污染短期/长期记忆。
        """
        messages = self.prompt_manager.proactive_messages(pet, _time_of_day_hint())

        try:
            raw = self.llm_client.chat(messages)
            self.available = True
        except AIServiceError as exc:
            log_exception(exc)
            self.available = False
            return _offline_proactive_line(pet)

        reply = self.emotion_analyzer.strip_tag(raw).strip()
        # 违规或空回复一律降级为离线文案，绝不展示原文
        if not reply or not self.moderator.is_safe(reply):
            return _offline_proactive_line(pet)
        return reply

    def _update_long_term_summary(self) -> None:
        """用 LLM 把最近几轮对话总结为一条主人习惯摘要，写入长期记忆。

        最佳努力：失败/违规则跳过；无论成败都清空缓冲，避免反复触发失败调用。
        """
        dialogues = self._summary_buffer
        self._summary_buffer = []
        try:
            summary = self.llm_client.chat(self.prompt_manager.summary_messages(dialogues))
        except AIServiceError as exc:
            log_exception(exc)
            return
        summary = self.emotion_analyzer.strip_tag(summary)
        if summary and self.moderator.is_safe(summary):
            self.memory.add_summary(summary)

    def notify_interaction(self, pet, action_name: str) -> None:
        """记录用户交互产生的长期重要事件（如首次喂食）。

        action_name: core.event.InteractionEventType 的字符串值
        （如 "feed"），由 Game 在分发交互事件时调用。
        """
        if action_name != "feed":
            return

        already_recorded = any(
            item.get("event") == _FIRST_FEED_EVENT for item in self.memory.long_term
        )
        if already_recorded:
            return

        emotion = "happy" if pet.mood >= settings.ATTRIBUTE_MAX / 2 else "neutral"
        self.memory.add_event(_FIRST_FEED_EVENT, emotion)

    def _apply_effect(self, pet, effect: EmotionEffect) -> None:
        """将情绪分析结果应用到宠物属性，并在需要时触发对应动画。"""
        if effect.mood_delta > 0:
            pet.increase_mood(effect.mood_delta)
        elif effect.mood_delta < 0:
            pet.decrease_mood(-effect.mood_delta)

        if effect.energy_delta > 0:
            pet.increase_energy(effect.energy_delta)
        elif effect.energy_delta < 0:
            pet.decrease_energy(-effect.energy_delta)

        if effect.suggested_animation and self.behavior is not None:
            self.behavior.trigger_temporary_animation(
                effect.suggested_animation, settings.AI_EFFECT_ANIMATION_DURATION
            )
