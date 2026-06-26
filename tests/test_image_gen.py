"""AI 文生图客户端 ImageGenClient 的回归测试（打桩 HTTP，不联网）。"""

import base64
import io

import pytest
from PIL import Image

from config import settings
from core import image_gen
from core.image_gen import ImageGenClient, ImageGenError, build_state_prompts


def _png_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), (10, 20, 30, 255)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _client():
    return ImageGenClient("https://x/v1", "sk-test", "m", "512x512")


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv(settings.IMAGE_GEN_API_KEY_ENV, raising=False)
    c = ImageGenClient("https://x/v1", "", "m")
    with pytest.raises(ImageGenError):
        c.generate("cat")


def test_api_key_falls_back_to_env(monkeypatch):
    # 窗口未填 Key 时，回退到 .env 注入的环境变量
    monkeypatch.setenv(settings.IMAGE_GEN_API_KEY_ENV, "sk-from-env")
    c = ImageGenClient("https://x/v1", "", "m")
    assert c.api_key == "sk-from-env"


def test_explicit_key_overrides_env(monkeypatch):
    # 窗口里填了 Key 则优先用它，不取环境变量
    monkeypatch.setenv(settings.IMAGE_GEN_API_KEY_ENV, "sk-from-env")
    c = ImageGenClient("https://x/v1", "sk-typed", "m")
    assert c.api_key == "sk-typed"


def test_empty_prompt_raises():
    with pytest.raises(ImageGenError):
        _client().generate("   ")


def test_generate_from_b64(monkeypatch):
    monkeypatch.setattr(
        image_gen, "_post_json", lambda *a, **k: {"data": [{"b64_json": _png_b64()}]}
    )
    img = _client().generate("a cat")
    assert isinstance(img, Image.Image)
    assert img.mode == "RGBA"
    assert img.size == (8, 8)


def test_generate_from_url(monkeypatch):
    monkeypatch.setattr(
        image_gen, "_post_json",
        lambda *a, **k: {"data": [{"url": "https://img/x.png"}]},
    )
    sentinel = Image.new("RGBA", (4, 4))
    monkeypatch.setattr(ImageGenClient, "_download", lambda self, url: sentinel)
    assert _client().generate("a cat") is sentinel


def test_generate_no_data_raises(monkeypatch):
    monkeypatch.setattr(image_gen, "_post_json", lambda *a, **k: {"data": []})
    with pytest.raises(ImageGenError):
        _client().generate("a cat")


def test_generate_retries_on_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr(image_gen.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            raise image_gen._transient_error("SSL 中断")
        return {"data": [{"b64_json": _png_b64()}]}

    monkeypatch.setattr(image_gen, "_post_json", flaky)
    img = _client().generate("a cat")  # 默认重试 2 次：第 3 次成功
    assert isinstance(img, Image.Image)
    assert calls["n"] == 3


def test_generate_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(image_gen.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def always_transient(*a, **k):
        calls["n"] += 1
        raise image_gen._transient_error("网络错误")

    monkeypatch.setattr(image_gen, "_post_json", always_transient)
    with pytest.raises(ImageGenError):
        _client().generate("a cat", retries=2)
    assert calls["n"] == 3  # 1 次原始 + 2 次重试


def test_generate_no_retry_on_permanent_error(monkeypatch):
    monkeypatch.setattr(image_gen.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def permanent(*a, **k):
        calls["n"] += 1
        raise ImageGenError("HTTP 401 鉴权失败")  # transient 默认 False

    monkeypatch.setattr(image_gen, "_post_json", permanent)
    with pytest.raises(ImageGenError):
        _client().generate("a cat")
    assert calls["n"] == 1  # 永久错误立即放弃，不重试


def test_base_url_normalized():
    c = ImageGenClient("https://x/v1/", "k", "m")
    assert c.base_url == "https://x/v1"


def test_build_state_prompts_covers_all_states():
    prompts = build_state_prompts("橘色小猫")
    assert set(prompts.keys()) == set(settings.IMAGE_GEN_STATE_ACTIONS.keys())
    for state, p in prompts.items():
        assert "橘色小猫" in p                                  # 保留用户角色描述
        assert settings.IMAGE_GEN_STATE_ACTIONS[state] in p     # 含该状态动作
        assert settings.IMAGE_GEN_CONSISTENCY in p              # 含一致性锚点


def test_build_state_prompts_subset():
    prompts = build_state_prompts("狗", states=["idle", "walk"])
    assert list(prompts.keys()) == ["idle", "walk"]
