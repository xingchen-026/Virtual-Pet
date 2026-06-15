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

- **最近一次完成**（`23f1b59`，已 push；并发布 **GitHub Release v1.0.0** 带 `VirtualPet.exe` 资产）：
  **B 打包分发（PyInstaller onefile）**：`config/settings.py` 拆 `RESOURCE_DIR`(_MEIPASS)
  与 `APP_DIR`(exe 旁)——只读资源（assets/动画/图片/声音、behavior/desktop/moderation 配置、ai_config 模板）走
  RESOURCE，可写数据（data/、logs/、user_config/skin_config、用户皮肤 `SKINS_DIR`）走 APP；新增 `ensure_user_data()`
  首运行播种（内置皮肤 copytree + ai_config 从 `config/ai_config.template.json` 拷贝，**绝不打包真实 Key**），`main.py`
  建 Game 前调用。打包脚本 `tools/build_exe.py`（PyInstaller CLI，`--onefile --windowed`，os.pathsep 拼 add-data，
  exclude scipy/matplotlib 等大库）+ `tools/make_icon.py`（取 cat idle 帧生成 `packaging/app_icon.ico`，故意不放
  build/ 以免被 --clean 清掉）；`utils/spritesheet.py` 的 scipy 改 try/except 缺失降级。`.gitignore` 加
  build/ dist/ *.spec packaging/ .build_venv/。**实机冒烟通过**：干净 venv 打出 **38MB** exe（全局脏环境曾打出 2.6GB），
  在空目录运行自动播种（ai_config 空 Key 已核 + 内置皮肤 cat + data/logs）、宠物正常漫游、无 error.log。
  开发态路径与原先完全一致，142 测试仍绿。源码已提交 push、exe 不入库仅随 Release 分发
  （`gh release create v1.0.0 dist/VirtualPet.exe`；本机 gh 在 `C:\Program Files\GitHub CLI\gh.exe`，已登录 xingchen-026）。
- **最近一次完成**（`1e89d8b`，已 push）：**围栏窗口化 + 鼠标取点 + 食物上限**（在下方「电子围栏」基础上迭代）：
  ①食物上限——`settings.FOOD_MAX_COUNT=10`；`FeedingController.add(point, max_count)` 返回 bool、新增 `is_full`；
  `Game._handle_feed_placement` 到顶忽略并气泡「先吃完这些」。
  ②围栏取点改为鼠标点两个对角（不再拖宠物）——点「围栏」进入**全屏取点态**（窗口铺满整屏透明遮罩、
  `_fence_selecting`），桌面点两下定对角，画橡皮筋预览；`FenceController` 加 `clear()`/`pending`。
  ③设好围栏后**窗口扩展为围栏大小并固定**——新增窗口三态（跟随 / 全屏取点 / 围栏固定）：
  `WindowController.follow` + `set_geometry` + `sync_to_pet` 分两路（固定模式不移窗、改设 `render_center=pet-window_pos`）；
  `DesktopManager.reapply_after_resize`（运行时 `set_mode` 后重取句柄、重应用透明/置顶/定位）；
  `Game._apply_window_geometry`/`_enter_select_mode`/`_enter_fence_mode`/`_enter_follow_mode` 编排（围栏模式漫游用
  半精灵内缩的围栏夹取、宠物不在围栏内则移到中心；拖拽改为在固定窗口内移动宠物）；`UIManager.set_canvas_size`
  随画布尺寸重算弹窗停靠；启动时若存有围栏直接进入围栏模式。测试 132→142（test_feeding/test_fence/test_window_controller）。
  实机冒烟已过（三态切换 + 运行时缩放不抛异常、几何/边界/渲染中心正确）；透明/置顶/点击/气泡的肉眼确认建议 `python main.py` 复核。
  - **用户反馈修复（同未提交）**：①喂食放置范围——无围栏时改为借用全屏遮罩（`_enter_fullscreen_overlay` +
    `_feed_overlay` 标志，结束恢复跟随），可在桌面任意处放食物而非局限宠物周围的小窗口；有围栏时窗口本就是围栏、
    放置即被夹在围栏内。②退化围栏防护——`FENCE_MIN_SIZE=150`，两角太近（误双击）得到的极小围栏被拒绝（留在取点态重选、
    气泡 `too_small`），存档中的退化围栏启动时忽略（`Game._fence_too_small`），避免窗口缩成一个点导致无法操作。
    ③取点态沿整块画布画一圈边框，直观提示"可在全屏范围内框选"。事件流冒烟逐项验证通过。
  - **用户反馈修复2「无法选择两个点」（同未提交）**：根因——桌宠用**颜色键透明（LWA_COLORKEY）**，
    其透明（洋红）像素上的点击会**穿透到桌面**（这正是桌宠平时的点击穿透特性），导致全屏遮罩里
    除宠物/边框外的空白处点不到、取不了点。修复：取点/无围栏放置态把分层窗口切到**统一半透明
    LWA_ALPHA**（`DesktopManager.set_overlay_alpha` + `settings.OVERLAY_ALPHA/OVERLAY_BG_COLOR`，
    `_render` 遮罩态填压暗色），整屏皆可点、桌面淡淡压暗示意；退出经 `_apply_window_geometry`→`set_transparent`
    还原颜色键。Win32 层冒烟确认：取点态 flags=LWA_ALPHA(alpha=96)、退出还原 LWA_COLORKEY。
