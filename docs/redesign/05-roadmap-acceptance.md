# 分期、验收与旧代码取舍

## 分期（每期都能独立装上去用）

### M0 · 能装（1 个迭代）
- 官方模板骨架：`package.json` + `cordis.patch.yml` + `index.js` + `client.js` + locale + icon。
- Host：`ctx.dshWorld` service 空壳，只提供 `getStatus()`。
- Client：`settings.section` 显示"鲸屿已安装 · 房间文件：world/room.json"。
- **验收**：`plugin_manager install_bundle` 返回 `application: applied`；设置页出现该分区；卸载后消失。

### M1 · 能有家（房间文件 + 投影）
- `world/room.json` 读写（走 `ctx.fs`，带版本守卫）。
- 注册 `dshWorld.room` 投影（`stateVersion: 1`），Client 经 `wire.view` 读瘦视图。
- `sidebar.panellist` 入口 + `sidebar.right.pane.tab` 只读房间网格（先无美术，用色块）。
- 工具：`dsh_world_room_get` / `dsh_world_room_edit`（同一 action 方法）。
- **验收**：模型能用工具改房间；用户在同一会话看到投影刷新；read-only 会话下编辑被拒且原因可见。

### M2 · 有成长（投影 fold + 反思工具）
- 注册 `dshWorld.growth`，纯 fold。
- `dsh_world_reflect` 工具（可选外部记忆）；无后端时明确返回"本次未反思"。
- 里程碑视图（`settings.section` 或右栏标签页）。
- **验收**：fork 会话后成长状态与父一致；撤销到 seq N 后状态正确回退；无外部记忆时不出现"编造记得"。

### M3 · 有陪伴（主动生活）
- `agent.followup()` 驱动的定时活动，**默认关闭**，Config 可开。
- 免打扰/频率写入会话投影（不是自建额度文件）。
- **验收**：关闭时不产生任何主动消息；开启后每日上限生效；退出 DSH 不补做。

### M4 · 有美术（像素房间）
- 搬回 `shared/isometric.js`/`motion.js`/`palette.js` 为 `world/*` 纯函数并单测。
- Canvas 渲染、家具拾取、保存。
- **验收**：视觉实机确认（见 [04](04-ui.md#验收视觉部分)）。

### M5 ·（待决策）Godot 舞台
仅当 M4 的像素房间无法满足观感时才考虑，且必须**作为渲染后端**接入，不得再承担业务。

## 决策：Godot 舞台去留

旧版让 Godot 直接构建 HUD/设置/聊天/背包/回忆/成长，并复用 HTTP 动作总线——它事实上成了第二套应用。
这与本次重设计的核心冲突（**一个真源**）。

三种选择：

| 选择 | 代价 | 适用 |
| --- | --- | --- |
| **A. 暂缓**（建议） | 旧 Godot 代码冻结在 git 历史里 | M0–M4 期间完全不需要 |
| B. 只做渲染后端 | 需要一层"投影 → 场景快照"的适配，且输入事件要回灌成 action | 美术要求像素 3D/等距光照 |
| C. 保留现状 | 双真源，问题原样保留 | 不推荐 |

建议 A：**先把"DSH 原生"这条腿站稳，再谈舞台。**

## 旧代码取舍

| 路径 | 处置 | 理由 |
| --- | --- | --- |
| `server/http.js`、`server/store.js` | **删除** | 自建总线/存档，被工具+文件取代 |
| `server/world.js`、`spaces.js`、`life.js`、`scheduler.js` | **重写** | 逻辑保留，但形态要改成 service + 投影 |
| `server/tools.js` | 重写为 `defineTool` | 旧版是可选注入的 3 个工具，粒度太粗 |
| `shared/isometric.js`、`motion.js`、`palette.js`、`pathing` | **搬进 `world/` 并加测** | 纯函数，无宿主依赖，是最有价值的资产 |
| `furniture/**` | 保留定义与素材，重写加载器 | 声明式定义思路正确 |
| `client/**`（旧 React 页面） | **删除** | 由插槽组件取代 |
| `godot/**` | 冻结（M5 再议） | 见上 |
| `services/hub.mjs`（社区/同步服务） | **移出仓库** | 它是独立服务器，不是插件 |
| `releases/*.tgz`、`*.sha256`、`*.audit.json` | **删除** | 12 个历史包，非运行资源 |
| `docs/` 旧文档（0.4.x–0.11.0 预览稿） | 归档 | 与新版冲突，易误导 |

## 验收纪律（继承旧版规矩并加强）

- 只有**实测**才算完成：`application: applied` + 目标能力可见可用。
- 自动化测试不替代：像素观感、麦克风、系统语音、通知、深浅色。
- 未验证的部分**明确写"未验证"**，不得用"已实现"代填。
- 每个里程碑结束时产出：变更清单、证据（命令输出/截图/日志片段）、未验证项。

## 立即可做的第一批任务（建议顺序）

1. 建 `package.json`/`cordis.patch.yml`/`index.js`/`client.js`/`locale`/`icon.svg`（严格套官方模板）。
2. 用 `plugin_manager install_bundle` 安装（**先跑通再写业务**）。
3. 用 `cordis_inspect_query` 核实 [01 §11](01-dsh-capability-map.md#11-待核实清单实施第一批任务) 的 5 个待核实项。
4. 再进入 M1。
