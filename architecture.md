# 架构说明

> **状态：设计定稿，未实施。** 目标宿主 **DSH Desktop 0.2.1-rc.5**（内嵌 Node 24.21.0）。
> 本文替代旧版 `architecture.md`（旧版描述的是 Godot 实验视图与自建 HTTP 总线，已废弃）。
> 设计细节见 [docs/redesign/](docs/redesign/README.md)；本文只讲**边界与不变量**。
>
> 契约标注：**[已核实]** = 读取 0.2.1-rc.5 内 `app.asar` 真实实现得出；**[待核实]** = 实施前必须确认。

## 1. 定位

插件是一个 **DSH bundle**，不是独立应用。它与 Harness 的关系只有四种：

| 关系 | 机制 | 用途 |
| --- | --- | --- |
| 挂载 | `dsh.bundle.patch` → `cordis.patch.yml` | 让插件进入 profile 插件树 |
| 读日志 | `ctx.sessionProjections` | 派生成长、在场、房间归属 |
| 给能力 | `ctx.tools` + `defineTool` | 让模型操作这个家 |
| 给界面 | `ctx.slots` | 让用户看见这个家 |

**不新增第五种关系。** 没有自建总线、没有自建存档、没有自建聊天通道。

## 2. 三条不变量（违反即视为架构缺陷）

**I1 · 单一真源。** 每个事实只有一处权威：
- 对话与成长事实 → DSH 会话日志
- 房间布局与人设 → 工作区文件
- 运行时缓存 → storage domain（只作缓存，丢失可重建）

**I2 · 可从日志重建。** 派生状态必须能由「会话日志 + 工作区文件」重算。fork 后子会话状态与父一致；撤销到 seq N 后状态正确回退。

**I3 · 一个操作一份实现。** 同一业务动作只有一处代码；模型经工具调用、用户经 UI 调用，都收敛到这一个 Host 方法。授予权限类动作**只有用户**这条路径。

## 3. 三层与边界

```
┌─ Client（浏览器）────────────────────────────────────┐
│  React 组件，经 ctx.slots.inject / register 注册        │
│  只做：渲染、点击、乐观反馈                             │
│  不做：业务规则、写存档、调模型、跨组件读 DOM             │
└──────────────────────────────────────────────────────┘
                        ↕  投影 wire.view / 同一 Host 方法
┌─ Host（插件 apply）───────────────────────────────────┐
│  ctx.dshWorld：唯一业务真源                             │
│  ├─ rooms      房间文件读 / 校验 / 写（版本守卫）        │
│  ├─ persona    人设基线，模型不可写                      │
│  ├─ actions    life.* / room.* 的唯一实现               │
│  ├─ projections growth / presence / room-of-session     │
│  └─ surfaces    tools（代理） + webServer（只读资源）    │
└──────────────────────────────────────────────────────┘
                        ↕  只用公开接缝
┌─ Harness 内核（只读，不改）────────────────────────────┐
│  session log · agent loop · tools · slots · fs · storage│
└──────────────────────────────────────────────────────┘
```

**边界规则：**
- Client **不得**直接读写文件、不得持有业务状态；它读的是 `wire.view`。
- Host **不得**渲染 HTML、不得拼句子给用户看（文案归 Client locale）。
- 插件 **不得**改 Harness 内核；需要内核没有的能力时，走工具体系而非私有分支。

## 4. 目录结构

```
dsh-world/
  package.json          dsh.bundle.patch + dsh.client
  cordis.patch.yml      一个 host 行
  index.js              Host: export apply / inject / Config
  client.js             Client: __ModuleLoader__ 工厂（构建产物）
  locale/{zh,en}.json   meta.title / meta.description
  icon.svg
  host/
    service.js          ctx.dshWorld 注册与生命周期
    rooms.js persona.js actions.js
    projections/{growth,presence,room-of-session}.js
    tools.js            defineTool × N，全部代理 actions.js
    assets.js           webServer 只读资源
  client/
    panel.jsx room-canvas.jsx controls.jsx
  world/                与宿主无关的纯逻辑（可单测，无 ctx）
    geometry.js pathing.js palette.js packs.js
  assets/               按需，体积受控
```

`world/` 是唯一允许「没有 ctx」的目录——它是本仓库最稳的资产，可独立测试。

## 5. 已核实的 DSH 契约

