"""全局配置模块。

集中管理窗口参数、运行帧率、资源路径以及宠物默认属性，
避免业务代码中出现硬编码的配置数值。
"""

import os
import shutil
import sys

# ----- 路径配置 -----
# 兼容打包：PyInstaller(onefile) 冻结后，只读资源解压在临时目录 sys._MEIPASS，
# 而运行期可写数据（存档/配置/日志/用户皮肤）需放在 exe 所在目录（便携）。
# 开发态两者都等于项目根，路径与打包前完全一致。
_FROZEN = getattr(sys, "frozen", False)
_MODULE_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if _FROZEN:
    RESOURCE_DIR = sys._MEIPASS                  # 打进 exe 的只读资源（解压临时目录）
    APP_DIR = os.path.dirname(sys.executable)    # 可写数据目录：exe 所在文件夹
else:
    RESOURCE_DIR = _MODULE_BASE
    APP_DIR = _MODULE_BASE

# 兼容旧引用：BASE_DIR 仍指向代码/资源根（只读）。新增可写路径一律基于 APP_DIR。
BASE_DIR = RESOURCE_DIR

# 只读资源：动画/图片/声音
ASSETS_DIR = os.path.join(RESOURCE_DIR, "assets")

# 可写运行数据目录
DATA_DIR = os.path.join(APP_DIR, "data")
PET_DATA_FILE = os.path.join(DATA_DIR, "pet_data.json")

# 自主行为参数配置文件（只读，行为概率/速度/阈值等，禁止硬编码）
BEHAVIOR_CONFIG_FILE = os.path.join(RESOURCE_DIR, "config", "behavior_config.json")

# 行为日志目录与文件（可写）
LOGS_DIR = os.path.join(APP_DIR, "logs")
PET_BEHAVIOR_LOG_FILE = os.path.join(LOGS_DIR, "pet_behavior.log")

# 桌面窗口参数配置文件（只读，透明/置顶/初始位置等，禁止硬编码）
DESKTOP_CONFIG_FILE = os.path.join(RESOURCE_DIR, "config", "desktop_config.json")

# AI 服务配置文件：用户填 Key 后会写回，故放可写目录；首次运行从只读模板播种。
AI_CONFIG_FILE = os.path.join(APP_DIR, "config", "ai_config.json")
AI_CONFIG_TEMPLATE_FILE = os.path.join(RESOURCE_DIR, "config", "ai_config.template.json")

# 宠物人格配置与记忆数据文件（可写）
PERSONALITY_FILE = os.path.join(DATA_DIR, "personality.json")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")

# 聊天窗口显示历史（与 AI 记忆分离：此处保存完整可见对话，重启后回填到聊天窗口）
CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.json")
CHAT_HISTORY_LIMIT = 60

# 内容审查违规词配置（只读，脏话/色情/暴力/政治敏感等，数据化便于增删）
MODERATION_CONFIG_FILE = os.path.join(RESOURCE_DIR, "config", "moderation.json")

# ----- 用户偏好配置 -----
# 设置窗口可修改的用户偏好（宠物大小等），可写
USER_CONFIG_FILE = os.path.join(APP_DIR, "config", "user_config.json")

# 宠物缩放倍数的取值范围与调节步长
PET_SCALE_MIN = 0.5
PET_SCALE_MAX = 2.0
PET_SCALE_STEP = 0.1
PET_SCALE_DEFAULT = 1.0

# 交互引起的属性变化在数值面板中以 +xx/-xx 形式显示的持续时间（秒）
ATTR_DELTA_DURATION = 2.5

# ----- 皮肤配置 -----
# 皮肤目录与当前皮肤配置文件均可写：用户可新建皮肤、切换当前皮肤。
# 内置皮肤（如 cat）随 exe 打包，首次运行由 ensure_user_data 播种到此目录。
SKINS_DIR = os.path.join(APP_DIR, "assets", "skins")
SKIN_CONFIG_FILE = os.path.join(APP_DIR, "config", "skin_config.json")
# 内置皮肤的只读来源（开发态与 SKINS_DIR 相同；打包态在 exe 内部资源里）
BUILTIN_SKINS_DIR = os.path.join(RESOURCE_DIR, "assets", "skins")

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

