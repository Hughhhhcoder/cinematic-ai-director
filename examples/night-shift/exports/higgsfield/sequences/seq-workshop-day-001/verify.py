#!/usr/bin/env python3
"""Verify one exported sequence cluster using only Python 3.10+."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "reference-map.json", "state-lock.json", "spatial-map.json", "format-plan.json",
    "camera-path.json", "environment-state.json", "temporal-lock.json", "dynamic-range.json", "quality-profile.json",
    "sequence-anchor.json", "settings.json", "prompt.txt",
)
OFFICIAL_PROFILE = "cinema-studio-4-seedance-2.5-official-2026-08-27"
BASE_HEADINGS = (
    "GLOBAL STYLE", "SCENE", "CHARACTERS", "LOCATION", "FIRST FRAME AND BLOCKING",
    "OPTICS", "CAMERA", "PHYSICS", "LIGHTING", "AUDIO",
)


def main() -> int:
    failures = [f"missing: {name}" for name in REQUIRED if not (ROOT / name).is_file()]
    if not failures:
        reference_map = json.loads((ROOT / "reference-map.json").read_text(encoding="utf-8"))
        settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
        references = reference_map.get("references", [])
        if reference_map.get("official_conformance_profile_id") != OFFICIAL_PROFILE:
            failures.append("reference map official conformance profile mismatch")
        if settings.get("official_conformance_profile_id") != OFFICIAL_PROFILE:
            failures.append("settings official conformance profile mismatch")
        if settings.get("target_workflow") != "cinema-studio-4" or settings.get("target_model") != "seedance-2.5":
            failures.append("settings must target Cinema Studio 4 / Seedance 2.5")
        if len(references) > 50:
            failures.append(f"reference count {len(references)} exceeds adapter limit 50")
        identity_ranks = [item.get("rank") for item in references if item.get("usage") == "identity_inspector_primary"]
        state_ranks = [item.get("rank") for item in references if item.get("usage") == "current_character_state"]
        if state_ranks and (not identity_ranks or min(identity_ranks) > min(state_ranks)):
            failures.append("unified identity inspector must precede character-state references")
        for item in references:
            path = Path(str(item.get("file", "")))
            if path.is_absolute() or ".." in path.parts:
                failures.append(f"unsafe reference path: {path}")
            elif not (ROOT.parent.parent / path).is_file():
                failures.append(f"missing reference file: {path}")
        prompt = (ROOT / "prompt.txt").read_text(encoding="utf-8")
        lines = [line.strip().rstrip(":") for line in prompt.splitlines() if line.strip()]
        if not lines or lines[0].upper() != "GLOBAL STYLE":
            failures.append("prompt must begin with GLOBAL STYLE")
        shot_headings = [line for line in lines if re.fullmatch(r"Shot [1-9][0-9]*", line)]
        if not shot_headings:
            failures.append("prompt requires at least one numbered Shot heading")
        ordered = []
        for heading in BASE_HEADINGS:
            try:
                ordered.append(next(index for index, line in enumerate(lines) if line.upper() == heading))
            except StopIteration:
                failures.append(f"prompt missing official section: {heading}")
        if ordered and ordered != sorted(ordered):
            failures.append("official prompt sections are out of order")
    if failures:
        print("INVALID sequence")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("VALID sequence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
