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
│   └── settings.py           # 全局配置
│
├── core/
│   ├── pet.py                # 宠物核心类
│   ├── game.py               # 游戏主循环
│   └── resource.py           # 资源管理
│
├── assets/
│   ├── images/               # 图片资源
│   ├── animations/           # 动画资源
│   └── sounds/               # 音频资源
│
├── data/
│   └── pet_data.json         # 宠物数据存储
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

## 后续开发计划

- 动画系统：多状态动画切换（待机、行走、互动等）
- 桌宠透明窗口与窗口置顶显示
- 鼠标拖拽互动
- 饥饿 / 心情 / 体力数值系统与状态机
- 喂食、玩耍等交互功能
- 数据自动保存与恢复
- 可扩展的宠物养成系统