- **更早一次完成**（`8fea886`，已 push）：**电子围栏 + 喂食放置 + 设置保存退出**：
  ①电子围栏——右键面板「围栏」按钮拖窗两点定角（点一次记宠物当前位置为一角、拖到对角再点定矩形，
  已有围栏时再点清除）；`core/fence.py` 的 `FenceController`（纯状态机 + `contains` + `popup_topleft` 布局函数）；
  `MovementController.set_fence/clear_fence` 把随机漫游夹到围栏内；存 `user_config.fence` 重启保留。
  ②喂食放置——点「喂食」进入放置模式，食物图标（`ui/food_icon.py` 程序化苹果）跟随鼠标，左键放下、
  右键取消、移出围栏自动取消；`core/feeding.py` 的 `FeedingController`；`AutonomousManager.food_target`
  最高优先级寻路，到达触发 `on_food_reached` 复用既有喂食管线（FeedAction+eating+属性增量+记忆）。
  ③设置「保存并退出」按钮——保存各项后请求 Game 退出（退出统一存档）。
  ④弹窗统一定位——设围栏后设置/状态/聊天/皮肤以围栏上边两角为基点、选能完整显示的一侧
  （`fence.popup_topleft` + `UIManager._anchored_rect` + `StatsPanel.draw(force_topleft=)`）。
  顺带修复 `Game.create_skin` 异常分支缺失的 `log_exception/AIServiceError` 导入（潜在 NameError）。
  测试 111→132（test_fence/test_feeding/test_movement/test_autonomous_food + 更新 test_ui_manager）。
- **更早一次完成**（`72f5b3b`，已 push）：**工程化收尾——计时器聚合 + UIManager/AIService 单测**：
  `utils/timer.py` 的 `IntervalTimer` 聚合自动存档/置顶维持/休息提醒三处计时；`Game._save_pet_data()`
  统一存档出口；新增 `tests/test_timer.py`、`tests/test_ai_service.py`（FakeLLM+tmp 隔离）、
  `tests/test_ui_manager.py`（font=None+tmp CHAT_HISTORY）。测试 88→111。
- **更早一次完成**（`7a2ceb1`，已 push）：**体力重做 + 自主睡眠 + 休息提醒 + 真实时间 + 圆角界面**（五项需求一次性完成）：
  ①体力仅移动时缓慢消耗、静止缓慢回升（`ENERGY_REGEN_PER_TICK`）、睡觉回升更快；
  `Game._update` 把 `moving=movement.has_target()` 传入 `PetBehavior.update(dt, moving)`。
  ②自主 SLEEP 改为进入持续睡眠恢复体力（体力满时仅小憩防夜晚抖动，`AutonomousManager._start_sleep`）。
  ③修复睡眠回满后"闪现"：主循环钳制 `dt`≤`MAX_FRAME_DT=0.1`（进程挂起后超大 dt 会让移动一步跳到目标）。
  ④休息提醒气泡 `ui/speech_bubble.py`（头顶圆角气泡，默认 30 分钟、随机文案、设置窗口可调间隔，
  存 `user_config.reminder_interval_minutes`）。⑤数值面板时间改为系统真实时间。
  ⑥全部窗口圆角：`theme.make_panel()`（SRCALPHA+圆角）替换 5 个面板的不透明 Surface。
  `tests/test_behavior.py`（体力增减）、`tests/test_autonomous_sleep.py`（自主睡眠+气泡计时）覆盖。
