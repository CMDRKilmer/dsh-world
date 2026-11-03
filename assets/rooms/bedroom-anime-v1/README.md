# 房间参考图 v1：动漫风平视卧室

2026-11-03 生成。用途是**美术方向参考与视觉验收基准**，不是运行时素材。

## 文件

| 文件 | 尺寸 | SHA-256 | 字节 |
| --- | --- | --- | --- |
| `room-reference.png` | 1536 × 864（精确 16:9） | `68e9becd0b7cb0af814d815a661b5a8c60f13148e81b63e97621fd8034de3bac` | 2,128,460 |

## 生成参数（可复现）

ComfyUI 库工作流 `anime_room_furnished`，id `f43dcfe0-bef7-4012-bfa9-7a044359b408`。

| 项 | 值 |
| --- | --- |
| 底模 | `moss_image_sft_int8_convrot.safetensors` |
| 文本编码器 | `qwen3.5_9b_w4a8_gptq.safetensors`（type = moss_image） |
| VAE | `flux2-vae_small.safetensors` |
| LoRA | `moss-anime-seinen.safetensors`（axiomofmind/Moss-image-anime-lora 的 ComfyUI 原生版，强度 1.0） |
| 采样 | 25 步 / CFG 2.5 / er_sde / simple / denoise 1.0 |
| 尺寸 | 1536 × 864 |
| seed | 20261103 |

LoRA 校验：504 个张量全部带 `diffusion_model.` 前缀，SHA-256 `6661F88183757C7BE9044578D3907335D6ABE83A736995BD502B78DB2C5B83CF`，与模型卡公布值一致；加载后日志 `lora key not loaded` 无增量。

## 构图约定（本图已满足，后续迭代须保持）

- **机位**：平视，站立视线高度，镜头正对房间。
- **墙体**：近墙移除，可见后墙与左右两面墙，共三面，竖直墙角清晰。
- **画幅**：精确 16:9。**宽高必须都是 16 的倍数**，否则 ComfyUI 自动下调——1920×1080 会变成 1920×1072（比例偏 0.746%），不可用。
- **书桌位置**：后墙窗户正下方。
- **光照**：傍晚阳光从后墙窗户射入，在地板落成暖色光斑，向上打到对面墙；窗侧暖琥珀主光、角落冷蓝补光；墙面与地板交界处有环境光遮蔽。
- **风格**：现代日本动画背景美术，干净线稿、赛璐璐平涂、硬边双色阴影、阴影内部无渐变。

## 家具清单（11 件，按位置分组）

| 位置 | 家具 |
| --- | --- |
| 后墙窗下长书桌 | 书桌、电脑（显示器 + 键鼠）、麦克风（悬臂支架）、MP3（缠绕耳机线）、手机、速写本 |
| 左墙 | 床、游戏机（含两个手柄 + 小电视，置于矮柜） |
| 右墙 | 书架、电子琴（折叠架 + 琴凳） |
| 窗边地面 | 画板（半成品画布）、电饭煲（小边几） |

环境陈设：地毯、垂吊绿植、小串灯、睡着的猫。

## 完整提示词

**正向**（8 句英文，按顺序拼接，实际使用时为一整段）：

1. Anime illustration of a cozy single bedroom seen from eye level, camera at standing height looking straight into the room, the near wall removed so three walls are visible: the back wall with a large window and the two side walls meeting it in clean vertical corners.
2. Wide cinematic 16:9 framing that shows the full width of the room, with the side walls receding toward the back wall.
3. A long wooden desk sits directly under the window on the back wall, crowded with gear: a computer monitor with keyboard and mouse, a studio microphone on a boom arm, a small MP3 player with coiled wired earbuds, a smartphone lying face up, an open sketchbook, a mug and a brass lamp, with an office chair pushed in.
4. Against the left wall a low bed with a rumpled quilt and two mismatched pillows; beside it a low wooden cabinet holding a game console with two controllers and a small television.
5. Against the right wall a tall bookshelf packed with colorful book spines, and an electronic keyboard on a folding stand with a small bench in front of it.
6. On the floor near the window a wooden easel holding a half-finished canvas; on a small side table a closed rice cooker; a woven rug, trailing potted plants, a string of small hanging lights, and a sleeping cat curled on the rug.
7. Late-afternoon sunlight pours through the window, casting a long warm parallelogram of light across the floor and up the opposite wall, with visible dust motes floating in the beam; warm amber key light from the window side and cool blue shadow fill in the corners, soft ambient occlusion where the walls meet the floor and under every piece of furniture.
8. Modern Japanese anime background art style, clean confident lineart with slightly varied line weight, flat cel-shaded color fills with crisp two-tone shadows and no gradients inside shadow shapes, soft airbrushed highlights only on metal and glass screens, painterly detail in the wood grain and fabric folds, rich but slightly desaturated palette, high production value theatrical anime film background, every object clearly separated and readable.

**负向**：

