"""AI 文生图客户端 ImageGenClient 的回归测试（打桩 HTTP，不联网）。"""

import base64
import io

import pytest
from PIL import Image

from core import image_gen
from core.image_gen import ImageGenClient, ImageGenError


def _png_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGBA", (8, 8), (10, 20, 30, 255)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _client():
    return ImageGenClient("https://x/v1", "sk-test", "m", "512x512")


def test_missing_key_raises():
    c = ImageGenClient("https://x/v1", "", "m")
    with pytest.raises(ImageGenError):
        c.generate("cat")


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


def test_base_url_normalized():
    c = ImageGenClient("https://x/v1/", "k", "m")
    assert c.base_url == "https://x/v1"
