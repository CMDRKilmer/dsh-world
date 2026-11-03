# DSH 能力面与契约（0.2.1-rc.5）

> 核实方式：从 `resources/app.asar` 解包读取官方 SDK 实现与官方脚手架（`@deepseek-ai/dsh-agent-preset/skills/cordis-plugin-development`）。
> **[已核实]** 指读过真实代码；**[待核实]** 指需要在实施时用 `cordis_inspect_query` 或真机确认。

## 0. 宿主事实

- Desktop 版本 `0.2.1-rc.5`，内嵌 Node `24.21.0`，pnpm `11.28.5`。【已核实：`runtime/primary-runtime/runtime.json`】
- 体系是 **Cordis 插件树 + profile patch 层**；profile 的 `cordis.yml` 是一个空数组，全部由 `package.json` 的 `dsh.profile.bundles` 与 `cordis.patch.yml` 叠加而成。【已核实】
- 当前 desktop profile 已装 16 个 bundle，含 Agent Teams、billion-context、super-code、recall、ssh-workspace 等。【已核实】
- SDK 共 **307 个 `@deepseek-ai/*` 包**，生产包**不提供 `.d.ts`**（只有 JSDoc 的实现文件）。【已核实】→ 意味着设计时只能以**运行时实现**为准，不能靠类型想象。

## 1. 插件形态（必须遵守）

官方脚手架 `cordis-plugin-development` 的硬规则【已核实，读 `SKILL.md` 与 `references/host-plugin.md`】：

- 一个 bundle = `package.json` 声明 `dsh.bundle.patch`，patch 文件用 Loader 方言 `insert: [{id, name, config}]`。
- Host 半：`export function apply(ctx, config)`，可选 `export const inject = ['tools']`、`export const Config`；**所有资源必须在 `apply` 内用 `ctx.effect`/`ctx.on` 注册并返回清理函数**。
- Client 半：`exports['./client']` + `dsh.client = {platform:'web', immediately:true, inject:[...]}`；浏览器侧是 `window.__ModuleLoader__.load({ id, factory(require) {...} })`，**id 必须等于包名**，React 由宿主的模块表提供。
- 显示元数据：`locale/en.json` 的 `meta.title`/`meta.description`，图标经 `./icon` 导出（SVG/PNG/JPEG/WebP ≤ 256 KiB，必须留在包内）。
- **禁止**在 `~/.dsh` 下手写 `package.json`/`cordis.patch.yml` 或跑 pnpm；安装一律走 `plugin_manager install_bundle`。

结论：新插件的目录结构应严格套用官方 `templates/decoration`，不要自创 manifest 字段。

## 2. 工具接缝（陪伴动作的出口）【已核实 `dsh-tools/lib/index.js`】

`defineTool` 的真实契约：

~~~js
defineTool({
  name, description,
  parameters,          // 属性表 → 编译成 object-root JSON Schema
  output: { schema, render(args, value), presentationMeta? },
  timeoutMs?, deferLoading?,
  async execute(args, exec) {...},
  presentCall?, presentResult?, isConcurrencySafe?, projectContent?, finalizeContent?,
})
~~~

- 参数 Schema 只允许子集：`type`/`oneOf`/`properties`/`required`/`additionalProperties`/`items`/`enum`/`const` + 注解。**不支持 `anyOf`/`$ref`/`patternProperties`**。
- 参数在 `execute` 前被强制校验；不符抛 `ToolArgsError`。
- 输出 Schema 走 `json` 节点（annotation-only 的任意 JSON 根）。

## 3. 会话投影（成长/关系状态的唯一正确位置）【已核实 `dsh-session-projection`】

~~~js
ctx.sessionProjections.register({
  key, stateSchema, stateVersion,
  init(sessionHeader, inheritedEventCount) -> state,
  apply(state, event) -> state,      // 纯函数；忽略的事件必须返回同一引用
  wire: { viewSchema, view(state) }  // 可选：给 Client 的派生视图
})
ctx.sessionProjections.stateOf(session, key)
ctx.sessionProjections.onChanged(listener)
~~~

要点（决定了很多设计取舍）：
- 注册是 **effect**，插件卸载即从快照里消失，Client 读作"能力不存在"。
- 同一 key 可被多个插件共注册，按 refs 计数，最后一个卸载才消失。
- 单位制是**整体值**驱动：事件必须是"变更后的完整状态"，不是增量。
- `apply` 必须纯且同步；`wire.view` 返回同一引用则不触发下游发布。
- **不允许**用自定义 `type` 追加会话事件（除 `ignorable:true` 的 `plugin:` 记录，且那属于实验包）。→ **成长状态必须能从既有事件折叠出来，不能自造事件流。**