```
nsfw, worst quality, bad anatomy, watermark, text, signature, photorealistic, 3d render, pixel art, low resolution, blurry, oversaturated, chromatic aberration, distorted perspective, fisheye, letterbox, black bars, empty room, bare walls, missing furniture, cluttered mess, overlapping objects, merged objects
```

负向词里 `empty room / bare walls / missing furniture` 与 `cluttered mess / overlapping objects / merged objects` 是**对冲的一对**：既防家具不够，也防堆成一团。

## 客观度量（用于后续对比，不替代肉眼验收）

| 指标 | 数值 |
| --- | --- |
| 边缘密度（相邻像素梯度均值之和） | 13.54 |
| 与少家具版对比 | +8.5%（12.48 → 13.54） |
| 颜色数 | 333,813 |
| 平均饱和度（HSV S 通道 0–255） | 150.4 |

## 肉眼验收（2026-11-03 补做）

生成这张图的会话所用模型不支持图像输入，当时无法读图；后续会话换成可读图的模型后补做了验收，结论：

- **11 件家具全部出现**且可辨认：床、书桌、电脑（显示器＋键盘＋鼠标）、MP3（缠着耳机线）、游戏机（白色主机＋两只手柄，置矮柜）、画板（架上半成品画布）、电饭煲（边几上）、手机（桌面平放，另有左侧一只深色）、书架（贴右墙，满墙书脊）、麦克风（悬臂支架）、电子琴（折叠架＋琴凳）。
- 三面墙成立：后墙窗户居中、左右墙角竖直，近墙已移除。
- 书桌位于后墙窗下，与构图约定一致。
- 配色与线稿符合「现代日本动画背景美术」的预期。

仍属主观、无法自动度量的部分：光影观感、家具疏密是否耐看。按 AGENTS.md 的口径，这只算**美术方向通过**，不算最终美术资产验收。

## 图层拆分（layers/）

把参考图拆成 **27 个对象图层 + 1 个房间背景图层**，z=0 最靠近镜头。

| 文件 | 内容 |
| --- | --- |
| `layers/room.png` | 整幅 1536×864，家具所占像素为透明 |
| `layers/NN_<name>.png` | 单个对象，裁切到自身包围盒，RGBA |
| `layers/manifest.json` | 画布尺寸、源图 SHA-256、每个图层的 z / 文件名 / 裁剪框 / 可见像素数 / 底部锚点 |
| `layers/preview.png` | 全部图层的接触表（棋盘格＝透明） |
| `tools/split_layers.py` | 生成脚本，参数化可复现 |

### 叠加规则

`manifest.json` 里 `z` 越小越靠前。合成顺序：先铺 `room.png`，再按 z 从大到小画，最后画 z=0。

### 验证（已实测）

| 项 | 结果 |
| --- | --- |
| 像素覆盖 | 1.0（每个像素恰好属于一个图层） |
| 按规则重新合成 vs 原图 | **逐像素完全相同**（`recomposite_exact = true`） |

互斥划分由「前向 claim」保证：对象按 z 从前往后依次抢占，已被抢走的像素不再分配给后面的对象，剩下的像素归 `room.png`。

### 方法

1. **SAM 2.1 hiera-large**（`facebook/sam2.1-hiera-large`）box + 正/负点提示，每个对象一次前向（约 0.8 s）。床与矮柜由多个部件提示并集（床头横杆、床垫枕头、被子、柜面、柜门）。
2. **手绘多边形**：书桌（平视视角下桌面只剩一条 70–100 px 的横带）与书架（贴墙的平木板）用多边形而不是 SAM，避免碎成横条。
3. 掩膜清理：夹到提示框 ±14 px、5×5 闭运算、填洞、丢弃小于最大连通域 2% 的碎片。
4. 前向 claim 分区（见上）。

### 图层清单（z 由前到后）

`cat` · `piano_bench` · `chair` · `rug` · `piano` · `stool` · `rice_cooker` · `bed` · `plant_floor` · `microphone` · `monitor` · `desk_lamp` · `computer_keyboard` · `sketchbook` · `mp3_player` · `phone` · `phone_black` · `mug` · `plant_desk` · `tv` · `game_console` · `desk` · `bedside_cabinet` · `bookshelf` · `easel` · `plant_left` · `plant_right`

### 已知限制（不是缺陷，是拆分方式的必然结果）

- **遮挡处是空洞。** 后排对象被前排挡住的部分没有像素——地毯上猫的位置、桌面被显示器/键盘/椅子挡住的位置都是洞。按叠加规则合成时这些洞被前层盖住、不可见；单独看后排图层会看到洞。
- **书桌上的小杂物并进了书桌图层**：鼠标、收音机、纸杯、线材等没有单独成层，留在 `21_desk.png` 里。
- **书架上垂吊的绿植并进了书架图层**，没有单独成层。
- **没有做补绘（inpainting）。** `room.png` 是被家具占掉像素后剩下的部分，不是「空房间底图」；要一张没有家具的空房间图，需要额外走一次生成式补绘，本次未做。
