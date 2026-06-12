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
│   └── resource.py           # 资源管理（图片 / 动画缓存）
│
├── assets/
│   ├── images/               # 图片资源
│   ├── animations/           # 动画资源
│   │   ├── idle/              # 待机动画帧
│   │   ├── happy/             # 开心动画帧
│   │   ├── hungry/            # 饥饿动画帧
│   │   └── tired/             # 疲劳动画帧
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

## 后续开发计划

- 桌宠透明窗口与窗口置顶显示
- 鼠标拖拽互动
- 饥饿 / 心情 / 体力数值系统与状态机
- 喂食、玩耍等交互功能
- 数据自动保存与恢复
- 可扩展的宠物养成系统
- 接入正式美术资源 / Lottie 动画，替换占位动画帧
