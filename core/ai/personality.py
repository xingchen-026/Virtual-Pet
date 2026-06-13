"""宠物人格系统模块。

PersonalityManager 从 data/personality.json 读取宠物名称与人格参数
（kindness / humor / curiosity 等，取值范围 0-100），供
PromptManager 拼接系统提示词，让 AI 回复体现出固定的人格倾向
（例如高幽默时更活泼、高冷时更简短）。

人格参数完全配置化，新增/调整人格维度无需修改代码。
"""

from __future__ import annotations

from typing import Dict, Optional

from config import settings
from utils.helper import load_json, save_json

# 配置文件缺失或损坏时使用的默认人格
_DEFAULT_PERSONALITY: Dict = {
    "name": "Mimi",
    "personality": {
        "kindness": 80,
        "humor": 70,
        "curiosity": 90,
    },
    # 用户在设置界面自定义的性格与语气（两个独立的自由文本，可空）
    "character": "",
    "tone": "",
}


class PersonalityManager:
    """管理宠物人格配置（名称 + 各维度数值）。"""

    def __init__(self, file_path: Optional[str] = None) -> None:
        self._file_path = file_path or settings.PERSONALITY_FILE

        data = load_json(self._file_path) or _DEFAULT_PERSONALITY
        self.name: str = data.get("name", _DEFAULT_PERSONALITY["name"])
        self.traits: Dict[str, float] = dict(
            data.get("personality", _DEFAULT_PERSONALITY["personality"])
        )
        # 用户自定义的性格与语气（两个独立字段，设置界面可微调，注入系统提示词）
        self.character: str = data.get("character", "")
        self.tone: str = data.get("tone", "")

    def trait(self, key: str, default: float = 50.0) -> float:
        """读取某个人格维度的数值（0-100），不存在时返回 default。"""
        return self.traits.get(key, default)

    def dominant_trait(self) -> str:
        """返回数值最高的人格维度名称，用于描述宠物的主要性格倾向。"""
        if not self.traits:
            return ""
        return max(self.traits, key=self.traits.get)

    def describe(self) -> str:
        """生成一段用于拼接进系统 Prompt 的人格描述文字。"""
        if not self.traits:
            return ""

        parts = [f"{key}={value}" for key, value in self.traits.items()]
        return f"你的人格参数（0-100）：{', '.join(parts)}；主要性格倾向：{self.dominant_trait()}。"

    def save(self) -> None:
        """将当前人格配置写回 data/personality.json。"""
        save_json(
            self._file_path,
            {
                "name": self.name,
                "personality": self.traits,
                "character": self.character,
                "tone": self.tone,
            },
        )
