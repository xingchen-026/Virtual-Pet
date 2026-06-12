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
│   └── feedback.py            # 交互提示 UI（自动消失的提示文字）
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
│   └── pet_data.json         # 宠物数据存储
│
├── tools/
│   └── generate_placeholder_animations.py  # 占位动画素材生成脚本
│
├── utils/
│   └── helper.py             # 工具函数
│
└── README.md
```

## 运行方式

1. 安装依赖：

   ```
   pip install pygame
   ```

2. 运行程序：

   ```
   python main.py
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

## 后续开发计划

- 桌宠透明窗口与窗口置顶显示
- 喂食 / 玩耍的图形化交互入口（按钮、拖放道具等）
- 可扩展的宠物养成系统（BathAction / SleepAction / GiftAction 等）
- 接入正式美术资源 / Lottie 动画，替换占位动画帧
- 为 SAD 等新状态补充专属动画资源
