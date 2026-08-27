#!/usr/bin/env python3
"""Verify this portable Higgsfield package without third-party dependencies."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKSUMS = ROOT / "checksums.sha256"


def main() -> int:
    if not CHECKSUMS.is_file():
        print("INVALID: checksums.sha256 is missing", file=sys.stderr)
        return 1
    failures = []
    manifest_path = ROOT / "manifest.json"
    conformance_path = ROOT / "official-conformance.json"
    if not manifest_path.is_file() or not conformance_path.is_file():
        failures.append("manifest.json and official-conformance.json are required")
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        conformance = json.loads(conformance_path.read_text(encoding="utf-8"))
        expected = "cinema-studio-4-seedance-2.5-official-2026-08-27"
        if manifest.get("official_conformance", {}).get("profile_id") != expected:
            failures.append("manifest official profile mismatch")
        if conformance.get("profile_id") != expected or conformance.get("strict") is not True:
            failures.append("official conformance record mismatch")
        if conformance.get("version_policy") != "snapshot-must-match-or-block":
            failures.append("official conformance version policy mismatch")
    listed = set()
    for raw_line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            expected, relative = raw_line.split("  ", 1)
        except ValueError:
            failures.append(f"malformed checksum line: {raw_line}")
            continue
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            failures.append(f"unsafe path: {relative}")
            continue
        listed.add(candidate.as_posix())
        path = ROOT / candidate
        if not path.is_file():
            failures.append(f"missing: {relative}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            failures.append(f"checksum mismatch: {relative}")
    present = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and path.name != "checksums.sha256" and "__pycache__" not in path.parts
    }
    for relative in sorted(present - listed):
        failures.append(f"unlisted file: {relative}")
    if failures:
        print("INVALID package")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"VALID package: {len(listed)} files verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
