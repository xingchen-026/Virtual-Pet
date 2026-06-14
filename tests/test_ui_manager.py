"""UIManager 纯逻辑部分的回归测试。

构造时传 font=None 并用替身充当协作对象，仅覆盖不涉及渲染/pygame 视频
子系统的逻辑：属性变化提示、聊天历史上限、面板按钮分发、休息提醒计时、
活跃态判断。CHAT_HISTORY_FILE 改指 tmp，避免读写真实聊天历史。
"""

import pytest

from config import settings
from core.event import InteractionEventType
from core.pet import Pet
from ui.ui_manager import UIManager

WINDOW_SIZE = (800, 600)


class FakePersonality:
    name = "小白"
    character = "活泼"
    tone = "可爱"


class FakeAIService:
    def __init__(self):
        self.personality = FakePersonality()


class FakeDesktop:
    def focus(self):
        pass


class FakeSprite:
    scale = 1.0
    rect = None


def _make_ui(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "CHAT_HISTORY_FILE", str(tmp_path / "chat.json"))
    pet = Pet()
    interactions = []
    ui = UIManager(
        None,
        pet,
        FakeSprite(),
        None,  # autonomous_manager（被测方法不引用）
        FakeAIService(),
        FakeDesktop(),
        {},  # ai_config
        WINDOW_SIZE,
        on_interaction=lambda event: interactions.append(event),
        on_user_prefs_changed=lambda: None,
    )
    return ui, pet, interactions


def test_attr_delta_suffix_and_expiry(monkeypatch, tmp_path):
    ui, pet, _ = _make_ui(monkeypatch, tmp_path)
    pet.set_mood(50)
    before = (pet.hunger, pet.mood, pet.energy)
    pet.set_mood(70)
    ui.record_attr_deltas(before)
    assert ui._attr_delta_suffix("mood") == "  +20"
    assert ui._attr_delta_suffix("hunger") == ""  # 无变化无后缀

    ui._update_attr_deltas(settings.ATTR_DELTA_DURATION + 0.1)
    assert ui._attr_delta_suffix("mood") == ""  # 超时后移除


def test_chat_history_capped(monkeypatch, tmp_path):
    ui, _, _ = _make_ui(monkeypatch, tmp_path)
    for i in range(settings.CHAT_HISTORY_LIMIT + 10):
        ui._record_chat("user", f"msg-{i}")
    assert len(ui._chat_history) == settings.CHAT_HISTORY_LIMIT
    # 保留最新的，丢弃最旧的
    assert ui._chat_history[-1]["text"] == f"msg-{settings.CHAT_HISTORY_LIMIT + 9}"


def test_panel_action_routes_growth_interaction(monkeypatch, tmp_path):
    ui, _, interactions = _make_ui(monkeypatch, tmp_path)
    ui._handle_panel_action("feed")
    assert len(interactions) == 1
    assert interactions[0].type == InteractionEventType.FEED


def test_panel_action_ignores_unknown(monkeypatch, tmp_path):
    ui, _, interactions = _make_ui(monkeypatch, tmp_path)
    ui._handle_panel_action("nonexistent")
    assert interactions == []


def test_rest_reminder_shows_bubble(monkeypatch, tmp_path):
    ui, _, _ = _make_ui(monkeypatch, tmp_path)
    ui._rest_timer.interval = 1.0
    ui._rest_timer.reset()
    assert not ui.speech_bubble.visible
    ui.update(1.0)
    assert ui.speech_bubble.visible


def test_is_active_reflects_panel_visibility(monkeypatch, tmp_path):
    ui, _, _ = _make_ui(monkeypatch, tmp_path)
    assert ui.is_active is False
    ui.stats_panel.visible = True
    assert ui.is_active is True
