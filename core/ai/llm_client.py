"""LLM 客户端封装模块。

LLMClient 统一封装不同 LLM 服务商的请求接口，对外提供单一方法：

    response = llm.chat(messages)

支持的 provider（由 config/ai_config.json 的 "provider" 字段决定）：

* "openai"   -> OpenAI Chat Completions API
* "deepseek" -> DeepSeek Chat Completions API（与 OpenAI 接口兼容）
* "local"    -> 本地模型接口（占位实现，便于离线开发与测试）

替换模型供应商仅需修改 config/ai_config.json 的 provider / model /
api_base / api_key_env 等字段，无需修改业务代码。

请求失败（网络异常 / 超时 / API Key 缺失 / 返回格式错误等）均抛出
AIServiceError，由上层 AIService 捕获并降级为离线回复，
保证桌宠核心功能不受影响。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Dict, List

from utils.exception import AIServiceError

# 内置的 OpenAI 兼容接口默认地址，可在 config/ai_config.json 中通过
# "api_base" 覆盖（例如指向本地代理或其他兼容服务）。
_DEFAULT_API_BASES = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
}


class LLMClient:
    """统一的 LLM 调用客户端，未来替换模型供应商无需修改业务代码。"""

    def __init__(self, config: Dict) -> None:
        self.provider: str = config.get("provider", "local")
        self.model: str = config.get("model", "")
        self.temperature: float = config.get("temperature", 0.7)
        self.max_tokens: int = config.get("max_tokens", 500)
        self.timeout: float = config.get("timeout", 10)
        # API Key 优先取配置中的 api_key（设置窗口写入），
        # 为空时回退到 api_key_env 指定的环境变量
        self.api_key: str = config.get("api_key", "")
        self.api_key_env: str = config.get("api_key_env", "")
        self.api_base: str = config.get("api_base") or _DEFAULT_API_BASES.get(self.provider, "")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """发送对话消息列表，返回模型回复文本。

        messages: [{"role": "system"/"user"/"assistant", "content": "..."}]
        失败时抛出 AIServiceError，由调用方处理离线降级逻辑。
        """
        if self.provider in ("openai", "deepseek"):
            return self._chat_openai_compatible(messages)

        if self.provider == "local":
            return self._chat_local(messages)

        raise AIServiceError(f"不支持的 LLM provider: {self.provider}")

    def _chat_openai_compatible(self, messages: List[Dict[str, str]]) -> str:
        """调用 OpenAI / DeepSeek 等 OpenAI 兼容的 Chat Completions 接口。"""
        api_key = self.api_key or (
            os.environ.get(self.api_key_env, "") if self.api_key_env else ""
        )
        if not api_key:
            raise AIServiceError(
                f"未配置 API Key（配置项 api_key 与环境变量 {self.api_key_env or '<未指定>'} 均为空）"
            )

        if not self.api_base:
            raise AIServiceError(f"未配置 api_base（provider={self.provider}）")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        request = urllib.request.Request(
            self.api_base,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # 提取服务端返回的错误描述（如 Key 无效 / 模型不存在 / 余额不足）：
            # OpenAI 兼容接口的错误体为 {"error": {"message": "..."}}
            detail = ""
            try:
                raw = exc.read().decode("utf-8", errors="replace").strip()
                try:
                    detail = json.loads(raw).get("error", {}).get("message", "") or raw
                except (json.JSONDecodeError, AttributeError):
                    detail = raw
            except Exception:
                pass
            detail = detail[:200] or exc.reason
            raise AIServiceError(f"LLM 请求失败: HTTP {exc.code} {detail}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise AIServiceError(f"LLM 请求失败: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AIServiceError(f"LLM 返回格式错误: {exc}") from exc

        try:
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AIServiceError(f"LLM 返回格式错误: {exc}") from exc

    def _chat_local(self, messages: List[Dict[str, str]]) -> str:
        """本地模型接口占位实现：当前阶段未接入真实本地模型。

        预留此分支是为了让 config/ai_config.json 中的
        "provider": "local" 可以被识别而不报“不支持的 provider”，
        后续接入本地模型时只需替换本方法的实现。
        """
        raise AIServiceError("本地模型接口尚未配置")
