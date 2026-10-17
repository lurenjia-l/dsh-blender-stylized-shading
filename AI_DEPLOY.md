# AI 部署手册（本文件写给 AI 执行）

> 适用：**DeepSeek Harness 0.2.x**。用户说「把这个仓库部署到本地 / 装这个模式 / 装这个技能」时，按本手册执行。
> 人类用户请看 `README.md`。

## 0. 目标与完成标准

把 `风格化着色(Blender NPR)` 预设与 `stylized-shading` 技能装到本机 DSH，使用户新建会话时能选中该模式。

全部满足才算完成：

- [ ] `<DSH_HOME>/skills/stylized-shading/SKILL.md` 存在（注意层级：是 `skills/stylized-shading/`，不要多套一层）
- [ ] `<DSH_HOME>/profiles/<profile>/cordis.patch.yml` 里 **有且只有 1 条** `- id: preset-stylized-blender`
- [ ] 加载器里 `preset-stylized-blender` 这一行状态为 **active**（不是 disabled，也没有诊断报错）
- [ ] 已明确告知用户：**必须新建会话**（旧会话钉住启动时的预设 revision）

## 1. 环境探测（先做，别猜）

```powershell
$env:DSH_HOME            # 空则 DSH_HOME = %USERPROFILE%\.dsh
$env:DSH_PROFILE         # 空则以 profiles 目录为准
Get-ChildItem "$(if ($env:DSH_HOME) { $env:DSH_HOME } else { "$env:USERPROFILE\.dsh" })\profiles" -Directory |
  Select-Object Name
```

- 桌面版 profile 通常是 **desktop**；`dsh web` 启动的是 **web**。
- ⚠️ `desktop` profile 由 Electron 托管：**不要**用 `dsh --profile desktop ...` 去启动它（会被拒绝）。
  改 `cordis.patch.yml` 即可，补丁层是**热加载**的。

## 2. 下载

```powershell
git clone https://github.com/lurenjia-l/dsh-blender-stylized-shading.git "$env:TEMP\dsh-ss"
# 没有 git：Invoke-WebRequest https://github.com/lurenjia-l/dsh-blender-stylized-shading/archive/refs/heads/main.zip
```

## 3. 安装（推荐：一条命令）

```powershell
# 1) 先干跑，确认它认到的 DSH_HOME / profile / 行号都对
python "$env:TEMP\dsh-ss\stylized-blender\install.py" --dry-run

# 2) 真装（技能目录与补丁文件都会先自动备份为 *.bak-<时间戳>）
python "$env:TEMP\dsh-ss\stylized-blender\install.py"

# 需要指定时：
python "$env:TEMP\dsh-ss\stylized-blender\install.py" --dsh-home "D:\dsh-home" --profile web
```

脚本行为（可据 dry-run 输出核对）：

1. 技能：`stylized-blender/skills/stylized-shading/` → `<DSH_HOME>/skills/stylized-shading/`（旧的先备份再替换）
2. 预设：在 profile 补丁里**按 `- insert:` 边界整段替换**同 id 的旧块；没有则追加。
   写入固定 **UTF-8 无 BOM**、保留原换行风格，并在写前自检「结果里有且只有 1 条声明」。

## 4. 手工安装（没有 python 时）

1. 技能：`Copy-Item -Recurse -Force "$env:TEMP\dsh-ss\stylized-blender\skills\stylized-shading" "<DSH_HOME>\skills\"`
2. 预设：用**能写 UTF-8** 的编辑工具，把 `stylized-blender\cordis.patch.yml` 的整段（一个 `- insert:` 块）
   追加到 `<DSH_HOME>\profiles\<profile>\cordis.patch.yml` 末尾。
   - ❌ 不要用 Windows PowerShell 5.1 的 `Add-Content`（默认 ANSI，会写坏中文）
   - ❌ 不要重复追加：已有 `- id: preset-stylized-blender` 时先删掉那一整段
3. 自检：`(Select-String -Path <补丁> -SimpleMatch "- id: preset-stylized-blender").Count` 必须为 `1`。

## 5. 校验（部署后必须自查）

| 检查项 | 方法 | 期望 |
|---|---|---|
| 补丁结构 | 读文件，确认 `- insert:` 块缩进与其他块同级 | 无缩进变化 |
| 声明条数 | 搜 `- id: preset-stylized-blender` | 恰好 1 条 |
| 加载状态 | `plugin_manager` → `list_plugins`，找 `preset-stylized-blender` | `fiberPhase: active` |
| 技能就位 | 读 `<DSH_HOME>/skills/stylized-shading/SKILL.md` 首行 | 存在且是 Markdown |
| 组合能否挂载 | 让用户新建会话并选该模式、发一句话 | 不出错（报错见 §7） |

> 不要用 `agentPresets/list` 之外的猜测判断「能不能用」：**声明行 active ≠ 组合能挂载**，
> 0.2.x 里组合 mount 失败只会在 roster 上标 broken。

## 6. 向用户汇报（模板）

```
已安装：
- 技能：<DSH_HOME>\skills\stylized-shading\（4 个文件）
- 预设：<DSH_HOME>\profiles\<profile>\cordis.patch.yml（替换/追加，1 条声明；原文件备份 *.bak-<时间>）

下一步（需要你操作）：
1. **新建**一个会话（旧会话不会自动切换）
2. 模式选择「风格化着色(Blender NPR)」，随便发一句话
3. 可选自检：在 Blender 里跑 blender_rt_do(file=r"<DSH_HOME>\skills\stylized-shading\verify_skill.py")，
   期望输出 VERIFY_SKILL {"ok":true,"passed":11,...}
```

## 7. 排障速查（0.2.x 实测）

| 现象 | 根因 | 处理 |
|---|---|---|
| 模式在列表里，但新建会话就失败 / 标 broken | 旧组合里 `skill-filesystem.customSkillDirs` 用 `createRequire(...).resolve('@deepseek-ai/dsh-agent-preset/package.json')`，0.2 该包只在 `app.asar`，抛 `MODULE_NOT_FOUND` | 删掉 `customSkillDirs`；技能放 `<DSH_HOME>/skills`（本仓库已改好） |
| 第一条消息报 `unknown prompt variable "{{cwd}}"` | 0.2 提示词变量只剩 `provider` / `model` | persona 里不要写 `{{cwd}}`；工作目录由 `working-directory` 上下文注入 |
| 配置里 `backgroundMode` 无效果 | 0.2 的 `dsh-tool-subagent` 已移除该键 | 删掉 |
| 列表里根本没有这个模式 | 用了 `legacy/` 里的目录式预设（0.2 不再扫描 `.agent-presets/`） | 改用 `stylized-blender/cordis.patch.yml` |
| 补丁改了但没变化 | 保存成了 ANSI / 结构被改坏 / 看的是旧会话 | 用 UTF-8 重贴；刷新页面；**新建**会话 |
| 技能列表里没有 stylized-shading | 复制层级错了 | 目标必须是 `<DSH_HOME>\skills\stylized-shading\SKILL.md` |
