"""utils.env 的 .env 解析与加载回归测试（不依赖真实文件/环境）。"""

import os

from utils.env import load_dotenv, parse_env


def test_parse_basic():
    env = parse_env("A=1\nB=hello")
    assert env == {"A": "1", "B": "hello"}


def test_parse_ignores_comments_blank_and_malformed():
    text = "# 注释\n\n  # 缩进注释\nKEY=value\nNOEQUALS\n=novalue"
    assert parse_env(text) == {"KEY": "value"}


def test_parse_strips_spaces_and_quotes():
    env = parse_env('  K1 = v1 \nK2="a b"\nK3=\'c d\'')
    assert env == {"K1": "v1", "K2": "a b", "K3": "c d"}


def test_parse_value_with_equals_and_url():
    # 值里含等号/冒号（URL、base64）应保留
    env = parse_env("URL=https://x/y?a=b\nTOKEN=ab==")
    assert env["URL"] == "https://x/y?a=b"
    assert env["TOKEN"] == "ab=="


def test_load_missing_file_is_silent(tmp_path):
    assert load_dotenv(str(tmp_path / "nope.env")) == {}


def test_load_sets_environ_without_override(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("FOO_NEW=fromfile\nFOO_EXIST=fromfile", encoding="utf-8")
    monkeypatch.delenv("FOO_NEW", raising=False)
    monkeypatch.setenv("FOO_EXIST", "preset")  # 已存在的不被覆盖
    load_dotenv(str(p))
    assert os.environ["FOO_NEW"] == "fromfile"
    assert os.environ["FOO_EXIST"] == "preset"


def test_load_override_true(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text("FOO_EXIST=fromfile", encoding="utf-8")
    monkeypatch.setenv("FOO_EXIST", "preset")
    load_dotenv(str(p), override=True)
    assert os.environ["FOO_EXIST"] == "fromfile"
