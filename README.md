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
│   ├── feeding.py             # 喂食放置状态机（放置模式 / 已放下食物）
│   ├── fence.py               # 电子围栏取点状态机 + 弹窗统一定位布局
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
│   ├── theme.py             # UI 共享配色常量 + 圆角面板工厂 make_panel()
│   ├── chat_window.py        # AI 对话窗口（输入框 / 消息历史 / 滚动）
│   ├── message_box.py        # 聊天消息气泡渲染
│   ├── speech_bubble.py      # 宠物头顶临时提示气泡（休息提醒 / AI 主动互动）
│   ├── stats_panel.py        # 右键数值信息与功能按钮面板
│   ├── food_icon.py          # 程序化食物图标（放置模式跟随鼠标/已放下渲染）
│   ├── settings_window.py    # 设置窗口（名称/性格/语气/大小/提醒间隔/AI 配置/保存退出）
│   ├── skin_window.py        # 皮肤选择窗口（缩略图预览选择）
│   └── skin_creator.py       # 创建皮肤窗口（精灵图/按状态 + 镜像/抠图/速度）
│
├── tests/                   # pytest 回归测试（Pet/情绪/记忆/精灵图切分/计时器/AIService/UIManager）
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
│   ├── timer.py              # IntervalTimer 周期计时器（存档/置顶/休息提醒）
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
   - 右键宠物弹出状态面板：查看数值信息（养成动作后的属性变化以 +xx
     形式显示在对应属性后），点击 `玩耍` / `洗澡` / `睡觉` / `礼物`
     养成按钮与 `围栏` / `皮肤` / `聊天` / `设置` 按钮交互。
   - **喂食（放置模式）**：点 `喂食` 后食物图标跟随鼠标，**左键放下**食物（最多 10 份）、**右键退出**；
     放下后宠物自主走过去逐个吃掉（恢复饥饿/心情）。无围栏时整屏铺成半透明放置层、可在桌面任意处放置；
     设了围栏时只能在围栏内放置。
   - **电子围栏**：点 `围栏` 后整屏进入半透明取点态，**鼠标点两个对角**框出矩形（拖动有预览框、
     点太近会被拒绝、右键/Esc 取消）；设定后**游戏窗口扩展为围栏大小并固定**，宠物只在该区域内漫游；
     已有围栏时再点 `围栏` 清除、窗口恢复跟随。围栏存盘，重启自动恢复为围栏窗口。
     设围栏后所有弹窗（设置/状态/聊天/皮肤）统一锚定到围栏上边一侧，避免鼠标来回移动。
   - **设置窗口「保存并退出」**：保存全部设置与游戏数据后关闭进程。
   - 右键面板「皮肤」按钮打开皮肤选择窗口，点击缩略图预览即时切换皮肤（无需重启）。
   - 皮肤选择窗口显示每个皮肤的缺失状态；非默认皮肤可点「补充动画」按状态补齐缺失动画
     （合并保留已有状态）。右下角「创建皮肤」打开制作窗口，支持两种方式：①精灵图——
     可添加多张精灵图（同一皮肤可由不同资源拼成），每张切成逐帧；**先点中文状态标签、
     再左键点帧贴上该状态（右键点帧取消）**，同一状态的帧按顺序成为该动画，每张图可单独
     「翻转」/抠图；②按状态分别上传图片。一键抠图（自动取背景色 / 选色 / 点源图取色）；
     右侧实时播放可**指定播放哪个状态**，开「镜像预览」时先播朝右再播朝左；预览下方用
     **拖拉条 + 数值框**调节当前状态的播放速度。生成后即时启用。
   - 设置窗口可修改宠物名称、分别自定义性格与语气、调节宠物大小（0.5x~2.0x）、设置
     休息提醒间隔、**开关 AI 主动互动并调节其间隔**（分钟，`-`/`+` 调节），并配置 AI 服务商
     （下拉选择）/ 接口地址（自定义 base_url）/ 模型 / API Key（保存后即时生效）。宠物名称在
     数值面板与聊天窗口统一显示。所有界面窗口/面板均为圆角风格。
   - 数值面板的「时间」一行显示系统真实时间（年-月-日 时:分:秒）。
   - 休息提醒：默认每 30 分钟在宠物头顶弹出一个圆角提示气泡，提醒主人起身活动/护眼/
     喝水（文案随机，气泡数秒后自动消失）；间隔可在设置窗口调整并持久化。
   - **AI 主动互动**：默认每 10 分钟，宠物结合自身状态/记忆/时段在头顶气泡主动说一句
     （非被动等聊天）；AI 不可用时用状态化离线文案降级；睡觉/聊天窗口打开/隐藏到托盘时跳过。
     可在设置窗口开关与调节间隔。
   - **互动音效**：喂食/玩耍/洗澡/送礼/点击等程序化合成的短音效（无需素材文件，离线自包含），
     可在设置窗口开关；音频设备不可用时自动静音。
   - **语音朗读（可选）**：开启后用 TTS（pyttsx3，离线）朗读主动发言与聊天回复；默认关，
     未安装 pyttsx3 时自动降级。可在设置窗口开关。
   - **成长 / 等级**：喂食/玩耍/洗澡/送礼等正向互动积累经验，满则升级（升级有庆祝动画+音效+气泡），
     等级与经验显示在右键数值面板，并随存档保留。
   - **自定义皮肤支持动图**：创建皮肤时「按状态上传」可直接选一张 GIF/APNG，自动展开为该状态的多帧动画。
   - **AI 绘图生成皮肤**：右键面板「AI皮肤」→ 填入你自己的 API Key（默认接入 Agnes AI，OpenAI 兼容，
     可改接口地址）→ 选模型/尺寸、输入提示词 → 生成预览 → 「应用为皮肤」自动抠图并启用。
     **Key 仅保存在本地、不入库**；窗口含版权声明，提示词会追加「原创/无品牌角色」等约束以规避侵权。
   - 体力机制：仅在宠物移动（漫游/奔跑）时缓慢消耗，静止时缓慢回升，睡觉时回升更快；
     宠物会在疲倦时自主进入睡眠状态恢复体力，回满后自动醒来。
   - 聊天历史持久化：可见对话保存在 `data/chat_history.json`，重启后回填到聊天窗口。
     AI 记忆分两层：短期记忆保留最近 3 轮对话，长期记忆由 LLM 每 3 轮总结主人习惯/偏好。
   - AI 对话内置内容审查（`core/ai/moderation.py` + `config/moderation.json`）：
     过滤脏话/色情/暴力血腥/政治敏感等违规内容，命中时温和岔开。
   - 拖拽宠物可移动位置；宠物自主漫游时窗口自动跟随（漫游范围为整个虚拟桌面，支持多显示器跨屏）。
     已设 DPI 感知（Per-Monitor v2），在缩放显示器上窗口与取点坐标准确。

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
   - 皮肤未覆盖的动画状态自动回退到内置动画；切换皮肤（含切回默认）在右键面板
     「皮肤」窗口点击缩略图选择，即时生效，无需重启或手改配置。
   - 背景与主体颜色接近导致切分/去背景异常时，用 `--tolerance` 调节阈值。