# 主循环单帧最大时间步长（秒）。进程被系统挂起/降频（如长时间睡眠、
# 窗口长期无焦点）后，下一帧 clock.tick 会返回很大的 dt；若不钳制，
# 移动会一步跳到目标（视觉上"闪现"），属性也会瞬间大幅衰减。
# 钳制到此上限可保证睡眠回满体力后仍平滑漫游。
MAX_FRAME_DT = 0.1

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
    "sad": "sad",
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
    "sad": 0.35,
}

# 宠物默认动画状态
DEFAULT_ANIMATION_STATE = "idle"

# 动画状态的中文显示名（UI 展示用，内部仍用英文 key）
STATE_DISPLAY_NAMES = {
    "idle": "待机",
    "happy": "开心",
    "hungry": "饥饿",
    "tired": "疲惫",
    "interact": "互动",
    "excited": "兴奋",
    "eating": "进食",
    "playing": "玩耍",
    "walk": "行走",
    "run": "奔跑",
    "look_around": "张望",
    "sleep": "睡觉",
    "sad": "难过",
}

# ----- 属性随时间变化配置 -----
# 属性自然衰减的计时间隔（秒）。开发/测试阶段取较小值，
# 正式发布时可调大（如 60）。
ATTRIBUTE_DECAY_INTERVAL = 5.0

# 每个间隔内饥饿值、体力值的衰减量。
# 体力衰减仅在宠物移动时发生（漫游/奔跑），静止时不消耗。
HUNGER_DECAY_PER_TICK = 1
ENERGY_DECAY_PER_TICK = 1

# 非移动、非睡眠状态下每个间隔体力的自然恢复量（站立缓慢回升）。
# 数值小于睡眠恢复量，体现"睡觉回体力更快"。
ENERGY_REGEN_PER_TICK = 1

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

# 设置窗口尺寸（靠右侧停靠，垂直居中）。高度容纳「保存并退出」按钮行
SETTINGS_WINDOW_WIDTH = 280
SETTINGS_WINDOW_HEIGHT = 656

# 皮肤选择窗口尺寸（靠右侧停靠，垂直居中；缩略图预览选择 + 缺失状态提示）
SKIN_WINDOW_WIDTH = 300
SKIN_WINDOW_HEIGHT = 400

# AI 情绪联动触发的临时动画播放时长（秒）
AI_EFFECT_ANIMATION_DURATION = 2.0

# ----- 休息提醒配置 -----
# 默认每隔多少分钟弹出一次"休息提醒"聊天气泡（用户可在设置窗口调整）
REST_REMINDER_INTERVAL_MINUTES = 30

# 休息提醒间隔可调范围与步长（分钟），用于设置窗口的 [-]/[+] 调节
REMINDER_INTERVAL_MIN = 5
REMINDER_INTERVAL_MAX = 180
REMINDER_INTERVAL_STEP = 5

# 提醒气泡在宠物头顶的显示时长（秒）
REST_REMINDER_BUBBLE_DURATION = 8.0

# 休息提醒文案候选（每次随机选取一条）
REST_REMINDER_MESSAGES = [
    "主人，坐了好一会儿啦，起来活动一下、喝口水吧~",
    "盯着屏幕好久咯，让眼睛看看远处休息 20 秒吧！",
    "记得按时休息哦，伸个懒腰，放松一下肩颈~",
    "工作再忙也要照顾好自己，陪我走两步好不好？",
]

# ----- 电子围栏配置 -----
# 围栏取点（全屏遮罩鼠标点两个对角）各阶段在宠物头顶弹出的提示气泡文案
FENCE_MESSAGES = {
    "start": "在桌面点两个对角，框出我的活动范围吧~",
    "first_corner": "点好第一个角啦~ 再点一个对角框出围栏吧！",
    "set": "围栏设好了，窗口变成这块区域，我会在里面玩耍~",
    "cleared": "围栏已清除，窗口恢复，我又能到处溜达啦！",
    "cancelled": "取消围栏选择~",
    "too_small": "这块地方太小啦，重新框个大一点的吧~",
}

# 围栏最小边长（像素）：两角太近（如误双击）会得到极小围栏，
# 小于此值视为无效，拒绝设定/忽略存档中的退化围栏，避免窗口缩成一个点。
FENCE_MIN_SIZE = 150

