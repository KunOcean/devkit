#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main 一更新就自动发布。

每次推送到 main 都产生一个 Release：

  · 本次推送改动了哪些主干（code/<主干>/ 下的文件），就给哪些主干各发一个
  · 一个主干都没改到（例如只改了文档或 CI），则只给**最新的主干**发一个，
    说明里写明「无功能更新」，并附上同一批文件与校验和，供比对确认一致
  · 标签命名：一个主干的第一个 Release 用主干名本身（如 A1_V_Φ8），
    之后递增为 A1_V_Φ8.1、A1_V_Φ8.2……

发布说明由 make_release_notes.build_notes() 生成；附件是该主干下的全部
版本 HTML。

用法（由 .github/workflows/release-on-main.yml 调用）：
    GITHUB_REPOSITORY=... GITHUB_TOKEN=... BEFORE_SHA=... AFTER_SHA=... \\
        python3 .github/scripts/auto_release.py

退出码：0 = 成功；1 = 出错。
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_release_notes import build_notes  # noqa: E402

API = "https://api.github.com"
UPLOAD_API = "https://uploads.github.com"
ZERO_SHA = "0" * 40

ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = ROOT / "code"
PHI_RE = re.compile(r"Φ(\d+)")


def api(method: str, url: str, token: str, payload: dict | None = None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "devkit-auto-release")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, (json.loads(body) if body.strip() else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def local_trunks() -> list[str]:
    return sorted(p.name for p in CODE_DIR.iterdir() if p.is_dir())


def latest_trunk() -> str | None:
    """按 Φ 数字取最大的主干；没有 Φ 时退化为字典序最大的那个。"""
    trunks = local_trunks()
    if not trunks:
        return None
    with_phi = [(int(m.group(1)), t) for t in trunks if (m := PHI_RE.search(t))]
    if with_phi:
        return max(with_phi)[1]
    return max(trunks)


def next_tag(trunk: str, existing: set[str]) -> str:
    """给定已存在的标签集合，算出该主干的下一个标签名。"""
    if trunk not in existing:
        return trunk
    nums = [
        int(m.group(1))
        for name in existing
        if (m := re.fullmatch(re.escape(trunk) + r"\.(\d+)", name))
    ]
    return f"{trunk}.{(max(nums) + 1) if nums else 1}"


def changed_trunks(repo: str, token: str, before: str, after: str) -> list[str] | None:
    """返回本次推送改动的主干列表；无法比较时返回 None（表示退化为全部）。"""
    if not before or before == ZERO_SHA:
        return None
    status, data = api("GET", f"{API}/repos/{repo}/compare/{before}...{after}", token)
    if status != 200 or not data:
        return None
    found: list[str] = []
    for f in data.get("files", []):
        name = f.get("filename", "")
        parts = name.split("/")
        if len(parts) >= 3 and parts[0] == "code":
            if parts[1] not in found:
                found.append(parts[1])
    return found


def existing_tags(repo: str, token: str, trunk: str) -> set[str]:
    url = f"{API}/repos/{repo}/git/matching-refs/tags/{urllib.parse.quote(trunk)}"
    status, data = api("GET", url, token)
    if status != 200 or not data:
        return set()
    names = set()
    for ref in data:
        name = ref.get("ref", "").removeprefix("refs/tags/")
        if name == trunk or name.startswith(trunk + "."):
            names.add(name)
    return names


def create_tag(repo: str, token: str, tag: str, sha: str) -> bool:
    status, _ = api(
        "POST", f"{API}/repos/{repo}/git/refs", token, {"ref": f"refs/tags/{tag}", "sha": sha}
    )
    return status in (201, 200)


def asset_name(filename: str) -> str:
    """把附件名转成 ASCII 安全形式。

    GitHub 会把 Release 附件名里的非 ASCII 字符换成别的字符：实测 Φ 变成了
    `.`，于是 deepseek_A1_V_Φ8_Fix_CN.html 上传后下载名成了
    deepseek_A1_V_.8_Fix_CN.html。上传时用 Phi 代替 Φ，另用 label 参数保留
    原写法供界面显示（label 若同样被净化也无副作用）。
    """
    return filename.replace("Φ", "Phi")


def upload_asset(repo: str, token: str, release_id: int, path: Path) -> bool:
    url = (
        f"{UPLOAD_API}/repos/{repo}/releases/{release_id}/assets"
        f"?name={urllib.parse.quote(asset_name(path.name))}"
        f"&label={urllib.parse.quote(path.name)}"
    )
    body = path.read_bytes()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/octet-stream")
    req.add_header("User-Agent", "devkit-auto-release")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.status in (200, 201)
    except urllib.error.HTTPError as e:
        print(f"[告警] 上传 {path.name} 失败：HTTP {e.code}")
        return False


def release_trunk(
    repo: str, token: str, trunk: str, sha: str, mode: str, forced_tag: str | None = None
) -> bool:
    trunk_dir = CODE_DIR / trunk
    files = sorted(trunk_dir.glob("deepseek_*.html"))
    if not files:
        print(f"[告警] {trunk} 下没有版本文件，跳过。")
        return True

    existing = existing_tags(repo, token, trunk)
    if forced_tag:
        if forced_tag in existing:
            print(f"[问题] 标签 {forced_tag} 已存在。换一个后缀，或删掉旧标签后重试。")
            return False
        tag = forced_tag
    else:
        tag = next_tag(trunk, existing)
    print(f"—— 主干 {trunk} → 标签 {tag}（{len(files)} 个附件）")

    if not create_tag(repo, token, tag, sha):
        print(f"[问题] 创建标签 {tag} 失败。")
        return False

    status, release = api(
        "POST",
        f"{API}/repos/{repo}/releases",
        token,
        {
            "tag_name": tag,
            "name": tag,
            "body": build_notes(trunk, mode),
            "draft": False,
            "prerelease": False,
        },
    )
    if status not in (201, 200) or not release:
        print(f"[问题] 创建 Release {tag} 失败（HTTP {status}）。")
        return False

    release_id = release["id"]
    uploaded = 0
    for path in files:
        if upload_asset(repo, token, release_id, path):
            uploaded += 1
    print(f"   已发布 {tag}，附件 {uploaded}/{len(files)}")

    if uploaded != len(files):
        print(f"[问题] {tag} 有附件未上传成功。")
        return False
    return True


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    before = os.environ.get("BEFORE_SHA", "").strip()
    after = os.environ.get("AFTER_SHA", "").strip()
    dispatch_trunk = os.environ.get("DISPATCH_TRUNK", "").strip()
    dispatch_suffix = os.environ.get("DISPATCH_SUFFIX", "").strip()

    if not repo or not token or not after:
        print("[问题] 需要 GITHUB_REPOSITORY、GITHUB_TOKEN、AFTER_SHA 环境变量。")
        return 1

    forced_tag: str | None = None

    if dispatch_trunk:
        # 手动触发：为指定主干补发一个 Release。用于自动发布覆盖不到的情况，
        # 例如为已冻结、不会再被推送碰到的老主干留一个固定的下载入口。
        if not (CODE_DIR / dispatch_trunk).is_dir():
            print(
                f"[问题] 找不到目录 code/{dispatch_trunk}。现有主干："
                + "、".join(local_trunks())
            )
            return 1
        targets = [dispatch_trunk]
        mode = "manual"
        if dispatch_suffix:
            forced_tag = f"{dispatch_trunk}.{dispatch_suffix}"
        reason = f"手动触发，补发主干 {dispatch_trunk}"
        if dispatch_suffix:
            reason += f"（指定标签后缀 {dispatch_suffix}）"
    else:
        changed = changed_trunks(repo, token, before, after)
        if changed is None:
            targets = local_trunks()
            mode = "changed"
            reason = "无法比较提交范围，退化为为全部主干发布"
        elif changed:
            targets = changed
            mode = "changed"
            reason = "本次推送改动了：" + "、".join(changed)
        else:
            latest = latest_trunk()
            if latest is None:
                print("[问题] code/ 下没有任何主干目录。")
                return 1
            targets = [latest]
            mode = "no_changes"
            reason = "本次推送未改动交付物文件，只给最新主干发一个「无功能更新」的 Release"

    print(f"仓库 {repo} · {reason}")
    print(f"将发布：{'、'.join(targets) if targets else '（无）'}")
    print()

    ok = True
    for trunk in targets:
        if not (CODE_DIR / trunk).is_dir():
            print(f"[告警] code/{trunk} 不存在，跳过。")
            continue
        if not release_trunk(repo, token, trunk, after, mode, forced_tag):
            ok = False

    print()
    print("发布完成。" if ok else "发布结束，但存在失败项。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
