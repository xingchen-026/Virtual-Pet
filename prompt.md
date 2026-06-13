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

- **最近一次完成**：**皮肤制作功能**（「创建皮肤」按钮落地）——新增构建引擎
  `core/skin_builder.py`（精灵图按行/网格切分 + 按状态上传 + 一键抠图 chroma_key
  + 一键镜像 + 逐动画速度 frame_durations，写入 skin.json）与 GUI `ui/skin_creator.py`
  （tkinter 选文件/选色，见 `utils/dialogs.py`）。皮肤窗口「创建皮肤」改为打开创建器，
  生成后经 `Game.create_skin -> _reload_skin` 即时启用。`SkinManager.frame_durations`
  + `Game._build_animation_manager` 支持逐皮肤播放速度。CLI `import_skin.py` 复用引擎。
  `tests/test_skin_builder.py` 覆盖。
- 已提交：皮肤选择独立窗口（缩略图预览，`b4cb315`）；性格/语气拆分（`0ee1bc4`）；
  统一名称/设置改名/提示词优化/内容审查（`bf820eb`）。
- ⚠️历史事故：曾因冒烟测试写空 api_key 覆盖清空用户本地 Key（见「操作备忘」末条，已确立备份做法）。
- **最近一次完成**：加 **CI 自动跑 pytest**（`.github/workflows/tests.yml`）——push 到 main / 提 PR
  时在 Linux + Python 3.12 上跑全部测试；CI 仅装 pygame/Pillow/numpy/scipy/pytest（不装
  Windows 专用 pywin32/pystray，已验证测试不依赖它们）。
- **聊天持久化 + 记忆分层 + 设置增强**：①聊天历史持久化——可见对话存
  `data/chat_history.json`（`settings.CHAT_HISTORY_*`），重启回填聊天窗口（UIManager 加载+
  `_record_chat`）；与 AI 记忆分离。②记忆分两层——短期=最近 3 轮（`SHORT_TERM_LIMIT=3`），
  长期=主人习惯摘要（AIService 每 3 轮用 LLM 总结 `_update_long_term_summary` +
  `MemoryManager.add_summary`/`PromptManager.summary_messages`）。③设置：服务商改**下拉选择**
  （SettingsWindow `_provider_open`/`_draw_provider_popup`）+ 新增**接口地址 base_url**字段
  （写入 ai_config `api_base`）。
- **创建窗口交互优化（4 项）**：①精灵图改为**先点中文状态标签、再左键点帧贴标签**
  （右键点帧取消），状态名全中文（`settings.STATE_DISPLAY_NAMES`）。②实时播放加**状态选择**
  （点中文 chip 指定播放哪个状态）+ **镜像预览**开关（开则先播朝右再播朝左，
  `_mirror_phase`）。③播放速度改为预览下方的**拖拉条 + 数值框**（数值框用编辑缓冲
  `_speed_text` 避免逐键钳制串改）。④（用户跳过第 3 项）。
- **多张精灵图 + 逐帧自由选状态**：精灵图可添加多张（同一皮肤不同资源拼成），每张切逐帧，
  任意帧分配状态（同状态帧按序成动画），每张单独翻转/抠图。后端
  `skin_builder.slice_frames/grouped_from_sheets/build_from_sheets`
  （config `sheets=[{path,mirror,chroma_color,frame_states}]`）。
- **点图取色 + 实时预览 + 皮肤合集/补充**：①源图点击取透明色（`SkinCreator._sample_color`）+
  右侧实时播放（`preview_grouped` + `update(dt)`）。②皮肤选择窗口显示每皮肤缺失状态
  （`SkinManager.covered_states/missing_states`），非默认皮肤「补充动画」按状态补齐
  （`build_from_state_images` 合并保留已有）。抠图：自动取角落 / tkinter 选色 / 点源图取色（精灵图模式作用于聚焦图）。
- **正在进行**：无（等待下一步指令）。
- **下一步候选**（尚未开始，按需挑选）：
  - 功能向：SAD 等新状态专属动画。
  - 工程向：给 UIManager/AIService 补单测（CI 已就绪）。
  - 小重构：托盘动作/自动存档/置顶维持等计时器逻辑聚合（价值低）。
  - 美术：接入正式素材/Lottie 动画，替换占位帧。
  - 注：「拖放道具」已被否决；「皮肤切换图形化」已完成，均不再列为候选。

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
6. **提交前跑测试**：`python -m pytest tests/ -q` 应全绿（当前 78 passed）。
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
- **CI**：`.github/workflows/tests.yml`——push main / PR 时 Linux+Py3.12 跑 pytest（仅装测试依赖）。
- **聊天持久化 + 记忆分层 + 设置增强**：聊天历史存 `data/chat_history.json` 重启回填；
  短期记忆=最近 3 轮、长期记忆=LLM 每 3 轮总结的主人习惯摘要；设置服务商下拉 + 自定义 base_url。
