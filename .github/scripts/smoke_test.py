#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DevKit HTML 运行时冒烟测试。

version_guard.py 只做静态检查：版本号是否一致、脚本能否被解析。它抓不到
"语法没错但一跑就报错"的问题——例如访问了不存在的 DOM 元素、变量未定义、
初始化流程抛异常。

本脚本用无头浏览器逐个打开 code/ 下的版本文件，检查：

  1. 控制台没有 Uncaught / SyntaxError / TypeError / ReferenceError
  2. <body> 带上了类名（说明初始化脚本跑到了设置主题那一步）
  3. 页面有非空 <title>

用法：
    本地： python3 .github/scripts/smoke_test.py
          浏览器不在 PATH 时用 CHROME_BIN 指定，例如：
          CHROME_BIN="/c/Program Files/Google/Chrome/Application/chrome.exe" python3 .github/scripts/smoke_test.py
    CI  ： 由 .github/workflows/repo-checks.yml 调用

退出码：0 = 通过；1 = 有文件未通过或找不到浏览器。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = ROOT / "code"

ERROR_RE = re.compile(r"CONSOLE.*?(Uncaught|SyntaxError|TypeError|ReferenceError)")
BODY_RE = re.compile(r'<body[^>]*\bclass="([^"]*)"', re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.I | re.S)

VIRTUAL_TIME_BUDGET = "6000"
WAIT_FOR_OUTPUT_SECONDS = 30

problems: list[str] = []
warnings: list[str] = []


def find_browser() -> str | None:
    override = os.environ.get("CHROME_BIN")
    if override and Path(override).exists():
        return override
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def wait_for_output(dom_file: Path, deadline_seconds: int) -> None:
    """等待子进程把 DOM 写完。

    在 Windows 上 chrome.exe 是启动器，可能在真正的浏览器进程产出输出之前
    就返回，于是 subprocess.run 结束时文件还是空的。轮询到有内容为止。
    """
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        try:
            if dom_file.stat().st_size > 0:
                return
        except OSError:
            pass
        time.sleep(0.3)


def run_one(browser: str, path: Path, rel: str) -> None:
    # 用 as_uri() 而不是手工拼 file:// 加 quote：手工拼会把 Windows 的盘符
    # 冒号也编码成 %3A，URL 失效后浏览器会打开新标签页，检查随之误判。
    url = path.as_uri()

    # 用文件重定向而不是管道：Windows 上管道会在启动器退出时被判定结束，
    # 真正的内容还没写进来。临时目录容忍清理失败——浏览器进程可能仍持有句柄。
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        dom_file = Path(tmp) / "dom.html"
        err_file = Path(tmp) / "err.txt"
        with open(dom_file, "w", encoding="utf-8") as df, open(
            err_file, "w", encoding="utf-8"
        ) as ef:
            subprocess.run(
                [
                    browser,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--virtual-time-budget=" + VIRTUAL_TIME_BUDGET,
                    "--enable-logging=stderr",
                    "--dump-dom",
                    url,
                ],
                stdout=df,
                stderr=ef,
                timeout=120,
            )
        wait_for_output(dom_file, WAIT_FOR_OUTPUT_SECONDS)
        dom_text = dom_file.read_text(encoding="utf-8", errors="replace")
        stderr_text = err_file.read_text(encoding="utf-8", errors="replace")

    console_errors = ERROR_RE.findall(stderr_text)
    if console_errors:
        first = ERROR_RE.search(stderr_text)
        snippet = first.group(0) if first else "未知错误"
        problems.append(f"{rel}：控制台报错 {len(console_errors)} 处，首条：{snippet[:160]}")
        return

    if not dom_text.strip():
        problems.append(f"{rel}：等待 {WAIT_FOR_OUTPUT_SECONDS} 秒后仍未取到页面内容")
        return

    # 版本文件要求 <body> 带上主题类名（说明初始化脚本跑到了设置主题那一步）；
    # 导航页是静态页，本来就没有类名，只要求 <body> 存在。
    is_nav = path.name == "index.html"
    body = BODY_RE.search(dom_text)
    if is_nav:
        if not re.search(r"<body\b", dom_text):
            problems.append(f"{rel}：找不到 <body> 标签")
    elif not body:
        problems.append(f"{rel}：找不到带类名的 <body> 标签")
    elif not body.group(1).strip():
        problems.append(f"{rel}：<body> 没有类名，初始化脚本可能未执行到设置主题那一步")

    title = TITLE_RE.search(dom_text)
    if not title or not title.group(1).strip():
        problems.append(f"{rel}：<title> 为空")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    browser = find_browser()
    if browser is None:
        print("[问题] 找不到 Chrome / Chromium。用 CHROME_BIN 指定浏览器路径后重试。")
        return 1

    # 除版本文件外，也覆盖三层导航页（落地页、code/ 目录页、各主干目录页）。
    # 导航页此前不在覆盖范围内，但它们是访客的实际入口，改坏了同样致命。
    files = sorted(CODE_DIR.glob("*/deepseek_*.html"))
    files += sorted(CODE_DIR.glob("*/index.html"))
    root_index = ROOT / "index.html"
    if root_index.exists():
        files.append(root_index)
    if not files:
        print("[问题] 没有找到任何可测的 HTML 文件。")
        return 1

    print(f"使用浏览器：{browser}")
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            run_one(browser, path, rel)
        except subprocess.TimeoutExpired:
            problems.append(f"{rel}：打开超时（超过 120 秒）")

    for p in problems:
        print(f"[问题] {p}")
    for w in warnings:
        print(f"[告警] {w}")

    print()
    print(f"冒烟测试完成：{len(files)} 个文件，{len(problems)} 个问题，{len(warnings)} 条告警。")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
