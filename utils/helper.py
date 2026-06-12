"""通用工具函数模块。

当前阶段提供基础的 JSON 文件读写接口，
供宠物数据持久化等功能复用。
"""

import json
import os


def load_json(file_path):
    """读取 JSON 文件并返回字典数据。

    如果文件不存在，返回 None。
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path, data):
    """将字典数据写入 JSON 文件，自动创建所需目录。"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
