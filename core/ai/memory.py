"""宠物记忆系统模块。

MemoryManager 负责维护两类记忆，均持久化到 data/memory.json：

* 短期记忆（short_term）：最近若干轮对话（user/pet 文本对），
  用于拼接进 Prompt，让 AI 了解最近的对话上下文。
* 长期记忆（long_term）：重要事件记录（事件描述 + 时间 + 情绪），
  用于让 AI "记住"用户的关键互动（如第一次喂食），
  并据此调整长期反馈。

数据结构::

    {
        "short_term": [{"user": "...", "pet": "..."}],
        "long_term": [{"event": "...", "time": "...", "emotion": "..."}]
    }
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from config import settings
from utils.helper import load_json, save_json

# 短期记忆最多保留的对话轮数
SHORT_TERM_LIMIT = 10

# 拼接进 Prompt 时取最近的对话轮数 / 长期事件条数
_PROMPT_DIALOGUE_LIMIT = 5
_PROMPT_EVENT_LIMIT = 5


class MemoryManager:
    """管理宠物的短期对话记忆与长期事件记忆。"""

    def __init__(self, file_path: Optional[str] = None) -> None:
        self._file_path = file_path or settings.MEMORY_FILE

        data = load_json(self._file_path) or {}
        self.short_term: List[Dict[str, str]] = list(data.get("short_term", []))
        self.long_term: List[Dict[str, str]] = list(data.get("long_term", []))

    def add_dialogue(self, user_message: str, pet_reply: str) -> None:
        """记录一轮对话，超过 SHORT_TERM_LIMIT 时丢弃最旧的记录。"""
        self.short_term.append({"user": user_message, "pet": pet_reply})
        if len(self.short_term) > SHORT_TERM_LIMIT:
            self.short_term = self.short_term[-SHORT_TERM_LIMIT:]
        self.save()

    def add_event(self, event: str, emotion: str = "") -> None:
        """记录一条长期重要事件（带日期与情绪标签）。"""
        self.long_term.append({
            "event": event,
            "time": datetime.now().strftime("%Y-%m-%d"),
            "emotion": emotion,
        })
        self.save()

    def recent_dialogues(self, limit: int = SHORT_TERM_LIMIT) -> List[Dict[str, str]]:
        """返回最近 limit 轮对话（按时间正序）。"""
        return self.short_term[-limit:]

    def recent_events(self, limit: int = _PROMPT_EVENT_LIMIT) -> List[Dict[str, str]]:
        """返回最近 limit 条长期事件（按时间正序）。"""
        return self.long_term[-limit:]

    def describe(self) -> str:
        """生成一段用于拼接进 Prompt 的记忆摘要文字。"""
        lines: List[str] = []

        for item in self.recent_dialogues(_PROMPT_DIALOGUE_LIMIT):
            lines.append(f"主人说：{item['user']} / 你回复：{item['pet']}")

        for item in self.recent_events(_PROMPT_EVENT_LIMIT):
            lines.append(f"[历史事件] {item['time']} {item['event']}（情绪：{item['emotion']}）")

        if not lines:
            return "（暂无历史记忆）"

        return "\n".join(lines)

    def save(self) -> None:
        """将当前记忆数据写回 data/memory.json。"""
        save_json(self._file_path, {"short_term": self.short_term, "long_term": self.long_term})
