"""食物数据模块。

定义喂食系统所需的 Food 数据结构，供 core.action 中的
FeedAction 使用。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Food:
    """食物：描述喂食后对宠物属性的影响。

    name: 食物名称。
    hunger_restore: 喂食后恢复的饥饿值。
    mood_restore: 喂食后恢复的心情值，默认为 0。
    """

    name: str
    hunger_restore: float
    mood_restore: float = 0


# 默认食物：FeedAction 在未指定具体食物时使用。
DEFAULT_FOOD = Food(name="Apple", hunger_restore=20, mood_restore=10)