## 打包为单文件 exe（Windows）

把桌宠打包成一个 `VirtualPet.exe`，非开发者双击即可运行（约 38 MB）：

```
pip install pyinstaller        # 仅打包需要，非运行期依赖
python tools/build_exe.py      # 产物：dist/VirtualPet.exe
```

- 打包采用 PyInstaller **onefile**：只读资源（动画/图片/声音、内置皮肤、行为/桌面/审查
  配置、AI 配置模板）打进 exe；运行期可写数据（存档、日志、`user_config`/`skin_config`、
  用户新建的皮肤）在**首次运行时自动生成在 exe 同级目录**（`ensure_user_data`）。
- **绝不打包真实 API Key**：仅打包 `config/ai_config.template.json`（空 Key），首次运行据此
  生成 `config/ai_config.json`；用户在设置窗口填入自己的 Key。
- exe 图标由 `tools/make_icon.py` 取内置皮肤的一帧自动生成。
- 体积控制：在干净虚拟环境（仅 `pygame / pywin32 / pystray / Pillow / numpy / pyinstaller`）
  里打包；`scipy`（仅皮肤网格切分的可选碎片剔除用到，缺失时自动降级）等大库已排除。
  若用含大量科学计算库的全局环境打包，exe 会异常臃肿——务必用纯净环境。

## 运行测试

