# Stylized Asset Suite for Blender · 参数逻辑参考手册

> 分析对象：`E:\rj\blender\plugin\addons\shaderaddon`（**Stylized Asset Suite for Blender**，作者 crzyzha，v1.0，适配 Blender 4.1+）
> 数据来源：源码 `__init__.py`（12334 行）+ Blender 4.2 实测追加 `nodegroups.blend` 后逐组自省 interface（输入名/默认值/范围）+ 面板 UI 的友好参数名映射 + EEVEE 实渲染验证。
> 用途：**作为"自然语言需求 → 本插件（风格化着色工具）节点组"映射的知识依据**（见 SKILL.md 第二部分）。它记录 SAS 各效果的参数语义（阈值/染色/阶梯/遮罩等处理逻辑），映射时据此决定用本插件的哪些组、怎么设参数。
> ⚠️ 该插件与"风格化着色工具"（blender_Stylized-Shading-Tools，路人甲）是**两套独立插件**：本手册只作逻辑参考，SAS 节点组未搬入本插件。

---

## 0. 插件总览

| 项 | 值 |
|---|---|
| 面板位置 | 3D 视图 N 侧栏 → **Stylized Asset Suite**（含 Background Settings 世界背景 + Shader 主面板） |
| 核心概念 | 给物体建基底材质（Base Color 组）→ 用下拉菜单"Select Effect to Add"逐个**追加效果组**（自动插入到链尾）→ 每个效果组是独立节点组，UI 面板按组显示参数 |
| 材质链 | `Base Color → [效果1] → [效果2] → ... → 材质输出`（新效果总是插到材质输出之前） |
| 渲染器 | 主要面向 **EEVEE**（Shader to RGB 需要 EEVEE 才实时；Cycles 需烘焙），基底设置自动开 GTAO + Bloom |
| 世界 | WorldSetup 一键建 `layeredworld`（Base Gradient 节点组驱动渐变背景） |
| 效果分类 | 光照着色 / 手绘贴图 / 风格化点光源 / 描边 / 纹理 / 调色 / 对象特效 / 烘焙导出 |
| 基底材质 | `bpy.ops.shaderaddon.objectsetup()`：新建材质，挂 `basecolor` 节点组（7 节点：RGB 底色 + 可选 Image Texture + Mix），连到材质输出；材质 blend_mode=BLENDED |

**AI 添加效果的统一入口**（等价于面板下拉+Add Effect 按钮）：

```python
import bpy
scene = bpy.context.scene
scene.my_operator_enum = 'DIFFUSELIGHTING'   # 枚举值见 §1 表格
bpy.ops.shaderaddon.execute_operator()        # 等价于直接调 bpy.ops.shaderaddon.addxxx()
```

每个效果也都有独立操作符（如 `bpy.ops.shaderaddon.adddiffuselighting()`），AI 可直接调用。

**参数访问模式**（所有效果组通用）：效果组是材质链上的 GROUP 节点，参数即组输入；UI 面板把输入索引映射为友好名。AI 用索引或名字改默认值：

```python
mat = bpy.context.active_object.active_material
node = next(n for n in mat.node_tree.nodes if n.type=='GROUP' and n.node_tree.name.startswith('DiffuseLight'))
node.inputs[4].default_value = 0.6          # Light Slider/Controller（友好名）
node.inputs[21].default_value = (1,0.5,0.2,1)  # Colorize Highlight（RGBA）
# 节点组内部被命名的子节点也可直接改，如 node.node_tree.nodes['Map Range'].interpolation_type = 'STEPPED'
```

---

## 1. 效果目录与操作符速查

