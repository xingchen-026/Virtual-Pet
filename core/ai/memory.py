"""宠物记忆系统模块。

MemoryManager 维护两类记忆，均持久化到 data/memory.json：

* 短期记忆（short_term）：最近 SHORT_TERM_LIMIT 轮对话（user/pet 文本对），
  提供给 Prompt 作为最近上下文。
* 长期记忆（long_term）：用户习惯/偏好的摘要（由 AIService 定期用 LLM 从
  对话中总结），以及少量重要事件（如第一次喂食），让 AI 长期"记住"主人。

数据结构::

    {
        "short_term": [{"user": "...", "pet": "..."}],
        "long_term": [
            {"summary": "主人喜欢晚上聊天", "time": "..."},
            {"event": "用户第一次喂食", "time": "...", "emotion": "happy"}
        ]
    }
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Dict, List, Optional

from config import settings
from utils.helper import load_json, save_json

# 短期记忆保留的对话轮数（仅保存最近三轮）
SHORT_TERM_LIMIT = 3

# 长期记忆最多保留的条数（习惯摘要 + 重要事件，超限丢弃最旧的）
LONG_TERM_LIMIT = 100

# 遗忘策略：长期记忆中超过该天数的条目会被淡忘（模拟"久远的事会忘"），
# 但始终保护最新 MEMORY_MIN_KEEP 条，避免长期未互动后记忆被清空。
MEMORY_FORGET_DAYS = 30
MEMORY_MIN_KEEP = 10

# 拼接进 Prompt 时取最近的长期记忆条数
_PROMPT_LONG_TERM_LIMIT = 8


def _age_days(time_str: Optional[str], now: datetime) -> Optional[int]:
    """长期记忆条目的天数年龄；时间缺失/无法解析时返回 None（视为不可淡忘）。"""
    if not time_str:
        return None
    try:
        recorded = datetime.strptime(time_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
    return (now.date() - recorded.date()).days


class MemoryManager:
    """管理宠物的短期对话记忆与长期习惯/事件记忆。"""

    def __init__(self, file_path: Optional[str] = None) -> None:
        self._file_path = file_path or settings.MEMORY_FILE

        # 对话记录在聊天工作线程写入，交互事件在主循环写入，
        # 用锁保护数据修改与文件写入，避免并发写坏 memory.json
        self._lock = threading.Lock()

        data = load_json(self._file_path) or {}
        self.short_term: List[Dict[str, str]] = list(data.get("short_term", []))
        self.long_term: List[Dict[str, str]] = list(data.get("long_term", []))
        # 启动即淡忘过于久远的长期记忆（长期未互动后重启会自动清理陈旧记忆）
        self._prune_long_term_locked()

    def add_dialogue(self, user_message: str, pet_reply: str) -> None:
        """记录一轮对话，仅保留最近 SHORT_TERM_LIMIT 轮。"""
        with self._lock:
            self.short_term.append({"user": user_message, "pet": pet_reply})
            if len(self.short_term) > SHORT_TERM_LIMIT:
                self.short_term = self.short_term[-SHORT_TERM_LIMIT:]
            self._save_locked()

    def add_summary(self, summary: str) -> None:
        """记录一条长期习惯/偏好摘要（带日期），超限丢弃最旧的。"""
        summary = (summary or "").strip()
        if not summary:
            return
        with self._lock:
            self.long_term.append({
                "summary": summary,
                "time": datetime.now().strftime("%Y-%m-%d"),
            })
            self._prune_long_term_locked()
            self._trim_long_term_locked()
            self._save_locked()

    def add_event(self, event: str, emotion: str = "") -> None:
        """记录一条长期重要事件（带日期与情绪），超限丢弃最旧的。"""
        with self._lock:
            self.long_term.append({
                "event": event,
                "time": datetime.now().strftime("%Y-%m-%d"),
                "emotion": emotion,
            })
            self._prune_long_term_locked()
            self._trim_long_term_locked()
            self._save_locked()

    def recent_dialogues(self, limit: int = SHORT_TERM_LIMIT) -> List[Dict[str, str]]:
        """返回最近 limit 轮对话（按时间正序）。"""
        return self.short_term[-limit:]

    def describe(self) -> str:
        """生成一段用于拼接进 Prompt 的记忆摘要文字。"""
        lines: List[str] = []

        for item in self.long_term[-_PROMPT_LONG_TERM_LIMIT:]:
            if "summary" in item:
                lines.append(f"[长期记忆] {item['summary']}")
            elif "event" in item:
                emotion = item.get("emotion", "")
                suffix = f"（情绪：{emotion}）" if emotion else ""
                lines.append(f"[重要事件] {item.get('time', '')} {item['event']}{suffix}")

        for item in self.recent_dialogues():
            lines.append(f"主人说：{item['user']} / 你回复：{item['pet']}")

        if not lines:
            return "（暂无历史记忆）"
        return "\n".join(lines)

    def save(self) -> None:
        """将当前记忆数据写回 data/memory.json（线程安全）。"""
        with self._lock:
            self._save_locked()

    def _trim_long_term_locked(self) -> None:
        if len(self.long_term) > LONG_TERM_LIMIT:
            self.long_term = self.long_term[-LONG_TERM_LIMIT:]

    def _prune_long_term_locked(self, now: Optional[datetime] = None) -> None:
        """遗忘策略：淡忘超过 MEMORY_FORGET_DAYS 天的长期记忆。

        始终保护最新 MEMORY_MIN_KEEP 条（不论年龄）；其余条目按记录日期淘汰，
        时间缺失/无法解析的条目保留（无法判断年龄就不淡忘）。调用方须持有锁。
        """
        now = now or datetime.now()
        if len(self.long_term) <= MEMORY_MIN_KEEP:
            return

        protected = self.long_term[-MEMORY_MIN_KEEP:]
        older = self.long_term[:-MEMORY_MIN_KEEP]
        kept = [
            item for item in older
            if (_age_days(item.get("time"), now) or 0) <= MEMORY_FORGET_DAYS
        ]
        self.long_term = kept + protected

    def _save_locked(self) -> None:
        """实际执行文件写入，调用方必须已持有 self._lock。"""
        save_json(self._file_path, {"short_term": self.short_term, "long_term": self.long_term})