核心逻辑（Pet 属性钳制、情绪分析、记忆系统、精灵图切分、皮肤构建、窗口坐标等）
的回归测试位于 `tests/`，无需图形界面即可运行：

```
python -m pytest tests/ -q
```

每次推送到 `main` 或提 PR 时，GitHub Actions（`.github/workflows/tests.yml`）会在
Linux + Python 3.12 上自动运行全部测试。CI 仅装测试所需依赖
（pygame / Pillow / numpy / scipy / pytest），不装 Windows 专用的 pywin32 / pystray。

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

**第八阶段：体力机制重做 / 休息提醒 / 圆角界面**

- 体力系统重做（`config/settings.py` + `core/behavior.py`）：体力仅在宠物移动
  （漫游/奔跑）时按 `ENERGY_DECAY_PER_TICK` 缓慢消耗，静止（非睡眠）时按
  `ENERGY_REGEN_PER_TICK` 缓慢回升；`Game` 每帧把"是否有移动目标"作为 `moving`
  传入 `PetBehavior.update()`
- 自主睡眠恢复体力（`core/autonomous.py`）：自主行为 `SLEEP` 不再只是临时动画——
  体力未满时进入 `PetBehavior` 的持续睡眠模式较快回体力（回满自动醒来），
  体力已满（如夜晚）时仅小憩一会儿，避免反复入睡/唤醒抖动
- 修复睡眠回满后"闪现"到其它位置：主循环钳制单帧 `dt`（`settings.MAX_FRAME_DT`），
  进程被系统挂起/降频后不再因超大 `dt` 导致移动一步跳到目标
- 休息提醒（`ui/speech_bubble.py` + `ui/ui_manager.py`）：默认每 30 分钟在宠物头顶
  弹出圆角提示气泡（文案随机、数秒后消失），间隔可在设置窗口调节并持久化到
  `config/user_config.json`
- 数值面板「时间」改为系统真实时间（不再显示模拟昼夜时刻）
- 全部界面窗口/面板改为圆角：`ui/theme.py` 新增 `make_panel()`（SRCALPHA + 圆角
  背景/边框），数值面板/聊天/设置/皮肤选择/创建皮肤窗口统一改用

**工程化收尾（计时器聚合 + 单测）**

- 新增 `utils/timer.py` 的 `IntervalTimer`，聚合自动存档 / 窗口置顶维持 / 休息提醒
  三处重复的计时逻辑；`Game._save_pet_data()` 统一存档出口
- 补 `tests/`：`test_timer` / `test_ai_service`（FakeLLM + tmp 路径隔离）/
  `test_ui_manager`（font=None + tmp CHAT_HISTORY 免渲染免污染）

**第九阶段：电子围栏 / 喂食放置 / 保存退出**

- 电子围栏（`core/fence.py` + `core/movement.py`）：右键面板 `围栏` 按钮拖窗两点定角
  （点一次记宠物当前位置为一角、拖到对角再点定矩形，已有围栏时再点清除）；
  `MovementController.set_fence/clear_fence` 把随机漫游夹到围栏内；围栏存
  `config/user_config.json`，重启保留
- 喂食放置模式（`core/feeding.py` + `ui/food_icon.py` + `core/autonomous.py`）：点 `喂食`
  进入放置模式，程序化苹果图标跟随鼠标，左键放下、右键取消、移出围栏自动取消；
  `AutonomousManager.food_target` 以最高优先级寻路，到达触发 `on_food_reached` 复用既有
  喂食管线（FeedAction + eating 动画 + 属性增量 + 记忆联动）
- 设置窗口「保存并退出」按钮：应用全部设置后请求退出，退出时统一存档宠物数据与偏好
- 设围栏后弹窗统一定位（`fence.popup_topleft` + `UIManager._anchored_rect` +
  `StatsPanel.draw(force_topleft=)`）：设置/状态/聊天/皮肤以围栏上边两角为基点、
  选能完整显示的一侧整体展示，避免鼠标来回移动
- `tests/`：`test_fence` / `test_feeding` / `test_movement` / `test_autonomous_food`

**第十阶段：围栏窗口化 / 鼠标取点 / 食物上限**