| 枚举 | 面板名 | 操作符 | 节点组 | 分类 |
|---|---|---|---|---|
| `DIFFUSELIGHTING` | Stylized 3D Lighting (Main) | `adddiffuselighting` | `DiffuseLight` (126 节点) | 光照 |
| `SPECULAR` | Add Specular Reflection | `addspecularreflection` | `SpecularReflection` (48) | 光照 |
| `MOODLIGHT` | Add Colored Circular Light | `addcoloredcircularlight` | `ColoredCircular` (23) | 光照 |
| `CIRCULARLIGHTING` | Add Circular Lighting | `addcircularlight` | `CircularLight` (10) | 光照 |
| `CROSSHATCHING` | Cross Hatch Lighting | `addcrosshatch` | `CrossHatch` (41) | 光照 |
| `AO` | Add Ambient Occlusion | `addao` | `AmbientOcclusion` (18) | 光照 |
| `CURVATURE` | Add Curvature | `addcurvature` | `AddCurvature` (44) | 光照 |
| `FAKELIGHT` | Add Stylized 3D Light (Per Object) | `addobjectlight` | `LightObject` (25) + 几何节点修改器 | 光照 |
| `HAIRCURVES` | Anisotropic Hair Reflection | `addhaircurves` | `HairCurves` (33) | 光照 |
| `DRAWPAINT` | Texture Paint / Draw | `addtexturepaint` | `TexturePaint` (16) | 手绘 |
| `DRAWONECOLOR` | Draw with Single Color | `addsinglecolor` | `SingleColor` (10) | 手绘 |
| `WORLDSTROKES` | Simple Transparency / Strokes | `addtransparentworldstrokes` | `TransparentWorldStrokes` (13) | 手绘 |
| `VERTEXPAINT` | Draw with Vertex Paint | `addvertexpaint` | `VertexPaint` (20) | 手绘 |
| `TRANSPARENTPAINT` | Watercolor/Charcoal Effect | `addtransparentpaint` | `TransparentPaint` (54) | 手绘 |
| `SPLRed/Green/Blue` | Stylized Point Light #1/2/3 | `addredlight/addgreenlight/addbluelight` | `RedLightSAS/GreenLightSAS/BlueLightSAS` (18) | 点光源 |
| `SOLIDIFYOUTLINE` | Add Object Outline | `addsolidifyoutline` | 修改器 + `solidifyoutline` 材质 | 描边 |
| `EDGEDETECT` | Add Edge Detect | `addedgedetect` | `EdgeDetect` (15) | 描边 |
| `COLOREDEDGES` | Add Colored Edges | `addcolorededges` | `ColoredEdges` (17) | 描边 |
| `LOCALGRADIENT` | Local Gradient (Rect) | `addlocalgradient` | `LocalGradient` (42) | 纹理 |
| `LOCALGRADIENTSPHERE` | Local Gradient (Sphere) | `addlocalgradientsphere` | `LocalGradientSphere` (40) | 纹理 |
| `INSTANTWATERCOLOR` | Stylized Grunge | `addinstantwatercolor` | `InstantWatercolor` (16) | 纹理 |
| `EASYDT` | Dynamic Texture (Simple) | `addeasydt` | `EasyDT` (19) | 纹理 |
| `NOISETEXTURE` | Dynamic Texture | `addnoisetexture` | `NoiseTexture` (106) | 纹理 |
| `OVERALLTEXTURE` | Texture Overlay | `addoveralltexture` | `OverallTexture` (18) | 纹理 |
| `BRUSHSTROKES` | Dynamic Brush Strokes | `addbrushstrokes` | `BrushStrokes` (44) | 纹理 |
| `STYLIZEDFOAM` | Stylized Foam | `addstylizedfoam` | `StylizedFoam` (36) | 纹理 |
| `TRANSPARENTNOISE` | Dynamic Texture (Transparent) | `addtransparentnoise` | `TransparentNoiseTexture` (119) | 纹理 |
| `CONTRAST` | Add Contrast | `addrgbcurves` | `RGBContrast` (7) | 调色 |
| `HSL` | Add HSL Effect | `addhsl` | `FinalHSL` (9) | 调色 |
| `OBJECTRANDOMIZE` | Add Object Randomization | `addobjectrandomize` | `ObjectRandomize` (19) | 调色 |
| `FOG` | Fog Object | `addfog` | `SB Fog` 材质对象 | 对象 |
| `STEAM` | Steam Object | `addsteam` | `SB Steam` 材质对象 | 对象 |
| `GODRAYS` | Godray Effect | `addgodrays` | `SB Godrays` 材质对象 | 对象 |
| `DISPLACE` | Displace Effect | `adddisplace` | `SB Disp` 修改器 + Clouds 纹理 | 对象 |
| `BAKE` | Bake Shader | `bakeall` + 各子烘焙 | — | 导出 |
| `BAKEANIMATED` | Bake (Animated) | `bakeanimationprotocol` | — | 导出 |
| `BAKENORMALS` | Bake Normals | `bakenormals` | — | 导出 |

> ⚠️ 互斥关系：`DiffuseLight` 与 `CrossHatch` 都是"光照"级效果，同一材质只能二选一（操作符检测到对方存在会直接 return）；`FAKELIGHT/FAKESUN` 是每物体灯光（几何节点 + 空物体）。多个 `LocalGradient`/`NoiseTexture` 等纹理效果可以叠加。

---

## 2. 光照与着色类（核心）

### 2.1 DiffuseLight —— Stylized 3D Lighting (Main)（126 节点，54 输入）

**实现架构**：Diffuse BSDF（Normal 走 NormalSwitch 法线混合）→ Shader to RGB → `ImportantRange`（Map Range，From Min=输入[4]）→ `Map Range`（From Max=输入[5]、Steps=输入[6]）得到**可调过渡曲线/阶梯化**的亮度系数 → 亮部(Highlights)与暗部(Shadows)各自 HSV + 染色混合 → 叠 rim(Fresnel)、Metallic、Distort/Bump、Painterly、Masks 后输出。输出除 `Result` 外还有 `Custom`（Shader to RGB 原色）、`LightMask`、`BSDF`（可接烘焙）。

面板参数（友好名 → 输入索引 → 默认 → 作用）：

