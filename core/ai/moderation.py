"""内容审查模块。

ContentModerator 对用户输入与 AI 回复做敏感词过滤，确保桌宠对话中
不出现脏话、色情、暴力血腥、政治敏感等违规内容：

* 命中违规词的用户输入：不调用 LLM，直接返回温和的岔开回复。
* 命中违规词的 AI 回复：替换为同样的岔开回复，不展示原文。

违规词表来自 config/moderation.json（数据而非代码，便于增删与本地化），
作为系统提示词约束之外的第二道防线。中文按子串匹配；英文按单词边界
匹配以避免「assistant 含 ass」之类误伤。
"""

from __future__ import annotations

import re
from typing import List

from config import settings
from utils.helper import load_json

# 配置缺失时的兜底违规词与回复（保证审查始终生效）
_DEFAULT_FALLBACK = "（这个话题我们换一个聊好不好呀~）"
_DEFAULT_BANNED: List[str] = ["fuck", "shit", "色情", "暴力", "杀人"]


class ContentModerator:
    """基于敏感词表的内容审查器。"""

    def __init__(self, config: dict) -> None:
        config = config or {}
        self.fallback_reply: str = config.get("fallback_reply", _DEFAULT_FALLBACK)

        words = config.get("banned_words") or _DEFAULT_BANNED
        # 含非 ASCII（中文等）按子串匹配；纯 ASCII（英文）按单词边界匹配
        self._substring_words = [w.lower() for w in words if not w.isascii()]
        ascii_words = [w.lower() for w in words if w.isascii() and w.strip()]
        if ascii_words:
            pattern = r"\b(?:" + "|".join(re.escape(w) for w in ascii_words) + r")\b"
            self._ascii_re = re.compile(pattern, re.IGNORECASE)
        else:
            self._ascii_re = None

    def is_safe(self, text: str) -> bool:
        """文本是否不含违规词（空文本视为安全）。"""
        if not text:
            return True

        lowered = text.lower()
        if any(word in lowered for word in self._substring_words):
            return False
        if self._ascii_re is not None and self._ascii_re.search(lowered):
            return False
        return True


def load_moderator() -> ContentModerator:
    """从 config/moderation.json 加载并构建内容审查器。"""
    return ContentModerator(load_json(settings.MODERATION_CONFIG_FILE) or {})
