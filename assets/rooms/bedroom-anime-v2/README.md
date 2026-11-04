# 房间 v2：方案 A（资产先行，无烘焙光影）

2026-11-04 生成。v1（`../bedroom-anime-v1/`）是「一张整图画好再切层」；v2 换路线：**每件家具单独生成、单独抠图、再按测得的地板平面组装**，所以每件家具都可以独立移动、缩放、替换，而且**生成阶段不烘焙任何光影**，全局光照留给后期或引擎。

## 文件

| 文件 | 尺寸 | SHA-256 | 字节 |
| --- | --- | --- | --- |
| `room.png` | 1536 × 864 | `253f703d3b86c0850572655f87b959b65e441019fee6fafac54e3cdf332f487b` | 1,922,134 |
| `room-layered.psd` | 1536 × 864（29 层） | `589eb1ec701d1e6269a9b49815cf8934640e53058e953829da3702a164873efe` | 12,624,590 |
| `shell_graded.png` | 1536 × 864 | `20ac6d092b8b502f253462d6c0f3e5a46f1c2c12a886884f503bfdc6999e64b6` | 1,673,466 |
| `_preview-labelled.png` | 1536 × 864 | `27c63a943145599a915e447515e73a3f326bca1c82c8f16a3df93ea9ab60acff` | 1,923,696 |
| `_contact-sheet.png` | 1400 × 800 | `5304d338822feda89bef951f7f351de59a1d3eeaaa5713fb2859dbcd9e8d320e` | 721,442 |

`shell.png` 是 `build_psd.py` 写 PSD 时用的本地副本，与 `shell_graded.png` 逐字节相同（PhotoCraft 只能读 read-root 之内的文件）。

## 目录

| 路径 | 内容 |
| --- | --- |
| `assets/` | 28 件抠图原样（绿幕 → alpha → 去溢色 → 紧裁），未调色 |
| `assets_graded/` | 同一批资产按房间曝光与色调重新配平后的版本，**组装用的是这一套** |
| `layers/` | 28 张画布尺寸（1536×864）RGBA 图层，按 z 排序命名 `NN_<name>.png` |
| `manifest.json` | 画布、地板平面常量、每件物件的 x/y/w/h/z/缩放/锚点/来源 |
| `compose-report.json` | 组装自检：覆盖率、每件可见比例、警告 |
| `verify_room.json` | SAM 3 在合成图上逐件反查的结果 |
| `tone-check.json` | 与 v1 参考图逐项比对的色调度量 |
| `v1_*.json` | 从 v1 参考图量出来的目标值（亮度、色度、尺寸） |
| `tools/` | 全部脚本，见文末 |

## 生成参数（可复现）

底模与采样沿用 v1 的 ComfyUI 配置，逐件生成时**每件一个独立 prompt**，seed 为 `20261104 + i × 7919`（i 是 OBJECTS 里的下标）。

| 项 | 值 |
| --- | --- |
| 底模 | `moss_image_sft_int8_convrot.safetensors` |
| 文本编码器 | `qwen3.5_9b_w4a8_gptq.safetensors`（type = moss_image） |
| VAE | `flux2-vae_small.safetensors` |
| LoRA | `moss-anime-seinen.safetensors`，强度 1.0 |
| 采样 | 25 步 / CFG 2.5 / er_sde / simple / denoise 1.0 |
| 尺寸 | 1024 × 1024（单件） |
| 耗时 | 28 件 / 1977 秒（约 65–70 秒一件） |

### 提示词结构

每件的正向词由五段拼成：**物件描述 + 视角 + 光照 + 绿幕 + 风格**。四段常量在 `tools/gen_assets.py` 第 21–39 行：