| 面板分组 | 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|---|
| 主 | Light Slider/Controller | [4] From Min | 0.0 | 亮度阈值下限：越大阴影区越大（整体变暗） |
| | Sharpen Light | [42] To Max | 1.0 | 亮度阈值上限（LINEAR 模式下显示）：越小高光越少 |
| | Toon Steps | [6] Steps | 3.5 | 阶梯化级数（非 LINEAR 时显示），越大色带越细 |
| | Blend Style | Map Range.interpolation | — | `LINEAR/STEPPED/SMOOTHSTEP/SMOOTHERSTEP`，过渡曲线 |
| | Darken Edge | [30] Value | 1.0 | 边缘压暗强度（基于相机 View Vector 距离） |
| | Distance | [29] Value | 0.02 | 边缘压暗的距离系数 |
| 高光 | Light Value | [3] Value | 1.0 | 高光亮度（Hue/Saturation/Value 的 Value） |
| | Colorize Highlight | [21] B | 白 | 高光染色色 |
| | Colorize Highlight Influence | [23] Factor | 0.0 | 高光染色强度（0=不染色） |
| | Hue / Saturation | [1]/[2] | 0.5 / 1.0 | 高光区色相 / 饱和度 |
| | Subsurface | [44] Factor | 0.0 | 次表面感（在亮部模拟透光，玉石/皮肤用） |
| 阴影 | Shadow Value | [9] Value | 0.3 | 暗部亮度（0.3=暗部压得很暗） |
| | Colorize Shadow | [20] B | 黑 | 暗部染色色 |
| | Colorize Shadow Influence | [22] Factor | 0.0 | 暗部染色强度 |
| | Hue / Saturation | [7]/[8] | 0.5 / 1.0 | 暗部区色相 / 饱和度 |
| 反弹光 | Bounced Light Color | Determiner of Bounced[7] | — | 反弹光染色（需先 BakeBounced 烘焙反弹光贴图） |
| | Strength | ExtraLights[0] | — | 反弹光强度 |
| | Spreading / Sharpness | ExtraRange[1]/[4] | — | 反弹光扩散 / 锐度 |
| 边缘光 | Enable Rim Light | [45] Factor | 0.0 | 1=开启边缘光 |
| | Rim Light Color | [43] B | 白 | 边缘光颜色 |
| | Size | [47] From Min | 0.96 | 边缘光范围（Fresnel 阈值） |
| | Rim Light Spreading | [44→?] [47] | — | 边缘光扩散 |
| | Softness | [50] IOR | 0.92 | 边缘光软硬（Fresnel IOR 反相） |
| 金属 | Metallic % | [46] Factor | 0.0 | 金属感强度（Fresnel 亮边） |
| | Metallic Steps | [48] Steps | 3.0 | 金属亮边阶梯化级数 |
| | Metallic Spreading | [49] From Min | 0.0 | 金属亮边范围 |
| 扭曲 | Distort Strength | [10] Strength | 0.0 | 法线扰动量（噪声/Voronoi 扰动明暗交界） |
| | Noise/Voronoi Switch | [11] Factor | 0.0 | 0=噪声 1=Voronoi |
| | Scale (Uniform) / Scale | [12]/[13] | 5.0 / (1,1,1) | 扰动缩放 |
| | Location / Rotation | [14]/[17] | 0 / 0 | 扰动坐标位置 / 旋转 |
| | Detail / Roughness | [15]/[16] | 2.0 / 0.5 | 扰动细节 / 粗糙度 |
| | Use Object/UV Coords (Distortion) | [24]/[25] | 1.0 / 0.0 | 扰动坐标来源 |
| 手绘 | Enable Painterly Effect? | [31] Factor | 0.0 | 1=开启笔触效果（Voronoi 笔触破碎明暗区） |
| | Stroke Scale (Uniform) | [41] Scale | 2.0 | 笔触整体缩放 |
| | Stroke Scale | [33] Scale | (1,1,1) | 笔触三轴缩放 |
| | Distort #1 / #2 | [34]/[40] | 0 / 0 | 笔触扭曲量 |
| | Smooth Strokes | [35] Bright | 0.18 | 笔触平滑度 |
| | Strokes Contrast | [36] Contrast | 1.9 | 笔触对比度 |
| | Strokes Map / Map Scale | Image Texture / [37] | — / (3.4) | 自定义笔触贴图及缩放 |
| 法线 | Enable Normal Map? | [18] Factor | 0.0 | 1=启用法线贴图 |
| | Normal Map Strength | [19] Strength | 1.0 | 法线强度 |
| | Map Location / Rotation / Scale | [26]/[27]/[28] | 0/0/(1,1,1) | 法线贴图坐标 |
| 遮罩 | Remove Light (SubtractLight) | [39] Enable | 0.0 | 用贴图减去光照（贴图黑=去光） |
| | Add Light (AddLight) | [38] Enable | 0.0 | 用贴图增加光照 |

**AI 用法要点**：这是 SAS 的"主灯"节点。基础卡通二分 = 面板 Blend Style 选 STEPPED + `Toon Steps` 2~4 + `Light Slider`≈0.4~0.5 + `Shadow Value` 0.2~0.4；暖/冷对比 = 亮部/暗部分别 Colorize；脏旧 = `Darken Edge` + 扭曲；手绘 = `Enable Painterly Effect`。`Custom`/`LightMask` 输出可用于烘焙高级通道。

### 2.2 SpecularReflection —— 风格化高光（48 节点，26 输入）

**架构**：Glossy BSDF（Roughness=输入[4]）→ Shader to RGB → ImportantRange + Map Range（Blend Style/Steps）→ 染色 Mix（Hue/Sat/Value=1,2,3）→ Color Ramp 大小钳制 → 输出。内部还有 Distortion（噪声扰动高光形状）、Painterly（笔触化高光）、Normal、Mask。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Blend Style | Map Range.interpolation | — | 高光过渡曲线（可阶梯化） |
| Roughness | [4] | 0.06 | Glossy 粗糙度：**越小高光越锐利**（0.06≈硬高光） |
| Steps | [7] | 0.6 | 阶梯化级数 |
| Shine Brightness | [24] Value | 3.0 | 高光整体亮度 |
| Color | [12] B | 白 | 高光颜色 |
| Color Strength | [25] Factor | 0.0 | 高光染色强度 |
| Size clamp (Min)/(Max) | [5]/[6] | 0.06 / 1.0 | 高光大小钳制（Min 越小高光越收窄） |
| Distortion Strength | [11] | 0.0 | 高光形状扰动 |
| Scale (Uniform)/Scale/Location/Roughness | [10]/[8]/[9]/[13] | 5.0 / (1,1,1) / 0 / 0.5 | 扰动参数 |
| Use UV Coordinates? | bumpswitch[0] | — | 扰动用 UV |
| Enable Painterly Effect? | [15] | 0.0 | 1=高光笔触化 |
| Scale/Scale(Uniform)/Distort/Smooth/Contrast | [16]/[23]/[17]/[18]/[19] | — | 笔触参数 |
| Strokes Map / Scale | BrushTekure / [20] | — | 自定义笔触贴图 |
| Enable Normal Map? / Strength | [21]/[22] | 0.0 / 1.0 | 法线贴图 |
| Enable Mask? | [14] | 0.0 | 遮罩贴图（Image Texture） |

### 2.3 AmbientOcclusion —— AO 暗角（18 节点，4 输入）

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| AO Strength | [1] Factor | 0.6 | 暗角强度 |
| AO Ramp Slider | ZhaRamp.color_ramp[1].position | — | AO 范围滑块（>0.5 收窄暗角） |
| AO Distance | [2] | 1.0 | 采样距离（越大影响越广） |
| Harshness | ImportantRange[1] | — | 边缘锐度 |
| AO Color | ZhaRamp.color_ramp[0].color | 黑 | 暗角颜色 |
| Mask / AO Mask Influence | [3] | 0.0 | 遮罩贴图及其强度 |

> ⚠️ 面板警告：AO 效果要求材质 Blend Mode 为 **Alpha Hashed 或 Opaque**（Alpha Blend 不工作）。

### 2.4 CrossHatch —— 排线光照（41 节点，41 输入）

