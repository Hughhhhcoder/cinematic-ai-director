#!/usr/bin/env python3
"""Build the compact v1.6.1 showcase without redrawing approved originals."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from cinematic_ai_director.boards import (  # noqa: E402
    _decode_png_rgb,
    _detect_horizontal_gutter_split,
    _encode_png_rgb,
)

try:
    from PIL import Image, ImageOps
except ImportError as exc:  # pragma: no cover - exercised by release tooling
    raise SystemExit("Pillow is required only to build publication WebP derivatives: pip install -r requirements-dev.txt") from exc


IDENTITY = Path("showcase/originals/identity-inspectors/identity-white-arctic-survey-pilot-v003.png")
EMPTY_SCENE = Path("showcase/originals/scenes/scene-arctic-rescue-hangar-v003.png")
NARRATIVE = Path("showcase/originals/narrative/narrative-white-survey-pilot-arctic-hangar-v003.png")
PROMPTS = {
    "identity": Path("showcase/prompts/identity-white-arctic-survey-pilot-v003.txt"),
    "empty_scene": Path("showcase/prompts/scene-arctic-rescue-hangar-v003.txt"),
    "narrative": Path("showcase/prompts/narrative-white-survey-pilot-arctic-hangar-v003.txt"),
}
SOURCE_GENERATIONS = {
    "identity": "exec-432fddbb-9c60-42c0-b078-74921ed214c6",
    "empty_scene": "exec-26aafbec-b83d-4f63-b87e-594242c74027",
    "narrative": "exec-6ebfccb6-6e59-4988-9ba0-82b32e72c554",
}
IDENTITY_ROLES = (
    "full_front",
    "full_left_profile",
    "full_right_profile",
    "full_back",
    "portrait_front",
    "portrait_left_profile",
    "portrait_right_profile",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def crop_identity_inspector(source_relative: Path) -> dict[str, Any]:
    """Extract seven exact cells; the unified Inspector remains authoritative."""
    source = REPOSITORY_ROOT / source_relative
    width, height, pixels = _decode_png_rgb(source)
    if width % 4:
        raise ValueError(f"Inspector width must divide exactly into four columns: {width}x{height}")
    cell_width = width // 4
    row_split, gutter_detection = _detect_horizontal_gutter_split(width, height, pixels)
    row_tops = (0, row_split)
    row_heights = (row_split, height - row_split)
    crop_root = REPOSITORY_ROOT / "showcase/originals/identity-crops/identity-white-arctic-survey-pilot-v003"
    crop_root.mkdir(parents=True, exist_ok=True)
    crops: list[dict[str, Any]] = []
    for index, role in enumerate(IDENTITY_ROLES):
        column = index % 4
        row = index // 4
        cell_height = row_heights[row]
        top = row_tops[row]
        crop = bytearray(cell_width * cell_height * 3)
        for output_y in range(cell_height):
            source_start = (((top + output_y) * width) + column * cell_width) * 3
            source_end = source_start + cell_width * 3
            target_start = output_y * cell_width * 3
            crop[target_start:target_start + cell_width * 3] = pixels[source_start:source_end]
        output = crop_root / f"{role}.png"
        encoded = _encode_png_rgb(cell_width, cell_height, bytes(crop))
        output.write_bytes(encoded)
        crops.append(
            {
                "role": role,
                "path": output.relative_to(REPOSITORY_ROOT).as_posix(),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "source_cell": {"column": column, "row": row},
                "crop_box_px": [column * cell_width, top, cell_width, cell_height],
                "width_px": cell_width,
                "height_px": cell_height,
            }
        )
    manifest = {
        "profile": "higgsfield-character-reference-sheet-two-row-single-solve-v1.6",
        "authority": source_relative.as_posix(),
        "authority_sha256": sha256(source),
        "operation": "exact-cell-crop-no-resample-no-redraw",
        "crops_are_authoritative": False,
        "grid": [4, 2],
        "row_split_px": row_split,
        "gutter_detection": gutter_detection,
        "blank_cell": {"column": 3, "row": 1},
        "crops": crops,
    }
    write_json(crop_root / "crop-map.json", manifest)
    return manifest


def contain(image: Image.Image, size: tuple[int, int], background: tuple[int, int, int]) -> Image.Image:
    canvas = Image.new("RGB", size, background)
    fitted = ImageOps.contain(image.convert("RGB"), size, method=Image.Resampling.LANCZOS)
    canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return canvas


def save_webp(source_relative: Path, output_name: str, maximum_width: int = 1600) -> Path:
    source = REPOSITORY_ROOT / source_relative
    output = REPOSITORY_ROOT / "docs/assets/showcase" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        if image.width > maximum_width:
            height = round(image.height * maximum_width / image.width)
            image = image.resize((maximum_width, height), Image.Resampling.LANCZOS)
        image.save(output, "WEBP", quality=88, method=6, exact=True)
    return output


def build_montage(output_name: str, size: tuple[int, int]) -> Path:
    output = REPOSITORY_ROOT / "docs/assets/showcase" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(REPOSITORY_ROOT / IDENTITY) as identity_source, Image.open(
        REPOSITORY_ROOT / EMPTY_SCENE
    ) as empty_source, Image.open(REPOSITORY_ROOT / NARRATIVE) as narrative_source:
        width, height = size
        gutter = max(8, round(min(width, height) * 0.014))
        left_width = round(width * 0.41)
        right_x = left_width + gutter
        right_width = width - right_x
        half_height = (height - gutter) // 2
        lower_height = height - gutter - half_height
        background = (16, 18, 20)
        canvas = Image.new("RGB", size, background)
        identity_card = contain(
            identity_source,
            (left_width - 2 * gutter, height - 2 * gutter),
            background,
        )
        canvas.paste(identity_card, (gutter, gutter))
        canvas.paste(
            ImageOps.fit(
                empty_source.convert("RGB"),
                (right_width, half_height),
                method=Image.Resampling.LANCZOS,
            ),
            (right_x, 0),
        )
        canvas.paste(
            ImageOps.fit(
                narrative_source.convert("RGB"),
                (right_width, lower_height),
                method=Image.Resampling.LANCZOS,
            ),
            (right_x, half_height + gutter),
        )
        canvas.save(output, "WEBP", quality=88, method=6, exact=True)
    return output


def dynamic_range_plan(kind: str) -> dict[str, Any]:
    common = {
        "policy": "finite_scene_referred",
        "working_latitude_stops": 14.0,
        "upper_latitude_stops": 6.0,
        "lower_latitude_stops": 8.0,
        "local_tone_mapping_detected": False,
        "multi_exposure_hdr_merge": False,
        "measurement_note": "Visual release QA estimate only; this generated image does not claim a physical camera, EXIF, or measured sensor response.",
    }
    if kind == "identity":
        return {
            **common,
            "scene_contrast_stops_estimate": 5.0,
            "exposure_priority": "protect_skin",
            "middle_tone_anchor": "face and midnight-blue cotton base layer",
            "highlight_loss_or_rolloff": "white field approaches the upper diffuse range without flattening facial planes",
            "shadow_loss_or_floor": "deepest trouser and shoe folds may merge without HDR lift",
            "allowed_clipping": [],
            "allowed_shadow_loss": ["deepest black-trouser and shoe folds"],
        }
    if kind == "empty_scene":
        return {
            **common,
            "scene_contrast_stops_estimate": 16.5,
            "exposure_priority": "balanced_middle_tones",
            "middle_tone_anchor": "interior concrete, off-white insulated panels and yellow deicing cabinet",
            "highlight_loss_or_rolloff": "apron floodlight and aircraft-light cores clip while the snow-lit falloff retains shape",
            "shadow_loss_or_floor": "the upper roof void, rear service bays and runway sky fall to black",
            "allowed_clipping": ["small apron floodlight cores", "tiny aircraft landing-light cores"],
            "allowed_shadow_loss": ["upper roof void", "rear service bays", "runway sky"],
        }
    return {
        **common,
        "scene_contrast_stops_estimate": 17.0,
        "exposure_priority": "protect_subject_separation_and_spatial_anchor",
        "middle_tone_anchor": "the woman's navy-charcoal separation, body silhouette and yellow deicing cabinet",
        "highlight_loss_or_rolloff": "apron floodlight and aircraft-light cores clip before the body silhouette or yellow anchor are flattened",
        "shadow_loss_or_floor": "the roof void, rear service bay, runway sky and deepest trouser folds lose fine information",
        "allowed_clipping": ["small apron floodlight cores", "tiny aircraft landing-light cores"],
        "allowed_shadow_loss": ["upper roof void", "rear service bay", "runway sky", "deepest trouser folds"],
    }


def evidence_record(kind: str, source_relative: Path, derivative: Path) -> dict[str, Any]:
    source = REPOSITORY_ROOT / source_relative
    prompt = REPOSITORY_ROOT / PROMPTS[kind]
    width, height, _ = _decode_png_rgb(source)
    has_person = kind != "empty_scene"
    is_widescreen = kind != "identity"
    material_pairs = {
        "identity": ["natural dry skin vs matte cotton", "hair vs white seamless field"],
        "empty_scene": ["structural steel vs matte concrete", "snow vs off-white insulated panels"],
        "narrative": ["ash-brown hair vs matte navy cotton", "painted yellow steel vs wet concrete"],
    }
    positive_evidence = {
        "identity": "One shared solve preserves the same face, haircut, body volume and clothing across seven views; matte skin, cotton and hair retain separate responses.",
        "empty_scene": "A reachable side-three-quarter camera, coherent portal frame, gantry, door, drains and service bays, a fixed yellow anchor, source-visible snow and deliberate floodlight clipping establish a reconstructable live-action hangar.",
        "narrative": "The approved white lead, long-legged role-matched physique, hangar topology and yellow anchor persist. A grounded rear-three-quarter stance carries scale, decision and weather while deliberately leaving face coverage to the identity Inspector; practical peaks clip and real dark regions remain lost.",
    }
    record = {
        "kind": kind,
        "source_generation_id": SOURCE_GENERATIONS[kind],
        "original_path": source_relative.as_posix(),
        "original_sha256": sha256(source),
        "prompt_path": PROMPTS[kind].as_posix(),
        "prompt_sha256": sha256(prompt),
        "publication_derivative_path": derivative.relative_to(REPOSITORY_ROOT).as_posix(),
        "publication_derivative_sha256": sha256(derivative),
        "actual_dimensions_px": [width, height],
        "generation_backend": "builtin-imagegen",
        "operation": "independent_generate" if kind != "narrative" else "generate_with_approved_references",
        "pixel_reproducible": False,
        "format_plan": {
            "working_frame": "2.39:1" if is_widescreen else "4x2 identity inspector on 3:2 canvas",
            "delivery_frame": "2.39:1" if is_widescreen else "3:2 authority board",
            "baked_black_bars": False,
        },
        "qa": {
            "scales_checked": ["thumbnail", "fit", "100_percent", "200_percent"],
            "live_action_quality": "pass",
            "geometry": "pass" if has_person else "not_applicable",
            "skin_surface_state": (
                "natural_dry"
                if kind == "identity"
                else "not_visibly_evaluated_by_shot_design"
                if kind == "narrative"
                else "not_applicable"
            ),
            "oil_film": (
                "absent"
                if kind == "identity"
                else "not_visible_by_shot_design"
                if kind == "narrative"
                else "not_applicable"
            ),
            "painterly_smear": "absent",
            "animation_or_cg_surface": "absent",
            "cross_material_dirty_texture": "absent",
            "source_light_causality": "pass",
            "positive_evidence": positive_evidence[kind],
            "material_pairs": material_pairs[kind],
            "same_repeating_texture": False,
            "finite_dynamic_range": dynamic_range_plan(kind),
            "reviewer": "codex-visual",
            "verdict": "pass",
        },
    }
    if kind == "narrative":
        record["reference_stack"] = [
            IDENTITY.as_posix(),
            EMPTY_SCENE.as_posix(),
        ]
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="replace deterministic publication derivatives")
    args = parser.parse_args(argv)
    required = [IDENTITY, EMPTY_SCENE, NARRATIVE, *PROMPTS.values()]
    missing = [path for path in required if not (REPOSITORY_ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError("missing approved showcase input(s): " + ", ".join(path.as_posix() for path in missing))
    outputs = [
        REPOSITORY_ROOT / "docs/assets/showcase/identity-white-arctic-survey-pilot-v003.webp",
        REPOSITORY_ROOT / "docs/assets/showcase/scene-arctic-rescue-hangar-v003.webp",
        REPOSITORY_ROOT / "docs/assets/showcase/narrative-white-survey-pilot-arctic-hangar-v003.webp",
        REPOSITORY_ROOT / "docs/assets/showcase/hero.webp",
        REPOSITORY_ROOT / "docs/assets/showcase/social-preview.webp",
        REPOSITORY_ROOT / "showcase/evidence.json",
    ]
    if not args.replace and any(path.exists() for path in outputs):
        raise FileExistsError("showcase output exists; pass --replace for an explicit deterministic rebuild")
    crop_manifest = crop_identity_inspector(IDENTITY)
    identity_webp = save_webp(IDENTITY, "identity-white-arctic-survey-pilot-v003.webp")
    empty_webp = save_webp(EMPTY_SCENE, "scene-arctic-rescue-hangar-v003.webp")
    narrative_webp = save_webp(NARRATIVE, "narrative-white-survey-pilot-arctic-hangar-v003.webp")
    hero = build_montage("hero.webp", (1800, 900))
    social = build_montage("social-preview.webp", (1280, 640))
    evidence = {
        "schema_version": "1.6",
        "showcase_profile": "compact-theatrical-widescreen-evidence-v1.6.1",
        "scope": "one unified identity Inspector, one 2.39:1 empty location, one 2.39:1 live-action person-in-location narrative frame",
        "selection_claim": "Three approved examples after four-scale visual QA; this compact gallery is not a statistical pass-rate claim.",
        "identity_authority_policy": "one ImageGen call, one shared identity solve, validate whole Inspector first, stop on failure, then crop exactly without resampling or redraw",
        "theatrical_format_policy": "scene and narrative originals are native 2.39:1 deliverables with no baked black bars; the identity authority remains a 4x2 inspection board",
        "higgsfield_contract": {
            "profile": "cinema-studio-4-seedance-2.5-official-2026-08-27",
            "scope": "The Skill exporter and prompt adapter are validated against this dated official profile; gallery images are ImageGen quality evidence, not Higgsfield outputs.",
        },
        "privacy": {
            "fictional_adult": True,
            "user_calibration_reference_published": False,
            "failed_candidates_published": False,
            "third_party_project_media_published": False,
        },
        "reproducibility_class": "workflow_only",
        "pixel_reproducible": False,
        "assets": [
            evidence_record("identity", IDENTITY, identity_webp),
            evidence_record("empty_scene", EMPTY_SCENE, empty_webp),
            evidence_record("narrative", NARRATIVE, narrative_webp),
        ],
        "identity_crops": crop_manifest,
        "publication_montages": [
            {"path": hero.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": sha256(hero), "operation": "deterministic-layout-only"},
            {"path": social.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": sha256(social), "operation": "deterministic-layout-only"},
        ],
    }
    write_json(REPOSITORY_ROOT / "showcase/evidence.json", evidence)
    print("Built compact v1.6.1 showcase: one Inspector and two native 2.39:1 live-action frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
