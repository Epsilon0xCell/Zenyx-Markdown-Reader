"""Tests for zenyx.py. Run with: python3 -m unittest"""

import subprocess
import sys
import unittest
from pathlib import Path

import zenyx
from zenyx import _safe_url, render

ROOT = Path(__file__).resolve().parent


def run_cli(*args, stdin_text=None):
    return subprocess.run(
        [sys.executable, str(ROOT / "zenyx.py"), *args],
        input=stdin_text, capture_output=True, text=True, cwd=ROOT, timeout=30)


class SafeUrlTests(unittest.TestCase):
    def test_allowed_schemes_pass_unchanged(self):
        for url in ("http://example.com", "https://example.com/a?b=1",
                    "HTTPS://example.com", "mailto:someone@example.com"):
            self.assertEqual(_safe_url(url), url)

    def test_schemeless_destinations_pass_unchanged(self):
        for url in ("page.md", "./docs/page.md", "../up.md", "#section",
                    "//example.com/protocol-relative", "/absolute/path.md"):
            self.assertEqual(_safe_url(url), url)

    def test_blocked_schemes_become_hash(self):
        for url in ("javascript:alert(1)", "JaVaScRiPt:alert(1)",
                    "data:text/html,hello", "vbscript:msgbox", "file:///etc/passwd"):
            self.assertEqual(_safe_url(url), "#", url)

    def test_leading_space_and_control_padding_still_blocked(self):
        self.assertEqual(_safe_url(" javascript:alert(1)"), "#")
        self.assertEqual(_safe_url("\x01\x02javascript:alert(1)"), "#")

    def test_tab_inside_scheme_still_blocked(self):
        # Browsers remove tab, CR, and LF from a URL before reading
        # the scheme, so the check has to read it the same way.
        self.assertEqual(_safe_url("java\tscript:alert(1)"), "#")
        self.assertEqual(_safe_url("java\nscript:alert(1)"), "#")
        self.assertEqual(_safe_url("java\rscript:alert(1)"), "#")
        self.assertEqual(_safe_url("\tjavascript:alert(1)"), "#")


class RenderHtmlTests(unittest.TestCase):
    def test_hostile_link_and_image_render_as_hash(self):
        out = render("[x](javascript:alert(1)) ![i](data:image/png;base64,AA)", "html")
        self.assertIn('<a href="#">x</a>', out)
        self.assertIn('<img alt="i" src="#">', out)
        self.assertNotIn("javascript:", out)
        self.assertNotIn("data:image", out)

    def test_allowed_link_keeps_destination(self):
        out = render("[ok](https://example.com) [rel](page.md)", "html")
        self.assertIn('<a href="https://example.com">ok</a>', out)
        self.assertIn('<a href="page.md">rel</a>', out)

    def test_heading_bold_and_code(self):
        out = render("# Title\n\nSome **bold** and `code` here.", "html")
        self.assertIn("<h1>Title</h1>", out)
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<code>code</code>", out)

    def test_raw_html_in_source_is_escaped(self):
        out = render("Text <script>alert(1)</script> end", "html")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_code_block_contents_are_escaped(self):
        out = render("```\n<b>not a tag</b>\n```", "html")
        self.assertIn("<pre><code>&lt;b&gt;not a tag&lt;/b&gt;</code></pre>", out)

    def test_ordered_list_keeps_start_number(self):
        out = render("3. three\n4. four", "html")
        self.assertIn('<ol start="3">', out)

    def test_table_renders_header_and_row(self):
        out = render("| A | B |\n|---|---|\n| 1 | 2 |", "html")
        self.assertIn("<th>A</th>", out)
        self.assertIn("<td>2</td>", out)

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            render("# Hi", "bogus")


class RenderPlainTests(unittest.TestCase):
    def test_plain_strips_markers_and_keeps_code_backticks(self):
        out = render("# Title\n\nSome **bold** and `code`.", "plain")
        self.assertIn("Title", out)
        self.assertIn("Some bold and `code`.", out)
        self.assertNotIn("**", out)

    def test_plain_link_shows_text_and_destination(self):
        out = render("[label](https://example.com)", "plain")
        self.assertIn("label (https://example.com)", out)

    def test_empty_source_renders_empty(self):
        self.assertEqual(render("", "plain"), "")


class CliTests(unittest.TestCase):
    def test_missing_file_exits_2_with_error_and_no_traceback(self):
        proc = run_cli("no-such-file-xyz.md", "--plain")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("Error:", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_non_utf8_file_exits_2_with_error_and_no_traceback(self):
        bad = ROOT / "tmp-not-utf8.md"
        bad.write_bytes(b"\xff\xfe\x00binary")
        try:
            proc = run_cli(bad.name, "--plain")
        finally:
            bad.unlink()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not valid UTF-8", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_directory_path_exits_2(self):
        proc = run_cli(".", "--plain")
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("Traceback", proc.stderr)

    def test_stdin_plain_render(self):
        proc = run_cli("-", "--plain", stdin_text="# From stdin\n")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("From stdin", proc.stdout)

    def test_html_output_file_written(self):
        src = ROOT / "tmp-cli-src.md"
        dest = ROOT / "tmp-cli-out.html"
        src.write_text("# Written\n", encoding="utf-8")
        try:
            proc = run_cli(src.name, "--html", "-o", dest.name)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("<h1>Written</h1>", dest.read_text(encoding="utf-8"))
        finally:
            src.unlink(missing_ok=True)
            dest.unlink(missing_ok=True)

    def test_repo_readme_renders_in_all_modes(self):
        source = (ROOT / "README.md").read_text(encoding="utf-8")
        for mode in ("plain", "ansi", "html"):
            out = render(source, mode)
            self.assertIn("Zenyx", out)


if __name__ == "__main__":
    unittest.main()