**架构**：Diffuse BSDF → Shader to RGB → ImportantRange（Light Slider/Controller=[4]）→ Map Range（Style/Steps）→ 亮/暗部 HSV+染色（同 DiffuseLight 结构）→ Voronoi 排线纹理（Strength=[10]）→ 可选的 Dotted Tone 点阵 → 输出。**与 DiffuseLight 互斥**，二者取其一。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Light Slider/Controller | [4] From Min | 0.0 | 亮度阈值（越大越暗） |
| Toon Steps | [6] | 3.5 | 阶梯级数 |
| Light Value | [3] | 3.0 | 亮部亮度 |
| Colorize Highlight / Influence | [21]/[23] | —/0.0 | 亮部染色 |
| Shadow Value | [9] | 1.0 | 暗部亮度 |
| Colorize Shadow / Influence | [20]/[22] | —/0.0 | 暗部染色 |
| Crosshatch Strength | [10] | 0.28 | 排线可见度（0=只有明暗） |
| Scale (Uniform) / Location / Detail / Roughness | [12]/[14]/[15]/[16] | 5.0/0/2.0/0.6 | 排线密度与细节 |
| Rotation | [17] | — | 排线方向 |
| Enable Dotted Tone? | [30] | 0.0 | 1=启用点阵网纹 |
| Invert / Scale / Scale(Uniform) / Dot Randomness / Detail / Dot Clamp | [31]/[35]/[32]/[33]/[34]/[36] | — | 点阵参数 |
| UV Coords / Window Coords | [24]/[25] | — | 坐标来源 |

> ⚠️ CrossHatch 不可烘焙（烘焙时会警告并移除）。

### 2.5 AddCurvature —— 曲率着色（44 节点；需要烘焙）

面板流程：先 UV 展开 → 选 Resolution / `hardsurface`（硬表面勾选）/ `curvaturelevels`（细节级数，默认 2）→ `bpy.ops.shaderaddon.bakecurvature()` 烘焙曲率图到 `CurvatureHelper` 图像 → 之后节点组才有内容可显示。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Value (Bright) | [4] | 1.0 | 凸面（亮部）亮度 |
| Value (Dark) | [1] | 2.5 | 凹面（暗部）亮度 |
| Sat / Hue | [5]/[6] | 1.0 / 0.5 | 曲率染色 |
| Spreading / Sharpness | [7]/[8] | 0.0 / 1.0 | 曲率范围/锐度 |
| Painterly Enable? | [14] | 0.0 | 1=笔触化曲率 |
| Dark/Bright Strokes / Detail / Roughness / Refinement | [17]/[18]/[20]/[21]/[28] | — | 笔触参数 |
| Scale (Uniform) / Location | [19]/[22] | — | 笔触缩放/位置 |

### 2.6 LightObject —— 假光（每物体灯光，25 节点 + 几何节点修改器）

`addobjectlight` 创建：一个空/网格"灯光物体" + 几何节点修改器 `SB Geono`（用 Store Named Attribute 把灯光物体的距离信息写入属性，材质里 `LightObject` 组读取）。灯光位置=移动灯光物体。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Light Slider | IMPORTANT MATH[1] | — | 灯光强度/范围 |
| Style / Steps / Sharpness | Map Range / [7] / [12] | — | 过渡曲线/阶梯 |
| Highlight Value | [1] | 3.0 | 亮部亮度 |
| Colorize Highlight | [13] | — | 亮部染色 |
| Hue / Sat | [2]/[3] | 0.5/1.0 | 亮部色相/饱和度 |
| Shadow Value | [4] | 1.0 | 暗部亮度 |
| Colorize Shadow / Influence | [16]/[17] | —/0.0 | 暗部染色 |
| Hue / Sat | [5]/[6] | 0.5/1.0 | 暗部色相/饱和度 |
| Light Object (must be a mesh) | Object Info[0] | — | 指定驱动灯光物体 |
| Subdivision Surface / Subdivide Mesh Levels | SB Geono 内 | — | 采样细分（影响灯光边界精度） |
| Painterly Enable / Scale / Breakup | painterlymix[0] / Voronoi[2] / Mix.002[0] | — | 灯光边界笔触化 |
| Remove Light / Add Light Mask | [15]/[18] | 0.0 | 遮罩贴图 |

### 2.7 HairCurves —— 各向异性毛发反光（33 节点，17 输入）

用于曲线（头发）。**架构**：曲线切线 → 各向异性高光。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Style / Steps | Important Range / [16] | —/4.0 | 高光过渡曲线/阶梯 |
| Spreading | [15] | 0.1 | 高光扩散 |
| Position | [2] | 0.03 | 高光位置 |
| Scale | [1] | 5.0 | 高光整体缩放 |
| Brightness | [5] | 2.0 | 高光亮度 |
| Hue / Saturation | [6]/[7] | 0.5/1.0 | 高光颜色 |
| Clamp Bottom / Top | Color Ramp | — | 高光范围钳制 |
| Rotation | [4] | 90 | 高光方向旋转 |
| Line Clamp | [9] | 0.1 | 发丝线密度钳制 |
| Scale / Scale(Uniform) / Detail / Roughness / Distortion | [11]/[10]/[12]/[13]/[14] | — | 发丝纹理细节 |

### 2.8 风格化点光源 RedLightSAS / GreenLightSAS / BlueLightSAS（各 18 节点）

三个一模一样的"假点光源"节点组（红/绿/蓝三色场景灯，也可用于灯光组）。需要先有 `Stylized Light (Dynamic)` 效果（面板警告）。配套灯光物体 `SAS Point Light Group #1/2/3`，选中灯光物体时面板直接显示灯光参数：

| 友好名 | 位置 | 默认 | 作用 |
|---|---|---|---|
| POWER | 灯光 energy | — | 点光源功率 |
| Cast Shadows? | 灯光 use_shadow | — | 是否投影 |
| Blend Style | zhaRange.interpolation | — | 过渡曲线 |
| Steps | zhaXYZ3.inputs[0/1/2] | — | 阶梯级数（红/绿/蓝各自索引 0/1/2） |
| Brightness | zhaValue.outputs[0] | — | 亮度 |
| Hue / Sat | zhaHSV inputs[0]/[1] | — | 颜色偏移 |
| Color Tint / Strength | zhaMix [7]/[0] | — | 染色色/强度 |
| Spreading / Sharpness | zhaXYZ1 / zhaXYZ2(zhaLinearRange) | — | 光照范围/锐度 |
| Occlude from Dark Areas / Sharpen Brighter Areas | zhaRamp color_ramp [0]/[1] position | — | 亮暗钳制 |