- **皮肤制作**：`core/skin_builder.py`（精灵图逐帧切分 `slice_frames` + 多张图逐帧分配
  `grouped_from_sheets/build_from_sheets` + 按状态上传 + chroma_key 抠图 + mirror 镜像
  + 逐动画速度，写 skin.json；`preview_grouped` 内存出帧供预览；旧 build_from_spritesheet/CLI 保留）；
  GUI `ui/skin_creator.py`（tkinter 选文件/选色 `utils/dialogs.py`；多张精灵图、逐帧缩略图点选状态、
  点源图取色、右侧实时播放 `update(dt)`）；`Game.create_skin/_reload_skin` 生成即时启用；
  逐皮肤播放速度经 `SkinManager.frame_durations` + `Game._build_animation_manager` 生效。
  皮肤选择窗口显示缺失状态并可「补充动画」（`SkinManager.covered_states/missing_states`）。
  `tests/test_skin_builder.py`、`tests/test_skin.py` 覆盖。
- **皮肤选择独立窗口**：右键面板「皮肤」按钮打开 `ui/skin_window.py`，缩略图预览点击选择、
  即时切换、当前皮肤高亮，右下角「创建皮肤」打开创建器。
  `SkinManager.available_skins/set_active/preview_path`；`Game._apply_skin` 重建动画即时生效。
  性格/语气已拆为两个独立字段（character/tone）。`tests/test_skin.py` 覆盖。
- **名称统一 + 性格自定义 + 提示词优化 + 内容审查**：宠物名称在数值面板/聊天窗口统一；
  设置可改名称与性格语气（注入系统提示词）；系统提示词重写（拟真宠物/简短有情绪/健康友善）；
  新增 `core/ai/moderation.py`（违规词过滤，双向审查输入与回复，配置 `config/moderation.json`）。
  `tests/test_moderation.py`、`tests/test_prompt.py` 覆盖。
- **聊天/设置窗口靠边停靠**：聊天左（CHAT_WINDOW_WIDTH=280）、设置右（SETTINGS_WINDOW_WIDTH=280，
  高 400），避免遮挡居中的宠物。数值面板同时去掉年龄。
- **睡眠模式 + 危急状态 + 面板精简**（用户反馈修复）：睡觉=持续模式（停原地缓慢回体力、
  可被唤醒，`core/behavior.py`）；饥饿/体力归零进入危急状态（停下并强制 hungry/tired 动画）；
  数值面板移除互动次数/最近动作/行为/情绪（改由动画呈现），后又移除年龄，
  仅留名称/饥饿/心情/体力/时间。`tests/test_behavior.py` 覆盖。
- **养成动作扩展**：在喂食/玩耍基础上新增洗澡（mood+15/energy-5）、送礼（mood+30）等养成动作
  （睡觉改为持续模式，见上），全部接入右键面板按钮；面板路由按事件类型通用分发，
  新增一次性动作四步即可（枚举 + Action + 注册 + 按钮）。`tests/test_action.py` 覆盖。
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
- `ui/ui_manager.py`：聊天/数值面板/设置/皮肤窗口 + 事件路由 + AI 异步回传 + 属性变化(+xx)显示。
- `ui/{chat_window,stats_panel,settings_window,skin_window,skin_creator,message_box,theme}.py`：各 UI 组件 + 共享配色。
- `core/skin_builder.py`：皮肤构建引擎（切分/抠图/镜像/速度，写 skin.json）；`utils/dialogs.py`：tkinter 文件/颜色对话框。
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
python -m pytest tests/ -q            # 回归测试（当前 78 passed）

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
- **冒烟测试勿污染真实配置**：`config/ai_config.json` 被 `git update-index --skip-worktree` 屏蔽，
  不显示在 `git status`，`git checkout` 也不还原。冒烟里任何会触发设置保存（写 ai_config）的操作
  前，必须先 `cp config/ai_config.json /tmp/bak` 备份、测后还原；否则会覆盖用户真实 API Key
  且无法找回（曾因此清空过用户 Key）。同理 `data/*.json`、`config/{user_config,personality}.json`
  会被冒烟写脏，测后用 `git checkout --` 还原。
