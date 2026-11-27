#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试版体系（build_test_version.py / test_guard.py / make_release_notes.py）的单测。

这套体系有两条容易悄悄坏掉的不变量：

  · 生成清单 ↔ 磁盘目录双向对齐。只校验清单内文件的话，手放一个
    测试版目录会绕过 --check 的漂移检测。
  · 各项目「文件该叫什么」的规则不同（dircleaner 没有 _CN 后缀、
    没有 CURRENT_VERSION；submerge-pro 没有 CURRENT_VERSION）。规则
    写错时 test_guard 会对全部测试版误报，或反过来全都放行。

用法：
    python3 .github/scripts/test_test_version_system.py
    python3 -m unittest discover -s .github/scripts -p 'test_*.py'

退出码：0 = 全部通过；1 = 有用例失败。
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]

sys.path.insert(0, str(SCRIPTS))

import make_release_notes as notes  # noqa: E402
import test_guard as guard  # noqa: E402


def _load_builder():
    """文件名以 test_ 开头，unittest discover 会把它当测试模块导入；
    测试版生成器同理需要按路径加载，不能直接 import。"""
    spec = importlib.util.spec_from_file_location(
        "build_test_version", SCRIPTS / "build_test_version.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


builder = _load_builder()


class TestTargetsManifest(unittest.TestCase):
    """生成清单本身必须自洽，否则 --check 会漏检或错检。"""

    def test_covers_all_five_projects(self):
        projects = {t["project"] for t in builder.TARGETS}
        self.assertEqual(
            projects,
            {"devkit", "writer", "persona", "dircleaner", "submerge-pro"},
        )

    def test_each_target_has_selftest_file(self):
        for t in builder.TARGETS:
            with self.subTest(project=t["project"]):
                self.assertTrue(
                    (SCRIPTS / t["selftest"]).exists(),
                    f"{t['selftest']} 不存在",
                )

    def test_base_paths_exist(self):
        for t in builder.TARGETS:
            with self.subTest(project=t["project"]):
                self.assertTrue(t["base_path"].exists(), t["base_path"])

    def test_out_dir_name_matches_test_name(self):
        for t in builder.TARGETS:
            with self.subTest(project=t["project"]):
                self.assertEqual(t["out_dir"].name, t["test_name"])

    def test_test_version_matches_language_suffix_rule(self):
        """dircleaner 不带 _CN，其余项目必须带。文件名与版本代号都由
        这一条规则推出，写错会让 test_guard 对整批测试版误报。"""
        for t in builder.TARGETS:
            with self.subTest(project=t["project"]):
                want_cn = t["project"] not in guard.NO_LANG_SUFFIX
                self.assertEqual(t["test_version"].endswith("_CN"), want_cn)

    def test_version_regex_accepts_all_test_names(self):
        for t in builder.TARGETS:
            with self.subTest(project=t["project"]):
                self.assertRegex(t["test_name"], guard.VERSION_RE)

    def test_baseline_dir_exists_in_code(self):
        """每个测试版的基线主干必须真实存在于 code/ 下。"""
        for t in builder.TARGETS:
            with self.subTest(project=t["project"]):
                base = guard.baseline_of(t["test_name"])
                self.assertTrue(
                    (ROOT / "projects" / t["project"] / "code" / base).is_dir(),
                    base,
                )


class TestGuardRules(unittest.TestCase):
    """test_guard 的项目级豁免，与 version_guard 的口径保持一致。"""

    def test_baseline_of_strips_only_test_suffix(self):
        self.assertEqual(guard.baseline_of("A1_VI_Φ1_Test1"), "A1_VI_Φ1")
        self.assertEqual(
            guard.baseline_of("A1_V_Φ9_Fix_Fix_Test2"), "A1_V_Φ9_Fix_Fix"
        )

    def test_baseline_of_keeps_skin_like_segments(self):
        """`_Fix` / `_Clean` 这类英文标识不是测试标记，不能被剥掉。"""
        self.assertEqual(guard.baseline_of("A1_I_Φ6_Test1"), "A1_I_Φ6")

    def test_version_regex(self):
        ok = ["A1_VI_Φ1_Test1", "A1_II_Φ15_Test1", "A1_V_Φ9_Fix_Fix_Test12"]
        bad = ["A1_VI_Φ1", "A1_VI_Φ1_Test", "T1", "A1_VI_Φ1_CN_Test1"]
        for v in ok:
            with self.subTest(v=v):
                self.assertRegex(v, guard.VERSION_RE)
        for v in bad:
            with self.subTest(v=v):
                self.assertIsNone(guard.VERSION_RE.match(v))

    def test_no_lang_suffix_matches_dircleaner_only(self):
        self.assertEqual(guard.NO_LANG_SUFFIX, {"dircleaner"})

    def test_no_current_version_covers_dircleaner_and_submerge(self):
        self.assertEqual(
            guard.NO_CURRENT_VERSION, {"dircleaner", "submerge-pro"}
        )


class TestSelftestCounts(unittest.TestCase):
    """发布说明里的自检项数按项目取值，不再是写死的 17。"""

    def test_each_project_has_an_entry(self):
        for t in builder.TARGETS:
            with self.subTest(project=t["project"]):
                self.assertIn(t["project"], notes.SELFTEST_COUNTS)

    def test_unknown_project_falls_back(self):
        self.assertEqual(
            notes.selftest_count("no-such-project"), notes.SELFTEST_COUNT
        )

    def test_known_project_returns_its_own_count(self):
        self.assertEqual(notes.selftest_count("submerge-pro"), 14)
        self.assertEqual(notes.selftest_count("devkit"), 17)


if __name__ == "__main__":
    unittest.main(verbosity=2)