`isolatelighting` / `regrouplighting`：把某个点光源灯光组"只作用于当前物体/恢复全场景"。

---

## 3. 手绘贴图类

### 3.1 TexturePaint —— 纹理绘制（16 节点）

在材质上叠加一张可绘制的图像（UV/纹理绘制模式画）。面板：选 "Drawing texture" 图像、Blend Mode（ImportantMix.blend_type）、Mask 及 Enable；`externalpaint` 可导出到外部图像编辑软件，`image.project_apply` 应用回贴图。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Blend Mode | ImportantMix.blend_type | — | 绘制层混合模式 |
| Enable Mask? | [2] | 0.0 | 遮罩 |
| Location/Rotation/Scale | [3]/[4]/[5] | — | 绘制贴图坐标 |

### 3.2 SingleColor —— 单色绘制（10 节点）

`Mix.blend_type` 混合模式 + Color（输入[1]）+ 绘制贴图（Image Texture）。AI 直接改 `node.inputs[1]` 的颜色即可改笔刷色。

### 3.3 VertexPaint —— 顶点色绘制（20 节点）

面板：Add Color Group / 选 Color Attribute 图层、可选 Painting Texture 及其影响、X/Y/Z Scale、Location/Rotation、UV/Window 坐标切换。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Painting Texture Influence | [8] | 1.0 | 贴图影响 |
| X/Y/Z Scale | [3]/[4]/[5] | 4.0 | 贴图缩放 |
| Location / Rotation | [1]/[2] | — | 贴图位置/旋转 |
| UV Coordinates / Window Coordinates | [9]/[10] | — | 坐标来源 |

### 3.4 TransparentWorldStrokes —— 简单透明/笔画（13 节点，Shader 级）

透明叠加层。`Transparency Amount`=输入[2]、`Invert?`=[3]、Mask=[1] Enable。作用于 Shader（不是颜色），可做手绘半透明笔触。

### 3.5 TransparentPaint —— 水彩/炭笔效果（54 节点，Shader 级）

**最强手绘效果**：图像贴图（Important Texture）按明暗/边缘混合透明度，可生成"水彩边缘堆积"感；内含 Hair 模式（毛发丝线）。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Texture | Important Texture | — | 水彩/炭笔笔触贴图 |
| Affect Edges? | [6] | — | 是否只作用于边缘 |
| Overall Blend (Edges) | [5] | — | 边缘混合度 |
| Overall Strength (Edges) | [4] | — | 边缘强度 |
| Overall Transparency | [1] | -0.1 | 整体透明度（负值=不透明） |
| Clamp (Min)/(Max) | Important Ramp [0]/[1] | — | 透明范围钳制 |
| Texture Scale X/Y/Z | [9]/[10]/[11] | 4.5 | 贴图缩放 |
| Texture Location / Rotation | [7]/[8] | — | 贴图位置/旋转 |
| Window/UV Coordinate Switch | [12] | — | 坐标来源 |
| Mask Enable | [13] | 0.0 | 遮罩 |
| Hair Enable? | [14] | 0.0 | 1=毛发丝线模式 |
| Strand Scale / Distortion / Clamp(1~4) | [16]/[17]/[15]/[24]/[25]/[26] | — | 发丝参数 |
| Specular Enable? | [18] | 0.0 | 发丝高光 |
| Specular Color / Roughness | [23]/[19] | —/0.17 | 发丝高光颜色/粗糙度 |
| Specular Strand Scale / Strength / Distortion | [20]/[21]/[22] | 2.87/0.21/0.0 | 发丝高光参数 |

> ⚠️ TransparentPaint 不可烘焙（烘焙时移除）。

---

## 4. 描边类

### 4.1 EdgeDetect —— 边缘检测着色（15 节点）

**架构**：Layer Weight (Facing/Fresnel) → Color Ramp → Map Range → HSV 调边缘色 → Blend。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Edge Value | [1] | 0.0 | 边缘亮度 |
| Edge Saturation / Edge Hue | [2]/[3] | 1.0/0.5 | 边缘颜色 |
| Spreading (From Min/Max) | [4]/[5] | 0.09/0.33 | 边缘检测范围 |
| Spreading (To Min/Max) | [6]/[7] | -0.21/0.81 | 边缘宽度映射 |
| Blend | [8] | 0.5 | 边缘叠加强度 |
| Mask / Enable Mask? | Mask / [9] | 0.0 | 遮罩 |

### 4.2 ColoredEdges —— 彩色边缘（17 节点）

**架构**：Layer Weight → Color Ramp → Map Range → Mix 边缘色。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Edge Color | [1] | 红 | 边缘颜色 |
| Blend | [6] | 0.5 | 叠加强度 |
| Spreading (From Max/Min, To Min/Max) | [3]/[2]/[4]/[5] | 0.33/0.12/-2.63/4.01 | 边缘范围/宽度 |
| Mask / Enable | Mask/[7] | 0.0 | 遮罩 |
| Location / Rotation / Scale | [8]/[9]/[10] | — | 遮罩坐标 |

### 4.3 SolidifyOutline —— 物体描边（修改器方案）

`addsolidifyoutline` 创建 Solidify 修改器（名 `SB Outline`，厚度可调）+ 描边材质（`Outline for <物体>`，用 `basecolor_solidify` 组）。面板：Outline Color（RGB）、Thickness、Vertex Group。**修改器方案**= 与模型同体的背面挤出描边，比 shader 描边稳。

---

## 5. 纹理/图案类

### 5.1 LocalGradient —— 局部渐变（矩形，42 节点）

