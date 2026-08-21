# dsh-blender-stylized-shading

**DeepSeek Harness 风格化着色（Blender NPR）模式 + stylized-shading 技能** 一键部署仓库。

本仓库打包了两样东西，它们配套使用，让你（或任何 AI）在 DeepSeek Harness 里直接对话就能驱动 Blender 制作卡通 / 赛璐璐 / 三渲二风格化（NPR）材质：

| 内容 | 是什么 | 位置 |
|---|---|---|
| **风格化着色模式** | 一个完整可选的 **Agent 预设（preset）**，名为 `风格化着色(Blender NPR)`。它把标准编码 Agent 的全部能力 + stylized-shading 技能预装进一个会话 | `stylized-blender/` |
| **stylized-shading 技能** | 一份给 AI 读的**使用说明书**，教 AI 正确调用"风格化着色工具"插件（blender_Stylized-Shading-Tools）的 NPR 节点组，并把你的自然语言需求翻译成节点参数 | `stylized-blender/skills/stylized-shading/` |

> 配套插件 **blender_Stylized-Shading-Tools**（"风格化着色工具"）本体**不在本仓库**，需要单独安装到 Blender（见"你需要准备"）。

---

## 仓库结构

```
dsh-blender-stylized-shading/
├── README.md          ← 你正在读的：给人类看的下载/部署/调用说明
├── AI_DEPLOY.md       ← 给 AI 看的部署手册：把仓库丢给任何 AI，它按此自动部署
├── .gitignore
└── stylized-blender/  ← 整个文件夹 = 一个 Agent 预设，复制到 .agent-presets 即可用
    ├── preset.yml                     # 预设名称与描述（roster 靠它显示）
    ├── agent.cordis.yml               # 预设组成（技能注册、工具、plan/compaction 等）
    └── skills/
        ├── stylized-shading/          # ★ 核心技能（本文档重点）
        │   ├── SKILL.md               # 主指南：节点组清单/添加/串联/调参/风格配方/创意效果
        │   ├── sas_reference.md       # Stylized Asset Suite 参数逻辑参考（发散建组用）
        │   └── material_pipeline.md   # 材质管线与灯光响应分工、EEVEE 踩坑修复
        ├── cordis-plugin-development/         # 配套技能：写/改 Cordis 插件
        └── editing-cordis-compositions/       # 配套技能：写/改 agent 组成文件
```

---

## 你需要准备

1. **DeepSeek Harness（dsh）** —— 本模式运行的宿主，Web 界面通常跑在 `http://127.0.0.1:3080`。
2. **Blender 3.4+**，并安装启用插件 **blender_Stylized-Shading-Tools**（"风格化着色工具"，作者 路人甲）。
   - 插件启用后，Blender 侧边栏 N 键 → "风格化材质"标签页可用；节点编辑器 Shift+A → "风格化节点"菜单。
   - ⚠️ 技能文档里写的插件路径（`E:\rj\blender\plugin\addons\...`）是**作者本机路径**，你自己的机器上按实际安装位置为准，AI 只把它当参考。
3. **（推荐）Blender MCP 连接** —— 让 AI 直接通过 `execute_blender_code` 驱动 Blender；没有它你也能手动照技能文档操作。

---

## 快速开始（3 步）

### 第 1 步：下载

```bash
git clone https://github.com/lurenjia-l/dsh-blender-stylized-shading.git
# 或者：GitHub 页面 Code → Download ZIP，解压到任意位置
```

### 第 2 步：部署（把 `stylized-blender` 整个文件夹放进预设目录）

预设目录位置（两者取其一）：

- 没设置 `DSH_HOME` 环境变量：`%USERPROFILE%\.dsh\.agent-presets\`
- 设置了 `DSH_HOME`：`%DSH_HOME%\.agent-presets\`

```powershell
# 示例（Windows）：
$dst = "$env:USERPROFILE\.dsh\.agent-presets"
Copy-Item -Recurse ".\dsh-blender-stylized-shading\stylized-blender" $dst
# 最终应看到：$dst\stylized-blender\preset.yml
```

> ⚠️ 是复制 `stylized-blender` **这个文件夹本身**（不是它的父目录），最终路径必须是 `...\.agent-presets\stylized-blender\preset.yml`。

### 第 3 步：调用

1. 刷新/打开 Harness Web 界面（`http://127.0.0.1:3080`）。
2. 新建会话，在 **Agent 预设**列表里选择 **`风格化着色(Blender NPR)`**。
3. 直接说需求，例如：
   - 「把选中的物体做成风格化卡通（三渲二）材质」
   - 「给选中的球做一个拉丝金属材质」
   - 「改成清透玻璃，边缘要有菲涅耳亮边」
   - 「加漫画排线，像素描」
   - 「场景里加雾 / 加光柱」

