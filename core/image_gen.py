"""AI 文生图客户端模块。

ImageGenClient 调用「OpenAI 兼容」的文生图接口（POST {base}/images/generations），
用户自带 API Key 与模型。返回 Pillow 图像，供皮肤管线处理（抠图/缩放/导入）。

* 仅用标准库 urllib 发请求，不引入新依赖。
* 响应同时兼容 `data[0].url`（下载）与 `data[0].b64_json`（解码）两种返回。
* 网络阻塞，调用方应在后台线程使用；异常统一抛 ImageGenError 由上层提示。
* 不在本模块持久化任何 Key（Key 由上层从用户配置传入）。
"""

from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.request
from typing import List, Optional

from PIL import Image

from config import settings
from utils.exception import AppError


class ImageGenError(AppError):
    """文生图调用失败（鉴权/网络/额度/返回格式等）。"""


def _post_json(url: str, api_key: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            pass
        raise ImageGenError(f"请求失败 HTTP {exc.code}：{detail or exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ImageGenError(f"网络错误：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise ImageGenError(f"返回不是合法 JSON：{exc}") from exc


def _bytes_to_image(raw: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception as exc:
        raise ImageGenError(f"图片解码失败：{exc}") from exc


class ImageGenClient:
    """OpenAI 兼容的文生图客户端（用户自带 Key/模型）。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        size: str = "1024x1024",
        timeout: float = settings.IMAGE_GEN_TIMEOUT,
    ) -> None:
        self.base_url = (base_url or settings.IMAGE_GEN_BASE_URL).rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = model
        self.size = size
        self.timeout = timeout

    def generate(self, prompt: str) -> Image.Image:
        """按 prompt 生成一张图片，返回 RGBA 的 Pillow 图像。"""
        if not self.api_key:
            raise ImageGenError("未填写 API Key")
        if not (prompt or "").strip():
            raise ImageGenError("提示词不能为空")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": self.size,
        }
        result = _post_json(
            f"{self.base_url}/images/generations", self.api_key, payload, self.timeout
        )
        items = result.get("data") or []
        if not items:
            raise ImageGenError(f"返回无图片数据：{json.dumps(result)[:200]}")
        item = items[0]

        b64 = item.get("b64_json")
        if b64:
            return _bytes_to_image(base64.b64decode(b64))

        url = item.get("url")
        if url:
            return self._download(url)

        raise ImageGenError("返回既无 url 也无 b64_json")

    def _download(self, url: str) -> Image.Image:
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return _bytes_to_image(resp.read())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ImageGenError(f"下载生成图片失败：{exc}") from exc

    @staticmethod
    def list_models(base_url: str, api_key: str, timeout: float = 20) -> List[str]:
        """拉取可用模型 id 列表（GET {base}/models）；失败时抛 ImageGenError。"""
        base = (base_url or settings.IMAGE_GEN_BASE_URL).rstrip("/")
        req = urllib.request.Request(f"{base}/models", method="GET")
        req.add_header("Authorization", f"Bearer {(api_key or '').strip()}")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise ImageGenError(f"获取模型列表失败：{exc}") from exc
        return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