**架构**：ZhaGradient（Gradient Texture，坐标=ZhaTexture Coordinate 绑定**球体空物体控制器**）→ 坐标混合（Object/Generated/UV/Window %）→ DistortMix（噪声/Voronoi 扭曲）→ Color Ramp/Map Range（Gradient Style + Toon Steps）→ realmix 混合。添加时自动创建空物体 `SB <组名> <物体名>`（父级=物体）并赋给坐标节点：**移动/旋转空物体=移动/旋转渐变**。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Gradient Color | [1] | 蓝 | 渐变颜色（输入[0]是底色=串联上游颜色） |
| Blending Mode | realmix.blend_type | — | 与底色混合模式 |
| INVERT? | [18] | 0.0 | 反转渐变方向 |
| Gradient Style | Map Range.interpolation | — | LINEAR/STEPPED/... 过渡曲线 |
| Toon Steps | [12] | 4.0 | 阶梯级数 |
| Visibility | Visibility[0] | — | 整体可见度 |
| Painterly Effect/Distort | [8] | 0.0 | 渐变边缘笔触化扭曲 |
| Noise/Voronoi Switch | [17] | 0.0 | 扭曲类型 |
| Painterly Distort Scale / Scale(Uniform) / Location | [9]/[16]/[10] | — | 扭曲参数 |
| Gradient Location / Rotation / Scale | [13]/[14]/[15] | — | 渐变坐标 |
| Clamp | [23] | — | 渐变钳制 |
| Object Coords (Default) % | [4] | 1.0 | 物体坐标权重 |
| UV Coordinates % | [6] | 0.0 | UV 坐标权重 |
| Mask / Enable Mask? / Mask Location/Scale/Rotation | [19]/[21]/[20]/[22] | — | 遮罩 |
| Gradient Object | ZhaTexture Coordinate.object | 空物体 | 指定控制器空物体 |

### 5.2 LocalGradientSphere —— 球体渐变（40 节点）

与 LocalGradient 同构，但渐变类型为球体径向（Spherical）。参数相同。

### 5.3 InstantWatercolor —— 风格化水彩噪点（16 节点，"Stylized Grunge"）

**架构**：双层 Noise Texture → Map Range（Style + Steps）→ HSV 明暗染色 → 混合。适合快速给模型加"水彩/纸质噪点"质感。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Bright Areas | [1] Value | 2.0 | 亮区亮度 |
| Dark Areas | [4] Value | 0.11 | 暗区亮度 |
| Scale (Uniform) | [7] | 4.81 | 噪点缩放 |
| Contrast | [18] | 0.23 | 噪点对比度 |
| Use UV Coords Instead? | [11] | 0.0 | 1=用 UV 坐标 |
| Location / Rotation / Scale | [8]/[9]/[10] | — | 噪点坐标 |
| Distort Amt / Overall Detail / Interstitial Scale / Interstitial Detail | [12]/[13]/[14]/[15] | — | 细节控制 |
| Style / Steps | Map Range / [5] | — | 过渡曲线/阶梯 |

### 5.4 NoiseTexture —— 动态纹理（106 节点，功能最全）

**架构**：8 种遮罩（Gradient Sphere/Rect、Noise、Wave×2、Voronoi、Tiles/Brick、Foam）按权重混合成遮罩 → 主 Noise 纹理按遮罩约束显示 → ImportantMix 混合 → MapRangeMask 阶梯化。面板"Mask Selector"下拉（`my_mask_enum`）决定编辑哪种遮罩的子参数。

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Noise Color | [1] B | 白 | 纹理颜色 |
| Blend Mode | ImportantMix.blend_type | — | 混合模式 |
| Toon/Linear Switch | MapRangeMask.interpolation | — | 过渡曲线 |
| Steps | [29] | 4.0 | 阶梯级数 |
| Invert? | [69] | 0.0 | 反转 |
| Mask Influence | [2] | 1.0 | 遮罩强度 |
| Mask Clamp Min / Max | [55]/[56] | 0.0/1.0 | 遮罩范围 |
| Bright Value Clamp | [68] | — | 亮度钳制 |
| 遮罩权重：Gradient(Sphere/Rect)/Noise/Wave/Wave2/Voronoi | [3]/[4]/[5]/[6]/[57]/[7] | 1/0/0/0/0/0 | 各遮罩占比 |
| Tile/Brick Factor / Foam Factor | [49]/[48] | 0.0 | 砖块/泡沫遮罩占比 |
| Mask Distort / Make Painterly | [12] | 0.0 | 遮罩边缘笔触化 |
| Painterly Distort Scale (Uniform/Scale) / Animate | [34]/[41]/[37] | 5.0 | 笔触参数 |
| Steps / Scale / Detail / Roughness / Distortion / Lacunarity（主噪声） | [23]/[22]/[24]/[25]/[26]/[27] | — | 主纹理噪声参数 |
| Enable Drawing Mask? | [40] | 0.0 | 手绘遮罩 |
| 坐标：Generated/Object/UV/Window（遮罩与纹理各一组） | [16-22]/[17-18] | — | 坐标来源 |
| Object/UV Coords (Mask) | [17]/[18] | — | 遮罩坐标 |

**遮罩子参数**（面板按 `my_mask_enum` 显示）：
- `GRADIENTSPHERE`：Clamp=SphereRange[1]、Scale=[47]、Position=[61]、Rotation=[62]
- `GRADIENTRECT`：Clamp=RectRange[1]、Scale=[46]、Position=[63]、Rotation=[64]
- `NOISE`：Noise Scale=[30]、Clamp=NoiseRange[2]、Detail/Roughness/Lacunarity/Distortion=NoiseZha[3-6]、Position=[42]、Scale=[45]、Rotation=[65]
- `WAVE`：Type/Band Direction=WaveZha、Wave Scale=[31]、Clamp=WaveRange[1]、Distortion/Detail/Offset=WaveZha[2,3,6]、Rotation=[58]
- `WAVE2`：同 WAVE（WaveZha2，Scale=[59] 等）
- `VORONOI`：Scale (Uniform)=[32]、Clamp=VoronoiRange[1]、Invert=[33]、Detail/Roughness/Lacunarity/Randomness=VoronoiZha[3-5,8]、Position=[43]、Scale=[44]
- `TILES`：Scale (Uniform)=TileZha[2]、Clamp=TileRange[1]、Detail/Roughness/Lacunarity/Randomness=TileZha[3,4,5,8]、Position=[51]、Scale=[50]、Rotation=[67]
- `FOAM`：Clamp=FoamRange[1]、Foam Detail=[54]、Position=[52]、Scale=[53]、Rotation=[66]

