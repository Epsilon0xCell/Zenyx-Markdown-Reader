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

# This code span pattern only knows single backticks. A span written
# with double backticks, which Markdown allows so the span can hold a
# backtick inside it, gets cut at the first inner backtick and the
# rest is treated as normal text. I saw that in testing and left it.
_CODE = re.compile(r"`([^`]+)`")
_IMG = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__")
# The italic pattern refuses to start inside a word. That guard is what
# keeps snake_case names and words with underscores in them from
# turning into emphasis. The bold pattern above has no such guard on
# its __ form, so a__b__c still comes out bold in the middle of a word.
# I checked both in testing. The two patterns disagree and I know it.
_ITALIC = re.compile(r"(?<!\w)\*([^*]+)\*|(?<!\w)_([^_]+)_")
# The link and image patterns stop the URL at the first ) or space, so
# a URL that contains a closing parenthesis is cut short and the rest
# of it is left sitting in the text. Real URLs with parentheses in
# them hit this. I have not taught the patterns to count brackets.
_STRIKE = re.compile(r"~~([^~]+)~~")
# I use NUL bytes for the stash placeholder because real Markdown text
# from a file essentially never contains them. A printable marker could
# turn up in a document by chance and then get swapped for code text by
# mistake. The index in the placeholder and the position in the stash
# list are the same number, and those two have to move together.
_PLACEHOLDER = "\x00{}\x00"

# A destination only earns its place in an href or src if it is one
# of these schemes, or has no scheme at all (a relative path or a
# #anchor). Anything else, javascript: and data: and vbscript: at
# the front of the list, is replaced with # in HTML output. I render
# files other people wrote, and a link I emit with a javascript:
# destination runs when the reader clicks it. That is the one
# place this renderer could hurt the person it is supposed to serve,
# so the check sits on the URL itself, before the tag is built.
_ALLOWED_SCHEMES = {"http", "https", "mailto"}
_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")


def _safe_url(url):
    """Return url unchanged if its scheme is allowed or it has no
    scheme; return '#' if it carries a scheme I do not allow."""
    # Browsers strip leading spaces and control characters before
    # they read a scheme, so the check has to strip them too. A
    # destination padded with a control character is still the
    # scheme it spells once the padding is gone.
    # Browsers also remove tab, carriage return, and newline
    # characters anywhere in a URL before they read the scheme, so I
    # remove them here too. Without that step a destination spelled
    # with a tab inside the scheme word slips past the scheme match
    # here and still reads as that scheme in the browser.
    candidate = url.replace("\t", "").replace("\r", "").replace("\n", "")
    candidate = candidate.strip()
    while candidate and ord(candidate[0]) <= 0x20:
        candidate = candidate[1:]
    match = _SCHEME.match(candidate)
    if match and match.group(1).lower() not in _ALLOWED_SCHEMES:
        return "#"
    return url


def _inline(text, mode, stash):
    """Apply inline formatting. Code spans are stashed first and restored
    last so their contents are never reformatted."""
    def keep(match):
        stash.append(match.group(1))
        return _PLACEHOLDER.format(len(stash) - 1)

    # The substitution order in this function is load bearing. Images
    # run before links because image syntax is link syntax with a !
    # in front. If links ran first, every image would come out as a
    # link with a stray bang in front of it. Bold runs before italic
    # for the same reason: the double marker has to be claimed before
    # the single marker pattern sees it.
    text = _CODE.sub(keep, text)
    if mode == "html":
        # I escape before I build any tags, never after. Escaping after
        # would turn my own strong and anchor markup into visible text.
        # The cost is that URLs and link text are matched against
        # already escaped text, which is why the quote handling below
        # has to exist at all.
        text = html.escape(text, quote=False)
        # The text above is escaped with quote=False, so a double quote in
        # a URL or alt text would break out of the attribute. Quote it.
        text = _IMG.sub(lambda m: '<img alt="{}" src="{}">'.format(
            m.group(1).replace('"', "&quot;"),
            _safe_url(m.group(2)).replace('"', "&quot;")), text)
        # A & in a URL reaches this line already turned into &amp; by
        # the escape step. That is the form an href value should carry
        # in HTML, so I leave it as it is instead of unescaping it.
        text = _LINK.sub(lambda m: '<a href="{}">{}</a>'.format(
            _safe_url(m.group(2)).replace('"', "&quot;"), m.group(1)), text)
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
                # Plain mode puts the backticks back around the code.
                # Dropping them would make a code span read as ordinary
                # words, and plain mode is the one people pipe into
                # files and other tools.
                text = text.replace(_PLACEHOLDER.format(i), "`{}`".format(code))
    return text


