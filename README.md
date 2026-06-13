# VirtualPet 桌面虚拟宠物

## 项目介绍

VirtualPet 是一个基于 Python + Pygame 开发的桌面虚拟宠物应用。
最终目标是实现一个具备多状态动画切换、桌面自由移动、鼠标拖拽互动、
饥饿 / 心情 / 体力系统、喂食与玩耍交互、数据保存与恢复、
可扩展养成系统的桌宠程序。

## 技术栈

- Python 3.12
- Pygame 2.6
- JSON（数据持久化）

## 项目结构

```
VirtualPet/
│
├── main.py                  # 程序入口
│
├── config/
│   └── settings.py           # 全局配置（窗口、宠物默认值、动画配置）
│
├── core/
│   ├── pet.py                # 宠物核心类
│   ├── game.py               # 游戏主循环
│   ├── animation.py          # 动画状态枚举与播放控制
│   ├── sprite.py             # 宠物 Sprite 渲染
│   ├── lottie_loader.py       # Lottie 动画加载接口（预留）
│   ├── resource.py           # 资源管理（图片 / 动画缓存）
│   ├── pet_state.py           # 宠物行为状态枚举
│   ├── state_machine.py       # 状态机：根据属性计算状态
│   ├── behavior.py            # 行为逻辑：属性衰减、状态/动画同步、临时动画
│   ├── event.py               # 交互事件类型与数据结构
│   ├── interaction.py         # 用户交互管理（点击 / 拖拽 / 按键）
│   ├── action.py              # 宠物行为动作与 BehaviorManager
│   ├── food.py                # 食物数据结构（喂食系统）
│   ├── feedback.py            # 交互提示 UI（自动消失的提示文字）
│   ├── desktop.py             # 桌面窗口能力（透明 / 置顶 / 隐藏 / 移动）
│   └── ai/
│       ├── llm_client.py       # LLM 接口封装（OpenAI / DeepSeek / 本地）
│       ├── personality.py      # 宠物人格系统
│       ├── memory.py           # 宠物记忆系统（短期对话 + 长期事件）
│       ├── prompt_manager.py   # Prompt 拼接（System + Pet State + Memory + User）
│       ├── emotion_analyzer.py # 文本情绪分析 -> 属性变化 / 建议动画
│       └── ai_service.py       # AI 服务入口（Pet -> AIService -> LLM）
│
├── ui/
│   ├── theme.py             # UI 共享配色常量
│   ├── chat_window.py        # AI 对话窗口（输入框 / 消息历史 / 滚动）
│   ├── message_box.py        # 聊天消息气泡渲染
│   ├── stats_panel.py        # 右键数值信息与功能按钮面板
│   └── settings_window.py    # 设置窗口（宠物大小 / AI 配置）
│
├── tests/                   # pytest 回归测试（Pet/情绪/记忆/精灵图切分）
│
├── assets/
│   ├── images/               # 图片资源
│   ├── animations/           # 动画资源
│   │   ├── idle/              # 待机动画帧
│   │   ├── happy/             # 开心动画帧
│   │   ├── hungry/            # 饥饿动画帧
│   │   ├── tired/             # 疲劳动画帧
│   │   ├── interact/          # 触摸反馈动画帧
│   │   ├── excited/           # 兴奋动画帧
│   │   ├── eating/            # 进食动画帧
│   │   └── playing/           # 玩耍动画帧
│   └── sounds/               # 音频资源
│
├── data/
│   ├── pet_data.json         # 宠物数据存储
│   ├── personality.json      # 宠物人格数据（名称 + 人格参数）
│   └── memory.json           # 宠物记忆数据（短期对话 + 长期事件）
│
├── tools/
│   ├── generate_placeholder_animations.py  # 占位动画素材生成脚本
│   └── import_skin.py        # 皮肤导入工具（精灵图切分/去背景）
│
├── utils/
│   ├── helper.py             # 工具函数（JSON 读写等）
│   ├── exception.py          # 自定义异常与错误日志
│   ├── behavior_logger.py    # 自主行为日志
│   ├── spritesheet.py        # 精灵图切分（背景检测/去除/帧归一化）
│   └── tray.py               # 系统托盘图标
│
└── README.md
```

