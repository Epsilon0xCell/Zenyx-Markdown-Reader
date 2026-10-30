#!/usr/bin/env python3
"""Zenyx Reader: a lightweight Markdown / README reader and renderer.

An open-source alternative in the spirit of ReadMe! style tools: point it at
a Markdown file and read it comfortably in the terminal, or render it to a
standalone HTML page.

    python3 zenyx.py README.md              # read in the terminal
    python3 zenyx.py README.md --plain      # terminal text without ANSI colors
    python3 zenyx.py README.md --html       # standalone HTML to stdout
    python3 zenyx.py README.md --html -o page.html
    cat README.md | python3 zenyx.py -      # read from stdin

Supported Markdown: ATX headings, paragraphs, bold, italic, strikethrough,
inline code, fenced code blocks, links, images, unordered and ordered lists,
blockquotes, horizontal rules, and pipe tables. Standard library only.
"""

import argparse
import html
import re
import sys

# ---------------------------------------------------------------- inline ---

_CODE = re.compile(r"`([^`]+)`")
_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__")
_ITALIC = re.compile(r"(?<!\w)\*([^*]+)\*|(?<!\w)_([^_]+)_")
_STRIKE = re.compile(r"~~([^~]+)~~")
_PLACEHOLDER = "\x00{}\x00"


def _inline(text, mode, stash):
    """Apply inline formatting. Code spans are stashed first and restored
    last so their contents are never reformatted."""
    def keep(match):
        stash.append(match.group(1))
        return _PLACEHOLDER.format(len(stash) - 1)

    text = _CODE.sub(keep, text)
    if mode == "html":
        text = html.escape(text, quote=False)
        text = _IMG.sub(r'<img alt="\1" src="\2">', text)
        text = _LINK.sub(r'<a href="\2">\1</a>', text)
        text = _BOLD.sub(lambda m: "<strong>{}</strong>".format(m.group(1) or m.group(2)), text)
        text = _ITALIC.sub(lambda m: "<em>{}</em>".format(m.group(1) or m.group(2)), text)
        text = _STRIKE.sub(r"<del>\1</del>", text)
        for i, code in enumerate(stash):
            text = text.replace(_PLACEHOLDER.format(i),
                                "<code>{}</code>".format(html.escape(code)))
    else:
        text = _IMG.sub(r"[image: \1 (\2)]", text)
        text = _LINK.sub(r"\1 (\2)", text)
        if mode == "ansi":
            text = _BOLD.sub(lambda m: "\033[1m{}\033[0m".format(m.group(1) or m.group(2)), text)
            text = _ITALIC.sub(lambda m: "\033[3m{}\033[0m".format(m.group(1) or m.group(2)), text)
            text = _STRIKE.sub(r"\1", text)
            for i, code in enumerate(stash):
                text = text.replace(_PLACEHOLDER.format(i), "\033[7m{}\033[0m".format(code))
        else:
            text = _BOLD.sub(lambda m: m.group(1) or m.group(2), text)
            text = _ITALIC.sub(lambda m: m.group(1) or m.group(2), text)
            text = _STRIKE.sub(r"\1", text)
            for i, code in enumerate(stash):
                text = text.replace(_PLACEHOLDER.format(i), "`{}`".format(code))
    return text


