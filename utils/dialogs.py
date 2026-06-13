"""系统文件/颜色对话框封装。

Pygame 没有原生文件选择器，这里用 tkinter（Python 自带）弹出系统对话框
供「创建皮肤」选择图片文件与透明色。对话框为一次性弹出（隐藏的临时
root），调用期间会短暂阻塞主循环——属用户主动操作，可接受。
tkinter 不可用或用户取消时返回 None。
"""

from __future__ import annotations

from typing import Optional, Tuple

_IMAGE_TYPES = [("图片", "*.png *.jpg *.jpeg *.bmp"), ("所有文件", "*.*")]


def _hidden_root():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def ask_open_image(title: str = "选择图片") -> Optional[str]:
    """弹出文件选择对话框，返回所选图片路径；取消/出错返回 None。"""
    try:
        from tkinter import filedialog

        root = _hidden_root()
        try:
            path = filedialog.askopenfilename(title=title, filetypes=_IMAGE_TYPES)
        finally:
            root.destroy()
        return path or None
    except Exception:
        return None


def ask_color() -> Optional[Tuple[int, int, int]]:
    """弹出取色对话框，返回 (r, g, b)；取消/出错返回 None。"""
    try:
        from tkinter import colorchooser

        root = _hidden_root()
        try:
            result = colorchooser.askcolor(title="选择透明色")
        finally:
            root.destroy()
        if result and result[0]:
            return tuple(int(c) for c in result[0])
        return None
    except Exception:
        return None
