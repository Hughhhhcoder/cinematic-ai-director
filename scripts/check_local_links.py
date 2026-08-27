#!/usr/bin/env python3
"""Validate repository-local Markdown and HTML image links without network access."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HTML_LINK = re.compile(r"(?:href|src)=[\"']([^\"']+)[\"']")
REMOTE_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:")


def candidate_documents(root: Path) -> list[Path]:
    files = [root / "README.md", root / "README.zh-CN.md"]
    files.extend(sorted((root / "docs").rglob("*.md")))
    return [path for path in files if path.is_file()]


def clean_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    if " " in value and not value.startswith(REMOTE_PREFIXES):
        value = value.split(" ", 1)[0]
    return unquote(value.split("#", 1)[0].split("?", 1)[0])


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for document in candidate_documents(root):
        text = document.read_text(encoding="utf-8")
        targets = [*MARKDOWN_LINK.findall(text), *HTML_LINK.findall(text)]
        for raw in targets:
            target = clean_target(raw)
            if not target or target.startswith(REMOTE_PREFIXES) or target.startswith("#"):
                continue
            if target.startswith("/"):
                errors.append(f"{document.relative_to(root)}: repository link must be relative: {raw}")
                continue
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"{document.relative_to(root)}: link escapes repository: {raw}")
                continue
            if not resolved.exists():
                errors.append(f"{document.relative_to(root)}: missing local target: {raw}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    errors = validate(args.root.resolve())
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("All repository-local documentation links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
