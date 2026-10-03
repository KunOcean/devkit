#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从版本历史生成 Release 说明。

每个版本 HTML 里都嵌着 VERSION_HISTORY 数组，记录了这一代产品的每次改动。
本脚本把它解析出来，汇总成本次发布的说明，避免 Releases 页面只有一句
「主干 X 下的全部版本文件」而看不出改了什么。

汇总规则：
  · 扫描 code/<主干>/ 下所有版本文件，把各文件的 VERSION_HISTORY 合并
  · 只保留版本号以该主干开头的条目
  · 按「说明内容」去重，而不是按版本号 —— 同一个主干下各皮肤会各自记一条
    改动，但内容往往是同一段话（例如「全站响应式适配」在四个旧皮肤里各记
    一遍），按版本号去重挡不住，会连续重复四遍
  · 同一个版本号出现多次时，保留说明最长的那一条
  · 跳过「中文版：同步应用主干版本号 …」这类纯语言后缀样板条目 —— 它们不
    携带改动信息，列出来只是噪音
  · 每条说明截断到 MAX_NOTE_CHARS 字，避免个别超长条目淹没整页
  · 找不到任何条目时回退为一句固定文案，不让发布因解析失败而中断

用法：
    python3 .github/scripts/make_release_notes.py <主干名>
    例：python3 .github/scripts/make_release_notes.py A1_V_Φ8

输出直接打到标准输出，供 gh release create --notes-file 使用。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = ROOT / "code"

MAX_NOTE_CHARS = 240
BOILERPLATE = "中文版：同步应用主干版本号"

ENTRY_RE = re.compile(
    r"\{\s*version:\s*'((?:[^'\\]|\\.)*)',\s*note:\s*'((?:[^'\\]|\\.)*)'",
    re.S,
)


def unescape(text: str) -> str:
    return text.replace("\\'", "'").replace("\\\\", "\\")


def collect(trunk: str) -> list[tuple[str, str]]:
    """返回 [(版本号, 说明)]，按说明内容去重且保持首次出现顺序。"""
    files = sorted((CODE_DIR / trunk).glob("deepseek_*.html"))
    best: dict[str, str] = {}
    order: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for version, note in ENTRY_RE.findall(text):
            version = unescape(version).strip()
            note = " ".join(unescape(note).split())
            if not version.startswith(trunk):
                continue
            if BOILERPLATE in note:
                continue
            if version not in best:
                order.append(version)
                best[version] = note
            elif len(note) > len(best[version]):
                best[version] = note

    # 按说明内容去重：同一段话只保留最早出现的那一条版本记录
    seen_notes: set[str] = set()
    result: list[tuple[str, str]] = []
    for version in order:
        note = best[version]
        if note in seen_notes:
            continue
        seen_notes.add(note)
        result.append((version, note))
    return result


def truncate(note: str) -> str:
    if len(note) <= MAX_NOTE_CHARS:
        return note
    return note[:MAX_NOTE_CHARS].rstrip() + "……"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if len(sys.argv) != 2:
        print("用法：make_release_notes.py <主干名>", file=sys.stderr)
        return 1

    trunk = sys.argv[1]
    trunk_dir = CODE_DIR / trunk
    if not trunk_dir.is_dir():
        print(f"找不到目录 code/{trunk}", file=sys.stderr)
        return 1

    files = sorted(trunk_dir.glob("deepseek_*.html"))
    entries = collect(trunk)

    lines: list[str] = []
    lines.append(f"主干 `{trunk}`，本 Release 附带 {len(files)} 个版本文件（每个都是自包含的单文件应用，下载后可直接用浏览器打开）。")
    lines.append("")

    if entries:
        lines.append("## 本代改动")
        lines.append("")
        for version, note in entries:
            lines.append(f"- **{version}** — {truncate(note)}")
        lines.append("")
    else:
        lines.append("（未从版本历史中解析到该主干的改动记录。）")
        lines.append("")

    lines.append("## 附件")
    lines.append("")
    for path in files:
        kb = path.stat().st_size / 1024
        lines.append(f"- `{path.name}`（{kb:.0f} KB）")

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
