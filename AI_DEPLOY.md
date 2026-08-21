# AI 部署手册（本文件是写给 AI 阅读执行的标准作业程序）

> 适用场景：用户说「把这个仓库部署到本地」「下载并安装这个模式/技能」「把 dsh-blender-stylized-shading 装到我的 harness」之类的话时，AI 按本手册执行。
> 本手册假定执行者是 DeepSeek Harness 里的一个 AI Agent（具备文件读写与 shell 能力）。人类用户请阅读 `README.md`。

## 0. 目标与完成标准

**目标**：把本仓库中的 `stylized-blender` 预设部署到目标机的 DeepSeek Harness 用户目录，使用户新建会话时可选择预设 **风格化着色(Blender NPR)**，且会话自动拥有 **stylized-shading** 技能。

**完成标准（全部满足才算完成）**：

- [ ] 目标目录存在：`<DSH_HOME>\.agent-presets\stylized-blender\`
- [ ] `preset.yml` 存在，且内容包含 `name: 风格化着色(Blender NPR)`
- [ ] `agent.cordis.yml` 存在
- [ ] `skills\stylized-shading\` 下存在 `SKILL.md`、`material_pipeline.md`、`sas_reference.md`
- [ ] 向用户报告：刷新 Harness Web 后新建会话 → 预设列表出现「风格化着色(Blender NPR)」

## 1. 环境探测（先做，别猜）

```powershell
# Windows PowerShell 示例
$DSH_HOME = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE ".dsh" }
$targetDir = Join-Path $DSH_HOME ".agent-presets\stylized-blender"
Write-Output "DSH_HOME=$DSH_HOME"
Write-Output "target=$targetDir"
Test-Path $targetDir   # 已存在则先看第 4 步的"覆盖规则"
```

- 如果 `$env:DSH_HOME` 有值，用它的值；否则默认 `%USERPROFILE%\.dsh`。
- 注意：**只部署到用户目录**（`.agent-presets` 在 `DSH_HOME` 或 `~/.dsh` 下）。**绝不要**写部署自带的 `agent-presets` 目录（升级会被覆盖，且污染部署）。

## 2. 下载本仓库

```powershell
# 方式 A：git clone（推荐）
git clone https://github.com/lurenjia-l/dsh-blender-stylized-shading.git "$env:TEMP\dsh-blender-stylized-shading"

# 方式 B：下载 ZIP 解压
# Invoke-WebRequest https://github.com/lurenjia-l/dsh-blender-stylized-shading/archive/refs/heads/main.zip -OutFile ...
```

若目标机上已存在同名目录（之前部署过），先备份再覆盖：

```powershell
if (Test-Path $targetDir) { Copy-Item -Recurse $targetDir "$targetDir.bak-$(Get-Date -Format yyyyMMdd-HHmmss)" }
```

## 3. 部署（复制 `stylized-blender` 整个文件夹）

**关键**：复制的是仓库内的 **`stylized-blender` 文件夹本身**，不是仓库根目录，也不是把里面的文件散开。

```powershell
$src = "$env:TEMP\dsh-blender-stylized-shading\stylized-blender"   # 或你 clone/解压的实际路径
New-Item -ItemType Directory -Force -Path (Join-Path $DSH_HOME ".agent-presets") | Out-Null
Copy-Item -Recurse -Force $src $targetDir
```

最终目录形态必须是这样（**一层不多、一层不少**）：

```
<DSH_HOME>\.agent-presets\
└── stylized-blender\
    ├── preset.yml
    ├── agent.cordis.yml
    └── skills\
        ├── stylized-shading\SKILL.md
        ├── stylized-shading\material_pipeline.md
        ├── stylized-shading\sas_reference.md
        ├── cordis-plugin-development\SKILL.md
        └── editing-cordis-compositions\SKILL.md
```

## 4. 校验与说明（部署后必须自查）

```powershell
Get-Content (Join-Path $targetDir "preset.yml") -TotalCount 1     # 应显示 name: 风格化着色(Blender NPR)
Get-ChildItem -Recurse $targetDir | Select-Object FullName, Length
```

- `agent.cordis.yml` **无需修改**：其中 `skill-filesystem` 行的 `customSkillDirs` 使用 `baseUrl` 相对解析，`baseUrl` 就是 preset 所在目录，因此无论装在哪台机器、哪个 `DSH_HOME` 下，`skills/` 都会被正确注册。
- 技能内文档（`SKILL.md`）提到的插件路径（`E:\rj\blender\plugin\addons\...`）是作者本机路径，**仅作参考**，部署本身不涉及；目标机只要装了「风格化着色工具」插件即可。

## 5. 向用户汇报

完成后向用户说明：

1. 已部署到 `<DSH_HOME>\.agent-presets\stylized-blender\`（列出校验过的文件清单）。
2. 请刷新/打开 Harness Web（`http://127.0.0.1:3080`），新建会话，在 Agent 预设列表选择 **风格化着色(Blender NPR)**。
3. 会话开始后即可直接提需求（如「把选中的物体做成风格化卡通材质」），AI 会自动加载 stylized-shading 技能。
4. 若用户问「模式和技能有什么区别 / 调用哪一个」：用模式即可，技能随模式自动生效；参考 `README.md` 中的对照表。

## 6. 排障速查

| 现象 | 原因与处理 |
|---|---|
| 预设列表没有「风格化着色(Blender NPR)」 | 目录层级不对：必须 `<DSH_HOME>\.agent-presets\stylized-blender\preset.yml`；检查是否多套了一层目录；让用户刷新页面 |
| 会话里没有 stylized-shading 技能 | `skills\` 未随目录一起复制（漏了子目录）；重新整目录复制 |
| 升级 DSH 后预设消失 | 用户目录不会被升级覆盖；若用户误装进部署自带目录，重新部署到用户目录 |
| 用户说 AI 不会用插件 | 确认 Blender 已启用「风格化着色工具」插件且版本 ≥3.4，并配置了 Blender MCP 连接 |
