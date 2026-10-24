#!/usr/bin/env python3
"""Check that stylesheets parse without errors.

Covers all non-vendored CSS files under ``streetsign_server/static`` plus
inline ``<style>`` blocks in templates that do not contain Jinja tags.
"""

import pathlib
import re
import sys

import tinycss2

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = ROOT / "streetsign_server" / "static"
TEMPLATES = ROOT / "streetsign_server" / "templates"

STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", flags=re.S | re.I)


def check_text(label, text):
    """Return a list of parse errors for a stylesheet string."""
    failures = []
    for rule in tinycss2.parse_stylesheet(
            text, skip_comments=True, skip_whitespace=True):
        if rule.type == "error":
            failures.append((label, rule.source_line, rule.message))
    return failures


def main():
    """Return 1 when any stylesheet has a parse error."""
    failures = []

    for path in sorted(STATIC.rglob("*.css")):
        relative = path.relative_to(STATIC)
        if relative.parts and relative.parts[0] == "lib":
            continue
        failures += check_text(
            str(path.relative_to(ROOT)), path.read_text(encoding="utf-8"))

    for path in sorted((TEMPLATES / "screens").rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for match in STYLE_RE.finditer(text):
            block = match.group(1)
            if "{{" in block or "{%" in block:
                continue
            failures += check_text(
                f"{path.relative_to(ROOT)} (inline <style>)", block)

    if failures:
        print("CSS parse errors:")
        for label, line, message in failures:
            print(f"  {label}:{line}: {message}")
        return 1

    print("CSS syntax OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
