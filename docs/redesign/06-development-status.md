# 开发完成表

> **本文是项目进度的唯一权威。** 其它文档不得单独宣称完成度。
> 证据等级：**实测** > **运行通过** > **代码存在** > **规划**。只有前两者可计入"已完成"。
>
> 最后更新：设计定稿当日。当前整体状态：**设计完成，编码未开始。**

## 图例

| 标记 | 含义 |
| --- | --- |
| ✅ | 已完成且有实测证据 |
| 🟡 | 代码/产物存在，但未经真实宿主验证 |
| ⬜ | 未开始 |
| 🚫 | 明确不做（非目标或已废弃） |
| ⚠️ | 受阻 / 待决策 |

## 0. 总览

| 里程碑 | 目标 | 状态 |
| --- | --- | --- |
| 设计 | 架构、规则、完成表定稿 | ✅ |
| M0 | 能装：最小骨架装上即生效 | ⬜ |
| M1 | 能有家：房间文件 + 投影 + 读写 | ⬜ |
| M2 | 有成长：投影 fold + 反思工具 + 撤销 | ⬜ |
| M3 | 有陪伴：主动生活（默认关） | ⬜ |
| M4 | 有美术：像素房间 | ⬜ |
| M5 | Godot 舞台（待决策） | ⚠️ |

## 1. 设计阶段 ✅

| 交付物 | 内容 | 证据 |
| --- | --- | --- |
| [architecture.md](../../architecture.md) | 三层边界、三条不变量、已核实契约、数据流、生命周期 | 本文档树 |
| [AGENTS.md](../../AGENTS.md) | 开发规则（含契约核实纪律、安装纪律） | 本文档树 |
| [01-dsh-capability-map.md](01-dsh-capability-map.md) | DSH 0.2.1-rc.5 能力面，逐条标注核实状态 | 解包读 `app.asar` 实现 |
| [02-architecture.md](02-architecture.md) | 目录结构、Host 骨架、投影设计 | 同上 |
| [03-data-and-memory.md](03-data-and-memory.md) | 房间/人设/成长数据分层、迁移 | 同上 |
| [04-ui.md](04-ui.md) | 插槽分工、交互模型、视觉验收 | 同上 |
| [05-roadmap-acceptance.md](05-roadmap-acceptance.md) | M0–M5、旧代码取舍 | 同上 |

**设计阶段实际做过的核实**（不是"读过文档"）：
- 解析 `app.asar` 头部，枚举 **307** 个 `@deepseek-ai/*` 包，确认生产包**无 `.d.ts`**。
- 读取 `dsh-tools/lib/index.js` → `defineTool` 真实签名与 Schema 子集。
- 读取 `dsh-session-projection` → `register/stateOf/onChanged` 语义与"纯同步 fold"要求。
- 读取 `dsh-storage-domain` → `open(spec)` 与调用方 `close()` 责任。
- 读取 `dsh-host-webserver` → `register({kind,path,handler})`。
- 读取官方脚手架 `cordis-plugin-development`（SKILL + 5 篇 references + 2 套模板）。
- 从已装社区插件中实测插槽名（`sidebar.panellist`、`sidebar.right.pane.tab`、`shell.overlay`、`settings.section` 等）。

## 2. M0 · 能装 ⬜

| 项 | 验收标准 | 状态 |
| --- | --- | --- |
| `package.json`（`dsh.bundle.patch` + `dsh.client`） | 字段严格套官方模板 | ⬜ |
| `cordis.patch.yml` | 单 host 行，id 唯一 | ⬜ |
| `index.js`（`apply`/`inject`/`Config`） | 只注册一个空 service | ⬜ |
| `client.js`（ModuleLoader 工厂，id=包名） | 能在浏览器加载不报错 | ⬜ |
| `locale/{zh,en}.json` | `meta.title`/`meta.description` 中英各一份 | ⬜ |
| `icon.svg` | 合法 SVG，≤256 KiB，留在包内 | ⬜ |
| `files` 白名单 | 装完后实际文件列表已核对 | ⬜ |
| 安装 | `plugin_manager` 返回 `application: applied` | ⬜ |
| 设置分区 | `settings.section` 显示"鲸屿已安装" | ⬜ |
| 卸载 | 插槽条目消失，无残留 DOM/路由/定时器 | ⬜ |

⚠️ 已知风险：`install_bundle` 每个动作需审批 → 一次备齐再装。

## 3. M1 · 能有家 ⬜

| 项 | 验收标准 | 状态 |
| --- | --- | --- |
| `world/room.json` 读写 | 走 `ctx.fs`，读-改-写带版本守卫 | ⬜ |
| `actions.setRoom` | 唯一实现；冲突时重读重试而非覆盖 | ⬜ |
| `dshWorld.room` 投影 | `stateVersion:1`，`wire.view` 只给瘦视图 | ⬜ |
| `dsh_world_room_get` / `_edit` 工具 | 代理同一 action | ⬜ |
| `sidebar.panellist` 入口 | 侧栏可见，点击开面板 | ⬜ |
| `sidebar.right.pane.tab` 房间视图 | 无美术，色块网格即可 | ⬜ |
| read-only 拒绝 | 编辑被拒 + 原因可见 | ⬜ |
| 损坏文件 | 报错 + 只读展示，不覆写 | ⬜ |