### 5.5 EasyDT —— 简单动态纹理（19 节点）

Noise 为主，参数精简版：Noise Color=[13]、Blend Mode、Toon/Linear Switch、Steps=[14]、Spreading (Clamp)=[12]、Invert?=[15]、Noise Scale (Uniform)=[5]、Detail=[6]、Roughness=[7]、Lacunarity=[16]、Distortion=[17]、Position=[2]、Scale=[4]、Rotation=[3]、Mask Distort=[8]、Painterly 参数 [9]/[19]/[18]、Object Coords=[20]、UV Coords=[1]。

### 5.6 BrushStrokes —— 动态笔触（44 节点）

用噪声/沃罗诺伊生成成簇笔触。参数（面板）：Scale (Uniform)=[2]、Value Min/Max=[7]/[8]、Saturation Min/Max=[5]/[6]、Smooth=[19]、Texture Contrast=[20]、Shape Randomness=[9]、Noise Randomness #1/#2=[10]/[12]、Strokes Scale=[11]、Noise/Voronoi Switch=[13]、Distort X/Y/Z Scale=[14]/[15]/[16]、Distort Location=[17]、Texture / Location / Scale XYZ / Rotation=[21]/[28]/[29]/[30]/[23]、UV=[24]、Object Coords=[27]。

### 5.7 StylizedFoam —— 风格化泡沫（36 节点）

水花/泡沫边缘效果。参数：Style=ImportantRange.interpolation、Steps=[10]、Foam Spreading=[8]、Foam Color=[6]、To Max=[9]、Foam Location=[2]、Foam Scale=[1]、Foam Detail=[3]、Painterly Distort Influence=[12]、Distort Scale (Uniform)=[4]、Distort Scale=[5]、Animate Painterly Distort=[7]、UV/Generated Switch=[11]、Mask=[13]/[14]/[15]/[16]。

### 5.8 OverallTexture —— 贴图叠加（18 节点）

整张贴图覆盖在材质上：Blend Mode=ImportantMix.blend_type、Strength=[1]、Texture、Location=[3]、Rotation=[4]、X/Y/Z Scale=[5]/[6]/[7]、UV/Window Switch=Vect[0]、Mask=[2]。

### 5.9 TransparentNoiseTexture —— 透明动态纹理（119 节点）

NoiseTexture 的透明版（多一个 Shader 输出，透明通道=噪声遮罩）。参数与 NoiseTexture 相同，另加：Transparency Amount=AddTransparency[0]、Bright Value Clamp=[68]、Edge Transparency Enable=[70]/Blend=[71]/Invert=[72]、Mask Location/Scale=[74]/[75]。

---

## 6. 调色类

### 6.1 RGBContrast —— 对比度（7 节点）

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Dark Contrast | [1] Darken | 0.0 | 暗部压暗 |
| Regular Contrast | [2] Contrast | 0.0 | 整体对比 |
| Bright Contrast | [3] Brighten | 0.0 | 亮部提亮 |

### 6.2 FinalHSL —— HSL 调色（9 节点）

| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Hue | [1] | 0.5 | 色相偏移（0.5=不变） |
| Saturation | [2] | 1.0 | 饱和度（1=不变） |
| Value | [3] | 1.0 | 明度 |
| Enable Mask? / Invert Mask? | [5]/[6] | 0.0 | 遮罩 |

### 6.3 ObjectRandomize —— 物体随机化（19 节点）

按物体实例随机化 HSV（多个物体共用材质时每个物体颜色不同）：
| 友好名 | 输入 | 默认 | 作用 |
|---|---|---|---|
| Hue (Min)/(Max) | [2]/[3] | 0.5/0.5 | 色相随机范围 |
| Hue Seed | [8] | 0.5 | 色相随机种子 |
| Value (Min)/(Max) | [6]/[7] | 1.0/1.0 | 明度随机范围 |
| Value Seed | [9] | 0.75 | 明度种子 |
| Saturation (Min)/(Max) | [4]/[5] | 1.0/1.0 | 饱和度随机范围 |
| Saturation Seed | [10] | 1.85 | 饱和度种子 |

---

## 7. 对象特效类（Fog / Steam / GodRays / Displace）

### 7.1 Fog（雾）
`addfog` 创建体积雾对象（材质 `SB Fog`）。参数：Scale (Uniform)=[0]、Scale=[1]、Clamp Fog Min/Max=[2]/[3]、Color=[4]、Fog Location=[7]、Detail=[9]、Roughness=[10]、Lacunarity=[11]、Distortion=[12]、Mask Location=[5]、Mask Clamp=[6]、Mask Distortion=[8]、Distort Location=[13]。

### 7.2 Steam（蒸汽）
`addsteam` 创建蒸汽对象（材质 `SB Steam`）。参数：Color=[0]、Steam Location=[9]、Scale (Uniform)=[4]、Scale=[3]、Steam Fade=[1]、Detail=[5]、Roughness=[6]、Spreading=[7]、Bottom=[8]。

### 7.3 GodRays（神光）
`addgodrays` 创建体积光锥（材质 `SB Godrays`）。参数：Color=[10]、Bottom Fade=[0]、Top Fade=[7]、Center Loc=[1]、Density 1=[5]、Density 2=[3]、Clamp Spread=[2]、Beam Detail=[16]、Enable Dust Particles?=[12]（开时显示 Particle Scale=[13]/Size=[15]/Location=[14]）、Animation Seed=[8]、Delay Between Fades=[11]、Animate=[9]。

