#!/usr/bin/env python3
"""把本仓库的「风格化着色(Blender NPR)」预设与 stylized-shading 技能装进本机 DSH（0.2.x）。

它做两件事：
  1. 技能  → <DSH_HOME>/skills/stylized-shading/（0.2 的 skill-filesystem 默认就扫这里）
  2. 预设  → 在 <DSH_HOME>/profiles/<profile>/cordis.patch.yml 里**替换或追加**
             一段 `- insert:` 块（同 id 的旧块会先被删掉，保证不会重复）

设计上刻意绕开两个手工部署最常踩的坑：
  - 编码：始终以 UTF-8（无 BOM）写，保留原文件的换行风格；不会把中文写成 ANSI。
  - 重复：按顶层 `- insert:` 边界整段替换，而不是盲目追加。

用法：
    python install.py                      # 默认 <DSH_HOME>（或 ~/.dsh）+ profile desktop
    python install.py --profile web
    python install.py --dsh-home "D:/dsh-home"
    python install.py --dry-run            # 只报告将要做什么，不写任何文件

退出码：0 成功；1 出错（信息打印到 stderr）。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PRESET_PATCH = REPO_ROOT / "cordis.patch.yml"
SKILL_SRC = REPO_ROOT / "skills" / "stylized-shading"

PRESET_ROW = "- id: preset-stylized-blender"
BLOCK_HEAD = "- insert:"

# 被管道/日志捕获时按 UTF-8 输出（Windows 控制台直连时 Python 会走 WriteConsoleW，无需干预）
if not sys.stdout.isatty() and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def info(msg: str) -> None:
    print(f"[install] {msg}")


def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"[install] 错误：{msg}", file=sys.stderr)
    raise SystemExit(1)


def resolve_home(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser().resolve()
    env = os.environ.get("DSH_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".dsh").resolve()


def resolve_profile(home: Path, arg: str | None) -> tuple[str, Path]:
    name = arg or os.environ.get("DSH_PROFILE") or "desktop"
    pdir = home / "profiles" / name
    if pdir.is_dir():
        return name, pdir
    profiles_dir = home / "profiles"
    available = sorted(d.name for d in profiles_dir.iterdir() if d.is_dir()) if profiles_dir.is_dir() else []
    die(f"找不到 profile '{name}'（{pdir}）。现有 profile：{available or '无'}，用 --profile 指定")


def read_text(path: Path) -> tuple[str, str]:
    """返回 (正文, 主导换行符)。"""
    raw = path.read_text(encoding="utf-8-sig")
    eol = "\r\n" if raw.count("\r\n") > raw.count("\n") - raw.count("\r\n") else "\n"
    return raw.replace("\r\n", "\n"), eol


def write_text(path: Path, text: str, eol: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace("\n", eol) if eol != "\n" else text)


def locate_preset_block(lines: list[str]) -> tuple[int, int] | None:
    """找到包含本预设 id 的那一整段顶层 `- insert:` 块，返回闭区间行号。"""
    row = next((i for i, line in enumerate(lines) if line.strip() == PRESET_ROW), None)
    if row is None:
        return None
    start = row
    while start >= 0 and lines[start] != BLOCK_HEAD:
        start -= 1
    if start < 0:
        die(f"在第 {row + 1} 行找到 {PRESET_ROW}，但它不在任何顶层 '{BLOCK_HEAD}' 块里；"
            "请手工检查该补丁文件的结构")
    end = row
    while end + 1 < len(lines) and not re.match(r"^- (id|insert):", lines[end + 1]):
        end += 1
    while end > start and lines[end].strip() == "":
        end -= 1
    return start, end


def patch_profile(patch_file: Path, block: str, dry_run: bool) -> dict:
    if not patch_file.exists():
        die(f"补丁文件不存在：{patch_file}（DSH 启动时通常会生成；确认 profile 名是否正确）")

    text, eol = read_text(patch_file)
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    span = locate_preset_block(lines)
    new_block = block.strip("\n").split("\n")

    if span is None:
        result = lines + ([""] if lines else []) + new_block
        action = "append"
    else:
        start, end = span
        result = lines[:start] + new_block + lines[end + 1:]
        action = f"replace(第 {start + 1}-{end + 1} 行)"

    out = "\n".join(result) + "\n"
    occurrences = sum(1 for line in result if line.strip() == PRESET_ROW)
    if occurrences != 1:
        die(f"内部校验失败：结果里有 {occurrences} 条 {PRESET_ROW}，已放弃写入")

    if not dry_run:
        backup = patch_file.with_name(patch_file.name + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(patch_file, backup)
        write_text(patch_file, out, eol)
        info(f"补丁已更新（{action}），备份：{backup.name}")
    else:
        info(f"[dry-run] 将 {action} 预设块；结果共 {len(result)} 行、1 条 {PRESET_ROW}")

    return {"action": action, "lines": len(result), "occurrences": occurrences}


def install_skill(home: Path, dry_run: bool) -> dict:
    if not SKILL_SRC.is_dir():
        die(f"仓库里缺少技能目录：{SKILL_SRC}")
    dest = home / "skills" / "stylized-shading"
    if not dry_run:
        (home / "skills").mkdir(parents=True, exist_ok=True)
        if dest.exists():
            backup = dest.with_name(dest.name + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
            shutil.move(str(dest), str(backup))
            info(f"已备份旧技能到：{backup.name}")
        shutil.copytree(SKILL_SRC, dest)
        info(f"技能已安装：{dest}")
    else:
        info(f"[dry-run] 将把技能复制到：{dest}")
    return {"dest": str(dest), "files": sorted(p.name for p in SKILL_SRC.iterdir() if p.is_file())}


def main() -> int:
    ap = argparse.ArgumentParser(description="安装风格化着色(Blender NPR)预设与 stylized-shading 技能")
    ap.add_argument("--dsh-home", help="DSH_HOME（默认读环境变量，否则 ~/.dsh）")
    ap.add_argument("--profile", help="profile 名（默认读 DSH_PROFILE，否则 desktop）")
    ap.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = ap.parse_args()

    home = resolve_home(args.dsh_home)
    profile_name, profile_dir = resolve_profile(home, args.profile)
    patch_file = profile_dir / "cordis.patch.yml"
    if not PRESET_PATCH.exists():
        die(f"仓库里缺少预设文件：{PRESET_PATCH}")

    block, _ = read_text(PRESET_PATCH)
    if PRESET_ROW not in block:
        die(f"{PRESET_PATCH} 里没有 {PRESET_ROW}，仓库可能不完整")

    info(f"DSH_HOME = {home}")
    info(f"profile  = {profile_name}  ({profile_dir})")

    skill = install_skill(home, args.dry_run)
    preset = patch_profile(patch_file, block, args.dry_run)

    print()
    print("完成度检查清单：")
    print(f"  [x] 技能：{skill['dest']}  ({len(skill['files'])} 个文件)")
    print(f"  [x] 预设：{patch_file}  ({preset['action']}，1 条声明)")
    print("  [ ] 在 Harness 里确认 preset-stylized-blender 行状态为 active")
    print("  [ ] **新建**会话（不要复用旧会话）→ 模式选「风格化着色(Blender NPR)」→ 发一句话")
    print("  [ ] 技能自检：blender_rt_do(file=r\"<技能目录>\\verify_skill.py\")，应输出 ok=true")
    if args.dry_run:
        print("\n（dry-run：未写入任何文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
