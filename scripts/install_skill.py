#!/usr/bin/env python3
"""Install or verify the runtime-only cinematic-ai-director Codex skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

SKILL_NAME = "cinematic-ai-director"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = ("SKILL.md", "agents", "assets", "references", "scripts/film_project.py", "src")
EXCLUDED_PARTS = {"__pycache__", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def runtime_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in RUNTIME_ROOTS:
        path = root / relative
        if not path.exists():
            raise FileNotFoundError(f"required runtime path is missing: {relative}")
        candidates: Iterable[Path] = path.rglob("*") if path.is_dir() else (path,)
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            rel = candidate.relative_to(root)
            if any(part in EXCLUDED_PARTS for part in rel.parts) or candidate.suffix in EXCLUDED_SUFFIXES:
                continue
            if rel.as_posix() == "scripts/install_skill.py":
                continue
            files.append(candidate)
    return sorted(set(files), key=lambda item: item.relative_to(root).as_posix())


def manifest(root: Path) -> dict[str, object]:
    rows = []
    for path in runtime_files(root):
        relative = path.relative_to(root).as_posix()
        rows.append({"path": relative, "sha256": sha256(path), "size": path.stat().st_size})
    return {
        "skill": SKILL_NAME,
        "version": "1.7.0",
        "schema_version": "1.6",
        "files": rows,
    }


def default_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def target_path(codex_home: Path) -> Path:
    return codex_home.expanduser().resolve() / "skills" / SKILL_NAME


def copy_runtime(source: Path, destination: Path) -> dict[str, object]:
    payload = manifest(source)
    for row in payload["files"]:
        assert isinstance(row, dict)
        relative = Path(str(row["path"]))
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, output)
    (destination / "runtime-manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return payload


def verify(target: Path) -> tuple[bool, list[str]]:
    manifest_path = target / "runtime-manifest.json"
    if not manifest_path.is_file():
        return False, ["runtime-manifest.json is missing"]
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"runtime manifest is unreadable: {exc}"]
    errors: list[str] = []
    expected_paths: set[str] = set()
    for row in payload.get("files", []):
        if not isinstance(row, dict):
            errors.append("runtime manifest contains a non-object file record")
            continue
        relative = str(row.get("path", ""))
        if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            errors.append(f"unsafe manifest path: {relative!r}")
            continue
        expected_paths.add(relative)
        path = target / relative
        if not path.is_file():
            errors.append(f"missing runtime file: {relative}")
        elif sha256(path) != row.get("sha256"):
            errors.append(f"checksum mismatch: {relative}")
    actual_paths = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file() and path.name != "runtime-manifest.json" and "__pycache__" not in path.parts
    }
    unexpected = sorted(actual_paths - expected_paths)
    if unexpected:
        errors.extend(f"unexpected runtime file: {path}" for path in unexpected)
    return not errors, errors


def install(codex_home: Path, replace: bool) -> int:
    target = target_path(codex_home)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not replace:
        print(f"ERROR: target exists; use --replace to back it up and install: {target}", file=sys.stderr)
        return 2

    stage = Path(tempfile.mkdtemp(prefix=f".{SKILL_NAME}.stage-", dir=target.parent))
    backup: Path | None = None
    try:
        copy_runtime(REPOSITORY_ROOT, stage)
        passed, errors = verify(stage)
        if not passed:
            raise RuntimeError("; ".join(errors))
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = target.with_name(f"{SKILL_NAME}.backup-{stamp}")
            suffix = 1
            while backup.exists():
                backup = target.with_name(f"{SKILL_NAME}.backup-{stamp}-{suffix}")
                suffix += 1
            target.replace(backup)
        stage.replace(target)
    except Exception as exc:
        if stage.exists():
            shutil.rmtree(stage)
        if backup is not None and backup.exists() and not target.exists():
            backup.replace(target)
        print(f"ERROR: installation failed: {exc}", file=sys.stderr)
        return 2

    print(f"Installed {SKILL_NAME} v1.7.0: {target}")
    if backup is not None:
        print(f"Previous installation backup: {backup}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "verify"):
        item = subparsers.add_parser(command)
        item.add_argument("--codex-home", type=Path, default=default_codex_home())
        if command == "install":
            item.add_argument("--replace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "install":
        return install(args.codex_home, args.replace)
    target = target_path(args.codex_home)
    passed, errors = verify(target)
    if not passed:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Verified {SKILL_NAME} runtime: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
