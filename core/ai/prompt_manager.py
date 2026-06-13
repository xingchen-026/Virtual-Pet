"""Prompt 管理模块。

PromptManager 集中管理与拼接发送给 LLM 的所有 Prompt 内容，
AI 模块与游戏核心逻辑之间的提示词均经由本模块统一生成，
不在其他模块中硬编码 Prompt 文本。

最终拼接结构::

    System Prompt
        +
    Pet State
        +
    Memory
        +
    User Message

* System Prompt：人格设定（名称 + 人格参数）+ 回复风格要求
* Pet State：宠物当前心情 / 饥饿 / 体力 / 状态
* Memory：MemoryManager 提供的短期对话与长期事件摘要
* User Message：用户本轮输入
"""

from __future__ import annotations

from typing import Dict, List

from core.ai.memory import MemoryManager
from core.ai.personality import PersonalityManager

# 系统提示词模板：{name}/{personality}/{tone} 由 PersonalityManager 填充。
# {tone} 为用户在设置界面自定义的性格语气（可空）。
_SYSTEM_PROMPT_TEMPLATE = (
    "你是一只名叫 {name} 的桌面虚拟宠物，像真实宠物一样陪伴主人，用第一人称说话。\n"
    "{personality}"
    "{tone}"
    "回复要求：\n"
    "1. 像可爱的小宠物一样说话，有情绪、有温度，可带简单的拟声或动作（如「喵~」「(蹭蹭)」「(歪头)」）。\n"
    "2. 简短自然，一般不超过 60 字，避免长篇大论与说教。\n"
    "3. 记得主人之前说过的话和互动，体现出熟悉感。\n"
    "4. 内容必须健康友善：绝不使用脏话、色情低俗、暴力血腥或政治敏感等不当内容；"
    "遇到这类话题时，以宠物的口吻温柔地岔开，引导到轻松愉快的方向。\n"
    "情绪标签：如果这句话让你的心情明显变化，可在回复最前面加上形如"
    "「[情绪:开心]」「[情绪:生气]」「[情绪:疲惫]」的标签（不会展示给主人，仅供内部判断）；"
    "没有明显情绪变化则不加标签。"
)

# 宠物当前状态模板
_PET_STATE_TEMPLATE = (
    "当前宠物状态：心情 {mood:.0f}/100，饥饿 {hunger:.0f}/100，"
    "体力 {energy:.0f}/100，行为状态 {state}。"
)


class PromptManager:
    """拼接系统提示词、宠物状态、记忆摘要与用户输入，生成完整对话消息。"""

    def __init__(self, personality: PersonalityManager, memory: MemoryManager) -> None:
        self.personality = personality
        self.memory = memory

    def system_prompt(self) -> str:
        """生成系统提示词：宠物名称 + 人格描述 + 自定义语气 + 回复风格要求。"""
        describe = self.personality.describe()
        personality_line = f"{describe}\n" if describe else ""

        tone = (self.personality.tone or "").strip()
        tone_line = f"你的性格与说话风格：{tone}\n" if tone else ""

        return _SYSTEM_PROMPT_TEMPLATE.format(
            name=self.personality.name,
            personality=personality_line,
            tone=tone_line,
        )

    def pet_state_prompt(self, pet) -> str:
        """根据宠物当前属性生成状态描述文本。"""
        return _PET_STATE_TEMPLATE.format(
            mood=pet.mood,
            hunger=pet.hunger,
            energy=pet.energy,
            state=pet.current_state.name,
        )

    def build_messages(self, pet, user_message: str) -> List[Dict[str, str]]:
        """拼接 System Prompt + Pet State + Memory + User Message，生成消息列表。"""
        context = "\n".join([
            self.pet_state_prompt(pet),
            "历史记忆：",
            self.memory.describe(),
        ])

        return [
            {"role": "system", "content": self.system_prompt()},
            {"role": "system", "content": context},
            {"role": "user", "content": user_message},
        ]
