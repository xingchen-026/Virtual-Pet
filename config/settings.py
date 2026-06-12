"""全局配置模块。

集中管理窗口参数、运行帧率、资源路径以及宠物默认属性，
避免业务代码中出现硬编码的配置数值。
"""

import os

# ----- 路径配置 -----
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
PET_DATA_FILE = os.path.join(DATA_DIR, "pet_data.json")

# ----- 窗口配置 -----
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 480
WINDOW_TITLE = "桌面虚拟宠物"
FPS = 60

# ----- 宠物属性数值范围 -----
ATTRIBUTE_MIN = 0
ATTRIBUTE_MAX = 100

# ----- 宠物默认配置 -----
DEFAULT_PET_NAME = "Pet"
DEFAULT_PET_AGE = 1
DEFAULT_PET_HUNGER = 100
DEFAULT_PET_MOOD = 100
DEFAULT_PET_ENERGY = 100
DEFAULT_PET_POSITION = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

# ----- 动画配置 -----
# 动画状态名称 -> assets/animations 下对应的资源目录名
ANIMATION_FOLDERS = {
    "idle": "idle",
    "happy": "happy",
    "hungry": "hungry",
    "tired": "tired",
}

# 动画状态名称 -> 单帧播放时长（秒），数值越小播放越快
ANIMATION_FRAME_DURATIONS = {
    "idle": 0.20,
    "happy": 0.10,
    "hungry": 0.25,
    "tired": 0.35,
}

# 宠物默认动画状态
DEFAULT_ANIMATION_STATE = "idle"

# ----- 属性随时间变化配置 -----
# 属性自然衰减的计时间隔（秒）。开发/测试阶段取较小值，
# 正式发布时可调大（如 60）。
ATTRIBUTE_DECAY_INTERVAL = 5.0

# 每个间隔内饥饿值、体力值的衰减量
HUNGER_DECAY_PER_TICK = 1
ENERGY_DECAY_PER_TICK = 1

# 非开心状态下，每个间隔内心情值的衰减量
MOOD_DECAY_PER_TICK = 0.2