## 运行方式

1. 安装依赖：

   ```
   pip install -r requirements.txt
   ```

   运行时依赖 pygame / pywin32 / pystray / Pillow；
   皮肤导入工具另需 numpy / scipy。

2. （可选）配置 AI 对话功能：

   - 编辑 `config/ai_config.json`，设置 `provider`（`openai` / `deepseek` / `local`）、
     `model`、`api_base` 等参数。
   - 设置对应的 API Key 环境变量（默认 `DEEPSEEK_API_KEY`，对应
     `ai_config.json` 中的 `api_key_env`）。
   - 未配置或网络不可用时，AI 对话自动降级为离线提示，桌宠核心功能不受影响。

3. 运行程序：

   ```
   python main.py
   ```

   - 按 `C` 打开/关闭 AI 对话窗口，输入文字后按 `Enter` 发送，`Esc` 关闭窗口。
   - 右键宠物弹出状态面板：查看数值信息（喂食/玩耍后的属性变化以 +xx
     形式显示在对应属性后），点击 `喂食` / `玩耍` / `聊天` / `设置` 按钮交互。
   - 设置窗口可调节宠物大小（0.5x~2.0x）并配置 AI 服务商 / 模型 / API Key
     （保存后写入 `config/user_config.json` 与 `config/ai_config.json`，即时生效）。
   - 拖拽宠物可移动位置；宠物自主漫游时窗口自动跟随（漫游范围为整个屏幕）。

4. （可选）导入自定义皮肤：

   准备一张精灵图（每行一个动作的多帧动画，背景为纯色即可，不要求透明），运行：

   ```
   python tools/import_skin.py 精灵图.png --name 皮肤名 --states idle,happy,walk
   ```

   - `--states` 按行从上到下指定每行对应的动画状态（可用状态见
     `config/settings.py` 的 `ANIMATION_FOLDERS`）。
   - 每个单元格是独立姿势/表情的素材（如情绪表情图）使用网格模式：

     ```
     python tools/import_skin.py 表情图.png --name 皮肤名 --grid 3x6 \
         --states excited,look_around,tired,skip,...,hungry,hungry,eating
     ```

     `--states` 按行优先顺序逐格指定状态（`skip` 跳过该格；同一状态
     出现多次时按顺序组成多帧动画），网格模式会自动剔除相邻单元格
     精灵越界产生的贴边碎片。
   - 工具自动检测背景色并去除背景、切分帧、统一尺寸后写入
     `assets/skins/<皮肤名>/`，并设为当前皮肤（重启桌宠生效）；
     向同名皮肤多次导入时按状态合并（本次涉及的状态清空重写）。
   - 皮肤未覆盖的动画状态自动回退到内置动画；切回默认皮肤可将
     `config/skin_config.json` 的 `active_skin` 改为 `"default"`。
   - 背景与主体颜色接近导致切分/去背景异常时，用 `--tolerance` 调节阈值。

## 运行测试

核心逻辑（Pet 属性钳制、情绪分析、记忆系统、精灵图切分）的回归测试位于
`tests/`，无需图形界面即可运行：

```
python -m pytest tests/ -q
```

## 当前完成阶段

**第一阶段：基础工程搭建**

- 完成项目目录结构初始化
- 搭建 Pygame 基础运行环境（窗口创建、主循环、正常退出）
- 创建基础 Pet 宠物类（name / age / hunger / mood / energy / position）
- 添加全局配置模块，统一管理窗口与宠物默认属性
- 创建 JSON 数据文件及读写接口（utils/helper.py 中的 load_json / save_json）

