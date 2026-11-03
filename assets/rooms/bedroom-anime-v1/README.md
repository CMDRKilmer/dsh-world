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

## 未验证

**没有做过肉眼验收。** 生成侧模型不具备图像输入能力，无法读取 PNG。以下均未确认，须由人看图：

- 11 件家具是否全部出现、是否被画成别的物体（尤其 MP3、手机、电饭煲这类小件）。
- 三面墙的比例与透视是否成立。
- 书桌是否真的位于窗户正下方。
- 配色与线稿观感是否符合预期。
