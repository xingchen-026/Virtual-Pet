"""MemoryManager 上限、持久化与并发写入的回归测试。"""

import json
import threading

from core.ai.memory import LONG_TERM_LIMIT, SHORT_TERM_LIMIT, MemoryManager


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