# ----------------------------------------------------------------- blocks ---

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HR = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_UL = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_OL = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_QUOTE = re.compile(r"^>\s?(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def _split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def render_blocks(lines, mode):
    """Render a list of Markdown source lines to a list of output strings."""
    out, i, n = [], 0, len(lines)
    paragraph = []

    def flush_paragraph():
        if paragraph:
            text = " ".join(paragraph)
            stash = []
            body = _inline(text, mode, stash)
            out.append("<p>{}</p>".format(body) if mode == "html" else body)
            paragraph.clear()

    while i < n:
        line = lines[i]

        if line.startswith("```"):
            flush_paragraph()
            code = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # closing fence
            body = "\n".join(code)
            if mode == "html":
                out.append("<pre><code>{}</code></pre>".format(html.escape(body)))
            elif mode == "ansi":
                out.append("\n".join("  \033[7m {}\033[0m".format(l) if l else "  " for l in code) or "  ")
            else:
                out.append("\n".join("    " + l for l in code))
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            stash = []
            body = _inline(heading.group(2), mode, stash)
            if mode == "html":
                out.append("<h{0}>{1}</h{0}>".format(level, body))
            elif mode == "ansi":
                out.append("\n\033[1m{}\033[0m".format(body))
            else:
                out.append("\n" + body)
            i += 1
            continue

        if _HR.match(line):
            flush_paragraph()
            out.append("<hr>" if mode == "html" else "-" * 60)
            i += 1
            continue

        if _QUOTE.match(line):
            flush_paragraph()
            quoted = []
            while i < n and _QUOTE.match(lines[i]):
                quoted.append(_QUOTE.match(lines[i]).group(1))
                i += 1
            stash = []
            body = _inline(" ".join(quoted), mode, stash)
            if mode == "html":
                out.append("<blockquote>{}</blockquote>".format(body))
            else:
                out.append("  | " + body)
            continue

        # Pipe table: a row, then a separator row of dashes.
        if "|" in line and i + 1 < n and _TABLE_SEP.match(lines[i + 1]) and "-" in lines[i + 1]:
            flush_paragraph()
            header = _split_row(line)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            if mode == "html":
                head = "".join("<th>{}</th>".format(_inline(c, mode, [])) for c in header)
                body = "".join(
                    "<tr>{}</tr>".format("".join("<td>{}</td>".format(_inline(c, mode, [])) for c in r))
                    for r in rows)
                out.append("<table><tr>{}</tr>{}</table>".format(head, body))
            else:
                widths = [max(len(r[c]) for r in [header] + rows if c < len(r)) for c in range(len(header))]
                def fmt(r):
                    return " | ".join((r[c] if c < len(r) else "").ljust(widths[c]) for c in range(len(header)))
                table_lines = [fmt(header), "-+-".join("-" * w for w in widths)]
                table_lines.extend(fmt(r) for r in rows)
                out.append("\n".join(table_lines))
            continue

        ul, ol = _UL.match(line), _OL.match(line)
        if ul or ol:
            flush_paragraph()
            ordered = ol is not None
            items = []
            while i < n:
                m = _OL.match(lines[i]) if ordered else _UL.match(lines[i])
                if not m:
                    break
                items.append((len(m.group(1)), m.group(2)))
                i += 1
            if mode == "html":
                tag = "ol" if ordered else "ul"
                out.append("<{0}>{1}</{0}>".format(
                    tag, "".join("<li>{}</li>".format(_inline(t, mode, [])) for _, t in items)))
            else:
                rendered = []
                for num, (indent, text) in enumerate(items, 1):
                    marker = "{}.".format(num) if ordered else "-"
                    rendered.append("{} {} {}".format(" " * indent, marker, _inline(text, mode, [])))
                out.append("\n".join(rendered))
            continue

        if not line.strip():
            flush_paragraph()
            i += 1
            continue

        paragraph.append(line.strip())
        i += 1

    flush_paragraph()
    return out


_CSS = """
body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
       max-width: 820px; margin: 2em auto; padding: 0 1em; line-height: 1.55; }
pre { background: #f4f4f4; padding: 0.8em; overflow-x: auto; border-radius: 6px; }
code { background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 4px; }
pre code { padding: 0; }
blockquote { border-left: 4px solid #ccc; margin-left: 0; padding-left: 1em; color: #555; }
table { border-collapse: collapse; } th, td { border: 1px solid #ccc; padding: 0.3em 0.7em; }
"""


def render(source, mode="ansi"):
    """Render Markdown source text. mode: 'ansi', 'plain', or 'html'."""
    blocks = render_blocks(source.splitlines(), mode)
    if mode == "html":
        return ("<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
                "<title>Zenyx Reader</title><style>{}</style></head>"
                "<body>\n{}\n</body></html>").format(_CSS, "\n".join(blocks))
    return "\n\n".join(b for b in blocks if b != "")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zenyx Reader: read Markdown in the terminal or render HTML.")
    parser.add_argument("path", help="Markdown file to read, or - for stdin")
    parser.add_argument("--html", action="store_true", help="render a standalone HTML page")
    parser.add_argument("--plain", action="store_true", help="no ANSI colors in terminal output")
    parser.add_argument("-o", "--output", help="write output to this file instead of stdout")
    args = parser.parse_args(argv)

    if args.path == "-":
        source = sys.stdin.read()
    else:
        try:
            with open(args.path, encoding="utf-8") as fh:
                source = fh.read()
        except OSError as exc:
            print("Error: {}".format(exc), file=sys.stderr)
            return 2

    if args.html:
        result = render(source, "html")
    else:
        mode = "plain" if args.plain or not sys.stdout.isatty() else "ansi"
        result = render(source, mode)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(result + "\n")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
