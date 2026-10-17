# dsh-blender-stylized-shading

**DeepSeek Harness 风格化着色（Blender NPR）模式 + stylized-shading 技能** 部署仓库。

两样东西配套使用，让你（或任何 AI）在 DeepSeek Harness 里直接对话就能驱动 Blender 做卡通 / 赛璐璐 / 三渲二（NPR）材质：

| 内容 | 是什么 | 位置 |
|---|---|---|
| **风格化着色模式** | 一个可选的 **Agent 预设**，名为 `风格化着色(Blender NPR)`：标准编码 Agent 的全部能力 + 运行时检查工具 + 精选技能 | `stylized-blender/cordis.patch.yml` |
| **stylized-shading 技能** | 给 AI 读的**使用说明书**：怎么调用「风格化着色工具」插件的 NPR 节点组，并把自然语言需求翻译成节点参数 | `stylized-blender/skills/stylized-shading/` |

> 配套 Blender 插件 **blender_Stylized-Shading-Tools**（「风格化着色工具」）**不在本仓库**，需单独装进 Blender。

> ⚠️ **兼容性**：本仓库自 2026-10 起适配 **DeepSeek Harness 0.2.x**。
> 0.2 不再读取 `.agent-presets/` 目录式预设，预设必须是一条 `@deepseek-ai/dsh-agent-preset` 声明行。
> 旧的 `preset.yml` + `agent.cordis.yml` 已移到 `legacy/`，**不要再用**（它们不会生效）。

---

## 仓库结构

```
dsh-blender-stylized-shading/
├── README.md                ← 给人类看的安装/调用说明
├── AI_DEPLOY.md             ← 给 AI 看的部署 SOP（把仓库丢给 AI 即可）
├── .gitignore
├── stylized-blender/
│   ├── cordis.patch.yml     ★ 预设声明（追加到 profile 补丁）
│   ├── install.py           ★ 一键安装脚本（技能 + 预设，自动备份、UTF-8 安全、不重复插入）
│   └── skills/
│       ├── stylized-shading/            ★ 核心技能
│       │   ├── SKILL.md                 # 节点组清单/添加/串联/调参/风格配方/创意效果/自检
│       │   ├── sas_reference.md         # Stylized Asset Suite 参数逻辑参考（发散建组用）
│       │   ├── material_pipeline.md     # 材质管线与灯光响应分工、EEVEE 踩坑修复
│       │   └── verify_skill.py          # 一键自检脚本（11 项断言）
│       ├── cordis-plugin-development/   # 配套技能：写/改 Cordis 插件
│       └── editing-cordis-compositions/ # 配套技能：写/改 agent 组成文件
└── legacy/                  ← 0.1.x 目录式预设，仅作历史参考
    ├── preset.yml
    └── agent.cordis.yml
```

---

## 你需要准备

1. **DeepSeek Harness 0.2.x**（桌面版或 `dsh web`）。Web 界面地址以实际启动输出为准。
2. **Blender 3.4+**，并安装启用插件 **blender_Stylized-Shading-Tools**。
   - 启用后：Blender 侧边栏 N → 「风格化材质」；节点编辑器 Shift+A → 「风格化节点」。
   - 技能里写的插件路径（`E:\rj\blender\plugin\addons\...`）是作者本机路径，仅作参考。
3. （推荐）DSH 的 Blender 连接（`@dsh-external/dsh-blender-plugin` 或 Blender MCP），让 AI 直接驱动 Blender。

---

## 安装

### 最省事：一条命令

```powershell
# 先干跑看看它认到的 DSH_HOME / profile / 行号
python .\stylized-blender\install.py --dry-run
# 确认无误后真装（技能目录与补丁文件都会先备份成 *.bak-<时间戳>）
python .\stylized-blender\install.py
# 需要指定时： --dsh-home "D:\dsh-home" --profile web
```

脚本会做两件事，并刻意绕开手工部署最容易踩的两个坑（编码写坏中文、重复插入同一 id）。

### 手工：两步

#### 第 1 步：技能 → 用户技能目录

DSH 0.2 的 `skill-filesystem` 默认就扫描 `<DSH_HOME>/skills`，放这里任何模式都能用：

```powershell
$DSH_HOME = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE ".dsh" }
New-Item -ItemType Directory -Force "$DSH_HOME\skills" | Out-Null
Copy-Item -Recurse -Force ".\stylized-blender\skills\stylized-shading" "$DSH_HOME\skills\"
# 结果应为：$DSH_HOME\skills\stylized-shading\SKILL.md
```

> 为什么不再由预设自带技能目录：0.1.x 的 preset 用 `createRequire(baseUrl).resolve('@deepseek-ai/dsh-agent-preset/package.json')` 定位 `skills/`，
> 而 0.2 起该包只存在于 `app.asar`、不再装进 profile 的 `node_modules`，那条表达式会抛 `MODULE_NOT_FOUND`，
> 导致整个预设 mount 失败（列表里能看到模式，但开不出会话）。所以现在改为「技能进用户目录，预设不引用技能路径」。

#### 第 2 步：预设 → profile 补丁

把 `stylized-blender/cordis.patch.yml` 的整段（一个 `- insert:` 块）**追加**到：

```
<DSH_HOME>/profiles/<profile>/cordis.patch.yml     # 桌面版通常是 desktop
```

要求：

- 文件必须是 **UTF-8（无 BOM）**。用 VS Code / Notepad++ 打开粘贴最稳；**Windows PowerShell 5.1 的 `Add-Content` 默认按 ANSI 写，会把中文写坏**，别用它。
- 若里面已经有一条 `- id: preset-stylized-blender`（旧版装过），**先删掉旧的那段**再追加，否则同一 id 重复会导致该预设声明加载失败。
- 该补丁层是**热加载**的：保存后无需重启 DSH。

