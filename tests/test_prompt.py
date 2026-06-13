"""PromptManager 系统提示词（含自定义语气与审查约束）的回归测试。"""

import os
import tempfile

from core.ai.memory import MemoryManager
from core.ai.personality import PersonalityManager
from core.ai.prompt_manager import PromptManager


def _prompt_manager(character="", tone=""):
    personality = PersonalityManager.__new__(PersonalityManager)
    personality.name = "旺财"
    personality.traits = {"kindness": 80}
    personality.character = character
    personality.tone = tone
    memory = MemoryManager(os.path.join(tempfile.gettempdir(), "_pm_test_mem.json"))
    return PromptManager(personality, memory)


def test_system_prompt_includes_name():
    text = _prompt_manager().system_prompt()
    assert "旺财" in text


def test_system_prompt_includes_moderation_rule():
    text = _prompt_manager().system_prompt()
    # 提示词应包含健康友善/不当内容约束
    assert "脏话" in text or "不当内容" in text


def test_custom_character_injected_when_present():
    text = _prompt_manager(character="高冷傲娇").system_prompt()
    assert "你的性格：高冷傲娇" in text


def test_custom_tone_injected_when_present():
    text = _prompt_manager(tone="说话奶声奶气").system_prompt()
    assert "你的说话语气：说话奶声奶气" in text


def test_no_character_tone_lines_when_empty():
    text = _prompt_manager().system_prompt()
    assert "你的性格：" not in text
    assert "你的说话语气：" not in text


def test_personality_character_and_tone_persisted(tmp_path):
    path = str(tmp_path / "personality.json")
    pm = PersonalityManager(path)
    pm.name = "球球"
    pm.character = "高冷傲娇"
    pm.tone = "活泼爱撒娇"
    pm.save()

    reloaded = PersonalityManager(path)
    assert reloaded.name == "球球"
    assert reloaded.character == "高冷傲娇"
    assert reloaded.tone == "活泼爱撒娇"