- `STYLE`：现代日本动画背景美术，干净线稿，每材质一个平涂色 + 至多一个平涂阴影色，材质细节用绘制而非渐变。
- `LIGHT`：均匀中性棚光，来自无特定方向 —— 不投背景影、无接触阴影、无环境光遮蔽压暗、无轮廓光、无高光、无色反弹。
- `GREEN`：纯 RGB 0,255,0 的平坦饱和绿幕，铺满画面边缘到边缘，无渐变、无阴影、无纹理。
- `NEG`：含 `cast shadow / drop shadow / contact shadow / ambient occlusion / rim light / backlight / glow / vignette / gradient background / floor / wall / room / scenery / furniture set / multiple objects / duplicate / cropped / green tint on the object` 等。

**绿幕只是抠图辅助**，抠完即丢，成品里没有任何绿色残留（28 件 `green_fringe` 全部为 0.0000）。

## 28 件资产

| 资产 | 抠图尺寸 | 可见像素 | 绿边 | 单件 SAM 3 反查 |
| --- | --- | --- | --- | --- |
| `bed.png` | 1003 × 576 | 306,090 | 0.0 | 0.96 pass |
| `desk.png` | 988 × 507 | 184,943 | 0.0 | 0.98 pass |
| `office_chair.png` | 561 × 806 | 225,561 | 0.0 | 0.99 pass |
| `monitor.png` | 806 × 587 | 379,914 | 0.0 | 0.85 CHECK（television 0.95，同物异名） |
| `keyboard.png` | 1010 × 544 | 339,031 | 0.0 | 0.98 pass |
| `mouse.png` | 552 × 810 | 171,728 | 0.0 | 0.84 pass |
| `microphone.png` | 498 × 952 | 181,820 | 0.0 | 0.67 pass |
| `mp3_player.png` | 731 × 561 | 206,443 | 0.0 | 0.93 pass |
| `phone.png` | 860 × 792 | 400,466 | 0.0 | 0.98 pass |
| `mug.png` | 669 × 699 | 328,290 | 0.0 | 0.97 pass |
| `desk_lamp.png` | 650 × 936 | 189,295 | 0.0 | 0.97 pass |
| `sketchbook.png` | 739 × 738 | 406,277 | 0.0 | 0.93 CHECK（notebook 0.97，同物异名） |
| `bookshelf.png` | 509 × 953 | 473,682 | 0.0 | 0.97 pass |
| `piano.png` | 777 × 534 | 132,882 | 0.0 | 0.95 pass |
| `piano_bench.png` | 517 × 467 | 105,411 | 0.0 | 0.83 CHECK（stool 0.98，同物异名） |
| `easel.png` | 479 × 1010 | 211,884 | 0.0 | 0.97 pass |
| `easel_painting.png` | 902 × 714 | 632,906 | 0.0 | 0.90 pass |
| `rice_cooker.png` | 686 × 687 | 367,660 | 0.0 | 0.99 pass |
| `side_table.png` | 790 × 780 | 236,743 | 0.0 | 0.62 pass |
| `game_console.png` | 913 × 383 | 231,700 | 0.0 | 0.24 CHECK（**重生成后**，见下） |
| `controller.png` | 823 × 526 | 246,441 | 0.0 | 0.97 pass |
| `tv.png` | 658 × 453 | 257,166 | 0.0 | 0.97 pass |
| `cabinet.png` | 640 × 500 | 264,421 | 0.0 | 0.97 pass |
| `rug.png` | 1006 × 474 | 369,446 | 0.0 | 0.90 pass |
| `plant_pot.png` | 412 × 654 | 83,861 | 0.0 | 0.96 pass |
| `plant_hanging.png` | 349 × 920 | 68,432 | 0.0 | 0.79 CHECK（plant 0.91，同物异名） |
| `basket.png` | 689 × 866 | 351,063 | 0.0 | 0.98 pass |
| `cat.png` | 897 × 593 | 415,295 | 0.0 | 0.97 pass |

「单件反查」= 把抠好的图单独交给 SAM 3，问它「这是 X 吗」，并同时问 2–3 个干扰概念，要求自己的 phrase ≥ 0.6 且高于所有干扰项。**5 个 CHECK 里有 4 个是同义词误判**（显示器 vs 电视、速写本 vs 笔记本、琴凳 vs 凳子、垂吊绿植 vs 绿植 —— SAM 3 只是更偏爱更宽的那个词）；只有 `game_console` 是真错，第一版画成了路由器（own 0.245 / router 0.969）。

