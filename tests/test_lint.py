import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINT_SCRIPT = ROOT / "scripts" / "lint.py"
STRUCTURE_SCRIPT = ROOT / "scripts" / "check_structure.py"


class LintAndStructureTests(unittest.TestCase):
    def _run_lint(self, text, mode="article", suffix=None):
        if suffix is None:
            return subprocess.run(
                [sys.executable, str(LINT_SCRIPT), "-", "--mode", mode],
                input=text,
                text=True,
                capture_output=True,
            )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / f"sample{suffix}"
            p.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(LINT_SCRIPT), str(p), "--mode", mode],
                text=True,
                capture_output=True,
            )

    def test_markdown_link_does_not_swallow_trailing_chinese_text(self):
        sample = "详见[文档](https://example.invalid/docs?a=1)，首先我们要赋能——不是工具而是镜子。\n"
        res = self._run_lint(sample)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("禁用词「首先」", res.stdout)
        self.assertIn("禁用词「赋能」", res.stdout)
        self.assertIn("破折号", res.stdout)
        self.assertIn("否定对比句", res.stdout)

    def test_bare_url_stops_before_chinese_punctuation_and_emdash(self):
        sample = (
            "参考 https://example.invalid/a?k=1，首先检查日志。\n"
            "见 https://example.invalid/b——底层逻辑有问题。\n"
        )
        res = self._run_lint(sample)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("第1行 禁用词「首先」", res.stdout)
        self.assertIn("第2行 破折号", res.stdout)
        self.assertIn("第2行 禁用词「底层逻辑」", res.stdout)

    def test_angle_bracket_comparisons_do_not_swallow_prose(self):
        sample = "当延迟 < 10 毫秒且吞吐 > 5 万时，首先赋能系统。\n"
        res = self._run_lint(sample)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("禁用词「首先」", res.stdout)
        self.assertIn("禁用词「赋能」", res.stdout)

    def test_html_tags_and_autolinks_remain_protected(self):
        sample = '<a id="first" data-note="首先"></a><https://example.invalid/首先>正常句子没有问题。\n'
        res = self._run_lint(sample)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("错误 0 项", res.stdout)

    def test_local_path_stops_at_chinese_delimiters_and_parens(self):
        sample = "路径在(~/docs/sample.md)首先赋能，另一份在 ~/docs/a.md、~/docs/b.md。\n"
        res = self._run_lint(sample)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("禁用词「首先」", res.stdout)
        self.assertIn("禁用词「赋能」", res.stdout)

    def test_utf8_bom_frontmatter_and_json_supported(self):
        md_with_bom = "\ufeff---\ntitle: 首先赋能\n---\n\n正文干净通顺。\n"
        res_md = self._run_lint(md_with_bom, suffix=".md")
        self.assertEqual(res_md.returncode, 0, res_md.stdout + res_md.stderr)

        json_with_bom = "\ufeff" + json.dumps([{"id": "首先", "text": "正文干净通顺。"}], ensure_ascii=False)
        res_json = self._run_lint(json_with_bom, suffix=".json")
        self.assertEqual(res_json.returncode, 0, res_json.stdout + res_json.stderr)

    def test_fixtures_smoke_and_check_structure_with_bom(self):
        fixture_md = ROOT / "tests" / "fixtures" / "structure.md"
        res = subprocess.run(
            [sys.executable, str(STRUCTURE_SCRIPT), str(fixture_md), str(fixture_md)],
            text=True,
            capture_output=True,
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        payload = json.loads(res.stdout)
        self.assertTrue(payload["passed"])

        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.md"
            b = Path(tmp) / "b.md"
            a.write_text("\ufeff---\ntitle: test\n---\n\n# 标题\n", encoding="utf-8")
            b.write_text("---\ntitle: test\n---\n\n# 标题\n", encoding="utf-8")
            res_bom = subprocess.run(
                [sys.executable, str(STRUCTURE_SCRIPT), str(a), str(b)],
                text=True,
                capture_output=True,
            )
            self.assertEqual(res_bom.returncode, 0, res_bom.stdout + res_bom.stderr)
            self.assertTrue(json.loads(res_bom.stdout)["preserved"]["frontmatter"])


if __name__ == "__main__":
    unittest.main()
