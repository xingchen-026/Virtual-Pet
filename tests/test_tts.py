"""TTSManager 的回归测试（只覆盖不发声的逻辑路径，避免测试时真的朗读）。

注意：禁用态 / 不可用态下 speak 不入队、不调用引擎，故测试不会触发实际语音。
"""

from core.tts import TTSManager


def test_disabled_speak_is_noop():
    m = TTSManager(enabled=False)
    m.speak("你好")
    assert m._queue.qsize() == 0  # 关闭时不入队、不朗读


def test_unavailable_speak_is_noop():
    m = TTSManager(enabled=True)
    m._ok = False  # 模拟引擎不可用
    m.speak("你好")
    assert m._queue.qsize() == 0


def test_empty_text_skipped():
    m = TTSManager(enabled=False)
    m.set_enabled(True)
    m._ok = False  # 确保即便启用也不真正朗读
    m.speak("")
    assert m._queue.qsize() == 0


def test_set_enabled_toggles():
    m = TTSManager(enabled=False)
    assert m.enabled is False
    m.set_enabled(True)
    assert m.enabled is True
    m.set_enabled(False)
    assert m.enabled is False
