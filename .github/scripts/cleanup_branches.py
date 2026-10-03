#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理已合并 PR 遗留的分支。

GitHub 的「自动删除头部分支」只对同仓分支生效：来自 fork 的 PR 合并后，
head 分支留在 fork 上；而为了让堆叠 PR 能指定 base，feature 分支又在上游
也放了一份。两边都会越积越多，本脚本负责清理上游这一份。

两种运行模式：
  · 定向模式：设置 PR_NUMBER，只处理该 PR 的 head 分支。用于「PR 一合并
    就删」——由 pull_request_target 的 closed 事件触发时使用。
  · 全量模式：不设 PR_NUMBER，扫描最近 100 个已合并 PR，清理所有残留分支。
    用于每周定时兜底（漏掉的、或当时因故跳过的）。

安全规则（任一命中即跳过）：
  · 默认分支（main）永不删除
  · 任何仍被「打开的 PR」当作 base 的分支不删 —— 堆叠链上的父分支要等
    子 PR 合并后才轮到它，否则会把子 PR 的 base 抽掉
  · 未合并就被关闭的 PR，其分支不删（可能还要继续用）
  · 该分支不存在于本仓库时跳过（正常情况：它只存在于 fork）

只清理本仓库（上游）的分支。fork 上的分支 GITHUB_TOKEN 无权删除——那需要
另配一个有 fork 写权限的令牌，本脚本刻意不碰。

用法：
    本地全量试跑：
        DRY_RUN=1 GITHUB_REPOSITORY=bmdy1145/devkit GITHUB_TOKEN=xxx \\
            python3 .github/scripts/cleanup_branches.py
    本地定向试跑：
        PR_NUMBER=9 DRY_RUN=1 ... python3 .github/scripts/cleanup_branches.py

退出码：0 = 执行完毕（含跳过）；1 = 出现无法忽略的错误。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"


def api(method: str, url: str, token: str):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "devkit-cleanup-branches")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def collect_targets(repo: str, token: str, target_pr: str, default_branch: str):
    """返回 (待删分支列表, 保留分支集合)。出错时抛 RuntimeError。"""
    status, branches = api("GET", f"{API}/repos/{repo}/branches?per_page=100", token)
    if status != 200:
        raise RuntimeError(f"读取分支列表失败（HTTP {status}）")
    existing = {b["name"] for b in (branches or [])}

    status, open_prs = api("GET", f"{API}/repos/{repo}/pulls?state=open&per_page=100", token)
    if status != 200:
        raise RuntimeError(f"读取打开的 PR 失败（HTTP {status}）")
    protected = {pr["base"]["ref"] for pr in (open_prs or [])}
    protected.add(default_branch)

    if target_pr:
        status, pr = api("GET", f"{API}/repos/{repo}/pulls/{target_pr}", token)
        if status != 200 or not pr:
            raise RuntimeError(f"读取 PR #{target_pr} 失败（HTTP {status}）")
        if not pr.get("merged_at"):
            print(f"PR #{target_pr} 未合并（仅关闭），其分支保留。")
            return [], protected
        closed_prs = [pr]
    else:
        status, closed_prs = api(
            "GET",
            f"{API}/repos/{repo}/pulls?state=closed&per_page=100&sort=updated&direction=desc",
            token,
        )
        if status != 200:
            raise RuntimeError(f"读取已关闭的 PR 失败（HTTP {status}）")

    candidates: list[str] = []
    for pr in closed_prs or []:
        if not pr.get("merged_at"):
            continue
        ref = (pr.get("head") or {}).get("ref")
        if ref and ref in existing and ref not in protected and ref not in candidates:
            candidates.append(ref)
    return candidates, protected


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    target_pr = os.environ.get("PR_NUMBER", "").strip()
    dry_run = os.environ.get("DRY_RUN", "") not in ("", "0", "false")

    if not repo or not token:
        print("[问题] 需要 GITHUB_REPOSITORY 与 GITHUB_TOKEN 环境变量。")
        return 1

    status, repo_info = api("GET", f"{API}/repos/{repo}", token)
    if status != 200 or not repo_info:
        print(f"[问题] 读取仓库信息失败（HTTP {status}）。")
        return 1
    default_branch = repo_info.get("default_branch", "main")

    mode = f"定向（PR #{target_pr}）" if target_pr else "全量"
    print(f"仓库 {repo} · 模式：{mode} · 默认分支 {default_branch}")

    try:
        candidates, protected = collect_targets(repo, token, target_pr, default_branch)
    except RuntimeError as e:
        print(f"[问题] {e}")
        return 1

    print(f"保留中的分支（默认分支 + 打开中的 PR 的 base）：{', '.join(sorted(protected))}")
    print()

    if not candidates:
        print("没有可清理的分支。")
        return 0

    failed: list[str] = []
    for ref in sorted(candidates):
        if dry_run:
            print(f"[试运行] 将删除 {ref}")
            continue
        status, _ = api("DELETE", f"{API}/repos/{repo}/git/refs/heads/{ref}", token)
        if status in (204, 200):
            print(f"已删除 {ref}")
        else:
            failed.append(f"{ref}（HTTP {status}）")
            print(f"[告警] 删除 {ref} 失败：HTTP {status}")

    for f in failed:
        print(f"[问题] {f}")

    print()
    action = "将删除" if dry_run else "已删除"
    print(f"清理完成：{action} {len(candidates)} 个分支，失败 {len(failed)} 个。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
