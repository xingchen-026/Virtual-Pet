"""宠物状态枚举模块。

使用 Enum 统一管理宠物的行为状态，避免状态名称以裸字符串
散落在状态机、行为逻辑与动画切换代码中。

后续如需新增状态（例如 SLEEPING / EXCITED / ANGRY），
只需在此枚举中追加新成员，并在 core/behavior.py 的
状态 -> 动画映射表中补充对应关系即可。
"""

import enum


class PetState(enum.Enum):
    """宠物行为状态。"""

    IDLE = "idle"
    HAPPY = "happy"
    HUNGRY = "hungry"
    TIRED = "tired"
    SAD = "sad"
