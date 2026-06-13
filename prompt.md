# Virtual-Pet 项目状态文档

> **本文件是项目的单一事实来源（Single Source of Truth）。**
> 每次对话被压缩后，只需读取本文件即可了解：**当前在做什么、接下来做什么、已经完成了什么。**
>
> **维护约定（重要）**：每当完成一项工作、改变方向、或确定下一步时，**立即更新本文件**对应小节
> （主要是「任务清单」与「已完成」两节）。这是项目的关键文件，必须主动、及时维护。

---

## 角色

你是一名资深 AI 应用架构工程师，同时具备 Python 桌面应用开发、LLM Agent 开发和
AI 辅助编程（Vibe Coding）实践经验，当前持续开发 Virtual-Pet 桌面虚拟宠物项目。

开发流程：需求分析 → Prompt 拆解 → AI 代码生成 → 人工审核 → 测试优化。
每完成一个阶段等待确认，不提前开发后续功能。

---

## 一句话简介

基于 **Python 3.12 + Pygame 2.6** 的桌面虚拟宠物：透明无边框窗口悬浮桌面、自主漫游、
喂食/玩耍互动、状态机养成（饥饿/心情/体力）、接入 LLM 的自然语言聊天与人格/记忆系统、
可导入自定义皮肤。数据用 JSON 持久化。仅 Windows 提供完整桌面能力（pywin32），其他平台降级为普通窗口。

---

## 任务清单 / 当前状态（CURRENT）

- **最近一次完成**：扩展养成系统——新增洗澡/睡觉/送礼三个养成动作（`core/action.py`
  BathAction/SleepAction/GiftAction，复用 happy/sleep/excited 动画），全部接入右键面板按钮
  （喂食/玩耍/洗澡/睡觉/礼物）。UIManager 面板路由改为「按钮标识 ↔ InteractionEventType」
  通用映射（`_PANEL_INTERACTION_TYPES` 由枚举自动派生），以后加养成动作零改动路由。
- **正在进行**：无（等待下一步指令）。
- **下一步候选**（尚未开始，按需挑选）：
  - **拖放道具**交互入口（把食物/玩具/礼物图标拖到宠物身上）——养成动作的另一种图形化入口，尚未做。
  - 功能向：聊天历史持久化展示、SAD 等新状态专属动画、皮肤切换的图形化入口
    （目前靠改 `config/skin_config.json` + 重启）。
  - 工程向：CI 跑 pytest、给 UIManager/AIService 补单测。
  - 小重构：托盘动作/自动存档/置顶维持等计时器逻辑聚合（价值低）。

---

## 约束 / 开发约定（必须遵守）

1. **AI 模块解耦**：`Pet -> AIService -> LLM`。禁止在 `core/pet.py` 直接调用 LLM。
   所有 LLM 调用封装在 `core/ai/llm_client.py`，换供应商只改 `config/ai_config.json`。
2. **离线可用**：AI 不可用（无 Key/网络异常/格式错误）时降级为离线回复，桌宠核心功能不受影响。
3. **配置文件化**：模型名/参数/按键/尺寸等不硬编码，集中在 `config/settings.py` 与 `config/*.json`。
4. **运行时数据不入库**：`data/pet_data.json`、`data/memory.json` 是用户运行产生的数据，提交时不要带上。
5. **API Key 绝不入库**：仓库版 `config/ai_config.json` 的 `api_key` 必须为空。
   本地真实 Key 已用 `git update-index --skip-worktree config/ai_config.json` 屏蔽，
   `config/ai_config.json.local` 在 `.gitignore` 中。提交前务必确认 `git show HEAD:config/ai_config.json` 不含 Key。
6. **提交前跑测试**：`python -m pytest tests/ -q` 应全绿（当前 36 passed）。
7. **提交规范**：commit message 用中文，描述「做了什么 + 为什么」；结尾加 `Co-Authored-By` 行。
   只在用户要求时 commit/push。`git push` 时 `credential-manager-core` 警告可忽略（推送已成功）。
8. **验证习惯**：改动后跑 pytest + 临时脚本冒烟（用完即删，命名 `tools/_xxx_test.py`），
   必要时 `python main.py` 实机启动确认。临时脚本会写 `data/memory.json`，测完还原。

---

## 已完成（DONE）

### 基础阶段（1-7，见 README 详细说明）
1. 工程骨架 + Pygame 主循环 + Pet 核心类 + JSON 持久化
2. 动画系统（AnimationState/Animation/AnimationManager/PetSprite）
3. 状态机（StateMachine）+ 属性衰减（PetBehavior）
4. 交互系统（点击/拖拽/喂食/玩耍，事件->行为->属性->动画）
5. 自主行为系统（AutonomousManager + 行为树 + 昼夜节奏 + 情绪 + 随机漫游）
6. 桌面应用能力（透明置顶无边框窗口 / 系统托盘 / 统一异常与日志）
7. AI 能力（LLMClient / PersonalityManager / MemoryManager / PromptManager /
   EmotionAnalyzer / AIService；聊天窗口；对话影响情绪、AI 行为影响状态）

### 近期迭代
- **养成动作扩展**：在喂食/玩耍基础上新增洗澡（mood+15/energy-5）、睡觉（energy+40/mood+5）、
  送礼（mood+30）三个养成动作，全部接入右键面板按钮；面板路由按事件类型通用分发，
  新增动作四步即可（枚举 + Action + 注册 + 按钮）。`tests/test_action.py` 覆盖。