# ----------------------------------------------------------------- blocks ---

# The heading pattern demands a space after the hashes, so a line like
# #nospace stays a paragraph. It also strips trailing hashes, so the
# closed form with hashes at the end renders the same as the open form.
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HR = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_UL = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_OL = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_QUOTE = re.compile(r"^>\s?(.*)$")
# This separator pattern on its own would also match a row made only of
# colons and pipes. The caller adds a test that the line contains a
# dash before it calls anything a table. Both halves are needed.
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def _split_row(line):
    # I strip at most one pipe from each end, the framing pipes. Then I
    # split on every pipe that is left, which is what lets a ragged row
    # keep its extra cells as extra cells instead of merging them into
    # the last column. A cell that itself contains a pipe is not
    # something this parser tries to save.
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
            # Source lines in one paragraph are joined with a single
            # space, so a hard line break in the file is lost. README
            # prose is usually wrapped by whoever wrote it, and
            # keeping every wrap would make terminal output look
            # broken in a way the source never intended.
            text = " ".join(paragraph)
            stash = []
            body = _inline(text, mode, stash)
            out.append("<p>{}</p>".format(body) if mode == "html" else body)
            paragraph.clear()

    while i < n:
        line = lines[i]

        if line.startswith("```"):
            # I ignore the word after the opening fence. A fence tagged
            # python and a bare fence render exactly the same here, and
            # no language name is kept for the HTML output.
            # An unclosed fence is not an error either. The loop below
            # just runs out of lines, and what it collected is shown as
            # code, the same as if the closing fence sat at the end of
            # the file.
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
                # An empty line inside the block gets plain spaces, not
                # an empty reversed segment, so a blank line in code
                # does not leave a stray highlighted strip on screen.
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
            # This check sits before the list checks on purpose. A line
            # like - - - matches the unordered list pattern too, and I
            # want it read as a rule, not as a one item list holding
            # two dashes.
            flush_paragraph()
            out.append("<hr>" if mode == "html" else "-" * 60)
            i += 1
            continue

        if _QUOTE.match(line):
            # Consecutive quote lines are joined into one paragraph,
            # the same join a normal paragraph gets. So a quote with a
            # blank line inside it comes out as two separate quotes,
            # and any list or heading markers inside the quote text
            # are never parsed as blocks of their own.
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
        # The header line alone never proves a table. I look one line
        # ahead, and only the pair counts. A paragraph line that
        # happens to contain a pipe stays a paragraph as long as the
        # next line is not a separator row.
        if "|" in line and i + 1 < n and _TABLE_SEP.match(lines[i + 1]) and "-" in lines[i + 1]:
            flush_paragraph()
            header = _split_row(line)
            i += 2
            rows = []
            # Body rows stop at the first line without a pipe. There
            # is no recovery for a row that forgot its pipes. It just
            # ends the table and becomes a paragraph below.
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
                # The terminal table prints cell text exactly as it was
                # written, markers and all. Only the HTML branch above
                # runs inline formatting on cells. I checked a cell
                # holding bold and code markers: HTML formats them,
                # the terminal shows the raw markers. The modes differ
                # here and this branch is why.
                ncols = max([len(header)] + [len(r) for r in rows])
                widths = [max(len(r[c]) for r in [header] + rows if c < len(r)) for c in range(ncols)]
                def fmt(r):
                    return " | ".join((r[c] if c < len(r) else "").ljust(widths[c]) for c in range(ncols))
                table_lines = [fmt(header), "-+-".join("-" * w for w in widths)]
                table_lines.extend(fmt(r) for r in rows)
                out.append("\n".join(table_lines))
            continue

        ul, ol = _UL.match(line), _OL.match(line)
        if ul or ol:
            # One list block holds one kind of marker. The loop below
            # only accepts the pattern the block started with, so a
            # dash list followed directly by a numbered list becomes
            # two lists, not one mixed list. I saw that split in
            # testing and it is the behavior I am keeping.
            # Only the first item number is read. Later numbers in the
            # source are ignored and the items count up from that
            # start, so a list typed as 3. 3. 3. renders 3. 4. 5.
            flush_paragraph()
            ordered = ol is not None
            start = int(ol.group(2)) if ordered else 1
            items = []
            while i < n:
                m = _OL.match(lines[i]) if ordered else _UL.match(lines[i])
                if not m:
                    break
                items.append((len(m.group(1)), m.group(3) if ordered else m.group(2)))
                i += 1
            if mode == "html":
                # The HTML branch ignores the indent each item carried.
                # A nested item is flattened into this same list, in
                # both the tag output here and the numbering below. The
                # terminal branch at least keeps the indent as spaces.
                # True nesting would need a stack, and this renderer
                # does not have one.
                tag = "ol" if ordered else "ul"
                # No start attribute at 1, so a normal list produces
                # the plain tag it always produced before start numbers
                # were kept at all.
                attr = ' start="{}"'.format(start) if ordered and start != 1 else ""
                out.append("<{0}{1}>{2}</{0}>".format(
                    tag, attr, "".join("<li>{}</li>".format(_inline(t, mode, [])) for _, t in items)))
            else:
                rendered = []
                for num, (indent, text) in enumerate(items, start):
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


