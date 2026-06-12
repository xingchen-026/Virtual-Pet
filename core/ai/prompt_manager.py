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

# 系统提示词模板：{name} 与 {personality} 由 PersonalityManager 填充
_SYSTEM_PROMPT_TEMPLATE = (
    "你是一只桌面虚拟宠物，你的名字是 {name}。\n"
    "{personality}\n"
    "你需要表现出：\n"
    "1. 可爱\n"
    "2. 有情绪\n"
    "3. 会记住主人行为\n"
    "回复不要超过100字。\n"
    "如果你判断这句话会让你的心情变化，可以在回复最前面加上"
    "形如「[情绪:开心]」「[情绪:生气]」「[情绪:疲惫]」的标签，"
    "标签不会展示给主人，仅用于内部判断；如果没有明显情绪变化则不加标签。"
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
        """生成系统提示词：宠物名称 + 人格描述 + 回复风格要求。"""
        return _SYSTEM_PROMPT_TEMPLATE.format(
            name=self.personality.name,
            personality=self.personality.describe(),
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