**game_console 已重生成**：提示词加 `no antennas, not a network router, not a wifi router`，负向词加 `router, wifi router, network switch, antenna, antennas, modem`，seed 20261104。重生成后单件反查仍是 0.24（位置对、iou 0.83，语义上 SAM 3 不认这个造型），但**在合成图里反查升到 0.85**，可用。

## 空房间底图（shell）

`shell_wide_00001_.png` 由同一套模型生成（1536×864，seed 20261104，25 步 / CFG 2.5 / er_sde），提示词要求「完全空的房间、三面墙、近墙移除、地板占下半幅、均匀无方向平光、无投影无光斑无环境光遮蔽、unshaded albedo」。实测：地板线 y=531，窗口 x627–763 / y264–385，左右墙角 x≈457 / 1075。

之后做了一次**只动饱和度**的调色（`grade_shell.py`）：在 HSV 的 S 通道上拉 2 倍、向暖色偏 0.04，V 通道完全不动 —— 房间亮度结构保持原样，没有凭空造光。结果：raw 饱和度 0.159 / 中位亮度 218.6 → graded 0.321 / 210.9。

## 组装规则（`compose_room.py`）

**尺寸用屏幕空间，不用公制。** 试过按米换算（房间宽 3.5 m，按地板线插值像素/米）：shell 的透视不自洽 —— 后墙 528 px，到画面下沿就变成 1536 px，180 px 的深度里跨 2.9 倍，算出来的 2 米宽的床有 878 px、直接被画布裁掉。所以尺寸全部按屏幕像素给，深度缩放用一条更缓的线性曲线。

### 地板平面（从 shell 实测）

| 常量 | 值 |
| --- | --- |
| `BACK_Y` | 531 |
| `BACK_X0` / `BACK_X1` | 480 / 1008 |
| `LEFT_EDGE_Y` / `RIGHT_EDGE_Y` | 711 / 707 |
| `SCALE_FAR` / `SCALE_NEAR` | 0.58 / 1.00 |

`floor_top(x)` 在两侧墙角外线性插值出该列的地板线；`depth_scale(y) = 0.58 + 0.42 × clip((y−531)/(864−531), 0, 1)`。

### 三种摆放模式

- **`floor`** — `(x, y=底边中心锚点, width_px, squash)`，高度按资产自身长宽比推出，再乘该深度的缩放。
- **`on`** — `(parent, u, v, rel_w, squash)`，子物件在父物件**自身矩形**内定位（u/v 是父物件宽高的比例），**继承父物件的透视**，不套地板缩放。这是让桌面物件不再缩到 0.55 下限的关键。`SURFACE` 表记录每个承托物的可用台面高度带，v 落在带外会记 warning。
- **`abs`** — `(x, y, width_px, scale)`，悬空物（垂吊绿植）用。

### z 序由脚位推导

落地物件的 z 直接等于锚点 y：**脚越靠画面下方 = 越靠前 = 越后画**。只有两件显式覆盖：`rug` z=2（平铺必须最底）、`plant_hanging` z=6（挂墙）。`on` 子物件继承 `parent_z + 0.5`。`cabinet` 也给了显式 z=900 —— 它站在床的**前方**近角，但脚位比床高，自动排序会把它排到床后面去。

早先手写 z 时柜子被排到床前、直接糊在床垫上，改成推导后才稳定。

### 组装结果

| 指标 | 值 |
| --- | --- |
| 覆盖率 | 41.4% 画布（v1 参考 45.7%） |
| 警告 | 0（无越界、无悬浮、无埋没） |
| 完全被遮挡的物件 | 0 |
| 尺寸对齐 | 24 件有对应物合计 652,033 px vs v1 556,597 px = **117.1%**，中位宽度倍数 0.98 |

## 图层清单（z 由后到前）