### 7.4 Displace（置换）
`adddisplace` 添加修改器 `SB Disp`（Displace 修改器）。面板：strength、mid_level、direction、texture、texture_coords、texture_coords_object；`addcloudstexture` 一键生成 Clouds 置换纹理。

---

## 8. 烘焙与导出（EEVEE→纹理化工作流）

插件把实时 EEVEE 风格化材质**烘焙成贴图**，便于 Cycles 渲染/游戏引擎导出。流程（面板 BAKE 项）：

1. 确认模型 **UV 展开**
2. 设 Bake Image Texture Name（`bake_name`）+ Resolution（`user_input_number`，默认 2048）
3. 按需分通道烘焙：
   - `bakediffuse` —— 烘焙漫射光照（可勾选 `applied_sld`=把 Stylized Light 应用进漫射）
   - `bakeao` —— 烘焙 AO
   - `bakespecular` —— 烘焙高光反射
   - `baketransparent` —— 烘焙透明（TransparentNoise/TransparentWorldStrokes 需要，独立于主烘焙）
   - `bakebounced` —— 烘焙反弹光（DiffuseLight 面板 → Bounced Light Settings，可加 `painterlyfilter` 笔触化）
   - `bakecurvature` —— 烘焙曲率（AddCurvature 需要，先选 hardsurface/curvaturelevels）
   - `bakenormals` —— 烘焙法线（需先有 DiffuseLight）
4. `bakeall` —— 一键烘焙全部 + 重组材质为贴图（CrossHatch/TransparentPaint 会被移除）
5. `bakeanimationprotocol` —— 逐帧烘焙动画（frame_start/end、light_animate_enum、specular_animate_enum、processing_speed）
6. `saveimagetextures` —— 保存/导出所有烘焙贴图到磁盘

其他工具操作符：
- `deletematerial` —— 彻底删除选中着色器（含相关对象）
- `deleteeffect` —— 删除指定效果组（arg1=组名）
- `duplicateeffect` —— 复制效果组
- `duplicatematerial` —— 材质/效果单用户化
- `swapnodes` —— 交换两个效果组顺序（node_groups_enum_swap1/swap2）
- `refreshmaterial` —— 刷新材质
- `mask speculars`（maskspeculars）—— 透明边缘高光遮罩
- `isolatelighting` / `regrouplighting` —— 点光源只影响当前物体/恢复
- `worldsetup` —— 建渐变背景世界（layeredworld）
- `appendbrushes` —— 追加画笔资产（水彩/蜡笔等 60+ 笔刷）

---

## 9. 背景世界（SAS_PT_WorldPanel）

`worldsetup` 建立 `layeredworld`（Base Gradient 节点组驱动渐变天空）。面板参数：

| 友好名 | 位置 | 作用 |
|---|---|---|
| Style | Base Gradient → Map Range interpolation | 天空渐变过渡曲线 |
| Gradient Type | Gradient Texture.gradient_type | 渐变类型（Linear/Radial/...） |
| Steps | Base Gradient inputs[14] | 阶梯级数 |
| Base Color | inputs[0] | 底色 |
| Top Value / Colorize Top / Influence | inputs[1]/[17]/[18] | 顶部颜色/染色/强度 |
| Bottom Value / Colorize Bottom / Influence | inputs[4]/[15]/[16] | 底部颜色/染色/强度 |
| Gradient Location / Rotation / Scale | inputs[8]/[9]/[10] | 天空渐变坐标 |
| Painterly Distort | inputs[7] | 天空笔触化扭曲 |
| Distort Scale (Uniform/Scale) | inputs[11]/[12] | 扭曲缩放 |
| Animate Distort | inputs[13] | 扭曲动画 |

---

## 10. AI 使用要点（规则总结）

1. **基底先行**：任何物体先 `bpy.ops.shaderaddon.objectsetup()` 建 Base Color 材质，再添加效果。
2. **效果插入位置**：效果自动插到材质输出前（链尾）；多个效果按添加顺序叠加，`swapnodes` 可换序。
3. **互斥**：DiffuseLight 与 CrossHatch 二选一；FakeLight 是独立灯光方案；SPL 点光源需要先有 DiffuseLight。
4. **灯光驱动**：LocalGradient/Sphere、CircularLight 等用**球体空物体控制器**（`SB <组> <物体>`）定位，移动空物体=移动效果；LightObject 用灯光网格物体驱动。
5. **参数寻址**：效果组输入索引 = 面板友好名（见上文各表）；颜色是 RGBA 4 元组；曲线类（interpolation_type）在组内命名节点上改（如 `node.node_tree.nodes['Map Range'].interpolation_type='STEPPED'`）。
6. **烘焙依赖**：Curvature 必须先 BakeCurvature；DiffuseLight 的反弹光需 BakeBounced；烘焙漫射可选应用风格化光照。
7. **EEVEE 优先**：Shader to RGB 类效果（光照/高光/排线）在 EEVEE 实时生效，Cycles 请烘焙。
8. **AO 与 Blend Mode**：AO 效果要求材质 Blend 为 Alpha Hashed/Opaque。
9. **不可烘焙**：CrossHatch、TransparentPaint 在最终烘焙时被移除（其效果需手工处理/保留实时）。
10. **互操作**：本插件效果组可与"风格化着色工具"（blender_Stylized-Shading-Tools）的节点组在同一材质链上混用（都是 Color 进→Result 出的 GROUP 节点），推荐 SAS 做光照/纹理层，路人甲插件做主节点二分与轮廓光等。

---

## 附：实测环境与产物

- 测试场景：`SAS_Test.001`（Suzanne × 26 效果物体，EEVEE）
- 实渲染图：`sas_test_01_diffuselight.png`（DiffuseLight 蓝调二分）、`sas_cluster_lighting2.png`（Diffuse/CrossHatch/Specular/AO 2×2）、`sas_live_debug.png` 等
- Schema 自省文件：`sas_nodegroups_schema.txt`（39 组 interface 全量）
- 内部结构文件：`sas_node_structure_lighting.txt` / `sas_node_structure_textures.txt`