- 食物上限（`FOOD_MAX_COUNT=10`）：达到上限后放置被忽略并气泡提示
- 围栏取点改为全屏遮罩鼠标点两个对角（不再拖宠物）：`FenceController.clear/pending`，
  橡皮筋预览 + 整屏边框提示；过小围栏（误双击）被拒绝、存档退化围栏启动忽略
- 设围栏后**游戏窗口扩展为围栏矩形并固定**，宠物在内漫游：窗口三态（跟随 / 全屏遮罩 /
  围栏固定），`WindowController.follow`/`set_geometry`，`DesktopManager.reapply_after_resize`
- 修复全屏遮罩空白处点击穿透（颜色键透明特性）：取点/放置时改用统一半透明 `LWA_ALPHA`
- `tests/`：`test_feeding` / `test_fence` / `test_window_controller`

**第十一阶段：打包为单文件 exe**

- `config/settings.py` 拆只读资源（`RESOURCE_DIR`/`_MEIPASS`）与可写数据（`APP_DIR`/exe 旁），
  `ensure_user_data()` 首次运行播种；`tools/build_exe.py` + `tools/make_icon.py`
- 绝不打包真实 API Key（仅打包空 Key 模板）；干净 venv 打出约 38MB exe，随 GitHub Release 分发

**第十二阶段：多屏 / DPI 健壮性 + AI 主动互动**

- DPI 感知（Per-Monitor v2，`enable_dpi_awareness`）统一 pygame 与 Win32 坐标，修缩放/混合 DPI 错位
- 虚拟桌面（`get_virtual_screen`）+ `MovementController` 漫游原点（`origin`）：取点遮罩覆盖所有屏、
  宠物可跨屏漫游、围栏可框在任意屏
- AI 主动互动：宠物按状态/记忆/时段定时在头顶气泡主动说话（`AIService.proactive_message`，
  后台线程 + 离线状态化文案降级 + 睡觉/窗口打开等跳过条件），设置窗口可开关与调间隔
- `tests/`：`test_movement`（origin/副屏围栏）/ `test_ai_service`（主动发言/离线/违规/时段）

**第十三阶段：美术升级 / 音效 / TTS / 成长系统**

- 美术升级：`skin_builder.load_image_frames` 支持 GIF/APNG 动图作为某状态的多帧来源
  （`grouped_from_state_images` 自动展开），文件选择器加 `*.gif`
- 互动音效：`core/sound.py` 程序化合成短音效（numpy），喂食/玩耍/洗澡/送礼/点击各异，设置可开关
- 语音朗读：`core/tts.py` 可选 pyttsx3 朗读主动发言/聊天回复（默认关、缺库降级），设置可开关
- 成长/等级：`Pet.level/exp` + `add_exp`，正向互动积累经验、升级庆祝，数值面板显示并持久化
- `tests/`：`test_skin_builder`（动图展开）/ `test_sound` / `test_tts` / `test_pet`（等级）

**第十四阶段：等级解锁称号 / 记忆遗忘 / AI 绘图生成皮肤**

- 等级解锁：`settings.LEVEL_TITLES` 成长阶段称号，面板显示、注入 AI 人格、跨阶段升级提示
- 记忆遗忘：`MemoryManager` 淡忘超 30 天的长期记忆、保护最新 10 条
- AI 绘图：`core/image_gen.py`（OpenAI 兼容文生图客户端）+ `ui/image_gen_window.py`（自带 Key/选模型/
  提示词/预览/应用为皮肤）；图片经抠图管线生成皮肤；Key 仅本地保存，含防侵权声明与提示词约束
- `tests/`：`test_pet`（称号）/ `test_memory`（遗忘）/ `test_image_gen`（客户端打桩）

## 后续开发计划

- **接入正式美术素材**：用正式美术替换占位帧（GIF/APNG 导入已支持；Lottie 渲染待评估）
- AI 情绪标签体系扩展、长期记忆遗忘策略
- 成长系统扩展：等级解锁皮肤 / 称号等长线玩法

## 已实现的养成与交互

- 养成动作（右键面板按钮）：喂食 / 玩耍 / 洗澡 / 睡觉 / 礼物，
  通过「事件 -> BehaviorManager -> Action -> 属性变化 + 临时动画」统一管线。
  扩展新动作只需在 `core/event.py` 增加事件类型、`core/action.py` 增加
  Action 子类并注册、`ui/stats_panel.py` 增加按钮，面板路由自动生效。
