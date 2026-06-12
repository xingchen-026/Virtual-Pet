## 角色

你是一名资深 Python 游戏交互开发工程师，同时具备 AI 辅助开发（Vibe Coding）项目实践经验。

当前正在继续开发桌面虚拟宠物应用。

此前阶段已经完成：

* Python + Pygame 工程架构
* Pet 核心对象
* JSON 数据持久化
* 动画系统
* Sprite 渲染系统
* 状态机系统
* 饥饿 / 心情 / 体力属性系统
* 状态自动变化与动画联动

当前阶段目标：

实现桌宠交互系统，让用户可以通过鼠标与宠物进行互动。

本阶段重点：

1. 鼠标拖拽移动
2. 点击宠物反馈
3. 喂食行为
4. 玩耍行为
5. 交互行为驱动属性变化和动画变化

开发原则：

1. 基于已有架构扩展，不重构已有模块。
2. 交互逻辑独立管理，不直接写入 Pet 类。
3. 行为系统需要支持未来增加更多动作。
4. 所有交互必须通过事件系统处理。
5. 每完成一个阶段等待确认，不提前开发后续功能。

开发流程：

需求分析 → Prompt拆解 → AI生成代码 → 人工审核 → 测试优化。

---

# 开发任务

## 1. 创建交互管理模块

新增：

```
core/

├── interaction.py       # 用户交互管理
├── event.py             # 游戏事件定义
└── action.py            # 宠物行为动作
```

设计：

InteractionManager 类。

负责：

* 鼠标事件监听
* 点击检测
* 拖拽处理
* 行为触发

示例：

```python
interaction.handle_event(event)
```

---

# 2. 实现桌宠鼠标拖拽功能

目标：

用户可以按住宠物并拖动。

实现：

鼠标按下：

判断：

```python
mouse_position in pet_rect
```

进入：

```python
dragging=True
```

鼠标移动：

更新：

```python
pet.position
```

鼠标释放：

```python
dragging=False
```

要求：

* 拖动过程中宠物跟随鼠标移动。
* 不影响动画播放。
* 不产生位置跳动。

---

# 3. 增加点击互动系统

实现：

点击宠物触发反馈。

点击行为：

普通点击：

效果：

```
mood +5
energy -2
animation = happy
```

连续点击：

触发：

```
excited状态
```

要求：

设计：

ClickCounter

记录：

* 点击次数
* 点击时间间隔

用于未来扩展特殊行为。

---

# 4. 实现喂食系统

新增：

```python
core/

food.py
```

设计：

Food 类。

包含：

```python
name
hunger_restore
mood_restore
```

示例：

```python
food = Food(
    "Apple",
    hunger_restore=20
)
```

实现：

喂食行为：

效果：

```
hunger +20
mood +10
```

同时：

触发：

```
animation = happy
```

要求：

属性最大值限制保持：

0-100

---

# 5. 实现玩耍系统

新增行为：

PlayAction

效果：

```
mood +20

energy -15

hunger -10
```

触发：

```
happy animation
```

要求：

玩耍逻辑独立。

未来可以扩展：

* 小游戏
* 玩具
* 道具系统

---

# 6. 建立行为系统

新增：

```
BehaviorManager
```

负责：

统一管理：

* Feed
* Play
* Click
* Drag

结构：

```
User Input

    ↓

InteractionManager

    ↓

BehaviorManager

    ↓

Pet Attribute

    ↓

StateMachine

    ↓

AnimationManager
```

要求：

保持模块之间低耦合。

---

# 7. 添加交互动画反馈

新增动画状态：

```
INTERACT

EXCITED

EATING

PLAYING
```

扩展：

```python
AnimationState
```

要求：

行为触发后：

自动切换动画。

例如：

喂食：

```
FeedAction

↓

EATING animation
```

玩耍：

```
PlayAction

↓

PLAYING animation
```

---

# 8. 添加交互提示 UI

增加简单提示：

例如：

用户点击后显示：

```
+5 Mood
```

喂食：

```
Hungry ↓
Happy ↑
```

要求：

提示显示：

* 自动消失
* 不阻塞游戏

---

# 9. 数据保存扩展

保存：

新增：

```
last_action
interaction_count
```

示例：

```json
{
"name":"Pet",
"hunger":80,
"mood":90,
"energy":70,
"last_action":"feed",
"interaction_count":15
}
```

---

# 项目限制

当前阶段禁止实现：

* 桌面透明窗口
* 开机启动
* 随机漫游
* 网络通信
* AI聊天
* 多宠物系统

这些将在后续阶段实现。

---

# 代码要求

1. 遵循 Python PEP8。

2. 所有交互逻辑必须模块化。

3. 不允许：

```python
if click:
    pet.hunger += 20
```

直接写大量业务逻辑。

必须：

```
事件

↓

行为

↓

属性变化
```

4. 支持未来扩展：

例如：

```
BathAction

SleepAction

GiftAction
```

5. 添加必要类型提示和注释。

---

# 当前项目状态

已经完成：

✅ Pygame基础环境

✅ 宠物对象

✅ 动画系统

✅ 状态机系统

✅ 属性养成系统

✅ 自动状态变化

当前阶段目标：

实现完整桌宠交互能力。

完成后项目应该具备：

* 用户可以拖动宠物
* 用户可以点击宠物
* 用户可以喂食
* 用户可以陪宠物玩耍
* 行为影响属性
* 行为影响动画

---

请完成本阶段开发，并输出：

1. 新增文件列表

2. 修改文件列表

3. 交互系统架构说明

4. 每个文件完整代码

5. 交互测试案例

6. 属性变化测试结果

7. 当前阶段完成总结

完成后停止，等待下一阶段指令。