**第二阶段：宠物动画系统**

- 新增 `AnimationState` 动画状态枚举（idle / happy / hungry / tired）
- 新增 `Animation` / `AnimationManager`，支持帧切换、循环播放、播放速度、状态切换
- 新增 `PetSprite`（继承 `pygame.sprite.Sprite`），关联 Pet 与动画管理器，负责更新与绘制
- `ResourceManager` 增加 `load_animation()`，缓存动画帧序列，避免重复加载
- `Pet` 增加 `current_animation` 属性与 `change_animation()` 方法
- `Game` 主循环中创建 Pet、PetSprite、加载默认动画并渲染到窗口
- 新增 `core/lottie_loader.py`：预留 Lottie 动画加载接口，当前环境未安装
  `python-lottie` 时自动回退为图片帧动画方案
- 新增 `tools/generate_placeholder_animations.py`：在正式美术资源到位前，
  生成简单的占位动画帧，写入 `assets/animations/<state>/`

**第三阶段：宠物状态机系统**

- 新增 `PetState` 状态枚举（IDLE / HAPPY / HUNGRY / TIRED / SAD，SAD 预留）
- 新增 `core/state_machine.py` 中的 `StateMachine`：根据 hunger / mood / energy
  独立计算当前状态（饥饿 > 疲劳 > 开心 > 默认），不依赖 Pet 或动画系统
- `Pet` 新增 `current_state` 属性，以及 `increase_/decrease_hunger/mood/energy()`
  相对修改接口（自动限制在 0~100）
- 新增 `core/behavior.py` 中的 `PetBehavior`：基于计时器（默认 5 秒一次）
  使饥饿 / 体力衰减、心情按状态衰减，并在状态变化时调用
  `pet.change_animation()` 同步动画（状态不变时不重复切换）
- `Game` 主循环集成 `PetBehavior`，并在窗口左上角绘制调试信息
  （Name / State / Hunger / Mood / Energy）
- `data/pet_data.json` 增加 `state` 字段；游戏启动时自动读取存档，
  关闭窗口时自动保存当前属性与状态

**第四阶段：交互系统**

- 新增 `core/event.py`：`InteractionEventType` 枚举（CLICK / EXCITED / DRAG_START /
  DRAG_MOVE / DRAG_END / FEED / PLAY）与 `InteractionEvent` 数据结构
- 新增 `core/interaction.py`：`InteractionManager` 监听鼠标按下/移动/释放与键盘事件，
  识别点击、拖拽（保留抓取偏移量，宠物跟随鼠标且不产生位置跳动）与连续点击；
  `ClickCounter` 记录点击时间戳，短时间内连续点击触发 excited
- 新增 `core/food.py`：`Food` 数据类（name / hunger_restore / mood_restore）及默认食物
- 新增 `core/action.py`：`ClickAction` / `ExcitedAction` / `TouchAction` /
  `FeedAction` / `PlayAction` 等行为，均只通过 Pet 已有的
  `increase_/decrease_*` 接口修改属性；`BehaviorManager` 统一分发
  Click / Excited / Drag / Feed / Play 事件，遵循
  `事件 -> 行为 -> 属性变化` 流程，并记录 `last_action` / `interaction_count`
- 新增 `core/feedback.py`：`FeedbackOverlay` 管理屏幕提示文字的显示与自动消失
- `core/animation.py` 的 `AnimationState` 新增 `INTERACT` / `EXCITED` /
  `EATING` / `PLAYING`，并在 `tools/generate_placeholder_animations.py`
  中补充对应占位动画帧
- `core/behavior.py` 的 `PetBehavior` 新增 `trigger_temporary_animation()`：
  播放交互触发的临时动画，结束后自动恢复为状态对应动画，
  且临时动画播放期间不会被属性衰减引发的状态切换打断
- `Pet` 新增 `last_action` / `interaction_count` 字段及 `record_interaction()`，
  并写入 `to_dict()` / `from_dict()`