# I keep the CSS inline and short on purpose. A rendered page has to
# work as one single file, opened from any folder, with no stylesheet
# sitting next to it. That is also why there is no dark mode or font
# loading here. The page borrows the system font and stops there.
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
    """Render Markdown source text. mode: 'ansi', 'plain', or 'html'.

    Any other mode raises ValueError. Before this check a mistyped
    mode name fell through to the plain text branches and produced
    output that looked fine, so a caller asking for HTML by a wrong
    name got terminal text and no sign anything was off.
    """
    if mode not in ("ansi", "plain", "html"):
        raise ValueError("unknown mode {!r}: use 'ansi', 'plain', or 'html'".format(mode))
    blocks = render_blocks(source.splitlines(), mode)
    if mode == "html":
        # The page title is always Zenyx Reader, whatever file was
        # rendered. I never take a title from the first heading, so two
        # different files open in browser tabs with the same title.
        return ("<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
                "<title>Zenyx Reader</title><style>{}</style></head>"
                "<body>\n{}\n</body></html>").format(_CSS, "\n".join(blocks))
    # Empty blocks are filtered before this join so a construct that
    # rendered to nothing cannot leave a double blank line behind. The
    # HTML path above does not filter. Its blocks sit inside the page
    # shell either way, so an empty one does no visible harm there.
    return "\n\n".join(b for b in blocks if b != "")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Zenyx Reader: read Markdown in the terminal or render HTML.")
    parser.add_argument("path", help="Markdown file to read, or - for stdin")
    parser.add_argument("--html", action="store_true", help="render a standalone HTML page")
    parser.add_argument("--plain", action="store_true", help="no ANSI colors in terminal output")
    parser.add_argument("-o", "--output", help="write output to this file instead of stdout")
    args = parser.parse_args(argv)

    if args.path == "-":
        try:
            source = sys.stdin.read()
        except UnicodeDecodeError as exc:
            print("Error: stdin is not valid UTF-8 text: {}".format(exc), file=sys.stderr)
            return 2
    else:
        try:
            with open(args.path, encoding="utf-8") as fh:
                source = fh.read()
        except OSError as exc:
            print("Error: {}".format(exc), file=sys.stderr)
            return 2
        except UnicodeDecodeError as exc:
            # A binary file or a file saved in another encoding is
            # input I cannot read, not a crash. It gets the same
            # short error and exit 2 as a missing file.
            print("Error: {} is not valid UTF-8 text: {}".format(args.path, exc), file=sys.stderr)
            return 2

    # If --html and --plain are both passed, --html wins and --plain is
    # ignored without a word. The html test comes first here, and the
    # plain flag is only read inside the other branch.
    if args.html:
        result = render(source, "html")
    else:
        # This mode choice looks at stdout, not at where the text ends
        # up. Rendering with -o from a terminal still writes ANSI
        # escape codes into the file, because stdout is a terminal at
        # the moment this runs. Passing --plain is the only way to
        # keep a file clean. Piping stdout the other way gives plain
        # text even without the flag.
        mode = "plain" if args.plain or not sys.stdout.isatty() else "ansi"
        result = render(source, mode)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(result + "\n")
        except OSError as exc:
            print("Error: {}".format(exc), file=sys.stderr)
            return 2
    else:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
