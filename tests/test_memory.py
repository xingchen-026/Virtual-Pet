"""MemoryManager 上限、持久化、遗忘策略与并发写入的回归测试。"""

import json
import threading
from datetime import datetime, timedelta

from core.ai.memory import (
    LONG_TERM_LIMIT,
    MEMORY_FORGET_DAYS,
    MEMORY_MIN_KEEP,
    SHORT_TERM_LIMIT,
    MemoryManager,
    _age_days,
)


def test_short_term_capped(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    for i in range(SHORT_TERM_LIMIT + 5):
        memory.add_dialogue(f"u{i}", f"p{i}")
    assert len(memory.short_term) == SHORT_TERM_LIMIT
    # 保留的是最近的记录
    assert memory.short_term[-1]["user"] == f"u{SHORT_TERM_LIMIT + 4}"


def test_long_term_capped(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    for i in range(LONG_TERM_LIMIT + 20):
        memory.add_event(f"event-{i}")
    assert len(memory.long_term) == LONG_TERM_LIMIT


def test_age_days_parsing():
    now = datetime(2026, 6, 15)
    assert _age_days("2026-06-15", now) == 0
    assert _age_days("2026-05-16", now) == 30
    assert _age_days(None, now) is None
    assert _age_days("乱码", now) is None


def test_forget_prunes_old_beyond_min_keep(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    now = datetime.now()
    old_day = (now - timedelta(days=MEMORY_FORGET_DAYS + 10)).strftime("%Y-%m-%d")
    # 构造：很多条陈旧记忆（手填旧日期）+ 最新若干条
    memory.long_term = [
        {"summary": f"old-{i}", "time": old_day} for i in range(MEMORY_MIN_KEEP + 8)
    ]
    memory._prune_long_term_locked(now=now)
    # 超出保护区且陈旧的被淡忘；保护区（最新 MEMORY_MIN_KEEP 条）保留
    assert len(memory.long_term) == MEMORY_MIN_KEEP
    assert memory.long_term[-1]["summary"] == f"old-{MEMORY_MIN_KEEP + 7}"


def test_forget_keeps_recent_and_undateable(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    now = datetime.now()
    fresh = now.strftime("%Y-%m-%d")
    old = (now - timedelta(days=MEMORY_FORGET_DAYS + 5)).strftime("%Y-%m-%d")
    memory.long_term = (
        [{"summary": "old-dated", "time": old}]          # 陈旧、在保护区外 -> 淡忘
        + [{"summary": "no-date"}]                        # 无日期 -> 保留
        + [{"summary": f"recent-{i}", "time": fresh} for i in range(MEMORY_MIN_KEEP)]
    )
    memory._prune_long_term_locked(now=now)
    summaries = [m["summary"] for m in memory.long_term]
    assert "old-dated" not in summaries
    assert "no-date" in summaries
    assert sum(s.startswith("recent-") for s in summaries) == MEMORY_MIN_KEEP


def test_persistence_roundtrip(tmp_path):
    path = str(tmp_path / "mem.json")
    memory = MemoryManager(path)
    memory.add_dialogue("你好", "你好呀")
    memory.add_event("用户第一次喂食", "happy")

    reloaded = MemoryManager(path)
    assert reloaded.short_term == [{"user": "你好", "pet": "你好呀"}]
    assert reloaded.long_term[0]["event"] == "用户第一次喂食"
    assert reloaded.long_term[0]["emotion"] == "happy"


def test_concurrent_writes_keep_file_valid(tmp_path):
    path = str(tmp_path / "mem.json")
    memory = MemoryManager(path)

    def dialogues():
        for i in range(60):
            memory.add_dialogue(f"u{i}", f"p{i}")

    def events():
        for i in range(60):
            memory.add_event(f"e{i}")

    threads = [threading.Thread(target=dialogues), threading.Thread(target=events)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 并发写入后文件仍是合法 JSON，且未超过各自上限
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["short_term"]) == SHORT_TERM_LIMIT
    assert len(data["long_term"]) == 60


def test_describe_handles_empty(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    assert "暂无" in memory.describe()


def test_short_term_keeps_last_three(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    for i in range(6):
        memory.add_dialogue(f"u{i}", f"p{i}")
    assert len(memory.short_term) == SHORT_TERM_LIMIT == 3
    assert memory.short_term[0]["user"] == "u3"  # 仅保留最近三轮


def test_add_summary_into_long_term(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    memory.add_summary("主人喜欢晚上聊天")
    assert memory.long_term[-1]["summary"] == "主人喜欢晚上聊天"
    assert "主人喜欢晚上聊天" in memory.describe()
    memory.add_summary("  ")  # 空白摘要忽略
    assert len(memory.long_term) == 1


def test_describe_renders_summary_and_event(tmp_path):
    memory = MemoryManager(str(tmp_path / "mem.json"))
    memory.add_summary("爱吃苹果")
    memory.add_event("用户第一次喂食", "happy")
    text = memory.describe()
    assert "爱吃苹果" in text and "用户第一次喂食" in text