AI 会自动加载 `stylized-shading` 技能，把需求翻译成插件的节点组与参数。

---

## 模式 vs 技能：到底调用哪一个？

这是最容易混淆的一点，对照如下：

| | **风格化着色模式（preset）** | **stylized-shading 技能（skill）** |
|---|---|---|
| 本质 | 一个 **Agent 预设**，是"会话级别的整套配置" | 一份 **技能文档**，是"教 AI 怎么干活的手册" |
| 形态 | `stylized-blender/` 文件夹（preset.yml + agent.cordis.yml + skills/） | `skills/stylized-shading/` 下的 md 文件 |
| 安装位置 | `%USERPROFILE%\.dsh\.agent-presets\` | 随 preset 一起装（`customSkillDirs` 自动指向 preset 内 `skills/`），也可被任何会话单独加载 |
| 何时用 | **绝大多数情况**。新会话选它，就同时拥有：完整工具链 + 技能自动可用 | 单独用：你的会话不是这个预设，但想临时借用这份手册时，让 AI 读该技能 |
| 一句话 | **「选这个模式 = 开箱即用」** | **「技能是模式的内置大脑」** |

**推荐用法**：直接用模式（预设）。技能作为模式的一部分自动生效，无需单独操心。

---

## 验证部署成功

- [ ] `%USERPROFILE%\.dsh\.agent-presets\stylized-blender\` 下存在 `preset.yml`、`agent.cordis.yml`、`skills\stylized-shading\SKILL.md`
- [ ] Harness Web 新建会话时，预设列表出现 **风格化着色(Blender NPR)**
- [ ] 会话开始后，AI 的工具/技能目录里能看到 `stylized-shading` 技能（告诉 AI「你现在有哪些技能？」，它应列出该技能并给出简介）

---

## 给 AI 的自动化部署（一条命令都不用你自己想）

把本仓库地址发给任何一个 DeepSeek Harness AI，说：

> 把这个仓库 https://github.com/lurenjia-l/dsh-blender-stylized-shading 部署到本地

AI 会读取仓库里的 **`AI_DEPLOY.md`**（专为 AI 编写的标准作业程序），自动完成：探测 `DSH_HOME` → 下载 → 复制到 `.agent-presets\stylized-blender` → 校验文件 → 汇报结果。你只需要最后刷新页面选预设。

---

## 常见问题（FAQ）

**Q：预设列表里没有"风格化着色(Blender NPR)"？**
A：检查复制路径是否正确：必须是 `...\.agent-presets\stylized-blender\preset.yml`（多套了一层或少了 `stylized-blender` 这层目录都不行）；复制后刷新页面。

**Q：会话里看不到 stylized-shading 技能？**
A：确认 `agent.cordis.yml` 和 `skills\stylized-shading\` 一起复制过去了（技能由 preset 内的 `skill-filesystem` 行注册，`customSkillDirs` 相对 preset 目录解析，所以**整目录复制即可，无需改配置**）。

**Q：技能里写的插件路径是 `E:\rj\blender\...`，我机器上没有？**
A：那是作者本机路径，仅作参考。你只需把"风格化着色工具"插件装到自己的 Blender 并启用；AI 通过 Blender MCP 的 `execute_blender_code` 操作时用的是 Blender 内部 API，不依赖该绝对路径。

**Q：升级 DeepSeek Harness 会不会覆盖我的预设？**
A：不会。本预设装在用户目录 `%USERPROFILE%\.dsh\.agent-presets\`，只有部署自带的 `agent-presets` 目录会在升级时被覆盖；用户目录的内容始终保留。

**Q：没有 Blender MCP 也能用吗？**
A：可以手动按 `SKILL.md` 在 Blender 里操作；但让 AI 自动干活需要 Blender MCP 连接。

---

## 关于

- 作者：路人甲
- 配套 Blender 插件：**blender_Stylized-Shading-Tools**（风格化着色工具）
- 技能参考手册：`stylized-blender/skills/stylized-shading/sas_reference.md`（Stylized Asset Suite 参数逻辑）、`material_pipeline.md`（材质管线与 EEVEE 踩坑修复）
- 本仓库内容 = DeepSeek Harness 用户目录中的 `stylized-blender` 预设原样归档，部署无需修改任何配置。
