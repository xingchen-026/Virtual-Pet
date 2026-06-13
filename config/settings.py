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

# 内容审查违规词配置（脏话/色情/暴力/政治敏感等，数据化便于增删）
MODERATION_CONFIG_FILE = os.path.join(BASE_DIR, "config", "moderation.json")

# ----- 用户偏好配置 -----
# 设置窗口可修改的用户偏好（宠物大小等）
USER_CONFIG_FILE = os.path.join(BASE_DIR, "config", "user_config.json")

# 宠物缩放倍数的取值范围与调节步长
PET_SCALE_MIN = 0.5
PET_SCALE_MAX = 2.0
PET_SCALE_STEP = 0.1
PET_SCALE_DEFAULT = 1.0

# 交互引起的属性变化在数值面板中以 +xx/-xx 形式显示的持续时间（秒）
ATTR_DELTA_DURATION = 2.5

# ----- 皮肤配置 -----
# 用户导入的皮肤目录与当前皮肤配置文件
SKINS_DIR = os.path.join(ASSETS_DIR, "skins")
SKIN_CONFIG_FILE = os.path.join(BASE_DIR, "config", "skin_config.json")

# 皮肤帧统一输出尺寸（导入时归一化，与窗口大小匹配）
SKIN_FRAME_SIZE = (128, 128)

# ----- 窗口配置 -----
# 窗口需为居中的宠物（最大 2.0x 缩放约 256px）两侧留出
# 足够空间放置数值面板/设置窗口，避免弹窗遮挡宠物本体；
# 背景为透明色键，窗口大小不影响视觉效果
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_TITLE = "桌面虚拟宠物"
FPS = 60

# 窗口隐藏（最小化到托盘）时使用的低帧率，降低后台运行时的 CPU 占用
BACKGROUND_FPS = 5

# 空闲时（无移动/拖拽/UI 窗口）使用的帧率。宠物动画最快帧间隔
# 0.08 秒（12.5fps），30fps 渲染完全够用，可省约一半渲染开销
IDLE_FPS = 30

# 宠物数据自动存档间隔（秒），避免进程异常退出丢失进度
AUTOSAVE_INTERVAL = 60.0

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

# 睡眠模式下每个间隔内体力的恢复量（点击「睡觉」后停在原地缓慢回体力，
# 数值大于自然衰减，体力回满后自动醒来）
SLEEP_ENERGY_RECOVER_PER_TICK = 5

# 危急阈值：饥饿或体力低至此值（含）时进入危急状态——停止自主漫游，
# 持续显示饥饿/疲劳动画，给出明确的视觉反馈
CRITICAL_ATTRIBUTE_THRESHOLD = 0

# ----- 交互配置 -----
# 连续点击触发 excited 状态：window 秒内点击次数达到 threshold 即触发
EXCITED_CLICK_WINDOW = 1.0
EXCITED_CLICK_THRESHOLD = 3

# ----- AI 对话窗口配置 -----
# 打开/关闭 AI 对话窗口的按键（对应 pygame.key.name() 返回值）
CHAT_TOGGLE_KEY = "c"

# 对话窗口尺寸与边距。窗口跟随模式下宠物固定在窗口中心，
# 对话窗口靠左侧停靠、设置窗口靠右侧停靠，避免遮挡居中的宠物。
CHAT_WINDOW_MARGIN = 20
CHAT_WINDOW_WIDTH = 280
CHAT_WINDOW_HEIGHT = 420

# 设置窗口尺寸（靠右侧停靠，垂直居中）
SETTINGS_WINDOW_WIDTH = 280
SETTINGS_WINDOW_HEIGHT = 440

# 皮肤选择窗口尺寸（靠右侧停靠，垂直居中；缩略图预览选择）
SKIN_WINDOW_WIDTH = 300
SKIN_WINDOW_HEIGHT = 360

# AI 情绪联动触发的临时动画播放时长（秒）
AI_EFFECT_ANIMATION_DURATION = 2.0