# 全屏遮罩（围栏取点 / 无围栏喂食放置）的背景色与整窗统一透明度。
# 取点/放置时窗口改用 LWA_ALPHA（统一半透明）而非颜色键透明——
# 颜色键透明会让空白处的点击穿透到桌面而无法取点；统一 alpha 下整屏都可点，
# 桌面以该背景色淡淡压暗，提示"正处于全屏取点/放置态"。
OVERLAY_BG_COLOR = (24, 26, 38)
OVERLAY_ALPHA = 96

# 围栏边框颜色与线宽（只画边框，内部保持透明色键以透出桌面）。
# 颜色须与 TRANSPARENT_COLOR_KEY 区分，避免边框被当作透明色抠掉。
FENCE_BORDER_COLOR = (80, 200, 120)
FENCE_BORDER_WIDTH = 3

# ----- 喂食放置配置 -----
# 食物图标（程序化苹果）的半径（像素）
FOOD_ICON_RADIUS = 14
# 同时可摆放的食物上限：达到后再左键放置会被忽略并气泡提示
FOOD_MAX_COUNT = 10

# ----- 音效 -----
# 互动音效总开关（可在设置窗口切换，存 user_config.sound_enabled）；音量 0~1
SOUND_ENABLED = True
SOUND_VOLUME = 0.45

# ----- 语音朗读（TTS）-----
# 朗读宠物主动发言/聊天回复的总开关（默认关，需用户主动开启；存 user_config.tts_enabled）。
# 依赖可选库 pyttsx3，未安装则即便开启也自动静默降级。
TTS_ENABLED = False


# ----- AI 主动互动（宠物基于状态/记忆/时间主动冒泡说话）-----
# 是否默认开启主动互动（可在设置窗口开关，存 user_config.proactive_enabled）
PROACTIVE_CHAT_ENABLED = True
# 每隔多少分钟尝试主动说一句（满足条件时后台请求 LLM；不满足则跳过）
PROACTIVE_CHAT_INTERVAL_MINUTES = 10
# 设置窗口里主动互动间隔的调节范围与步长（分钟）
PROACTIVE_INTERVAL_MIN = 2
PROACTIVE_INTERVAL_MAX = 60
PROACTIVE_INTERVAL_STEP = 2
# 主动气泡显示时长（秒）
PROACTIVE_BUBBLE_DURATION = 6.0
# AI 不可用（无 Key / 离线）时，按宠物当前动画状态随机选一句，保证离线也能主动互动。
# 键对应 current_animation；未命中用 default。
PROACTIVE_OFFLINE_MESSAGES = {
    "hungry": ["肚子有点饿了呢，有好吃的吗~", "闻到食物的味道了…我饿啦！"],
    "tired": ["有点困了…想打个盹儿。", "今天好累呀，陪我歇会儿好不好~"],
    "sad": ["有点小情绪…抱抱我嘛。", "感觉闷闷的，陪陪我好吗？"],
    "happy": ["今天心情超好哒！", "和你在一起好开心呀~"],
    "excited": ["好有精神呀，一起玩嘛！", "嘿嘿，今天超有活力！"],
    "default": ["在忙什么呢？我在看着你哦~", "要不要摸摸我呀？", "今天也要元气满满哦！"],
}


def ensure_user_data() -> None:
    """打包(onefile)首次运行时，把可写数据从只读资源播种到 exe 旁目录。

    开发态 APP_DIR == RESOURCE_DIR，无需播种直接返回。打包态：
    * 建好 config / data / logs 目录；
    * ai_config.json 不存在则从模板（空 Key）拷贝，保证有合理默认且不泄露 Key；
    * 内置皮肤目录不存在则整体拷过来，供 SkinManager 读取与用户新建皮肤共用。
    其余可写文件（user_config / skin_config / 存档等）由 save_json 写时自建，无需预置。
    由 main.py 在创建 Game 之前调用。
    """
    if not _FROZEN:
        return

    os.makedirs(os.path.join(APP_DIR, "config"), exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

    if not os.path.exists(AI_CONFIG_FILE) and os.path.exists(AI_CONFIG_TEMPLATE_FILE):
        shutil.copyfile(AI_CONFIG_TEMPLATE_FILE, AI_CONFIG_FILE)

    if not os.path.isdir(SKINS_DIR) and os.path.isdir(BUILTIN_SKINS_DIR):
        shutil.copytree(BUILTIN_SKINS_DIR, SKINS_DIR)
