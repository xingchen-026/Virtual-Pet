"""EmotionAnalyzer 关键词规则与情绪标签解析的回归测试。"""

from core.ai.emotion_analyzer import EmotionAnalyzer


def test_positive_keyword_raises_mood():
    effect = EmotionAnalyzer().analyze("你好可爱呀")
    assert effect.mood_delta > 0
    assert effect.suggested_animation is None


def test_negative_keyword_lowers_mood():
    effect = EmotionAnalyzer().analyze("你真笨")
    assert effect.mood_delta < 0


def test_tired_keyword_lowers_energy_and_suggests_sleep():
    effect = EmotionAnalyzer().analyze("你累了吗？")
    assert effect.energy_delta < 0
    assert effect.suggested_animation == "sleep"


def test_neutral_text_is_empty():
    assert EmotionAnalyzer().analyze("今天天气不错").is_empty


def test_from_tag_parses_emotion_tag():
    effect = EmotionAnalyzer().from_tag("[情绪:开心] 嘿嘿")
    assert effect.mood_delta > 0


def test_from_tag_tired_label_suggests_sleep():
    effect = EmotionAnalyzer().from_tag("[情绪:疲惫] 好困")
    assert effect.energy_delta < 0
    assert effect.suggested_animation == "sleep"


def test_strip_tag_removes_tag_and_trims():
    assert EmotionAnalyzer.strip_tag("[情绪:开心] 你来啦~") == "你来啦~"


def test_strip_tag_without_tag_unchanged():
    assert EmotionAnalyzer.strip_tag("普通回复") == "普通回复"