## 4. 持久化【已核实 `dsh-storage-domain`】

`ctx.storage.domain.open(spec)` 返回 domain 句柄，调用方自己 `close()`（通常挂在自己的 `ctx.effect`）。
带 `name`/`tables`（zod `valueSchema`）/`global`，加载时逐条校验，可配 `invalidRecords:'backup-and-skip'`。
- 适合**运行时缓存/索引**；不适合承载用户可读可编辑的"家"。

## 5. Web 路由【已核实 `dsh-host-webserver`】

`ctx.webServer.register({ kind:'exact'|'prefix', path, handler(req,res) })`，重复 (kind,path) 抛错，返回 disposer。
- 只用于**静态资源/JSON 只读端点**。旧插件用 `connection.fetch.register` 是另一条路，但**新设计优先工具化，宁可少用 HTTP**。

## 6. 提示词与命令【已核实】

- `ctx.systemPrompt.section(section)` 插入系统提示层（`dsh-system-prompt`）。
- `ctx.commands.register(definition)` 注册人类可用的斜杠命令（`dsh-commands`）。

## 7. Agent 循环的扩展点（来自官方 practices.md）【已核实文档】

由弱到强：`ctx.tools.restrict()` < `ctx.tools.guard()` < waterfall 监听（`agent/pre-step`、`tools/pre-execute` 等）< `system-prompt/assemble`。
- 不拥有决策的 waterfall 监听**必须** `return next()`；改写 `agent/pre-step` 时要展开原 decision。
- 加提示文本用 `systemPrompt.section()`；加每 agent 上下文用 `agent.inject()`（会被记为 inbox 拼接、进入下一步）。
- 定时器要唤醒 agent 用 `agent.followup()`；`agent.inject()` 不会唤醒。
- 等待持久事件 `turn/end`、`assistant/message`、`tool/result`；**不要轮询 `agent/status`**。

## 8. UI 插槽【已核实】

- `ctx.slots.inject(ownerKey, () => ctx.slots.register({ name, id|key, order }, Component))`；owner 折叠时卸载、回来时重装。
- 官方与社区实践中的真实插槽名（【已核实】于 dsh-pet / dsh-unlag / dsh-client-ui-sidebar / conversation）：
  - `sidebar.panellist`、`sidebar.panellist.actions`
  - `sidebar.right.pane.tab`（右侧栏标签页）
  - `shell.overlay`、`shell.leading`、`root`
  - `settings.section`
  - `conversation.composer.dock`、`conversation.chat.node`
- 样式只能用主题令牌 `--dsw-alias-*`；**不得** `require('@deepseek-ai/dsh-client-ui-primitives')`；不得写 `document.body`；不得用 iframe 承载页面（iframe 拿不到主题与 locale）。

## 9. 用户动作 ↔ 工具【已核实文档 `user-actions.md`】

一个操作只实现一次（Host service 方法）；UI 侧经 Client 可调用的 Host 入口调用；工具侧用 `defineTool` 调同一个方法。
授予/确认权限类动作**必须仅限用户**，不得给模型。

## 10. 已知坑（设计时必须绕开）

| 坑 | 后果 | 对策 |
| --- | --- | --- |
| 生产包无 `.d.ts` | 类型幻觉 | 只以 `lib/*.js` 实现为契约 |
| 不能自造 session event type | 会话无法重开 | 成长用投影 fold |
| `config` 覆盖是**整体替换** | patch 漏字段即失效 | 每次重述完整 config |
| 替换已装包需重启 | 误判"没生效" | 用 `application`/`warnings` 而非日志判断 |
| 一个抛错的组件会**清空整个插槽条目** | 页面空白 | 组件内兜底 try/catch，保持首版极简 |
| `plugin_manager` 每个动作都要审批 | 流程被打断 | 安装前一次过准备齐全，避免反复 |
| Desktop 里 `app.asar` 内文件 shell/glob/node **都读不到** | 无法用 rg 检索 | 只能用 Host 的文件读工具 |

## 11. 待核实清单（实施第一批任务）

1. Client 侧读取投影的唯一推荐姿势：`useResource`/`wire.view` 的具体 hook 形态（`dsh-client-resources`）。
2. UI→Host 的**官方推荐**入口：是 `remote.commands.execute`（dsh-pet 用法）还是别的新 API；需用 `cordis_inspect_query` 对 `remote`/`commands` 逐条确认。
3. 插槽 `sidebar.right.pane.tab`/`shell.overlay` 的 **props 形状**与 options（`Slots.listSubTree`）。
4. `--dsw-alias-*` 令牌清单（`Theme` 查询）。
5. `ctx.fs` 接缝在 Host 插件里是否直接可用、是否受 session 沙箱约束。
