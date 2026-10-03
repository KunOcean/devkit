#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DevKit 相对链接检查。

扫描仓库内的 HTML 与 Markdown，找出指向不存在文件的相对链接。
这类 404 在 GitHub 上很常见，且肉眼发现不了——例如新增版本文件后忘了
把它加进目录索引，或重命名文件后没改引用。

只检查仓库内的相对链接；http(s)、mailto、纯锚点（#...）一律跳过。

用法：
    本地： python3 .github/scripts/link_check.py
    CI  ： 由 .github/workflows/link-check.yml 调用

退出码：0 = 通过；1 = 存在失效链接。
"""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCAN_SUFFIXES = {".html", ".md"}
SKIP_DIRS = {".git", "node_modules", ".claude"}

ATTR_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"', re.I)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)")

problems: list[str] = []
checked = 0


def is_external(target: str) -> bool:
    lowered = target.lower()
    if lowered.startswith(("http://", "https://", "mailto:", "tel:", "data:")):
        return True
    if target.startswith("#"):
        return True
    # 站点绝对路径（以 / 开头）：它相对于站点根解析，与文件在磁盘上的位置
    # 无关，本地无法校验，跳过而不是误判为失效（404.html 的跳转链接即是这种）。
    if target.startswith("/"):
        return True
    # 模板占位符，例如 {{ url }} 或 ${{ ... }}
    if "{{" in target or "${" in target:
        return True
    return False


def collect_targets(text: str, path: Path) -> list[str]:
    targets = ATTR_RE.findall(text)
    if path.suffix == ".md":
        targets += MD_LINK_RE.findall(text)
    return targets


def check_file(path: Path) -> None:
    global checked
    text = path.read_text(encoding="utf-8", errors="replace")
    rel_file = path.relative_to(ROOT).as_posix()

    for raw in collect_targets(text, path):
        target = raw.strip()
        if not target or is_external(target):
            continue

        # 去掉锚点与查询串后判断文件是否存在
        bare = target.split("#", 1)[0].split("?", 1)[0]
        if not bare:
            continue

        decoded = urllib.parse.unquote(bare)
        candidate = (path.parent / decoded).resolve()

        checked += 1
        if decoded.endswith("/"):
            if not candidate.is_dir():
                problems.append(f"{rel_file} → {target}（目录不存在）")
        elif not candidate.exists():
            problems.append(f"{rel_file} → {target}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    files = [
        p
        for p in sorted(ROOT.rglob("*"))
        if p.is_file()
        and p.suffix in SCAN_SUFFIXES
        and not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
    ]

    for path in files:
        check_file(path)

    for p in problems:
        print(f"[问题] 失效链接：{p}")

    print()
    print(f"检查完成：扫描 {len(files)} 个文件、{checked} 条相对链接，{len(problems)} 个失效。")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
