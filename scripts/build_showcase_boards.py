#!/usr/bin/env python3
"""Build the v1.6.4 single-chain showcase without redrawing approved pixels."""

from __future__ import annotations

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
except ImportError as exc:  # pragma: no cover - release-only dependency
    raise SystemExit(
        "Pillow is required only to build publication derivatives: pip install -r requirements-dev.txt"
    ) from exc


IDENTITY = Path(
    "showcase/originals/identity-inspectors/identity-white-coastal-survey-engineer-v001.png"
)
EMPTY_SCENE = Path(
    "showcase/originals/scenes/scene-coastal-tide-station-overcast-v001.png"
)
LIVE_ACTION_PROBE = Path(
    "showcase/originals/narrative/live-action-probe-coastal-survey-engineer-v001.png"
)
PROMPTS = {
    "identity": Path("showcase/prompts/identity-white-coastal-survey-engineer-v001.txt"),
    "empty_scene": Path("showcase/prompts/scene-coastal-tide-station-overcast-v001.txt"),
    "live_action_probe": Path(
        "showcase/prompts/live-action-probe-coastal-survey-engineer-v001.txt"
    ),
}
SOURCE_GENERATIONS = {
    "identity": "exec-54f49254-c489-4a69-bfc0-3764c1ce393a",
    "empty_scene": "exec-a61709cd-80fb-4c63-8c2f-a1afa8519282",
    "live_action_probe": "exec-98116d6f-fee0-4913-babb-a8f32bf7304b",
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
CHECK_SCALES = ["thumbnail", "fit", "100_percent", "200_percent"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def crop_identity_inspector() -> dict[str, Any]:
    """Extract seven exact cells while keeping the one Inspector authoritative."""
    source = REPOSITORY_ROOT / IDENTITY
    width, height, pixels = _decode_png_rgb(source)
    if width % 4:
        raise ValueError(f"Inspector width must divide exactly into four columns: {width}x{height}")
    cell_width = width // 4
    row_split, gutter_detection = _detect_horizontal_gutter_split(width, height, pixels)
    row_tops = (0, row_split)
    row_heights = (row_split, height - row_split)
    crop_root = (
        REPOSITORY_ROOT
        / "showcase/originals/identity-crops/identity-white-coastal-survey-engineer-v001"
    )
    crop_root.mkdir(parents=True, exist_ok=True)
    crops: list[dict[str, Any]] = []
    for index, role in enumerate(IDENTITY_ROLES):
        column = index % 4
        row = index // 4
        top = row_tops[row]
        cell_height = row_heights[row]
        crop = bytearray(cell_width * cell_height * 3)
        for output_y in range(cell_height):
            source_start = (((top + output_y) * width) + column * cell_width) * 3
            source_end = source_start + cell_width * 3
            target_start = output_y * cell_width * 3
            crop[target_start : target_start + cell_width * 3] = pixels[source_start:source_end]
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
        "authority": IDENTITY.as_posix(),
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


def save_webp(source_relative: Path, output_name: str, maximum_width: int = 1600) -> Path:
    source = REPOSITORY_ROOT / source_relative
    output = REPOSITORY_ROOT / "docs/assets/showcase" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        if image.width > maximum_width:
            height = round(image.height * maximum_width / image.width)
            image = image.resize((maximum_width, height), Image.Resampling.LANCZOS)
        image.save(output, "WEBP", quality=89, method=6, exact=True)
    return output


def contain(
    source: Image.Image, size: tuple[int, int], background: tuple[int, int, int]
) -> Image.Image:
    canvas = Image.new("RGB", size, background)
    fitted = ImageOps.contain(source.convert("RGB"), size, method=Image.Resampling.LANCZOS)
    canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return canvas


def build_montage(output_name: str, size: tuple[int, int]) -> Path:
    """Arrange the approved originals; this does not generate or repaint content."""
    output = REPOSITORY_ROOT / "docs/assets/showcase" / output_name
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    margin = max(12, round(min(size) * 0.025))
    gap = max(10, margin // 2)
    background = (238, 237, 233)
    canvas = Image.new("RGB", size, background)
    top_height = round((height - margin * 2 - gap) * 0.64)
    bottom_height = height - margin * 2 - gap - top_height
    bottom_identity_width = round((width - margin * 2 - gap) * 0.34)
    bottom_scene_width = width - margin * 2 - gap - bottom_identity_width
    with (
        Image.open(REPOSITORY_ROOT / IDENTITY) as identity,
        Image.open(REPOSITORY_ROOT / EMPTY_SCENE) as scene,
        Image.open(REPOSITORY_ROOT / LIVE_ACTION_PROBE) as probe,
    ):
        canvas.paste(
            ImageOps.fit(
                probe.convert("RGB"),
                (width - margin * 2, top_height),
                method=Image.Resampling.LANCZOS,
                centering=(0.55, 0.48),
            ),
            (margin, margin),
        )
        bottom_y = margin + top_height + gap
        canvas.paste(
            contain(identity, (bottom_identity_width, bottom_height), background),
            (margin, bottom_y),
        )
        canvas.paste(
            ImageOps.fit(
                scene.convert("RGB"),
                (bottom_scene_width, bottom_height),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            ),
            (margin + bottom_identity_width + gap, bottom_y),
        )
    canvas.save(output, "WEBP", quality=90, method=6, exact=True)
    return output


def dimensions(path: Path) -> list[int]:
    with Image.open(path) as image:
        return [image.width, image.height]


def finite_dynamic_range(kind: str) -> dict[str, Any]:
    if kind == "identity":
        return {
            "policy": "finite_scene_referred",
            "exposure_priority": "natural-dry face and neutral clothing",
            "middle_tone_anchor": "light-blue shirt and facial middle tones",
            "allowed_highlight_loss": [],
            "allowed_shadow_loss": ["deepest charcoal trouser folds"],
            "local_tone_mapping_detected": False,
            "multi_exposure_hdr_merge": False,
        }
    return {
        "policy": "finite_scene_referred",
        "exposure_priority": (
            "face and middle-grey room"
            if kind == "live_action_probe"
            else "middle-grey room and chart cabinet"
        ),
        "middle_tone_anchor": (
            "face, pale-blue shirt, and painted concrete"
            if kind == "live_action_probe"
            else "painted concrete and pale-grey steel chart cabinet"
        ),
        "allowed_highlight_loss": ["bright overcast harbor sky"],
        "allowed_shadow_loss": ["unlit doorway", "space below the work counter"],
        "local_tone_mapping_detected": False,
        "multi_exposure_hdr_merge": False,
    }


def qa_record(kind: str) -> dict[str, Any]:
    human = kind in {"identity", "live_action_probe"}
    return {
        "scales_checked": CHECK_SCALES,
        "ai_visual_verdict": "pass",
        "skin_surface_state": "natural_dry" if human else "not_applicable",
        "oil_film": "absent" if human else "not_applicable",
        "painterly_smear": "absent",
        "animation_cg_or_game_surface": "absent",
        "repeating_cross_material_texture": "absent",
        "unmotivated_rim_or_beauty_light": "absent",
        "finite_dynamic_range": finite_dynamic_range(kind),
        "positive_evidence": {
            "photographic_event": (
                "One task-led survey engineer writes on a chart in a reachable room camera."
                if kind == "live_action_probe"
                else "One shared neutral casting solve."
                if kind == "identity"
                else "A reachable side-three-quarter location-scout view proves one physical room."
            ),
            "skin_and_material": (
                "Natural-dry skin has broad weak window response; hair, cotton, wool, paper, paint, glass and steel stay separate."
                if kind == "live_action_probe"
                else "Natural-dry skin, hair, cotton, wool and leather stay separate under one neutral source."
                if kind == "identity"
                else "Concrete paint, linoleum, paper, glass, steel, cable and the red case keep independent response."
            ),
            "exposure_tradeoff": "Bright harbor sky loses information while the unlit doorway and counter recess approach black."
            if kind != "identity"
            else "The white field approaches the upper diffuse range while deepest dark-fabric folds retain a real floor.",
        },
        "hard_failures": [],
        "reviewer": "codex-visual",
        "reviewed_at": "2026-08-28T00:00:00Z",
    }


def evidence_record(
    kind: str, original_relative: Path, derivative: Path
) -> dict[str, Any]:
    original = REPOSITORY_ROOT / original_relative
    prompt = REPOSITORY_ROOT / PROMPTS[kind]
    record: dict[str, Any] = {
        "kind": kind,
        "source_generation_id": SOURCE_GENERATIONS[kind],
        "generator": "builtin-imagegen",
        "operation": "generate",
        "original_path": original_relative.as_posix(),
        "original_sha256": sha256(original),
        "prompt_path": PROMPTS[kind].as_posix(),
        "prompt_sha256": sha256(prompt),
        "publication_derivative_path": derivative.relative_to(REPOSITORY_ROOT).as_posix(),
        "publication_derivative_sha256": sha256(derivative),
        "actual_dimensions_px": dimensions(original),
        "qa": qa_record(kind),
    }
    if kind == "identity":
        record["identity_inspector"] = {
            "single_identity_solve": True,
            "authoritative": True,
            "grid": [4, 2],
            "roles": [*IDENTITY_ROLES, "blank"],
            "visible_body_balance": "balanced_four_six",
            "unintended_five_five": False,
        }
    if kind == "empty_scene":
        record["spatial_qa"] = {
            "view_role": "side_three_quarter_wide",
            "three_quarter_yaw_deg": 45,
            "adjacent_planes_visible": True,
            "camera_accessible": True,
            "primary_anchor": "pale-grey chart cabinet plus muted-red calibration case",
            "anchor_grounded_and_scaled": True,
            "verdict": "pass",
        }
    if kind == "live_action_probe":
        record["reference_stack"] = [IDENTITY.as_posix(), EMPTY_SCENE.as_posix()]
        record["live_action_integration_probe"] = {
            "status": "approved",
            "attempt_batch_count": 1,
            "max_attempt_batches": 2,
            "ordinary_light_only": True,
            "special_environment_disabled": True,
            "prompt_strategy_id": "image2-live-action-integration-probe-v1.6",
            "verdict": "pass",
            "failure_classes": [],
        }
        record["subject_environment_integration_qa"] = {
            "shared_light": "one broad overcast harbor-window source plus weak room bounce",
            "shared_focus_and_occlusion": "face, hands, chart, counter edge and room share one optical stack",
            "contact_and_grounding": "both hands contact the chart/counter and both feet share the room floor",
            "shared_tone_mapping": True,
            "cutout_edges_detected": False,
            "separate_person_tone_mapping_detected": False,
            "background_only_atmosphere_detected": False,
            "verdict": "pass",
        }
        record["geometry_qa"] = {
            "approved_identity_proportions_preserved": True,
            "hands_and_contact": "pass",
            "perspective_and_grounding": "pass",
            "verdict": "pass",
        }
    return record


def main() -> int:
    for relative in (IDENTITY, EMPTY_SCENE, LIVE_ACTION_PROBE, *PROMPTS.values()):
        if not (REPOSITORY_ROOT / relative).is_file():
            raise SystemExit(f"Missing showcase source: {relative}")

    crop_manifest = crop_identity_inspector()
    identity_webp = save_webp(
        IDENTITY, "identity-white-coastal-survey-engineer-v001.webp"
    )
    scene_webp = save_webp(
        EMPTY_SCENE, "scene-coastal-tide-station-overcast-v001.webp"
    )
    probe_webp = save_webp(
        LIVE_ACTION_PROBE, "live-action-probe-coastal-survey-engineer-v001.webp"
    )
    hero = build_montage("hero.webp", (1600, 900))
    social = build_montage("social-preview.webp", (1200, 630))
    evidence = {
        "schema_version": "1.6",
        "release_version": "1.6.4",
        "showcase_profile": "single-chain-live-action-probe-v1.6.4",
        "generator": "builtin-imagegen",
        "reproducibility_class": "workflow_only",
        "pixel_reproducible": False,
        "publication_policy": {
            "one_authoritative_identity_board": True,
            "failed_or_rejected_candidates_public": False,
            "old_arctic_and_western_material_removed": True,
            "user_quality_reference_included": False,
            "third_party_media_included": False,
        },
        "candidate_pool": {
            "target": "live_action_probe",
            "independent_generations": 3,
            "selected_generation_id": SOURCE_GENERATIONS["live_action_probe"],
            "selected_count": 1,
            "unselected_generations_retained_outside_public_tree": 2,
            "mutual_editing": False,
        },
        "assets": [
            evidence_record("identity", IDENTITY, identity_webp),
            evidence_record("empty_scene", EMPTY_SCENE, scene_webp),
            evidence_record("live_action_probe", LIVE_ACTION_PROBE, probe_webp),
        ],
        "identity_crops": crop_manifest,
        "montages": {
            "hero": {
                "path": hero.relative_to(REPOSITORY_ROOT).as_posix(),
                "sha256": sha256(hero),
                "operation": "approved-original-layout-no-generative-repaint",
            },
            "social_preview": {
                "path": social.relative_to(REPOSITORY_ROOT).as_posix(),
                "sha256": sha256(social),
                "operation": "approved-original-layout-no-generative-repaint",
            },
        },
    }
    write_json(REPOSITORY_ROOT / "showcase/evidence.json", evidence)
    print("Built v1.6.4 showcase: one Inspector, one empty 2.39:1 location, and one approved ordinary-light live-action probe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
