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

# 自主行为参数配置文件（行为概率、速度、阈值等，禁止硬编码）
BEHAVIOR_CONFIG_FILE = os.path.join(BASE_DIR, "config", "behavior_config.json")

# 行为日志目录与文件
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PET_BEHAVIOR_LOG_FILE = os.path.join(LOGS_DIR, "pet_behavior.log")

# 桌面窗口参数配置文件（透明/置顶/初始位置等，禁止硬编码）
DESKTOP_CONFIG_FILE = os.path.join(BASE_DIR, "config", "desktop_config.json")

# AI 服务配置文件（模型供应商/模型名称/参数，禁止硬编码）
AI_CONFIG_FILE = os.path.join(BASE_DIR, "config", "ai_config.json")

# 宠物人格配置与记忆数据文件
PERSONALITY_FILE = os.path.join(DATA_DIR, "personality.json")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")

# ----- 皮肤配置 -----
# 用户导入的皮肤目录与当前皮肤配置文件
SKINS_DIR = os.path.join(ASSETS_DIR, "skins")
SKIN_CONFIG_FILE = os.path.join(BASE_DIR, "config", "skin_config.json")

# 皮肤帧统一输出尺寸（导入时归一化，与窗口大小匹配）
SKIN_FRAME_SIZE = (128, 128)

# ----- 窗口配置 -----
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 480
WINDOW_TITLE = "桌面虚拟宠物"
FPS = 60

# 窗口隐藏（最小化到托盘）时使用的低帧率，降低后台运行时的 CPU 占用
BACKGROUND_FPS = 5

# 窗口背景透明色键：填充该颜色的区域会被 DesktopManager 设为透明
TRANSPARENT_COLOR_KEY = (255, 0, 255)

# 维持窗口置顶状态的检查间隔（秒）。避免每帧调用系统 API 影响性能。
TOPMOST_REFRESH_INTERVAL = 2.0

# ----- UI 字体配置 -----
# 界面文字字体候选列表（按顺序匹配系统已安装字体）。
# 必须包含中文字体，否则中文会渲染为方块乱码；
# 文件读写已统一 UTF-8，界面乱码均由字体缺少中文字形导致。
UI_FONT_NAMES = ["microsoftyahei", "simhei", "kaiti", "fangsong"]
UI_FONT_SIZE = 16

# ----- 宠物数值面板配置 -----
# 右键点击宠物弹出/关闭数值信息面板
STATS_PANEL_WIDTH = 220
STATS_PANEL_PADDING = 10
STATS_PANEL_MARGIN = 8

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
    "interact": "interact",
    "excited": "excited",
    "eating": "eating",
    "playing": "playing",
    "walk": "walk",
    "run": "run",
    "look_around": "look_around",
    "sleep": "sleep",
}

# 动画状态名称 -> 单帧播放时长（秒），数值越小播放越快
ANIMATION_FRAME_DURATIONS = {
    "idle": 0.20,
    "happy": 0.10,
    "hungry": 0.25,
    "tired": 0.35,
    "interact": 0.15,
    "excited": 0.08,
    "eating": 0.25,
    "playing": 0.12,
    "walk": 0.15,
    "run": 0.08,
    "look_around": 0.30,
    "sleep": 0.50,
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

# ----- 交互配置 -----
# 连续点击触发 excited 状态：window 秒内点击次数达到 threshold 即触发
EXCITED_CLICK_WINDOW = 1.0
EXCITED_CLICK_THRESHOLD = 3

# 喂食 / 玩耍功能按键（对应 pygame.key.name() 返回值）
FEED_KEY = "f"
PLAY_KEY = "p"

# ----- AI 对话窗口配置 -----
# 打开/关闭 AI 对话窗口的按键（对应 pygame.key.name() 返回值）
CHAT_TOGGLE_KEY = "c"

# 对话窗口在主窗口中的边距与尺寸
CHAT_WINDOW_MARGIN = 20
CHAT_WINDOW_HEIGHT = 320

# AI 情绪联动触发的临时动画播放时长（秒）
AI_EFFECT_ANIMATION_DURATION = 2.0
