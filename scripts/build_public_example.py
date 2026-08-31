#!/usr/bin/env python3
"""Build the sanitized, deterministic Schema 1.6 public example from the test fixture."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_MODULE = ROOT / "tests" / "test_film_project.py"
CLI = ROOT / "scripts" / "film_project.py"
FIXED_TIMESTAMP = "2026-08-25T12:00:00Z"
EXAMPLE_README = """# Night Shift — validated structural example

This sanitized fixture demonstrates one complete Schema 1.6 sequence: approved identity and role-physique facts, a location state with a side-three-quarter view and fixed spatial anchor, an approved ordinary-light person/world integration probe, quality/cinematography/format records, candidate isolation, Foundation and sequence gates, compiled image/video prompts, official three-skill method routing with every platform operation disabled, and a deterministic Higgsfield export. The probe remains an internal QA artifact and is deliberately excluded from the Higgsfield upload references.

The tiny neutral PNG files are deliberately non-promotional structural fixtures used to exercise paths, hashes, boards, and portability. They are **not** visual quality claims and contain no real identity, user reference, rejected quality candidate, or paid-platform data. See the public evidence gallery for visual results.

Validate it from the repository root:

```bash
python3 scripts/film_project.py validate examples/night-shift
python3 examples/night-shift/exports/higgsfield/verify_package.py
```
"""


def load_fixture_class():
    specification = importlib.util.spec_from_file_location("cad_public_fixture", FIXTURE_MODULE)
    if specification is None or specification.loader is None:
        raise RuntimeError("unable to load the public fixture builder")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module.ProjectFixture


def run_cli(*args: str) -> None:
    result = subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "examples" / "night-shift")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        if not args.replace:
            print(f"ERROR: output exists; pass --replace to rebuild: {output}", file=sys.stderr)
            return 2
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    Fixture = load_fixture_class()
    with tempfile.TemporaryDirectory(prefix="cad-public-example-") as directory:
        fixture = Fixture(Path(directory))
        project_path = fixture.path / "project.json"
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project.update(
            {
                "title": "Night Shift",
                "slug": "night-shift",
                "logline": "A bicycle courier discovers that a sealed case in a daylight repair workshop was opened before she arrived.",
                "language": "en",
                "created_at": FIXED_TIMESTAMP,
                "updated_at": FIXED_TIMESTAMP,
            }
        )
        project_path.write_text(
            json.dumps(project, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        # copyfile keeps the public fixture byte-identical without propagating
        # macOS quarantine/provenance xattrs from the temporary build tree.
        shutil.copytree(fixture.path, output, copy_function=shutil.copyfile)

    # Git does not track empty directories. Preserve every schema directory in
    # a clean clone so the committed example validates on CI and user machines.
    for directory in sorted(path for path in output.rglob("*") if path.is_dir()):
        if not any(directory.iterdir()):
            (directory / ".gitkeep").write_text("", encoding="utf-8", newline="\n")

    # The test fixture exercises failed-candidate isolation. The public example
    # intentionally contains no failed candidate record or binary, so every
    # non-selected variant is converted to a structurally passing alternative.
    candidates_path = output / "manifests" / "candidates.json"
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    for candidate_set in candidates["candidate_sets"]:
        alternatives = [
            item
            for batch in candidate_set["batches"]
            for item in batch["candidates"]
            if item["status"] == "selected"
        ]
        if len(alternatives) != 1:
            raise RuntimeError(f"public fixture candidate set lacks one selected exemplar: {candidate_set['id']}")
        passing_regions = alternatives[0]["diagnostic_regions"]
        for batch in candidate_set["batches"]:
            for candidate in batch["candidates"]:
                if candidate["status"] in {"failed", "discarded"}:
                    candidate["status"] = "passed"
                    candidate["quality_verdict"] = "pass"
                    candidate["hard_failures"] = []
                    candidate["diagnostic_regions"] = json.loads(json.dumps(passing_regions))
    candidates_path.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    methods_path = output / "manifests" / "higgsfield-methods.json"
    methods = json.loads(methods_path.read_text(encoding="utf-8"))
    methods["status"] = "approved"
    methods["generation_routes"] = [
        {
            "id": "route-location-authority",
            "status": "approved",
            "task_kind": "image",
            "intent": "Prepare an empty, topology-readable workshop location authority.",
            "capability_family": "location_image",
            "scope_ids": ["loc-workshop--v001"],
            "reference_asset_ids": [],
            "reference_roles": [],
            "model_advisory": "soul_location",
            "model_schema_verification_required": True,
            "prompt_contract": {
                "mode": "visible-model-facts-only",
                "preferred_max_tokens": 180,
                "overage_reason": "",
            },
            "output_contract": "One empty location image preserving topology, fixed facilities, and the spatial anchor.",
            "platform_operation": "not_performed",
        },
        {
            "id": "route-sequence-video",
            "status": "approved",
            "task_kind": "video",
            "intent": "Animate one serious live-action sequence from approved start and end keyframes.",
            "capability_family": "serious_video",
            "scope_ids": ["sh-010-010"],
            "reference_asset_ids": ["kf-sh-010-010-start--v001", "kf-sh-010-010-end--v001"],
            "reference_roles": ["start_image", "end_image"],
            "model_advisory": "seedance_2_0",
            "model_schema_verification_required": True,
            "prompt_contract": {
                "mode": "visible-model-facts-only",
                "preferred_max_tokens": 240,
                "overage_reason": "The structured shot must preserve spatial, camera, temporal, finite-exposure, and audio facts.",
            },
            "output_contract": "One shot matching approved identity, location, path, action, timing, blur, and sound responsibilities.",
            "platform_operation": "not_performed",
        },
        {
            "id": "route-sequence-audio",
            "status": "approved",
            "task_kind": "audio",
            "intent": "Prepare picture-linked workshop ambience and contact Foley as separate mix responsibilities.",
            "capability_family": "audio_generation",
            "scope_ids": ["sh-010-010"],
            "reference_asset_ids": [],
            "reference_roles": [],
            "model_advisory": "seed_audio",
            "model_schema_verification_required": True,
            "prompt_contract": {
                "mode": "visible-model-facts-only",
                "preferred_max_tokens": 160,
                "overage_reason": "",
            },
            "output_contract": "Separate ambience and Foley work orders aligned to the approved shot duration.",
            "platform_operation": "not_performed",
        },
    ]
    methods_path.write_text(
        json.dumps(methods, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (output / "README.md").write_text(EXAMPLE_README, encoding="utf-8", newline="\n")

    run_cli("validate", str(output))
    run_cli("export-higgsfield", str(output), "--output", str(output / "exports" / "higgsfield"))
    print(f"Built validated public example: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
