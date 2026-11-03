# 重新设计：从「自带一套运行时」到「Harness 原生的一份生活」

> 状态：**设计提案**（未实施）。基线：现有 0.11.0 源码（git HEAD），目标宿主 **DSH Desktop 0.2.1-rc.5**。
> 本文档集用于替换旧的 `docs/plugin-design.md`（那是一份面向"通用插件"的蓝图，其假设已被 DSH 实际契约取代）。
> 所有对 DSH 的断言都标注了核实状态：**[已核实]** = 读取了 0.2.1-rc.5 内的真实实现；**[待核实]** = 实施前必须再确认。

## 一句话结论

旧插件把自己做成了一个**寄生在 DSH 里的独立应用**：自建 HTTP 动作总线、自建 JSON 存档、自建 React 页面、自建对话与短期上下文、自建 Godot 业务旁路。
新插件应该把自己做成一个 **DSH 的一等公民**：会话日志是唯一事实源，状态用投影派生，界面用插槽贡献，能力用工具暴露，文件留在工作区里。

**这不是换皮，是把"记忆 / 成长 / 房间 / 陪伴"四个概念重新映射到 DSH 已有的四个机制上。**

## 四组映射（本次重设计的核心）

| 旧概念（自建） | 新落点（DSH 原生） | 收益 |
| --- | --- | --- |
| 自建 JSON `state.json` + 自建 action 总线 | **工作区文件** + `ctx.fs` 接缝 | 用户可读可改、可 diff、可 git、可被 agent 直接读写 |
| 自建对话 + 八轮短期上下文 | **DSH 会话本身**（Session log） | fork / 回放 / 压缩 / 统计 / 搜索全部免费获得 |
| 成长日志 / 兴趣 / 里程碑（自建写入） | **`ctx.sessionProjections` 纯 fold** | 可从日志重建、可撤销到某 seq、可 checkpoint |
| 自建 React 页面 + iframe + Godot 业务桥 | **Slots（插槽）** | 主题令牌、locale、布局一致；卸载即回收 |
| 动作白名单 `/api/dsh-world/action` | **工具 + 同一个 Host 方法** | 模型与用户共用一条实现（"一个操作、两个调用者"） |

## 文档索引

| 文档 | 回答什么 |
| --- | --- |
| [01-dsh-capability-map.md](01-dsh-capability-map.md) | DSH 到底给了什么？哪些契约已核实、哪些是坑 |
| [02-architecture.md](02-architecture.md) | 新架构分层、模块边界、插件的 `apply` 骨架 |
| [03-data-and-memory.md](03-data-and-memory.md) | 房间/人设/成长怎么存，记忆与 Hindsight 怎么降级 |
| [04-ui.md](04-ui.md) | 界面落在哪些插槽，视觉与交互规则 |
| [05-roadmap-acceptance.md](05-roadmap-acceptance.md) | 分期、验收标准、旧代码的取舍与迁移 |

## 相对旧版**保留**的部分

- 产品灵魂：不惩罚、不签到、不假装有意识、成长不覆盖用户设定边界。
- 像素资产与角色图集、`furniture/*` 的目录式家具定义、`shared/` 里的几何/寻路/调色板纯函数。
- 内容包（content pack）的**受限声明式**思路与来源/许可记录。
- 备份、可撤销、来源可追溯的用户控制原则。

## 相对旧版**明确放弃**的部分

- `/api/dsh-world/action` 自建动作总线与 36 MB 请求体。
- `.dsh/dsh-world/<profile>/state.json` 自建存档与自建 schema 迁移链。
- 插件自带聊天（含 `previousResponseId` 式八轮上下文）——改为寄生 DSH 会话。
- 把 Godot 当作"第二套 UI + 业务控制器"的业务旁路。
- 随包内置 130 MB 素材与 `releases/*.tgz` 历史包。

## 实施前必须先回答的三个问题

1. **是否保留 Godot 舞台？** 见 [05](05-roadmap-acceptance.md#决策-godot-舞台去留)；建议先降级为可选渲染后端，M0–M2 完全不引入。
2. **记忆主库是谁？** 见 [03](03-data-and-memory.md#记忆主库决策)；建议 DSH 会话日志为主、Hindsight 为可选外部后端。
3. **房间是文件还是数据库域？** 见 [03](03-data-and-memory.md#房间的存储形态)；建议房间=工作区文件，运行时缓存=storage domain。
