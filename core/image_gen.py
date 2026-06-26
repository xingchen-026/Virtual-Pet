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
import os
import time
import urllib.error
import urllib.request
from typing import List, Optional

from PIL import Image

from config import settings
from utils.exception import AppError


class ImageGenError(AppError):
    """文生图调用失败（鉴权/网络/额度/返回格式等）。

    transient=True 表示「临时性」错误（网络中断/超时/5xx/429），调用方可重试；
    鉴权失败/参数错误/返回格式错误等为 False（重试无意义）。
    """

    transient = False


def _transient_error(message: str) -> ImageGenError:
    err = ImageGenError(message)
    err.transient = True
    return err


def _key_from_env() -> str:
    """从 .env 注入的环境变量里取文生图 API Key（窗口未填时的回退来源）。"""
    return os.environ.get(settings.IMAGE_GEN_API_KEY_ENV, "").strip()


def build_state_prompts(base_prompt: str, states: Optional[List[str]] = None) -> dict:
    """把用户的角色描述改写成「同一角色不同状态」的整套提示词。

    每个状态的提示词 = 用户角色描述 + 该状态动作（settings.IMAGE_GEN_STATE_ACTIONS）
    + 一致性锚点（settings.IMAGE_GEN_CONSISTENCY）+ 风格/合规后缀。这样一次性生成的
    各帧尽量是同一只宠物的不同动作。states 为 None 时覆盖全部内置动画状态。

    返回 {状态: 完整提示词}（保持状态顺序）。
    """
    base = (base_prompt or "").strip()
    actions = settings.IMAGE_GEN_STATE_ACTIONS
    states = states or list(actions.keys())
    prompts = {}
    for state in states:
        action = actions.get(state, "")
        prompts[state] = (
            f"{base}，{action}。{settings.IMAGE_GEN_CONSISTENCY}"
            f"{settings.IMAGE_GEN_PROMPT_SUFFIX}"
        )
    return prompts


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
        msg = f"请求失败 HTTP {exc.code}：{detail or exc.reason}"
        # 5xx 服务端错误与 429 限流是临时性的，可重试；4xx（鉴权/参数）不重试。
        if exc.code >= 500 or exc.code == 429:
            raise _transient_error(msg) from exc
        raise ImageGenError(msg) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise _transient_error(f"网络错误：{exc}") from exc
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
        # Key 优先用传入值（窗口里填的）；为空时回退到 .env 的环境变量，
        # 让用户把密钥统一放 .env、窗口留空即可。
        self.api_key = (api_key or "").strip() or _key_from_env()
        self.model = model
        self.size = size
        self.timeout = timeout

    def generate(self, prompt: str, retries: Optional[int] = None) -> Image.Image:
        """按 prompt 生成一张图片，返回 RGBA 的 Pillow 图像。

        临时性网络错误（SSL 中断/超时/5xx/429）自动重试 retries 次（默认取
        settings.IMAGE_GEN_RETRIES），每次按 settings.IMAGE_GEN_RETRY_DELAY 递增退避；
        鉴权/参数/格式等永久错误立即抛出，不重试。
        """
        if not self.api_key:
            raise ImageGenError("未填写 API Key")
        if not (prompt or "").strip():
            raise ImageGenError("提示词不能为空")

        attempts = (settings.IMAGE_GEN_RETRIES if retries is None else retries) + 1
        for attempt in range(attempts):
            try:
                return self._generate_once(prompt)
            except ImageGenError as exc:
                if not exc.transient or attempt == attempts - 1:
                    raise
                time.sleep(settings.IMAGE_GEN_RETRY_DELAY * (attempt + 1))

    def _generate_once(self, prompt: str) -> Image.Image:
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
            raise _transient_error(f"下载生成图片失败：{exc}") from exc

    @staticmethod
    def list_models(base_url: str, api_key: str, timeout: float = 20) -> List[str]:
        """拉取可用模型 id 列表（GET {base}/models）；失败时抛 ImageGenError。"""
        base = (base_url or settings.IMAGE_GEN_BASE_URL).rstrip("/")
        req = urllib.request.Request(f"{base}/models", method="GET")
        req.add_header("Authorization", f"Bearer {(api_key or '').strip() or _key_from_env()}")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise ImageGenError(f"获取模型列表失败：{exc}") from exc
        return [m.get("id", "") for m in data.get("data", []) if m.get("id")]