> 嫌手工麻烦：把本仓库地址丢给 Harness 里的 AI，说「按 AI_DEPLOY.md 部署这个仓库」，它会用 UTF-8 安全的方式完成两步并自检。

---

## 验证

1. 插件/加载器里能看到 `preset-stylized-blender` 这一行，状态 **active**（`plugin_manager` → `list_plugins`，或用「设置 → 插件」）。
2. **新建**一个会话（不要复用旧会话：会话会钉住启动时的预设 revision）→ 模式列表出现 **风格化着色(Blender NPR)** → 能正常发第一条消息。
3. 技能自检（Blender 里跑一遍全部文档化操作符，跑完自动清场）：

```python
# DSH blender 插件
blender_rt_do(file=r"<DSH_HOME>\skills\stylized-shading\verify_skill.py")
# 或：Blender 文本编辑器打开该文件 → Run Script
# 或：blender.exe -b --python "<DSH_HOME>\skills\stylized-shading\verify_skill.py"
```

判据：输出里有一行 `VERIFY_SKILL {"ok":true,"passed":11,"failed":0,...}`。哪一步失败、为什么、怎么修，见 `SKILL.md` §11 的对照表。

---

## 升级排障：0.2.x 踩过的坑

| 现象 | 根因 | 修法 |
|---|---|---|
| 模式在列表里，但选中/新建会话直接失败（roster 标 broken） | `skill-filesystem.customSkillDirs` 里的 `createRequire(...).resolve('@deepseek-ai/dsh-agent-preset/package.json')` 在 0.2 解析不到（包只在 `app.asar`） | 删掉 `customSkillDirs`；技能放 `<DSH_HOME>/skills`（本仓库已改好） |
| 第一条消息就报 `unknown prompt variable "{{cwd}}"` | 0.2 的提示词变量只剩 `provider` / `model`，`cwd` 已移除 | persona 里不要写 `{{cwd}}`；工作目录由 `working-directory` 作为系统提示上下文注入 |
| 配置里 `backgroundMode` 无效 | 0.2 的 `dsh-tool-subagent` 已移除该键（续聊子代理变成默认能力） | 删掉该键 |
| 升级后模式从列表里消失 | 0.2 不再扫描 `.agent-presets/` 目录式预设 | 用本仓库的 `cordis.patch.yml`（声明式） |
| 手工粘贴后整份补丁不生效 | 中文被写成 ANSI / 或 YAML 缩进被改 | 用 UTF-8 编辑器重贴；缩进必须与文件里其他 `- insert:` 块同级 |

---

## 模式 vs 技能：调用哪一个？

| | **风格化着色模式（preset）** | **stylized-shading 技能（skill）** |
|---|---|---|
| 本质 | 一个 **Agent 预设** = 会话级整套配置 | 一份 **技能文档** = 教 AI 怎么干活的手册 |
| 形态 | `stylized-blender/cordis.patch.yml`（一条声明行） | `skills/stylized-shading/` 下的 md + 自检脚本 |
| 安装位置 | `<DSH_HOME>/profiles/<profile>/cordis.patch.yml` | `<DSH_HOME>/skills/stylized-shading/` |
| 何时用 | **绝大多数情况**：新会话选它 = 完整工具链 + 技能可用 | 单用：当前会话不是这个预设，但想临时借用这份手册 |
| 一句话 | **选这个模式 = 开箱即用** | **技能是模式的内置大脑** |

> 技能放在用户技能目录有一个好处：**任何模式**都看得到它，不再依赖预设的路径解析（这也是升级后唯一稳妥的形态）。

---

## 常见问题

**Q：模式列表里没有「风格化着色(Blender NPR)」？**
A：先确认 `<DSH_HOME>/profiles/<profile>/cordis.patch.yml` 里那段 `- insert:` 加进去了、缩进没被改、且文件是 UTF-8。补丁是热加载的，保存后刷新页面即可；仍不出现就看加载器里 `preset-stylized-blender` 这一行的状态与诊断。

**Q：能看到模式，但一选就报错 / 列表里标红？**
A：说明声明行加载了、但组合 mount 失败。用上表逐条对照（0.2 最常见就是 `customSkillDirs` 与 `{{cwd}}`）。

**Q：会话里看不到 stylized-shading 技能？**
A：确认 `<DSH_HOME>/skills/stylized-shading/SKILL.md` 存在（是这一层，不是再多套一层 `stylized-shading/`）。

**Q：技能里写的插件路径 `E:\rj\blender\...` 我机器上没有？**
A：作者本机路径，仅作参考。你只需把「风格化着色工具」装进自己的 Blender；AI 通过 Blender 连接操作时用的是 Blender 内部 API。

**Q：升级 DSH 会覆盖这些吗？**
A：`<DSH_HOME>/skills/` 和 profile 的 `cordis.patch.yml`（用户层）在升级时保留；被覆盖的是应用自带的 bundle。若哪天 DSH 改了预设字段，按上表思路对着新版官方 `standard` 预设比对即可。

---

## 关于

- 作者：路人甲
- 配套插件：**blender_Stylized-Shading-Tools**（风格化着色工具）
- 参考手册：`stylized-blender/skills/stylized-shading/sas_reference.md`（SAS 参数逻辑）、`material_pipeline.md`（材质管线与 EEVEE 踩坑）
- 本仓库内容 = 作者本机在用的这套预设与技能的归档；0.2.x 下经实测可运行（见 `verify_skill.py` 的 11 项自检）。
- 这套 skill 还在迭代，碰到不顺手的地方欢迎提 issue。
