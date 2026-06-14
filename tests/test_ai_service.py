"""AIService 对话管线的回归测试。

用 FakeLLM 替身避免真实 LLM 调用；MemoryManager / PersonalityManager
传入 tmp 路径，避免污染 data/ 下的真实记忆与人格文件。
"""

import pytest

from core.ai.ai_service import _FIRST_FEED_EVENT, _OFFLINE_REPLY, AIService
from core.ai.emotion_analyzer import EmotionEffect
from core.ai.memory import MemoryManager
from core.ai.moderation import ContentModerator
from core.ai.personality import PersonalityManager
from core.behavior import PetBehavior
from core.pet import Pet
from utils.exception import AIServiceError

_BANNED = "脏话"
_FALLBACK = "换个话题吧~"


class FakeLLM:
    """LLMClient 替身：返回固定回复或按需抛出 AIServiceError。"""

    def __init__(self, reply="好呀", fail=False):
        self.reply = reply
        self.fail = fail
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        if self.fail:
            raise AIServiceError("boom")
        return self.reply


def _service(tmp_path, reply="好呀", fail=False):
    pet = Pet()
    behavior = PetBehavior(pet)
    memory = MemoryManager(file_path=str(tmp_path / "memory.json"))
    personality = PersonalityManager(file_path=str(tmp_path / "personality.json"))
    service = AIService({}, personality, memory, behavior)
    service.llm_client = FakeLLM(reply=reply, fail=fail)
    service.moderator = ContentModerator(
        {"banned_words": [_BANNED], "fallback_reply": _FALLBACK}
    )
    return service, pet, memory


def test_chat_returns_reply_and_records_memory(tmp_path):
    service, pet, memory = _service(tmp_path, reply="你好呀")
    reply = service.chat(pet, "在吗")
    assert reply == "你好呀"
    assert len(memory.short_term) == 1
    assert service.llm_client.calls  # 确实调用了 LLM


def test_unsafe_user_input_blocked(tmp_path):
    service, pet, memory = _service(tmp_path)
    reply = service.chat(pet, f"你这个{_BANNED}")
    assert reply == _FALLBACK
    assert service.llm_client.calls == []  # 不送入 LLM
    assert memory.short_term == []  # 不写入记忆


def test_unsafe_ai_reply_replaced(tmp_path):
    # LLM 返回违规内容：替换为兜底回复、仍记录对话、不联动情绪
    service, pet, memory = _service(tmp_path, reply=f"哼{_BANNED}")
    before_mood = pet.mood
    reply = service.chat(pet, "讲个笑话")
    assert reply == _FALLBACK
    assert len(memory.short_term) == 1
    assert pet.mood == before_mood  # 未应用情绪效果


def test_llm_failure_returns_offline_and_marks_unavailable(tmp_path):
    service, pet, memory = _service(tmp_path, fail=True)
    reply = service.chat(pet, "在吗")
    assert reply == _OFFLINE_REPLY
    assert service.available is False
    assert len(memory.short_term) == 1  # 离线时仍记录对话


def test_summary_triggered_after_three_rounds(tmp_path):
    # 连续三轮成功对话后触发长期记忆总结，写入一条 long_term
    service, pet, memory = _service(tmp_path, reply="嗯嗯")
    for _ in range(3):
        service.chat(pet, "今天聊聊天")
    assert len(memory.long_term) == 1
    assert "summary" in memory.long_term[0]


def test_notify_interaction_records_first_feed_once(tmp_path):
    service, pet, memory = _service(tmp_path)
    service.notify_interaction(pet, "feed")
    service.notify_interaction(pet, "feed")  # 第二次不应重复记录
    feeds = [i for i in memory.long_term if i.get("event") == _FIRST_FEED_EVENT]
    assert len(feeds) == 1


def test_notify_interaction_ignores_non_feed(tmp_path):
    service, pet, memory = _service(tmp_path)
    service.notify_interaction(pet, "play")
    assert memory.long_term == []


def test_apply_config_resets_availability(tmp_path):
    service, pet, memory = _service(tmp_path)
    service.available = False
    service.apply_config({})
    assert service.available is True


def test_apply_effect_changes_attributes_and_animation(tmp_path):
    service, pet, memory = _service(tmp_path)
    pet.set_mood(50)
    pet.set_energy(50)
    effect = EmotionEffect(mood_delta=10, energy_delta=-5, suggested_animation="happy")
    service._apply_effect(pet, effect)
    assert pet.mood == 60
    assert pet.energy == 45
    assert pet.current_animation == "happy"


def test_test_connection_success(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.ai.ai_service.LLMClient", lambda cfg: FakeLLM(reply="你好主人")
    )
    ok, message = AIService.test_connection({})
    assert ok is True
    assert "连接成功" in message


def test_test_connection_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.ai.ai_service.LLMClient", lambda cfg: FakeLLM(fail=True)
    )
    ok, message = AIService.test_connection({})
    assert ok is False
    assert "连接失败" in message