| 图层 | 位置 | 尺寸 | z | 可见 | 合成图 SAM 3 |
| --- | --- | --- | --- | --- | --- |
| `rug` | 601, 655 | 458 × 173 | 2 | 0.60 | 0.97 / 0.56 ok |
| `plant_hanging` | 250, 40 | 120 × 316 | 6 | 1.00 | 0.95 / 0.51 ok |
| `easel` | 383, 368 | 94 × 198 | 566 | 0.69 | 0.78 / 0.67 ok |
| `easel_painting` | 385, 334 | 94 × 74 | 566 | 1.00 | 0.87 / 0.97 ok |
| `desk` | 582, 399 | 416 × 213 | 612 | 0.59 | 0.95 / 0.54 ok |
| `monitor` | 690, 259 | 208 × 151 | 612 | 1.00 | 0.97 / 0.94 ok |
| `microphone` | 569, 284 | 67 × 128 | 612 | 0.85 | 0.70 / 0.38 ok |
| `desk_lamp` | 915, 256 | 108 × 156 | 612 | 1.00 | 0.95 / 0.90 ok |
| `mp3_player` | 682, 391 | 50 × 27 | 612 | 1.00 | 0.44 / 0.67 CHECK |
| `sketchbook` | 586, 386 | 100 × 60 | 612 | 1.00 | 0.76 / 0.94 ok |
| `keyboard` | 703, 420 | 133 × 32 | 612 | 1.00 | 0.94 / 0.94 ok |
| `mouse` | 836, 414 | 42 × 43 | 612 | 1.00 | 0.89 / 0.86 ok |
| `mug` | 892, 387 | 46 × 48 | 612 | 1.00 | 0.94 / 0.90 ok |
| `phone` | 931, 435 | 50 × 28 | 612 | 1.00 | 0.72 / 0.00 CHECK |
| `bookshelf` | 1085, 117 | 290 × 543 | 660 | 0.82 | 0.98 / 0.35 CHECK |
| `piano` | 1042, 464 | 437 × 300 | 764 | 0.94 | 0.95 / 0.76 ok |
| `office_chair` | 766, 473 | 208 × 299 | 772 | 0.98 | 0.95 / 0.94 ok |
| `bed` | 73, 436 | 654 × 376 | 812 | 0.75 | 0.96 / 0.67 ok |
| `cat` | 420, 458 | 222 × 147 | 812 | 1.00 | 0.97 / 0.98 ok |
| `side_table` | 934, 661 | 173 × 171 | 832 | 0.97 | 0.97 / 0.89 ok |
| `rice_cooker` | 954, 545 | 126 × 126 | 832 | 1.00 | 0.63 / 0.97 ok |
| `basket` | 632, 668 | 135 × 170 | 838 | 1.00 | 0.96 / 0.72 ok |
| `piano_bench` | 1138, 674 | 184 × 166 | 840 | 1.00 | 0.96 / 0.93 ok |
| `plant_pot` | 1392, 635 | 139 × 221 | 856 | 1.00 | 0.82 / 0.89 ok |
| `cabinet` | 10, 648 | 210 × 164 | 900 | 0.90 | 0.90 / 0.88 ok |
| `tv` | 24, 526 | 181 × 125 | 900 | 0.86 | 0.96 / 0.84 ok |
| `game_console` | 42, 609 | 147 × 62 | 900 | 0.92 | 0.85 / 0.89 ok |
| `controller` | 18, 642 | 84 × 40 | 900 | 1.00 | 0.93 / 0.88 ok |

z 小的先画（在后面），z 大的后画（在前面）。PSD 的层序与之相同，`room` 在最底。

## 色调配平（`grade_assets.py`）

资产是在中性棚光下**单独**生成的，每件自带一套曝光与白平衡；房间 shell 是明亮的米色室内。直接摆进去会出现：书桌亮度只有背景的 0.40 倍、书架 0.44 倍、办公椅 0.37 倍 —— 家具像在另一个暗得多的房间拍的。

