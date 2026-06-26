"""极简 .env 加载器（仅标准库，不引入 python-dotenv 依赖）。

把项目根目录（打包态为 exe 旁目录）下的 .env 文件解析为 KEY=VALUE，
写入 os.environ，供各模块按环境变量读取隐私数据（API Key 等）。

约定与常见 dotenv 行为一致：
* 忽略空行与以 # 开头的注释行；
* 行内 `KEY=VALUE`，等号两侧空白会被 strip；
* 值两端可选地包裹一对单/双引号（会被去掉），便于含空格的值；
* 默认 **不覆盖** 已存在的真实环境变量——这样在 CI / 系统里 export 的
  变量优先级高于 .env，便于部署时覆盖。

把密钥放进 .env（已被 .gitignore 屏蔽）而非任何入库文件，是隐私数据的
推荐存放方式；.env.example 为入库模板，引导用户填写。
"""

from __future__ import annotations

import os
from typing import Dict


def parse_env(text: str) -> Dict[str, str]:
    """把 .env 文本解析为 {KEY: VALUE} 字典（不写 os.environ，便于单测）。"""
    result: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        result[key] = value
    return result


def load_dotenv(path: str, override: bool = False) -> Dict[str, str]:
    """读取 path 处的 .env 写入 os.environ，返回解析到的键值对。

    文件不存在时静默返回空字典（开发/打包态均允许不带 .env）。
    override=False 时不覆盖已存在的环境变量。
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            pairs = parse_env(fh.read())
    except (FileNotFoundError, OSError):
        return {}

    for key, value in pairs.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return pairs