- **右键数值面板 + 中文字体修复**：右键宠物弹出状态面板；UI 改用含中文字形的系统字体（微软雅黑等），修复方块乱码。
- **皮肤替换系统**：`utils/spritesheet.py` 自动检测背景色+去背景+切分；`tools/import_skin.py`
  支持行模式（每行一个动作）与网格模式（每格一个表情，`--grid 3x6`，自动剔除越界碎片）；
  `core/skin.py` 按 `config/skin_config.json` 选皮肤，缺失状态回退内置动画。已内置 **cat 皮肤**（覆盖全部 12 个动画状态）。
- **窗口跟随 + 镜像 + 右键功能菜单 + 设置窗口**：宠物固定窗口中心、移动整窗跟随；向左移动镜像翻转；
  喂食/玩耍移入右键面板按钮（不再用 F/P 键）；设置窗口可调宠物大小（0.5x~2.0x）、配置 AI 服务商/模型/API Key
  （支持 Ctrl+V 粘贴、首尾明文掩码、「测试」按钮后台验证连接）。

### 代码审查 12 项（全部完成）
1-6（`9d8339f`）：聊天线程异常兜底、MemoryManager 加锁+长期记忆 100 条上限、宠物数据 60s 自动存档、
新增 `requirements.txt`、三档帧率（隐藏 5 / 空闲 30 / 活跃 60 fps）。
7-9/11-12（`82e660a`）：MessageBox 预渲染消息行、删死代码（feedback.py / ActionResult.message）、
抽 `ui/theme.py` 统一配色、漫游内缩半窗口防出屏、窗口位置跨会话持久化、新增 `tests/`（pytest）。
10（`6a47e73` + `ca05cee`）：抽 `WindowController` 与 `UIManager`，Game 瘦身为纯编排者。

---

## 关键架构与文件地图

**核心数据流**
```
用户输入 -> UIManager.handle_event（界面优先消化）
         -> 未消化 -> InteractionManager -> Game._dispatch_interaction
         -> BehaviorManager -> Pet 属性 -> StateMachine -> AnimationManager
自主行为：Pet 状态 -> AutonomousManager -> 行为决策 -> 移动/动画
窗口跟随：WindowController 维护「窗口中心 = 宠物屏幕坐标」不变式
AI 聊天：UIManager -> 后台线程 AIService.chat -> 队列回传 -> 写回聊天窗口
```

**模块职责速查**
- `core/game.py`：主循环编排（事件/更新/渲染/帧率/托盘/自动存档/退出）。已瘦身。
- `core/window_controller.py`：窗口跟随坐标换算与拖拽（坐标不变式集中于此）。
- `ui/ui_manager.py`：聊天窗口/数值面板/设置窗口 + 事件路由 + AI 异步回传 + 属性变化(+xx)显示。
- `ui/{chat_window,stats_panel,settings_window,message_box,theme}.py`：各 UI 组件 + 共享配色。
- `core/ai/*`：LLM 封装、人格、记忆、Prompt 拼接、情绪分析、AIService 入口。
- `core/{pet,behavior,state_machine,autonomous,behavior_tree,movement,schedule,emotion}.py`：宠物与行为系统。
- `core/{desktop,resource,sprite,animation,skin,interaction,action,event,food}.py`：平台/资源/渲染/交互。
- `config/*.json`：ai_config（AI）、behavior_config（自主行为）、desktop_config（窗口）、
  skin_config（当前皮肤）、user_config（宠物大小/窗口位置）。
- `tests/`：pytest 回归（Pet 钳制/序列化、情绪规则、记忆并发与上限、精灵图切分、窗口坐标不变式）。

---

## 运行与测试

```bash
pip install -r requirements.txt      # pygame/pywin32/pystray/Pillow（皮肤工具另需 numpy/scipy）
python main.py                        # 启动桌宠
python -m pytest tests/ -q            # 回归测试（当前 36 passed）

# 导入皮肤（行模式 / 网格模式）
python tools/import_skin.py 图.png --name 皮肤名 --states idle,happy,walk
python tools/import_skin.py 表情图.png --name 皮肤名 --grid 3x6 --states excited,...,eating
```

**操作**：右键宠物弹面板（养成动作：喂食/玩耍/洗澡/睡觉/礼物 + 聊天/设置）；
`C` 开关聊天；拖拽移动；自主漫游时窗口跟随。设置里填 API Key 后点「测试」验证再保存。

---

## 操作备忘（踩过的坑，避免重复）

- **中文乱码**根因不是文件编码（早已统一 UTF-8），而是 `pygame.font.SysFont(None,...)` 默认字体无中文字形 ——
  必须用 `settings.UI_FONT_NAMES`（微软雅黑等）。
- **API Key 401**：DeepSeek 平台 Key 只在创建时完整显示一次，列表里是截断版；复制截断版会 401。
  设置窗口的错误行已透传服务端 `error.message`（含 Key 末 4 位）便于核对。
- **窗口跟随不变式**：任何改动 `WindowController` 的地方都要保持「窗口中心 = 宠物屏幕坐标」，
  否则会出现「拖完弹回原位」类 bug（已有 `tests/test_window_controller.py` 锁定）。
- **皮肤网格切分**：均匀网格会把相邻格越界的精灵边缘切进来，`_remove_border_debris` 按「贴边且远小于主体」剔除；
  zZ/星星/气泡等合法装饰不受影响（阈值 `_BORDER_DEBRIS_RATIO`）。
- **PowerShell/Bash**：本机两种 shell 都可用；停止桌宠用 `Get-Process python | Stop-Process -Force`。