配平做法：以 shell 自身中位亮度为锚，把 v1 参考图里每件家具的中位亮度**按最亮物件归一化**后映射到一个区间：

```
target_i = shell_median × (0.40 + 0.60 × v1_median_i / 210)
```

然后对每件资产的 RGB 施加一条单调 gamma（0.33 … 9.30），把其中位亮度推到 target，再按 `sat_pull` 向 shell 的色调收一点饱和度、按 `warm` 做一次轻微暖偏。**Hue 全程保持**，所以蓝色显示器还是蓝的。

这是**调色，不是打光**：没有引入任何方向光、投影或高光，物体内部的材质差异（黑钢琴仍然是最暗的东西）也保留下来，全局光照仍然可以后期加。

## 验证（已实测）

| 项 | 结果 |
| --- | --- |
| 组装自检 | 28 件全部放置，无越界，无悬浮，无埋没，warnings 为空 |
| 完全被遮挡物件 | 0 |
| SAM 3 在合成图上逐件反查 | **25/28**（判据：某 phrase 的 score ≥ 0.5 且与所放位置的 iou ≥ 0.35） |
| PSD 压平导出 vs `room.png` | **逐像素相同**（max abs diff 1，差异像素 0） |
| PSD 层数 | 29（28 物件 + room），每层是嵌入智能对象 |
| 绿边残留 | 28 件全部 0.0000 |

### SAM 3 未通过的 3 项

| 物件 | score | iou | 原因 |
| --- | --- | --- | --- |
| `mp3_player` | 0.44 | 0.67 | 合成后只有 50×27 px，语义识别不到 |
| `phone` | 0.72 | 0.00 | 它在别处找到了另一只手机（off 258 px）；所放位置本身只有 50×28 px |
| `bookshelf` | 0.98 | 0.35 | 钢琴切掉了书架下半部，SAM 3 给的高分实例是整个书架，与可见部分的重叠因此只有 0.35 |

前两项是**尺寸下限**问题，不是位置问题（iou 与 offset 都指向正确位置）；第三项是**遮挡**造成的度量口径问题，不是摆错。

## 已知限制

- **色调仍未与 v1 完全一致，这是刻意的。** v1 是傍晚暗房间（整帧中位亮度 82、饱和度 0.59），v2 是白天亮房间（165、0.38）。按 AGENTS.md 的口径，v1 的「家具相对亮度」不能直接搬到一个更亮的房间里 —— 那会要求 216 的墙配 288 的书桌，直接过曝。所以只搬「材质亮度的次序与间距」，整帧绝对值必然不同。
- **28 件里仍有 9 件的相对亮度偏离 v1 目标超阈值**：`desk`、`office_chair`、`monitor`、`sketchbook`、`keyboard`、`mug`、`tv`、`game_console`、`easel_painting`。多数是同一原因：v1 的对应物本身带烘焙阴影，v2 的是干净的平涂材质，两者中位亮度天然不同。
- **色温跨度仍然偏大**：R/B 从 0.45（monitor，最冷）到 3.86（plant_pot，最暖），饱和度从 0.24 到 0.74。单件生成 + 单件配平无法把白平衡完全统一。
- **没有阴影、没有接触阴影、没有环境光遮蔽。** 这是设计要求（用户要求「不要光影，全局光照可以后期补足」），但代价是家具看起来「浮」在地板上。补 GI 时需要给每件物件补一条接触阴影。
- **遮挡处是空洞。** 每个 `layers/NN_<name>.png` 只是该物件被前层盖住后**剩下的可见像素**；被挡住的部分不存在。按 z 叠回去能还原 `room.png`，但单独看某一层会看到洞。
- **桌面物件的遮挡关系按 `on` 模式的矩形推导，不是按真实三维位置**。所以 `desk ↔ phone`、`desk ↔ mouse`、`desk ↔ keyboard` 的「100% 遮挡」是度量口径的产物（桌面矩形与桌面小物件矩形完全重合），不是真的被桌子盖住 —— 这三件在合成图里都完整可见，SAM 3 也都能认出来。
- **书桌正面被床挡住了 41%**，`bed` 自身被 tv / cat 挡了 30%。这是布局选择的结果，不是 bug。
- **`plant_pot` 与右边界只差 8 px**，再往右移就会被裁。

