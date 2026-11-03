# 项目开发规则

> 适用：本仓库全部代码与文档。优先级：用户明确指令 > 本文件 > 外部技能/工具默认建议。
> 与旧版规则相比，本版新增了**契约核实纪律**与**安装纪律**，其余沿用。

## 1. 任务路由

| 要做的事 | 先读 |
| --- | --- |
| 改架构、改边界、加新机制 | [architecture.md](architecture.md) |
| 改数据形态、房间/人设/成长字段 | [docs/redesign/03-data-and-memory.md](docs/redesign/03-data-and-memory.md) |
| 加 UI 界面、改插槽 | [docs/redesign/04-ui.md](docs/redesign/04-ui.md) |
| 查 DSH 到底提供什么 | [docs/redesign/01-dsh-capability-map.md](docs/redesign/01-dsh-capability-map.md) |
| 判断某项是否"已完成" | [docs/redesign/06-development-status.md](docs/redesign/06-development-status.md) |
| 美术与像素规格 | [docs/redesign/04-ui.md](docs/redesign/04-ui.md) |

## 2. 工作契约

- 本地隔离环境或分支中的读取、编辑、单元测试为预授权，不中途询问。
- 常规可逆决策合理假设后推进；仅在缺少严重影响正确性或权限边界的信息时提问。
- 外部技能不得引入无必要的暂停或偏离。
- **不把规划写成已实现。** 文档里每一条"已完成"必须对应一次真实运行证据。

## 3. 契约核实纪律（本版新增，最重要的一条）

DSH 是**生产构建**：`app.asar` 内的 307 个 `@deepseek-ai/*` 包**不带 `.d.ts`**，只有带 JSDoc 的实现文件。

因此：

1. **不得凭类型或印象编写代码。** 任何 Service 方法、事件名、参数形状，必须来自下列之一：
   - `cordis_inspect_query`（`Service` / `Event` / `Tool` / `Slots` / `Theme` / `Config.listConfigs`）
   - 已安装包的 `lib/*.js` 源码
   - 官方脚手架 `@deepseek-ai/dsh-agent-preset/skills/cordis-plugin-development`
2. 文档中区分 **[已核实]** / **[待核实]** 两种标注，不得混用。
3. 待核实项在**动手实现前**必须先核实；核实不了的，写进"未验证"而不是猜一个答案。

### 已知陷阱（反复踩过，列在此处避免重犯）

- `config` 覆盖是**整体替换**，不是深合并 —— patch 时必须重述完整 config。
- 工具参数 Schema 只支持子集：**无 `anyOf` / `$ref` / `patternProperties`**。
- 投影 `apply` 必须**纯且同步**；忽略的事件必须返回**同一引用**。
- **不能自造 session event type**（自造的会话将无法重新打开）。
- 插槽组件一旦抛错，会**清空整个插槽条目** —— 每个组件入口必须有兜底。
- Desktop 里 `app.asar` 内文件：`ls` / `cat` / `rg` / `node` **全部读不到**，只能用 Host 自己的文件读工具。
- 替换已安装包需**重启**才加载新模块；判断是否生效看 `application`/`warnings`，不看日志。

## 4. 安装纪律（本版新增）

- **不要在 `$DSH_HOME` 下手写 `package.json` / `cordis.patch.yml`，不要在 profile 目录跑 pnpm。**
- 安装一律走 `plugin_manager` 的 `install_bundle`（`actions` 需审批，不要反复调用）。
- 安装前一次过备齐：manifest、patch、locale（中英）、图标、`files` 白名单。避免因缺一项而反复审批。
- **先装最小骨架再写业务**：M0 跑通 `application: applied` 之前，不写第二行业务代码。

## 5. 代码规则

- **单一真源。** 新状态必须有唯一归属；不得出现"内存一份 + 文件一份"。
- **一个操作一份实现。** UI 与工具调用同一个 Host 方法；不得各写一遍业务逻辑。
- **`world/` 目录不得 import 任何 `ctx` 或 DSH 包** —— 它是纯函数区，必须能脱离宿主单测。
- **资源必须可释放。** 每个 `ctx.effect` / `ctx.on` / 定时器 / 请求都要有清理路径。
- **文案不进 Host。** 面向用户的字符串走 Client locale。
- **颜色不写死。** 界面只用 `--dsw-alias-*` 令牌；字面颜色仅允许出现在美术素材。
- 不新增依赖，除非已说明理由且能举出无法用现有能力实现的例子。

## 6. 界面规则

- 先选渲染面再写视图；选错面之后调 CSS 救不回来。
- 不使用 iframe 承载页面（拿不到主题令牌与 locale）。
- 不 `require` 宿主 UI 包（会随版本变）；需要控件时**抄**行为与结构，并改到自己的前缀下。
- 不写 `document.body`、不读别的插件的 DOM/样式。
- 可点元素必须是真实 `<button>` 或 `role="switch" aria-checked`；Escape 关闭、焦点回收。
- 尊重 `prefers-reduced-motion`。

## 7. 验证纪律

| 改动 | 最低验证 |
| --- | --- |
| `world/` 纯函数 | 单元测试（`node --test`） |
| Host service / actions | 单元测试 + 一次真实调用 |
| 工具 | 实际让模型调一次，看 tool result |
| 插槽 UI | 装上去实机看，中英各一次 |
| 文档 | 与代码交叉核对，不留悬空引用 |

- **"装上了" ≠ "用户看到了"。** 未做浏览器实测前，只报告"已安装、已注册插槽"，不声称视觉验收通过。
- 自动化测试不替代：像素观感、麦克风、系统语音、通知、深浅色。
- 未验证的部分**明确写"未验证"**。

## 8. 数据与迁移

- 不静默丢弃旧布局、旧人设。迁移前备份，重建由用户明确选择。
- 迁移**只读**旧文件，不改旧文件；失败即中止并保留原文件。
- 字段变更必须同步更新 [03](docs/redesign/03-data-and-memory.md) 与完成表的字段列。

## 9. 美术与内容

- 像素尺寸、帧数、锚点、调色板**未经样板验证不写死**；确认后回写文档。
- 家具保持声明式（`definition.js` + `manifest.json` + 素材），不执行第三方代码。
- 内容包只允许受限像素矩形与调色板；记录来源、许可、权限。
- 第三方素材必须可再分发，并保留归属声明。

## 10. 文档纪律

- 规划、实现、验收三者分开表述，**不互相冒充**。
- 完成表是唯一的进度权威；其它文档不得单独宣称完成度。
- 删除或推翻旧文档时，在完成表的"已废弃"区留一行记录与理由。
