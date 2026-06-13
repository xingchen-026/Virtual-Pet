"""内容审查 ContentModerator 的回归测试。"""

from core.ai.moderation import ContentModerator

CONFIG = {
    "fallback_reply": "换个话题吧~",
    "banned_words": ["fuck", "色情", "杀人"],
}


def _mod():
    return ContentModerator(CONFIG)


def test_clean_text_is_safe():
    assert _mod().is_safe("今天天气真好，我们出去玩吧")


def test_chinese_banned_word_detected():
    assert not _mod().is_safe("我想看色情内容")


def test_english_banned_word_detected_case_insensitive():
    assert not _mod().is_safe("What the FUCK")


def test_english_word_boundary_avoids_false_positive():
    # "assistant" 不应因包含子串而误判（banned 列表里没有 ass，这里验证边界匹配机制）
    mod = ContentModerator({"banned_words": ["ass"], "fallback_reply": "x"})
    assert mod.is_safe("the assistant helps you")
    assert not mod.is_safe("you ass")


def test_empty_text_is_safe():
    assert _mod().is_safe("")


def test_fallback_reply_loaded():
    assert _mod().fallback_reply == "换个话题吧~"


def test_defaults_when_config_empty():
    mod = ContentModerator({})
    assert mod.fallback_reply  # 有兜底文案
    assert not mod.is_safe("fuck")  # 有兜底词表