## 4. M2 · 有成长 ⬜

| 项 | 验收标准 | 状态 |
| --- | --- | --- |
| `dshWorld.growth` 投影 | 纯 fold，忽略事件返回同一引用 | ⬜ |
| 撤销到 seq N | 状态正确回退 | ⬜ |
| fork 一致性 | 子会话成长与父一致 | ⬜ |
| `dsh_world_reflect` 工具 | 结论经 `tool/result` 落日志后被 fold 吸收 | ⬜ |
| 无外部记忆 | 明说"本次未反思"，不编造 | ⬜ |
| 人设边界 | 模型无任何写入人设的路径 | ⬜ |

## 5. M3 · 有陪伴 ⬜

| 项 | 验收标准 | 状态 |
| --- | --- | --- |
| `agent.followup()` 定时活动 | **默认关闭**；关闭时零主动消息 | ⬜ |
| 频率/免打扰 | 写会话投影，不建自建额度文件 | ⬜ |
| 退出行为 | 退出 DSH 不补做离线活动 | ⬜ |

## 6. M4 · 有美术 ⬜

| 项 | 验收标准 | 状态 |
| --- | --- | --- |
| `world/isometric.js` 搬入 | 纯函数 + 单测 | ⬜ |
| `world/motion.js` 搬入 | 纯函数 + 单测 | ⬜ |
| Canvas 房间渲染 | 整数倍缩放、pixelated | ⬜ |
| 家具拾取与保存 | 乐观反馈 + 跟随投影 | ⬜ |
| 视觉实机验收 | 中英 × 深色/浅色 四项通过 | ⬜ |

## 7. M5 · Godot ⚠️ 待决策

建议暂缓。若恢复，**只作渲染后端**，不得承担业务。

## 8. 旧代码处置 ⬜（尚未执行）

> 工作树当前为空，全部文件在 `HEAD` 中。处置动作需先 `git checkout -- .` 再逐路径处理。

| 路径 | 计划处置 | 状态 |
| --- | --- | --- |
| `server/http.js`、`server/store.js` | 删除（自建总线/存档） | ⬜ |
| `server/{world,spaces,life,scheduler}.js` | 重写为 service + 投影 | ⬜ |
| `server/tools.js` | 重写为 `defineTool` | ⬜ |
| `shared/{isometric,motion,palette,pathing}` | 搬入 `world/` 并加测 | ⬜ |
| `furniture/**` | 保留定义与素材，重写加载器 | ⬜ |
| `client/**`（旧 React 页面） | 删除，由插槽组件取代 | ⬜ |
| `godot/**` | 冻结至 M5 | ⬜ |
| `services/hub.mjs` | 移出仓库（独立服务器） | ⬜ |
| `releases/*.tgz`、`*.sha256`、`*.audit.json` | 删除（12 个历史包） | ⬜ |
| `docs/0.4.x–0.11.0` 预览稿 | 归档，避免与新设计冲突 | ⬜ |

## 9. 已废弃 🚫

| 项 | 理由 |
| --- | --- |
| `docs/plugin-design.md`（旧产品蓝图） | 假设已被 DSH 真实契约取代，由 `docs/redesign/` 替代 |
| 旧 `architecture.md`（Godot 实验视图 + 自建总线） | 与新架构冲突 |
| `/api/dsh-world/action` 动作总线 | 由工具体系 + 同一 Host 方法取代 |
| 自建 `state.json` 与 schema 迁移链 | 由工作区文件取代 |
| 插件自带聊天（八轮上下文） | 由 DSH 会话取代 |
| Godot 作为第二套 UI + 业务控制器 | 违反 I1 单一真源 |

## 10. 待核实清单（阻塞实现）

| # | 事项 | 阻塞谁 | 状态 |
| --- | --- | --- | --- |
| 1 | Client 读投影的官方 hook 形态（`useResource` / `wire.view`） | M1 | ⚠️ |
| 2 | UI→Host 的官方推荐入口（`remote.commands.execute`？） | M1 | ⚠️ |
| 3 | `sidebar.right.pane.tab` / `shell.overlay` 的 props 形状 | M1 | ⚠️ |
| 4 | `--dsw-alias-*` 令牌清单（`Theme` 查询） | M1/M4 | ⚠️ |
| 5 | `ctx.fs` 在 Host 插件中是否受 session 沙箱约束 | M1 | ⚠️ |

**这 5 项未核实前，M0 可以照常做（M0 不依赖它们），M1 不得开工。**

## 11. 更新规则

每次里程碑推进时：
1. 先更新本表状态，再写代码。
2. 每条 ✅ 必须写清证据（命令输出 / 截图 / tool result 摘要）。
3. 未通过验收的，保持 ⬜ 并写明卡点，不降级为"基本完成"。