- **更早的迭代**（SAD 难过状态、皮肤制作全套、聊天持久化+记忆分层、设置增强、CI 等）详见下方「已完成」。
- ⚠️历史事故：曾因冒烟测试写空 api_key 覆盖清空用户本地 Key（见「操作备忘」末条，已确立备份做法）。
- **正在进行**：无（等待下一步指令）。
- **下一步候选**（尚未开始，按需挑选）：
  - **A. 美术升级**：接入正式素材 / GIF·APNG·Lottie 动画，替换占位帧（视觉是桌宠灵魂，最大短板；需素材）。
  - **C. AI 主动互动**：宠物基于状态/记忆/时间主动冒泡说话（非被动等聊天），体验跃升；可选 TTS 朗读。
  - **D. 健壮性**：多显示器 + DPI 缩放兼容（当前 `get_screen_size` 只取主屏、未设 DPI 感知，
    围栏窗口化在多屏/非 100% 缩放机器上可能有坑，是新引入的技术债）。
  - 注：「B 打包分发」已完成（见上）；「工程向单测」「计时器聚合」「皮肤切换图形化」已完成；
    「拖放道具」已被否决，均不再列为候选。

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
6. **提交前跑测试**：`python -m pytest tests/ -q` 应全绿（当前 142 passed）。
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
- **围栏窗口化 + 鼠标取点 + 食物上限**（未提交）：食物上限 10（`FOOD_MAX_COUNT`、`FeedingController.add`
  返 bool + `is_full`、到顶气泡）；围栏取点改全屏遮罩点两个对角（`_fence_selecting` + `FenceController.clear/pending`
  + 橡皮筋预览）；设围栏后窗口缩成围栏矩形并固定、宠物在内漫游——窗口三态（`WindowController.follow`/`set_geometry`/
  `sync_to_pet` 分两路、`DesktopManager.reapply_after_resize`、`Game._apply_window_geometry`/`_enter_*_mode`、
  `UIManager.set_canvas_size`、启动恢复直接进围栏模式）。`tests/test_feeding/test_fence/test_window_controller` 覆盖（132→142）。
- **电子围栏 + 喂食放置 + 设置保存退出**（未提交）：
  ①电子围栏（`core/fence.py`：`FenceController` 两点定角状态机 + `contains` + `popup_topleft`；
  `MovementController.set_fence/clear_fence` 夹取随机漫游范围；存 `user_config.fence`）；
  ②喂食放置模式（`core/feeding.py` `FeedingController`；`ui/food_icon.py` 程序化苹果；
  `AutonomousManager.food_target`/`on_food_reached` 寻路到达后复用喂食管线；受围栏约束、移出自动取消）；
  ③设置窗口「保存并退出」按钮（`UIManager._apply_save` 抽取，save/save_exit 共用，退出经 `on_quit`）；
  ④设围栏后弹窗统一定位（`fence.popup_topleft` + `UIManager._anchored_rect` + `StatsPanel.draw(force_topleft=)`）。
  `tests/test_fence.py`、`tests/test_feeding.py`、`tests/test_movement.py`、`tests/test_autonomous_food.py` 覆盖。
- **工程化收尾——计时器聚合 + UIManager/AIService 单测**（`72f5b3b`）：
  抽 `utils/timer.py` 的 `IntervalTimer`（累计 dt、到点触发回调并清零、超大 dt 只触发一次），
  替换 `Game`（自动存档/置顶维持）与 `UIManager`（休息提醒）三处重复的计时器累加；
  `Game._save_pet_data()` 统一存档出口。新增 `tests/test_timer.py`、`tests/test_ai_service.py`
  （FakeLLM + tmp 路径隔离，覆盖审查/离线降级/违规回复替换/三轮总结/首次喂食去重/连接测试）、
  `tests/test_ui_manager.py`（font=None + tmp CHAT_HISTORY，覆盖属性提示/历史上限/面板分发/提醒计时/活跃态）。测试 88→111。
- **体力重做 + 自主睡眠 + 休息提醒 + 真实时间 + 圆角界面**（`7a2ceb1`）：
  ①体力仅移动时缓慢消耗、静止缓慢回升、睡觉回升更快（`ENERGY_REGEN_PER_TICK`；
  `Game` 把 `moving=movement.has_target()` 传入 `PetBehavior.update`）；
  ②自主行为 SLEEP 改为进入持续睡眠恢复体力，体力满时仅小憩防夜晚抖动
  （`AutonomousManager._start_sleep`）；③修复睡眠回满后"闪现"——主循环钳制单帧
  `dt`≤`MAX_FRAME_DT=0.1`，避免进程挂起后超大 dt 让移动一步跳到目标；
  ④休息提醒气泡 `ui/speech_bubble.py`（头顶圆角气泡，默认 30 分钟一次、随机文案、
  设置窗口可调间隔并存 `user_config.reminder_interval_minutes`）；⑤数值面板时间改系统
  真实时间；⑥所有窗口圆角——`theme.make_panel()`（SRCALPHA+圆角）替换 5 个面板的
  不透明 Surface。`tests/test_behavior.py`、`tests/test_autonomous_sleep.py` 覆盖。