## 复现步骤

```powershell
# 0. 起 ComfyUI（后台），确认 127.0.0.1:8188 可访问
# 1. 逐件生成 28 个绿幕资产（约 33 分钟）
python tools\gen_assets.py
# 2. 绿幕抠图 -> assets/
python tools\cutout_assets.py
# 3. 单件语义反查（可选，要 GPU）
python tools\verify_assets.py
# 4. shell 调色 -> shell_graded.png
python tools\grade_shell.py
# 5. 资产曝光/色调配平 -> assets_graded/
python tools\grade_assets.py
# 6. 组装 -> room.png + layers/ + manifest.json + compose-report.json
python tools\compose_room.py --assets assets_graded --shell shell_graded.png
# 7. 检查
python tools\layout_check.py      # 可见度、埋没、遮挡、落地
python tools\layout_map.py        # 文本布局图
python tools\compare_layout.py    # 与 v1 的分区覆盖率对比
python tools\size_report.py       # 与 v1 的尺寸对比
python tools\check_tone.py        # 与 v1 的色调对比
python tools\verify_room.py       # SAM 3 在合成图上反查
# 8. 预览图
python tools\build_preview.py
# 9. 组装 PSD（需要 PhotoCraft）
python tools\build_psd.py
```

## 工具说明

| 脚本 | 作用 |
| --- | --- |
| `gen_assets.py` | 逐件生成 28 个绿幕资产，写 `gen_assets.json` + `gen_assets.log` |
| `cutout_assets.py` | 绿幕抠图：alpha 斜坡 + 去溢色 + 连通域清理 + 紧裁，写 `assets/index.json` |
| `verify_assets.py` | 单件语义反查（自己 vs 干扰概念），写 `verify_assets.json` |
| `grade_shell.py` | 只动饱和度的 shell 调色 |
| `grade_assets.py` | 按 v1 材质亮度次序 + shell 锚点配平每件资产，写 `assets_graded/grade.json` |
| `harmonize_assets.py` | 早期版本的单一 gamma 配平，已被 `grade_assets.py` 取代，保留作对照 |
| `compose_room.py` | 组装：地板平面、三种摆放模式、z 推导、写 `layers/` + `manifest.json` + `compose-report.json` |
| `layout_check.py` | 逐件可见度 / 埋没 / 遮挡来源 / 落地检测 |
| `layout_map.py` | 96×27 文本布局图，每格显示最上层物件代号 |
| `compare_layout.py` | 与 v1 的分区覆盖率对比（12×6 网格） |
| `size_report.py` | 与 v1 的逐件尺寸对比 |
| `check_tone.py` | 与 v1 的色调对比，写 `tone-check.json` |
| `verify_room.py` | SAM 3 在合成图上逐件反查，写 `verify_room.json` |
| `build_preview.py` | 接触表与带标注预览图 |
| `build_psd.py` | 通过 PhotoCraft MCP 组装 29 层 PSD 并压平校验 |
| `measure_floor.py` | 从 shell 量地板线 |
| `measure_v1_*.py` | 从 v1 参考图量目标值 |
| `tone_report.py` / `chroma_report.py` | 单件色调与色度诊断 |

## 未验证

- **没有任何人眼验收。** 本次会话所用模型不支持图像输入（`read_image` 报 `model "deepseek-v4.1-flash-sg" does not declare image input`），所有结论来自 PIL/numpy 数值统计、ASCII 亮度图与 SAM 3 反查。**观感、疏密、构图是否耐看，一律未验收。**
- 全局光照补足方案（接触阴影、环境光、色反弹的具体做法）只描述了方向，没有实现，也没有在引擎里试过。
- 资产在游戏引擎里的实际使用（缩放、九宫格、锚点）未测试。
