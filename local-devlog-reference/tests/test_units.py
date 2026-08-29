"""test_units.py — 单元测试（任何平台可跑，不需要 OpenVINO / 模型 / Intel 硬件）。

覆盖重点是本 skill 的三条正确性底线：
  1. 反幻觉守卫必须剔除证据中不存在的数字，且不得误伤真实数字
  2. 无证据字段必须诚实标「待补充」/「未验证」，不得被当成有效内容
  3. 证据锚点必须来自真实的 git / 日志解析结果

运行：
    python tests\\test_units.py            （或 python -m unittest discover tests）
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import backends  # noqa: E402
import common  # noqa: E402
import devlog_engine as de  # noqa: E402
import evidence  # noqa: E402


# ==========================================================================
class TestHallucinationGuard(unittest.TestCase):
    """反幻觉守卫：本 skill 的立身之本。"""

    CORPUS = ("38 tests passed\nelapsed 1.82 s\n"
              "OpenVINO version 2026.3.0\nDevice: GPU.0\nthroughput 24.5 tok/s")

    def test_removes_fabricated_numbers(self):
        text = ("延迟从 500 ms 降到 120ms，吞吐达到 99.9 tok/s，"
                "升级到 v3.2.1，占用 8 GiB。")
        out, removed = de._guard_numbers(text, self.CORPUS)
        for token in ("500 ms", "120ms", "99.9 tok/s", "v3.2.1", "8 GiB"):
            self.assertIn(token, removed, f"{token} 应被拦截")
            self.assertNotIn(token, out, f"{token} 不应留在输出里")
        self.assertIn(de.UNVERIFIED, out)

    def test_keeps_real_numbers(self):
        """证据里真实存在的数字必须原样保留，否则守卫就是在破坏内容。"""
        text = "实测 elapsed 1.82 s，吞吐 24.5 tok/s，版本 2026.3.0。"
        out, removed = de._guard_numbers(text, self.CORPUS)
        self.assertEqual(removed, [], f"不应拦截任何数字，实际拦截 {removed}")
        self.assertIn("1.82 s", out)
        self.assertIn("24.5 tok/s", out)
        self.assertIn("2026.3.0", out)

    def test_whitespace_insensitive_match(self):
        """'120 ms' 与 '120ms' 应视作同一数字，避免因空格差异误判。"""
        out, removed = de._guard_numbers("耗时 120 ms", "measured 120ms total")
        self.assertEqual(removed, [])
        self.assertIn("120 ms", out)


class TestOutputCleaning(unittest.TestCase):
    def test_strips_code_fence(self):
        self.assertEqual(de._clean("```markdown\n内容\n```"), "内容")

    def test_strips_chatml_markers(self):
        self.assertEqual(de._clean("内容<|im_end|>"), "内容")

    def test_strips_answer_prefix(self):
        self.assertEqual(de._clean("回答：内容说明"), "内容说明")

    def test_strips_heading_line(self):
        self.assertEqual(de._clean("### 标题\n正文内容"), "正文内容")


class TestTodoDetection(unittest.TestCase):
    def test_treats_evasive_answers_as_todo(self):
        """模型的敷衍回答不能被当成有效内容写进日志。"""
        for value in ("待补充", "未验证", "", "  ", "。", "无"):
            self.assertTrue(de._is_todo(value), f"{value!r} 应判为待补充")

    def test_accepts_real_content(self):
        self.assertFalse(de._is_todo("这是一段有效的决策说明内容"))


class TestRuleFields(unittest.TestCase):
    """由规则产生的字段绝不能凭空出现内容。"""

    def test_alternatives_only_from_user_input(self):
        self.assertEqual(de._alternatives_from_input([]), [])
        got = de._alternatives_from_input([{"option": "裸指针", "reason": "不安全"}])
        self.assertEqual(got, [{"option": "裸指针", "reason": "不安全"}])

    def test_alternatives_missing_reason_marked(self):
        got = de._alternatives_from_input([{"option": "方案A", "reason": ""}])
        self.assertEqual(got[0]["reason"], de.TODO_MARK)

    def test_facts_empty_without_test_log(self):
        self.assertEqual(de._facts_from_test_log({}), [])
        self.assertEqual(de._facts_from_test_log({"test_log": None}), [])


class TestRuleDegradedExtraction(unittest.TestCase):
    def test_llm_fields_left_todo(self):
        """无 LLM 时四个模型字段必须全为待补充，且不报错。"""
        be = backends.RuleBackend(reason="unit test")
        fields = de.extract_fields(
            evidence={"repo": {}, "stats": {}}, intent="测试意图",
            rejected=[], backend=be, log=None)
        self.assertTrue(fields["degraded"])
        for name in de.LLM_FIELDS:
            self.assertEqual(fields[name], de.TODO_MARK)
        self.assertEqual(fields["title"], "测试意图")


class TestRendering(unittest.TestCase):
    def _fields(self):
        return {
            "title": "标题", "status": "已接受（2026-08-28）",
            "context": "背景说明", "decision": "决策说明",
            "non_goals": de.TODO_MARK, "pitfalls": de.TODO_MARK,
            "alternatives": [], "verified_facts": [],
            "anchors": ["`commit abc1234` — 测试"], "guard_removed": [],
            "degraded": False,
        }

    def test_all_sections_present(self):
        text = de.render_adr(self._fields(), 7, "标题",
                             {"repo": {}, "stats": {}}, {})
        self.assertIn("## ADR-0007 标题", text)
        for section in ("Context", "Decision", "Non-Goals",
                        "Alternatives Considered", "Verified Facts",
                        "Pitfalls", "Evidence"):
            self.assertIn(f"### {section}", text, f"缺少 {section} 章节")

    def test_missing_evidence_explains_how_to_supply(self):
        """留空处必须告诉作者怎么补，而不是只丢一个占位符。"""
        text = de.render_adr(self._fields(), 1, "t", {"repo": {}, "stats": {}}, {})
        self.assertIn("--rejected", text)
        self.assertIn("--test-log", text)

    def test_guard_report_rendered(self):
        f = self._fields()
        f["guard_removed"] = ["500 ms", "v9.9.9"]
        text = de.render_adr(f, 1, "t", {"repo": {}, "stats": {}}, {})
        self.assertIn("反幻觉守卫", text)
        self.assertIn("2 处", text)

    def test_count_unverified(self):
        n, names = de.count_unverified(self._fields())
        self.assertEqual(n, 4)
        for expected in ("Non-Goals", "Pitfalls",
                         "Alternatives Considered", "Verified Facts"):
            self.assertIn(expected, names)

    def test_append_creates_header_once(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "DEVLOG.md"
            de.append_entry(p, "## ADR-0001 A\n\n")
            de.append_entry(p, "## ADR-0002 B\n\n")
            text = p.read_text(encoding="utf-8")
            self.assertEqual(text.count("# 工程决策日志"), 1)
            self.assertIn("ADR-0001", text)
            self.assertIn("ADR-0002", text)

    def test_next_adr_number(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "DEVLOG.md"
            self.assertEqual(de.next_adr_number(p), 1)
            de.append_entry(p, "## ADR-0001 A\n\n")
            self.assertEqual(de.next_adr_number(p), 2)
            de.append_entry(p, "## ADR-0042 B\n\n")
            self.assertEqual(de.next_adr_number(p), 43)


class TestEvidenceParsing(unittest.TestCase):
    def test_parse_numstat(self):
        got = evidence._parse_numstat("12\t3\tsrc/a.py\n-\t-\tbin/x.png\n")
        self.assertEqual(got["src/a.py"], (12, 3))
        self.assertEqual(got["bin/x.png"], (0, 0))

    def test_parse_name_status(self):
        got = evidence._parse_name_status("A\tnew.py\nM\told.py\nD\tgone.py\n")
        self.assertEqual(got, {"new.py": "A", "old.py": "M", "gone.py": "D"})

    def test_split_diff_by_file(self):
        diff = ("diff --git a/x.py b/x.py\n@@ -1,2 +1,3 @@\n+add\n"
                "diff --git a/y.py b/y.py\n@@ -5,1 +5,1 @@\n-old\n+new\n")
        chunks = evidence._split_diff_by_file(diff)
        self.assertEqual(set(chunks), {"x.py", "y.py"})

    def test_hunk_anchors_line_numbers(self):
        anchors = evidence._hunk_anchors("x.py", "@@ -1,2 +10,5 @@\n+a\n")
        self.assertEqual(anchors[0]["ref"], "x.py:10-14")

    def test_test_log_metric_extraction(self):
        """实测数字必须带真实行号锚点，这是可审计性的基础。"""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.txt"
            p.write_text("line one\n38 tests passed\nelapsed 1.82 s\n"
                         "throughput 24.5 tok/s\np95 142 ms\n",
                         encoding="utf-8")
            info = evidence._parse_test_log(p)
            self.assertTrue(info["has_metrics"])
            self.assertIn("tests_passed", info["metrics"])
            self.assertEqual(info["metrics"]["tests_passed"][0]["line"], 2)
            self.assertEqual(info["metrics"]["duration"][0]["anchor"], "test.txt:3")
            self.assertIn("throughput", info["metrics"])
            self.assertIn("percentile", info["metrics"])

    def test_diff_budget_truncation(self):
        """超预算的 diff 必须被截断并标记，避免灌爆小模型上下文。"""
        big = {"a.py": "x" * (evidence.MAX_FILE_DIFF_CHARS + 500)}
        text, truncated = evidence._truncate_diff(big)
        self.assertTrue(truncated)
        self.assertLessEqual(len(text), evidence.MAX_TOTAL_DIFF_CHARS + 200)

    def test_not_a_repository_raises(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(evidence.NotARepository):
                evidence.collect(cwd=Path(td))


class TestBackendSelection(unittest.TestCase):
    def test_rule_backend_always_available(self):
        ok, _ = backends.RuleBackend.probe()
        self.assertTrue(ok)

    def test_rule_backend_is_not_llm(self):
        self.assertFalse(backends.RuleBackend().is_llm)

    def test_rule_backend_refuses_to_generate(self):
        """降级后端必须拒绝生成，而不是返回一段看起来像样的假内容。"""
        with self.assertRaises(RuntimeError):
            backends.RuleBackend().generate("s", "u")

    def test_forced_rule_backend(self):
        old = os.environ.get(backends.ENV_FORCE_BACKEND)
        os.environ[backends.ENV_FORCE_BACKEND] = "rule"
        try:
            be = backends.create_backend(model_dir=None, model_id="x")
            self.assertIsInstance(be, backends.RuleBackend)
        finally:
            if old is None:
                os.environ.pop(backends.ENV_FORCE_BACKEND, None)
            else:
                os.environ[backends.ENV_FORCE_BACKEND] = old


class TestNoCloudCompliance(unittest.TestCase):
    """合规红线：整个 scripts/ 不得出现任何云端推理端点。

    官方模板两处明文要求 "Never fall back to a cloud service"，
    赛事技术约束也要求模型必须纯本地运行，因此用测试机械强制。
    """

    BANNED = ("api.openai.com", "dashscope", "anthropic.com",
              "generativelanguage", "api.deepseek", "openrouter",
              "api.moonshot", "bigmodel.cn", "aliyuncs.com/compatible-mode")

    @classmethod
    def _scan(cls, text: str) -> list[str]:
        low = text.lower()
        return [t for t in cls.BANNED if t in low]

    def test_scanner_catches_known_violation(self):
        """负例验证：先证明扫描器真的会报错。

        没有这一项的话，一个永远返回「通过」的扫描器也能让测试全绿，
        合规检查就成了摆设。
        """
        fake = ("import requests\n"
                "r = requests.post('https://api.openai.com/v1/chat/completions')\n")
        hits = self._scan(fake)
        self.assertIn("api.openai.com", hits,
                      "扫描器未能发现已知违规，它本身是坏的")

    def test_scanner_does_not_overmatch(self):
        """正例验证：正常的本地代码不应被误报。"""
        clean = ("url = 'http://127.0.0.1:7317/v1/chat/completions'\n"
                 "# 本地 Isvik，OpenAI 兼容协议但不是云端\n")
        self.assertEqual(self._scan(clean), [])

    def test_real_sources_are_clean(self):
        scripts = Path(__file__).resolve().parent.parent / "scripts"
        checked = 0
        for py in scripts.glob("*.py"):
            hits = self._scan(py.read_text(encoding="utf-8"))
            self.assertEqual(hits, [], f"{py.name} 出现云端端点：{hits}")
            checked += 1
        self.assertGreater(checked, 0, "没有扫描到任何源文件，路径可能不对")


class TestProtocolConstants(unittest.TestCase):
    def test_exit_codes_match_template(self):
        self.assertEqual(common.EXIT_OK, 0)
        self.assertEqual(common.EXIT_ERROR, 1)
        self.assertEqual(common.EXIT_CONN, 2)
        self.assertEqual(common.EXIT_DOWNLOADING, 3)

    def test_pipe_address_shape(self):
        addr = common.pipe_address()
        if os.name == "nt":
            self.assertTrue(addr.startswith("\\\\.\\pipe\\"),
                            f"Windows 下应为命名管道，实际 {addr}")
            self.assertIn(common.SKILL_NAME, addr)
        else:
            self.assertTrue(addr.endswith(".sock"))

    def test_authkey_matches_skill_name(self):
        """client 与 server 的 authkey 不一致会导致连接被拒，这是模板列出的坑。"""
        self.assertEqual(common.AUTHKEY, common.SKILL_NAME.encode("utf-8"))


class TestEndToEndRuleMode(unittest.TestCase):
    """完整链路：真实 git 仓库 → 证据采集 → 规则渲染 → 落盘。"""

    def setUp(self):
        import shutil
        if not shutil.which("git"):
            self.skipTest("git 不可用")

    def test_full_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            run = lambda *a: subprocess.run(  # noqa: E731
                ["git", *a], cwd=str(repo), capture_output=True, check=True)
            run("init", "-q")
            run("config", "user.email", "t@t.io")
            run("config", "user.name", "T")
            (repo / "a.txt").write_text("one\n", encoding="utf-8")
            run("add", ".")
            run("commit", "-qm", "init")

            (repo / "b.py").write_text("def f():\n    return 1\n", encoding="utf-8")
            run("add", "b.py")

            log = repo / "t.txt"
            log.write_text("12 tests passed\nelapsed 0.5 s\n", encoding="utf-8")

            pack = evidence.collect(cwd=repo, commits=None, test_log=log)
            self.assertFalse(pack["empty"])
            self.assertEqual(pack["stats"]["files"], 1)
            self.assertTrue(pack["test_log"]["has_metrics"])
            self.assertTrue(any(a["kind"] == "commit" for a in pack["anchors"]))

            fields = de.extract_fields(
                evidence=pack, intent="加入 b.py",
                rejected=[{"option": "内联实现", "reason": "复用性差"}],
                backend=backends.RuleBackend(), log=None)

            out = repo / "DEVLOG.md"
            entry = de.render_adr(fields, de.next_adr_number(out), "加入 b.py",
                                 pack, {"backend": "rule-template"})
            de.append_entry(out, entry)

            text = out.read_text(encoding="utf-8")
            self.assertIn("ADR-0001 加入 b.py", text)
            self.assertIn("内联实现", text)        # 用户提供的被否方案
            self.assertIn("12 tests passed", text)  # 日志里真实存在的数字
            self.assertIn("待补充", text)           # 无模型时诚实留空


if __name__ == "__main__":
    unittest.main(verbosity=2)