- **SAD 难过状态**：心情极低（<20）进入 `PetState.SAD` -> `sad` 动画；新增内置占位帧
  `assets/animations/sad/`、中文名「难过」。`tests/test_state_machine.py` 覆盖。
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
喂食放置：面板「喂食」-> FeedingController 放置模式 -> Game 处理鼠标 -> AutonomousManager.food_target 寻路 -> 到达 on_food_reached 复用喂食管线
电子围栏：面板「围栏」-> FenceController 两点定角 -> MovementController.set_fence 限定漫游 + 约束喂食 + 弹窗统一定位
```

**模块职责速查**
- `core/game.py`：主循环编排（事件/更新/渲染/帧率/托盘/自动存档/退出）。已瘦身。
- `core/window_controller.py`：窗口跟随坐标换算与拖拽（坐标不变式集中于此）。
- `ui/ui_manager.py`：聊天/数值面板/设置/皮肤窗口 + 事件路由 + AI 异步回传 + 属性变化(+xx)显示。
- `ui/{chat_window,stats_panel,settings_window,skin_window,skin_creator,message_box,speech_bubble,food_icon,theme}.py`：各 UI 组件 + 头顶提示气泡 + 食物图标 + 共享配色/圆角面板工厂。
- `core/skin_builder.py`：皮肤构建引擎（切分/抠图/镜像/速度，写 skin.json）；`utils/dialogs.py`：tkinter 文件/颜色对话框。
- `core/ai/*`：LLM 封装、人格、记忆、Prompt 拼接、情绪分析、AIService 入口。
- `core/{pet,behavior,state_machine,autonomous,behavior_tree,movement,schedule,emotion}.py`：宠物与行为系统。
- `core/{fence,feeding}.py`：电子围栏取点/布局 与 喂食放置 的纯状态机（Game 编排接入）。
- `core/{desktop,resource,sprite,animation,skin,interaction,action,event,food}.py`：平台/资源/渲染/交互。
- `config/*.json`：ai_config（AI）、behavior_config（自主行为）、desktop_config（窗口）、
  skin_config（当前皮肤）、user_config（宠物大小/窗口位置/休息提醒间隔/电子围栏）。
- `utils/timer.py`：`IntervalTimer` 周期计时器（聚合自动存档/置顶维持/休息提醒的累加触发逻辑）。
- `tests/`：pytest 回归（Pet 钳制/序列化、情绪规则、记忆并发与上限、精灵图切分、窗口坐标不变式、
  计时器触发、AIService 对话管线、UIManager 纯逻辑、围栏取点/布局、喂食放置、移动围栏、食物寻路）。

---

## 运行与测试

```bash
pip install -r requirements.txt      # pygame/pywin32/pystray/Pillow（皮肤工具另需 numpy/scipy）
python main.py                        # 启动桌宠
python -m pytest tests/ -q            # 回归测试（当前 142 passed）

# 导入皮肤（行模式 / 网格模式）
python tools/import_skin.py 图.png --name 皮肤名 --states idle,happy,walk
python tools/import_skin.py 表情图.png --name 皮肤名 --grid 3x6 --states excited,...,eating

# 打包单文件 exe（务必在干净 venv 里，否则全局脏环境会打出超大 exe）
python -m venv .build_venv && .build_venv/Scripts/python -m pip install pygame pywin32 pystray Pillow numpy pyinstaller
.build_venv/Scripts/python tools/build_exe.py   # 产物 dist/VirtualPet.exe（约 38MB）
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
- **打包 exe 体积暴涨**：PyInstaller 按"运行它的那个 Python 的 site-packages"打包。用装了一堆科学计算库的
  **全局 Python** 打包会把 numpy/scipy 等连带塞进去，曾打出 **2.6GB** 的 exe。务必在**干净 venv**
  （仅 pygame/pywin32/pystray/Pillow/numpy/pyinstaller）里 `tools/build_exe.py`，得到约 **38MB**。
  `build_exe.py` 已 `--exclude-module scipy/matplotlib/...` 兜底；scipy 仅皮肤网格碎片剔除可选用到，
  `utils/spritesheet.py` 已对其 import 做缺失降级。
- **打包勿泄 Key**：只打包 `config/ai_config.template.json`（空 Key），**绝不打包** `config/ai_config.json`
  （含真实 Key、被 skip-worktree 屏蔽）；首运行 `ensure_user_data()` 据模板生成。打包后在空目录跑一次确认
  生成的 `config/ai_config.json` 的 `api_key` 为空。
- **冒烟测试勿污染真实配置**：`config/ai_config.json` 被 `git update-index --skip-worktree` 屏蔽，
  不显示在 `git status`，`git checkout` 也不还原。冒烟里任何会触发设置保存（写 ai_config）的操作
  前，必须先 `cp config/ai_config.json /tmp/bak` 备份、测后还原；否则会覆盖用户真实 API Key
  且无法找回（曾因此清空过用户 Key）。同理 `data/*.json`、`config/{user_config,personality}.json`
  会被冒烟写脏，测后用 `git checkout --` 还原。
