#!/usr/bin/env python3
"""Build deterministic runtime and evidence archives for a GitHub release."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from install_skill import REPOSITORY_ROOT, SKILL_NAME, manifest, runtime_files

VERSION = "1.6.6"
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def write_zip(output: Path, sources: list[tuple[Path, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, archive_name in sorted(sources, key=lambda item: item[1]):
            info = zipfile.ZipInfo(archive_name, ZIP_TIMESTAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPOSITORY_ROOT / "dist")
    parser.add_argument("--manifest-output", type=Path, default=REPOSITORY_ROOT / "release" / "runtime-manifest.json")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    runtime_payload = manifest(REPOSITORY_ROOT)
    manifest_path = args.manifest_output.resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(runtime_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    runtime_sources = [
        (path, f"{SKILL_NAME}/{path.relative_to(REPOSITORY_ROOT).as_posix()}")
        for path in runtime_files(REPOSITORY_ROOT)
    ]
    runtime_sources.append((manifest_path, f"{SKILL_NAME}/runtime-manifest.json"))
    runtime_zip = output / f"{SKILL_NAME}-v{VERSION}.zip"
    write_zip(runtime_zip, runtime_sources)

    optional_archives: list[Path] = []
    showcase = REPOSITORY_ROOT / "showcase"
    if showcase.is_dir():
        files = [(path, path.relative_to(showcase).as_posix()) for path in showcase.rglob("*") if path.is_file()]
        showcase_zip = output / f"{SKILL_NAME}-showcase-originals-v{VERSION}.zip"
        write_zip(showcase_zip, files)
        optional_archives.append(showcase_zip)
    example_export = REPOSITORY_ROOT / "examples" / "night-shift" / "exports" / "higgsfield"
    if example_export.is_dir():
        files = [(path, path.relative_to(example_export.parent).as_posix()) for path in example_export.rglob("*") if path.is_file()]
        example_zip = output / f"{SKILL_NAME}-higgsfield-example-v{VERSION}.zip"
        write_zip(example_zip, files)
        optional_archives.append(example_zip)

    artifacts = [runtime_zip, *optional_archives]
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest(path)}  {path.name}\n" for path in sorted(artifacts)),
        encoding="utf-8",
        newline="\n",
    )
    print(f"Built {len(artifacts)} deterministic release archive(s) in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
