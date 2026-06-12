## 角色

你是一名资深 Python 游戏 AI 行为系统开发工程师，同时具备 AI 辅助开发（Vibe Coding）项目实践经验。

当前正在继续开发桌面虚拟宠物应用。

此前阶段已经完成：

* Python + Pygame 工程架构
* Pet 核心对象
* JSON 数据持久化
* 动画系统
* Sprite 渲染系统
* 状态机系统
* 饥饿 / 心情 / 体力属性系统
* 鼠标拖拽系统
* 点击互动系统
* 喂食与玩耍行为系统

当前阶段目标：

实现桌宠自主行为系统。

让宠物不再只是等待用户操作，而是能够：

* 自动移动
* 随机探索
* 自动切换动作
* 根据状态产生不同表情
* 模拟真实宠物生命周期

开发原则：

1. 基于已有状态机和行为系统扩展。
2. 不修改已有交互逻辑。
3. 自主行为必须通过行为管理系统控制。
4. 不允许直接在 Game 主循环中堆积 AI 判断逻辑。
5. 所有行为需要可配置。
6. 每完成一个阶段等待确认，不提前开发后续功能。

开发流程：

需求分析 → Prompt 拆解 → AI生成代码 → 人工审核 → 测试优化。

---

# 开发任务

## 1. 创建宠物自主行为系统

新增模块：

```id="2ih7rh"
core/

├── autonomous.py        # 自主行为控制
├── behavior_tree.py     # 行为决策树
├── movement.py          # 移动控制
└── schedule.py          # 生命周期调度
```

设计：

AutonomousManager 类。

负责：

* 判断宠物当前状态
* 选择自动行为
* 执行动作
* 控制行为频率

结构：

```id="j1q7j7"
Pet State

    ↓

AutonomousManager

    ↓

Behavior Decision

    ↓

Action Execute

    ↓

Animation Update
```

---

# 2. 实现随机漫游系统

目标：

宠物可以在窗口范围内随机移动。

新增：

MovementController

功能：

* 随机生成目标位置
* 控制移动速度
* 平滑移动
* 到达目标后重新选择位置

例如：

```python id="zv21yw"
move_to(random_position)
```

要求：

移动规则：

* 不超出窗口边界。
* 移动过程中播放 walking 动画。
* 停止后恢复 idle 动画。

---

# 3. 增加移动动画状态

扩展：

AnimationState

新增：

```python id="fdh1bb"
WALK
RUN
LOOK_AROUND
SLEEP
```

行为对应：

移动：

```
WALK animation
```

快速移动：

```
RUN animation
```

观察：

```
LOOK_AROUND animation
```

睡觉：

```
SLEEP animation
```

要求：

动画切换由行为驱动。

---

# 4. 实现空闲行为系统

设计：

IdleBehavior

宠物处于空闲状态时随机执行：

行为列表：

## 看周围

效果：

```
LOOK_AROUND
```

## 打哈欠

效果：

```
TIRED animation
```

## 睡觉

条件：

```
energy < 20
```

效果：

```
SLEEP animation
```

## 开心动作

条件：

```
mood > 80
```

效果：

```
HAPPY animation
```

要求：

行为随机概率可配置。

例如：

```json
{
"idle_action_probability":0.3
}
```

---

# 5. 实现状态影响行为决策

根据宠物属性调整行为。

规则：

## 饥饿

条件：

```
hunger < 30
```

行为：

* 减少移动
* 增加寻找食物动作
* 播放 hungry 动画

---

## 疲劳

条件：

```
energy < 30
```

行为：

* 降低移动速度
* 增加休息概率

---

## 开心

条件：

```
mood > 80
```

行为：

* 增加随机活动
* 播放快乐动作

要求：

行为系统不能修改属性。

只能产生行为。

---

# 6. 实现生命周期时间系统

新增：

ScheduleManager

模拟：

时间流逝。

例如：

每分钟：

```
hunger - 1
```

每五分钟：

```
energy - 5
```

根据时间：

触发：

* 白天活动
* 夜晚睡眠

要求：

不要使用真实分钟阻塞程序。

使用：

pygame.time

---

# 7. 添加宠物表情系统

新增：

EmotionManager

管理：

```python id="9r7j7f"
happy
sad
angry
hungry
sleepy
excited
```

根据：

* 属性
* 行为
* 用户操作

自动切换。

例如：

用户喂食：

```
happy expression
```

长期饥饿：

```
sad expression
```

---

# 8. 增加行为日志系统

新增：

```id="y7h2fj"
logs/

pet_behavior.log
```

记录：

例如：

```
12:01 Pet started walking

12:05 Pet became hungry

12:08 User fed pet
```

用于：

调试 AI 行为。

---

# 9. 配置化行为参数

新增：

```id="v4x5zq"
config/

behavior_config.json
```

保存：

```json
{
"walk_speed":2,
"idle_time":5,
"random_walk":true,
"sleep_threshold":20
}
```

要求：

禁止硬编码行为参数。

---

# 项目限制

当前阶段禁止实现：

* 多宠物系统
* 网络同步
* AI聊天
* 语音交互
* 云端数据
* 商店系统

这些将在后续阶段开发。

---

# 代码要求

1. 遵循 Python PEP8。

2. 使用面向对象设计。

3. 行为决策和执行分离。

禁止：

```python
if hungry:
    move=False
```

推荐：

```python
State

↓

Behavior Decision

↓

Action
```

4. 所有概率、速度、阈值配置化。

5. 保持与已有模块兼容。

---

# 当前项目状态

已经完成：

✅ 项目基础架构

✅ 动画系统

✅ 状态机

✅ 属性养成

✅ 用户交互

✅ 喂食与玩耍

当前阶段目标：

实现桌宠自主生命系统。

完成后项目应该具备：

* 宠物自动移动
* 自动执行行为
* 根据状态改变行为
* 自动切换表情
* 模拟宠物生命周期

---

请完成本阶段开发，并输出：

1. 新增文件列表

2. 修改文件列表

3. 自主行为系统架构说明

4. 行为决策流程图

5. 每个文件完整代码

6. 自动行为测试案例

7. 随机漫游测试结果

8. 当前阶段完成总结

完成后停止，等待下一阶段指令。
