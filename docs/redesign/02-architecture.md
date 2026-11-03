# 新架构：一份生活，寄生在 Harness 里

> 目标：用**最少的自有机制**换取**最大的一致性**。任何"DSH 已经做了"的东西，插件都不重做。

## 1. 三层职责

```
┌───────────────────────────────────────────────────────────┐
│ Client（浏览器）                                            │
│  React 组件 → slots.inject 注册                             │
│  只做：渲染、点击、乐观显示                                  │
│  不做：业务规则、存档写入、模型调用                            │
├───────────────────────────────────────────────────────────┤
│ Host（插件 apply）                                          │
│  ctx.dshWorld（一个 service）＝ 唯一业务真源                  │
│  ├─ rooms      读/校验/写 工作区里的房间文件                  │
│  ├─ persona    人设基线（受保护的不可静默覆盖）                │
│  ├─ projections 注册 growth / presence / roomOfSession        │
│  ├─ actions    life.* 等"一个操作"的唯一实现                  │
│  └─ surfaces   tools（同方法）+ webServer（只读资源）          │
├───────────────────────────────────────────────────────────┤
│ Harness 内核（不动）                                         │
│  session log / agent loop / tools / slots / storage / fs     │
└───────────────────────────────────────────────────────────┘
```

**铁律：有且只有一个业务真源。** 旧版有 3 个（World 内存、state.json、Godot 控制器），是绝大多数竞态与"文档写不等于已实现"的来源。

## 2. 目录结构（建议）

```
dsh-world/
  package.json            # dsh.bundle.patch + dsh.client
  cordis.patch.yml        # 一个 host 行
  index.js                # Host: export apply / inject / Config
  client.js               # Client: __ModuleLoader__ 工厂（构建产物）
  locale/{en,zh}.json     # meta.title / meta.description
  icon.svg
  host/
    service.js            # ctx.dshWorld 注册与生命周期
    rooms.js  persona.js  actions.js
    projections/{growth,presence,room-of-session}.js
    tools.js              # defineTool × N，全部代理到 actions.js
    assets.js             # webServer 只读资源
  client/
    panel.jsx  room-canvas.jsx  controls.jsx
  world/                  # 与宿主无关的纯逻辑（可单测，无 ctx）
    geometry.js pathing.js palette.js packs.js
  assets/                 # 按需，注意体积
```

对比旧版：删掉 `server/http.js`（自建总线）、`server/store.js`（自建存档）、`services/hub.mjs`（自建社区服务）、`godot/`（暂缓）。
保留 `world/`（纯函数）与 `assets/`、`furniture/*/definition.js`（声明式家具）。

## 3. Host 骨架（真实可写）

```js
// index.js
export const name = 'dsh-world'
export const inject = ['tools', 'sessionProjections', 'fs', 'systemPrompt']
export const Config = Schema.object({
  roomFile: Schema.string().default('world/room.json'),
  autoLife: Schema.boolean().default(false),
})

export function apply(ctx, config) {
  const world = createWorld(ctx, config)
  ctx.effect(() => {
    world.mount()                       // 注册投影 / 工具 / 路由
    return () => world.dispose()        // 释放定时器、AbortController、domain
  }, 'dsh-world: world')

  ctx.inject(['tools'], scoped => registerTools(scoped, world))
  ctx.systemPrompt.section({           // 最弱机制：只加文本
    name: 'dsh-world:presence',
    text: () => world.presenceText(),  // 当前房间/时段/角色状态的自然语言摘要
  })
}
```

设计说明（对应官方 practices 的"用最弱机制"）：
- **不加** `tools.guard`；不需要拦截别的工具。
- **不监听** `agent/pre-step`；房间状态通过 `inject` 上下文 + systemPrompt 段落进入模型即可。
- 定时器只在一个地方，且必须 `agent.followup()` 才能唤醒 agent；默认关闭（`autoLife=false`）。

## 4. 投影设计（成长作为 fold，而不是日志）

~~~js
const GROWTH = {
  key: 'dshWorld.growth',
  stateVersion: 1,
  stateSchema,                       // 纯 JSON
  init: () => ({ interests: [], milestones: [], revision: 0 }),
  apply(state, event) {
    // 只消费已存在的事件：用户消息、助手消息、工具结果、inbox 拼接
    // 忽略的事件必须 return state（同一引用）
  },
  wire: { viewSchema, view: state => /* 给 Client 的瘦视图 */ }
}
~~~

**为什么这样最优**：`stateOf` 永远与日志一致；fork 会自然继承；旧 reader 遇到未知字段不炸；checkpoint 缓存自动生效。
**代价**：`apply` 必须纯（不能发网络请求）。→ 任何需要外部 IO 的"反思"必须发生在 **工具调用**里，把结果落回一条既有事件（工具调用天然就是日志的一部分），再被 `apply` 折叠。这是本设计最关键的技巧。

## 5. "一个操作，两个调用者"

~~~js
// host/actions.js —— 唯一实现
async function setMood({ session, mood }) { /* 校验 → 落日志（经 agent.inject 或工具结果）→ 返回 status */ }

// host/tools.js —— 给模型
defineTool({ name: 'dsh_world_mood', parameters: {...}, output: {...},
  execute: (args, exec) => actions.setMood({ session: exec.session, mood: args.mood }) })

// client —— 给用户：经 Client 可调用入口调同一个 actions.setMood
~~~

**用户专属动作**（批准、确认删除、授权外部记忆）只保留 UI 路径，工具侧不暴露。

## 6. 与旧版的行为差异（必须让用户知道）

| 项 | 旧 | 新 |
| --- | --- | --- |
| 聊天 | 插件自带 chat，八轮上下文 | 就是 DSH 会话 |
| 主动问候 | Host 心跳 + 自建预算 | `agent.followup()` + 会话内限额投影；默认关 |
| 房间布局 | state.json 内嵌 | 工作区 `world/room.json`，可 git |
| 成长记录 | 自建 JSON + Hindsight 依据 | 投影 fold；Hindsight 降级为可选"反思"工具 |
| 备份 | 自建 v1–v5 | 文件本身即备份（git / 用户目录） |

## 7. 失败与降级策略

- 房间文件损坏 → **报告**，绝不覆写成默认；提供 `dsh_world_room_repair`（需用户确认）。
- 投影越界（stateVersion 变更）→ 保留旧键、新键加后缀，避免静默错读。
- 插槽组件抛错会清空整个条目 → 组件入口包 try/catch，降级为一行提示。
- 外部记忆不可达 → 明确"本次未使用记忆"，不伪造记得。