| 能力 | 真实形态 | 关键限制 |
| --- | --- | --- |
| 插件本体 | `export function apply(ctx, config)`；`inject`/`Config` 可选 | 所有资源必须在 `apply` 内 `ctx.effect`/`ctx.on` 注册并返回清理 |
| 工具 | `defineTool({name,description,parameters,output:{schema,render},execute})` | 参数 Schema 仅子集：**无 `anyOf`/`$ref`/`patternProperties`** |
| 投影 | `ctx.sessionProjections.register({key,stateVersion,init,apply,wire})` | `apply` 必须**纯且同步**；忽略事件须返回同一引用 |
| 持久化 | `ctx.storage.domain.open(spec)` → 调用方 `close()` | 带 zod 校验；`invalidRecords:'backup-and-skip'` 可选 |
| Web 路由 | `ctx.webServer.register({kind,path,handler})` | 重复 (kind,path) 抛错；只用于只读资源 |
| 提示词 | `ctx.systemPrompt.section(section)` | 只加文本；**不得**用 `system-prompt/assemble` 增删工具 |
| 界面 | `ctx.slots.inject(owner, () => ctx.slots.register({name,id,order}, Comp))` | 组件抛错会**清空整个插槽条目** |

**实测得到的插槽名**（[已核实] 于 dsh-pet / dsh-client-ui-sidebar / conversation）：
`sidebar.panellist`、`sidebar.panellist.actions`、`sidebar.right.pane.tab`、`shell.overlay`、`shell.leading`、`root`、`settings.section`、`conversation.composer.dock`、`conversation.chat.node`。

## 6. 数据流

**用户改房间：**
点击 → 组件乐观高亮 → Host `actions.setRoom`（版本守卫读改写）→ 成功 → 投影 `onChanged` 推送 → 视图重绘。
失败 → 回退高亮 + 显示 `reason`。**视图永远跟随投影，不跟随响应。**

**模型改房间：**
模型调用 `dsh_world_room_edit` → 同一 `actions.setRoom` → 工具结果进日志 → 同一投影推送 → UI 同步更新。

**成长推进：**
`apply(state, event)` 消费既有事件（用户消息 / 助手消息 / `tool/result` / `agent/inbox/spliced`）→ 纯计算派生。
需要外部 IO 的「反思」必须先由**工具**执行，结果作为 `tool/result` 落进日志，再被 fold 吸收。
→ 因此成长**永远**可在日志里找到依据，未经工具落盘的外部结论不会进入状态。

## 7. 生命周期与资源释放

| 资源 | 归谁 | 释放点 |
| --- | --- | --- |
| 投影注册 | 插件 ctx | `ctx.effect` 返回的 disposer |
| 工具 | `ctx.inject(['tools'], …)` 作用域 | 随插件卸载 |
| 插槽注册 | `ctx.slots.inject(owner, …)` | owner 折叠 / 插件卸载 |
| storage domain | 本插件持有句柄 | 自己的 `ctx.effect` 里 `close()` |
| webServer 路由 | `register` 返回值 | 随 `apply` 清理 |
| 定时器 / 请求 | 单一 AbortController | `dispose()` 统一 `abort()` |

**卸载后不得残留**：无插槽条目、无路由、无定时器、无挂起请求。

## 8. 失败与降级

| 情形 | 行为 | 禁止 |
| --- | --- | --- |
| 房间文件损坏 | 报告错误 + 只读展示 | ❌ 覆写成默认 |
| read-only 会话写房间 | 拒绝并给出原因 | ❌ 静默失败 |
| 投影 stateVersion 变更 | 旧键保留，新键加后缀 | ❌ 静默错读旧值 |
| 插槽组件抛错 | 顶层接管，降级为一行提示 | ❌ 让整条目空白 |
| 外部记忆不可达 | 明说「本次未使用记忆」 | ❌ 伪称记得 |
| 工作区无写权限 | 只读模式 + 说明 | ❌ 自动写到别处 |

## 9. 与旧架构的差异

| 项 | 旧（0.3–0.11） | 新 |
| --- | --- | --- |
| 总线 | `POST /api/dsh-world/action` | 工具体系 + 同一 Host 方法 |
| 存档 | `.dsh/dsh-world/<profile>/state.json` | 工作区 `world/room.json` |
| 聊天 | 插件自带 + 八轮上下文 | DSH 会话本身 |
| 成长 | 自建 JSON 写入 | 会话投影 fold |
| UI | 自建 React 页面 + iframe + Godot HUD | Slots |
| 真源 | 3 处（内存 / state.json / Godot 控制器） | 2 处（日志 / 工作区文件） |

## 10. 未决事项

1. **Godot 舞台去留** — 建议暂缓（作渲染后端接入，不承担业务）。
2. **记忆主库** — 建议会话日志为主，Hindsight 为可选反思后端。
3. **UI→Host 的官方入口形态** — [待核实]，实施第一步确认。
4. **`--dsw-alias-*` 令牌清单** — [待核实]，做界面前查 `Theme`。