- `Game` 集成 `InteractionManager` 与 `BehaviorManager`：
  鼠标拖拽移动宠物、点击/连续点击/喂食（F 键）/玩耍（P 键）
  均通过事件系统驱动属性变化、临时动画与提示文字
- 数据流：`User Input -> InteractionManager -> BehaviorManager ->
  Pet Attribute -> StateMachine -> AnimationManager`

**第五阶段：自主行为系统**

- 新增 `core/autonomous.py`：`AutonomousManager` 根据 Pet 属性与时间表自主决策
  行为（漫游 / 休息 / 玩耍等），与用户交互（拖拽）互斥，避免冲突
- 引入昼夜节奏（`Schedule`）与情绪（`Emotion`），影响行为决策权重
- `utils/behavior_logger.py`：记录自主行为日志，便于调试与回放
- 数据流：`Pet State -> AutonomousManager -> Behavior Decision -> Action Execute
  -> Animation Update`

**第六阶段：桌面应用能力**

- 新增 `core/desktop.py`：`DesktopManager` 封装窗口透明色键 / 置顶 / 隐藏 /
  显示 / 移动等 OS 能力（Windows），不支持的平台自动降级
- 窗口改为 `pygame.NOFRAME` 无边框窗口，配合透明色键实现"只显示宠物本体"
  的桌面悬浮效果；拖拽时整窗随鼠标移动
- 新增 `utils/tray.py`：`TrayIcon` 系统托盘图标（显示/隐藏/保存/退出），
  在独立线程运行，动作通过队列回传主循环处理
- 新增 `utils/exception.py`：统一异常类型（`ResourceLoadError` /
  `AnimationLoadError` / `SaveDataError` / `DesktopWindowError` 等）与
  `log_exception()`，错误写入 `logs/error.log`
- 后台隐藏时主循环降帧（`BACKGROUND_FPS`）以降低 CPU 占用

**第七阶段：AI 对话 / 人格 / 记忆系统**

- 新增 `core/ai/`：`LLMClient`（统一 `chat()` 接口，支持 OpenAI / DeepSeek /
  本地，供应商与参数全部来自 `config/ai_config.json`，不硬编码）、
  `PersonalityManager`（人格参数 `data/personality.json`）、
  `MemoryManager`（短期对话 + 长期事件，`data/memory.json`）、
  `PromptManager`（拼接 System Prompt + Pet State + Memory + User Message）、
  `EmotionAnalyzer`（关键词规则 + AI 回复情绪标签 `[情绪:xxx]`，输出
  mood/energy 变化与建议动画）、`AIService`（唯一对外入口：
  `Pet -> AIService -> LLM`）
- 新增 `ui/chat_window.py` + `ui/message_box.py`：按 `C` 打开/关闭的对话窗口
  （输入框 / 消息气泡历史 / 鼠标滚轮滚动）
- `Game` 集成：聊天消息在后台线程调用 `AIService.chat()`，结果经
  `queue.Queue` 回传主循环写回对话窗口，避免阻塞动画与置顶维护；
  交互事件（喂食等）通过 `AIService.notify_interaction()` 写入长期记忆
- 情绪联动示例："你好可爱" -> `mood +10`；"你累了吗？" -> `energy -5` 并
  播放 `sleep` 临时动画
- 新增 `utils/exception.AIServiceError`：LLM 请求失败 / 网络异常 / 返回
  格式错误统一捕获，记录日志后降级为离线回复，桌宠核心功能不受影响

## 后续开发计划

- 喂食 / 玩耍的图形化交互入口（按钮、拖放道具等）
- 可扩展的宠物养成系统（BathAction / SleepAction / GiftAction 等）
- 接入正式美术资源 / Lottie 动画，替换占位动画帧
- 为 SAD 等新状态补充专属动画资源
- AI 情绪标签体系扩展、长期记忆摘要与遗忘策略
