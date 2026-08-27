#!/usr/bin/env python3
"""Regression tests for cinematic-ai-director's offline v1.6 validator."""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "film_project.py"
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from cinematic_ai_director.boards import _detect_horizontal_gutter_split  # noqa: E402

TIMESTAMP = "2026-08-25T12:00:00Z"
STORY_MOMENT = "The courier notices the opened case under the existing desk lamp."
LOCKED_BLOCKING = (
    "Same identity, plain work clothes with a declared right-cuff crease, opened case, time of day and spatial relationship: "
    "the courier stands at the near table edge while the workshop doorway remains behind her."
)
IMAGE_STRATEGY = "image2-live-action-narrative-v1.6"
IMAGE_HEADINGS = (
    "PHOTOGRAPHIC EVENT",
    "APPROVED IDENTITY WORLD AND STATE",
    "PHYSICAL CAMERA AND BLOCKING",
    "SOURCE LIGHT AND MATERIAL RESPONSE",
    "FOCUS EXPOSURE AND CONTINGENCY",
    "EXCLUSIONS",
)
VIDEO_HEADINGS = (
    "GLOBAL STYLE",
    "SCENE",
    "CHARACTERS",
    "LOCATION",
    "FIRST FRAME AND BLOCKING",
    "Shot 1",
    "OPTICS",
    "CAMERA",
    "PHYSICS",
    "LIGHTING",
    "AUDIO",
)
PHOTO_CHECKS = (
    "capture_plausibility",
    "optical_coherence",
    "exposure_lighting",
    "material_skin",
    "texture_locality",
    "profile_continuity",
)
AUTH_CHECKS = (
    "casting_specificity",
    "human_surface",
    "set_causality",
    "lighting_causality",
    "composition_contingency",
    "material_contact",
    "artifact_absence",
    "brief_fit",
)
TEXTURE_CHECKS = (
    "painterly_smear_or_low_frequency_blur",
    "repeating_swirl_scale_fingerprint_or_cellular_pattern",
    "cross_material_texture_leakage",
    "skin_hair_and_fabric_scale",
    "oversharpen_halos_specks_and_dirty_shadows",
    "localized_defect_bounds",
    "resampling_compression_and_color_mode",
)
CHARACTER_VIEWS = [
    "full_front",
    "full_left_profile",
    "full_right_profile",
    "full_back",
    "portrait_front",
    "portrait_left_profile",
    "portrait_right_profile",
]
GEOMETRY_CHECKS = (
    "silhouette_and_volume",
    "joint_topology",
    "segment_lengths",
    "hands_feet_and_digits",
    "shoulder_pelvis_alignment",
    "weight_bearing_and_center_of_mass",
    "foreshortening_and_projection",
    "occlusion_logic",
    "garment_body_separation",
    "multi_person_relative_scale",
)
LIVE_ACTION_SURFACE_CHECKS = (
    "no_painterly_or_patch_smear",
    "no_wax_plastic_or_cg_skin",
    "natural_eye_hair_and_edge_behavior",
    "skin_specular_source_size_and_extent",
    "skin_tone_continuity_and_subsurface_behavior",
    "local_contrast_and_tone_mapping",
    "material_response_separation",
    "material_roughness_independence",
    "contact_shadow_and_reflection_causality",
    "no_render_outline_or_oversharpen_halo",
    "no_repeating_or_cross_material_artifact",
    "no_game_cinematic_render_signature",
    "performance_observation_not_promo_pose",
    "live_action_polish_ceiling",
)
LIVE_ACTION_QUALITY_CHECKS = (
    "photographic_event_plausibility",
    "skin_specular_topology",
    "skin_tone_continuity",
    "eye_hair_and_edge_behavior",
    "material_response_separation",
    "material_roughness_independence",
    "detail_integrity_without_smear",
    "no_repeating_or_cross_material_artifact",
    "lighting_and_contact_causality",
    "finite_dynamic_range_and_exposure_tradeoff",
    "set_and_object_causality",
    "performance_observation_not_promo_pose",
    "brief_polish_fit",
)
TEMPORAL_TAKE_CHECKS = (
    "identity_and_body_consistency",
    "background_consistency",
    "texture_crawl_and_flicker",
    "morphing_and_ghost_limbs",
    "lighting_and_exposure_continuity",
    "environment_advection_and_material_response",
    "camera_path_conformance",
    "focus_and_motion_blur",
    "rolling_shutter_and_frame_blending",
    "start_end_frame_match",
)
LOCATION_VIEWS = ["front_wide", "left_three_quarter_wide", "right_three_quarter_wide", "reverse_wide"]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tiny_png_bytes(
    rgb: tuple[int, int, int] = (180, 180, 180),
    *,
    width: int = 2,
    height: int = 2,
) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = bytes([0]) + bytes(rgb) * width
    scanlines = row * height
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b"")


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def image_prompt(
    *,
    story_moment: str = "A documented story moment.",
    blocking: str = "Causal blocking.",
    strategy: str = IMAGE_STRATEGY,
    human_subject: bool = True,
) -> str:
    headings = IMAGE_HEADINGS
    approved_facts = (
        "Use only the approved courier identity roots, role-physique-char-hero-v1, "
        "state-char-hero-baseline, state-workshop-day and prop-state-table-baseline."
        if human_subject
        else "Use only approved location world loc-workshop, state-workshop-day and the fixed red worktable spatial anchor. No people."
    )
    material_response = (
        "Existing north window and desk lamp shape normal dry skin; hair, cloth, concrete, steel and glass retain distinct roughness and reflection."
        if human_subject
        else "Existing north window and desk lamp shape concrete, steel, glass and wood with separate roughness and reflection; no decorative fill light."
    )
    middle_tone_anchor = "the courier's face" if human_subject else "the mid-gray painted wall"
    exclusions = (
        "No painterly smear or patch smear. No wax skin, plastic skin, CG render, animated rendering, game-cinematic rendering or synthetic glossy skin. No repeating swirl or cross-material texture. No rendered outline, oversharpen halo or HDR halo."
        if human_subject
        else "No painterly smear or patch smear. No illustration, animation, CG/PBR render or game-environment finish. No repeating swirl or cross-material texture. No rendered outline, oversharpen halo or HDR halo."
    )
    bodies = {
        "PHOTOGRAPHIC EVENT": story_moment + " A physically present production camera records an observed event.",
        "APPROVED IDENTITY WORLD AND STATE": approved_facts,
        "PHYSICAL CAMERA AND BLOCKING": "Approved 16:9 frame and reachable aisle camera. " + blocking,
        "SOURCE LIGHT AND MATERIAL RESPONSE": material_response,
        "FOCUS EXPOSURE AND CONTINGENCY": (
            "Focus on the narrative plane and accept source-caused falloff and partial occlusion. Finite scene-referred capture: working latitude 14 stops against 15 stops of scene contrast. "
            f"Exposure priority: protect_subject_and_practicals; middle-tone anchor: {middle_tone_anchor}. "
            "Allowed clipping: the lamp filament core. Allowed shadow loss: the deepest shelf gap. No local tone mapping; no multi-exposure HDR merge."
        ),
        "EXCLUSIONS": exclusions,
    }
    lines = ["Use case: live-action production image", f"Prompt strategy: {strategy}", ""]
    for heading in headings:
        lines.extend([heading, bodies[heading], ""])
    return "\n".join(lines)


def format_position(position: dict[str, Any]) -> str:
    return f"({float(position['x']):.1f}, {float(position['y']):.1f}, {float(position['z']):.1f}) m"


def spatial_prompt_block(shot: dict[str, Any], spatial_map: dict[str, Any]) -> str:
    marks = {mark["id"]: mark for mark in spatial_map["marks"]}
    anchor = spatial_map["primary_anchor"]
    coordinate = spatial_map["coordinate_system"]
    camera = marks[shot["camera_mark_id"]]
    projection = shot["anchor_projection"]
    distance = f"{float(projection['distance_m']):.1f} m"
    lines = [
        f"Spatial map {spatial_map['id']}; scene state {spatial_map['scene_state_id']}.",
        f"Primary anchor {anchor['asset_id']}: origin at its ground-contact center (0.0, 0.0, 0.0) m; orientation {anchor['orientation']}.",
        f"Set-fixed axes: +X {coordinate['x_positive_label']}; +Y {coordinate['y_positive_label']}; +Z {coordinate['z_positive_label']}.",
        f"Camera {camera['id']}: {format_position(camera['position_m'])}; facing {camera['facing']}; {camera['relation_to_anchor']}; {distance} from {anchor['asset_id']}.",
    ]
    for asset_id in sorted(shot["subject_mark_ids"]):
        mark = marks[shot["subject_mark_ids"][asset_id]]
        lines.append(
            f"Subject {asset_id} at {mark['id']}: {format_position(mark['position_m'])}; facing {mark['facing']}; {mark['relation_to_anchor']}."
        )
    lines.append(
        f"Anchor projection: {projection['visibility']}; screen region {projection['screen_region']}; "
        f"camera-relative direction {projection['direction_from_camera']}; set-fixed direction "
        f"{projection['set_fixed_direction']}; {projection['set_fixed_relation']}; distance {distance}."
    )
    lines.append(f"Depth order, camera-near to far: {' -> '.join(shot['depth_order'])}.")
    return "\n".join(lines)


def video_prompt(shot: dict[str, Any], spatial_map: dict[str, Any]) -> str:
    lines: list[str] = []
    for heading in VIDEO_HEADINGS:
        if heading == "GLOBAL STYLE":
            temporal = shot["temporal_capture"]
            body = (
                "Original live-action grounded observational drama in 16:9 with no baked black bars. "
                f"Capture {temporal['capture_fps']} fps at {temporal['shutter_angle']} degree shutter with 1/48 second exposure and deliver {temporal['delivery_fps']} fps. "
                "Clean source-led digital response. No animation or CG/PBR finish. No game-cinematic rendering. "
                "No synthetic glossy skin. No smear, repeated texture or unmotivated rim light."
            )
        elif heading == "SCENE":
            body = "Inside a functioning concrete repair workshop in clear indoor air, a courier notices that an opened case has been disturbed."
        elif heading == "CHARACTERS":
            body = (
                "The approved adult courier keeps the same face, hairline, athletic body geometry, workwear and dry natural skin. "
                "Task-led behavior, ordinary breathing and grounded weight transfer."
            )
        elif heading == "LOCATION":
            body = spatial_prompt_block(shot, spatial_map)
        elif heading == "FIRST FRAME AND BLOCKING":
            signatures = [lock["proportion_signature_id"] for lock in shot["body_geometry_locks"].values()]
            physiques = [lock["role_physique_brief_id"] for lock in shot["body_geometry_locks"].values()]
            body = (
                "The courier stands weight-bearing on the declared floor mark, oriented toward the opened case; five fingers per visible hand. "
                "Preserve the approved body signature and role-fit physique: " + ", ".join(signatures + physiques) + "."
            )
        elif heading == "Shot 1":
            body = (
                "She stops, notices the broken seal, turns her eyes and head toward the case, then holds. "
                "Her expression changes only after seeing the seal; end on a settled attentive posture."
            )
        elif heading == "OPTICS":
            body = "Moderate focal length, focus begins on her eyes and transfers naturally toward the broken seal; protect practical highlights."
        elif heading == "CAMERA":
            plan = shot["camera_move_plan"]
            blur = shot["motion_blur_plan"]
            body = (
                f"{plan['primitive']} camera on {plan['support']} from {plan['start_camera_mark_id']} to {plan['end_camera_mark_id']}; "
                f"zero translation, then settle for {plan['settle_hold_s']} seconds. "
                f"{blur['direction'] or 'No directional blur'}; static workshop edges remain stable; no frame blending, ghost limbs or jelly deformation."
            )
        elif heading == "PHYSICS":
            body = "Natural balance, inertia and garment response; hands maintain causal contact and the case stays grounded on the table."
        elif heading == "LIGHTING":
            body = (
                "The documented broad north window is the skin key source from camera-left; dry skin keeps a broad, "
                "low-intensity skin specular extent. Use restrained local contrast and scene-referred tone mapping; "
                "skin, hair, cotton and metal retain independent material roughness responses. "
                "Finite scene-referred capture: working latitude 14.0 stops, 6.0 above and 8.0 below middle gray, against estimated scene contrast 15.0 stops. "
                "Exposure priority: protect_skin_and_practicals; middle-tone anchor: the courier's face. Highlights roll gradually; allowed clipping: the lamp filament core. "
                "Shadows meet a firm floor; allowed shadow loss: the deepest unlit shelf gap. Never locally tone-map every region into equal clarity; no multi-exposure HDR merge."
            )
        elif heading == "AUDIO":
            body = "Quiet workshop room tone, cloth movement and one shoe stop on concrete; no invented dialogue."
        else:
            body = f"Concrete visible instruction for {heading.lower()}."
        lines.extend([heading, body, ""])
    return "\n".join(lines)


def qa() -> dict[str, Any]:
    return {"hard_failures": [], "soft_notes": [], "checked_at": TIMESTAMP}


def photographic_qa(mode: str, *, passed: bool = True) -> dict[str, Any]:
    return {
        "mode": mode,
        "reconstruction_pass": passed,
        "checks": {name: "pass" if passed else "fail" for name in PHOTO_CHECKS},
        "hard_failures": [] if passed else ["reconstruction failed"],
        "notes": [],
        "checked_at": TIMESTAMP,
    }


def authenticity_qa(
    mode: str,
    *,
    passed: bool = True,
    user_decision: str = "approved",
    attempt_index: int = 1,
    escalation: str = "none",
) -> dict[str, Any]:
    return {
        "mode": mode,
        "attempt_index": attempt_index,
        "checks": {name: "pass" if passed else "fail" for name in AUTH_CHECKS},
        "ai_smell_verdict": "pass" if passed else "fail",
        "hard_failures": [] if passed else ["visible AI prior"],
        "notes": [],
        "checked_at": TIMESTAMP,
        "user_decision": user_decision,
        "user_decided_at": TIMESTAMP if user_decision != "pending" else "",
        "escalation": escalation,
    }


def texture_qa(
    mode: str = "clean_authority",
    *,
    passed: bool = True,
    user_decision: str = "approved",
    attempt_index: int = 1,
    escalation: str = "none",
) -> dict[str, Any]:
    return {
        "mode": mode,
        "attempt_index": attempt_index,
        "scales_checked": {
            "thumbnail": passed,
            "fit": passed,
            "100_percent": passed,
            "200_percent": passed,
        },
        "checks": {name: "pass" if passed else "fail" for name in TEXTURE_CHECKS},
        "verdict": "pass" if passed else "fail",
        "cross_material_pairs": [
            {"material_a": "skin", "material_b": "fabric", "same_repeating_texture": False}
        ],
        "hard_failures": [] if passed else ["repeating texture or smear"],
        "notes": [],
        "checked_at": TIMESTAMP,
        "user_decision": user_decision,
        "user_decided_at": TIMESTAMP if user_decision != "pending" else "",
        "escalation": escalation,
    }


def geometry_qa(
    *,
    human: bool,
    mode: str = "narrative_frame",
    passed: bool = True,
    user_decision: str = "approved",
    projection_class: str = "perspective_narrative",
) -> dict[str, Any]:
    if not human:
        return {
            "mode": "not_applicable",
            "reference_signature_id": "",
            "projection_class": "not_applicable",
            "views_checked": [],
            "checks": {name: "not_applicable" for name in GEOMETRY_CHECKS},
            "measurements_compared": [],
            "verdict": "not_applicable",
            "hard_failures": [],
            "notes": [],
            "checked_at": "",
        }
    return {
        "mode": mode,
        "reference_signature_id": "prop-char-hero-v1",
        "projection_class": projection_class,
        "views_checked": ["portrait_front", "full_front", "full_back"],
        "checks": {name: "pass" if passed else "fail" for name in GEOMETRY_CHECKS},
        "measurements_compared": [
            {"field": "head_to_body", "expected": 0.137, "observed": 0.137 if passed else 0.19, "tolerance": 0.02, "pass": passed}
        ],
        "verdict": "pass" if passed else "fail",
        "hard_failures": [] if passed else ["proportion drift"],
        "notes": [],
        "checked_at": TIMESTAMP,
    }


def live_action_surface_qa(
    *,
    passed: bool = True,
    user_decision: str = "approved",
    mode: str = "authority_reference",
) -> dict[str, Any]:
    return {
        "mode": mode,
        "scales_checked": {
            "thumbnail": True,
            "fit": True,
            "100_percent": True,
            "200_percent": True,
        },
        "checks": {name: "pass" if passed else "fail" for name in LIVE_ACTION_SURFACE_CHECKS},
        "verdict": "pass" if passed else "fail",
        "hard_failures": [] if passed else ["animation or smeared surface prior"],
        "notes": [],
        "checked_at": TIMESTAMP,
        "user_decision": user_decision,
        "user_decided_at": TIMESTAMP if user_decision != "pending" else "",
    }


def approval_qa(check_names: tuple[str, ...]) -> dict[str, Any]:
    return {
        "checks": {name: True for name in check_names},
        "hard_failures": [],
        "notes": [],
        "checked_at": TIMESTAMP,
        "reviewer": "codex-structural",
    }


def live_action_quality_qa(*, human: bool, narrative: bool = False, passed: bool = True) -> dict[str, Any]:
    return {
        "mode": "narrative_frame" if narrative else "authority_reference",
        "scales_checked": {
            "thumbnail": passed,
            "fit": passed,
            "100_percent": passed,
            "200_percent": passed,
        },
        "checks": {name: "pass" if passed else "fail" for name in LIVE_ACTION_QUALITY_CHECKS},
        "positive_evidence": {
            name: f"Visible source-grounded evidence for {name.replace('_', ' ')}."
            for name in LIVE_ACTION_QUALITY_CHECKS
        },
        "material_pairs": [
            {
                "material_a": "skin" if human else "paint",
                "material_b": "fabric" if human else "metal",
                "same_repeating_texture": not passed,
            }
        ],
        "skin_surface_state": "natural_dry" if human else "not_applicable",
        "skin_state_cause": "ordinary clean indoor condition" if human else "",
        "skin_state_regions": ["face and hands"] if human else [],
        "dynamic_range_evidence": {
            "exposure_priority": "protect_skin_and_practicals" if human and narrative else "protect_skin" if human else "balanced_middle_tones",
            "middle_tone_anchor": (
                "The face and neutral garment sit in a stable middle-tone band."
                if human
                else "The primary painted set or object surface sits in a stable middle-tone band."
            ),
            "highlight_loss_or_rolloff": (
                "The practical core approaches clipping while its housing retains a source-shaped transition."
                if narrative
                else "The white reference field or bright installed source approaches the upper diffuse range without local recovery."
            ),
            "shadow_loss_or_floor": (
                "The deepest unlit shelf gap loses texture instead of receiving global HDR lift."
                if narrative
                else "The deepest garment fold or construction joint may merge without global HDR lift."
            ),
            "global_tone_mapping_detected": False,
        },
        "verdict": "pass" if passed else "fail",
        "hard_failures": [] if passed else ["oil film, smear or synthetic rendering"],
        "notes": [],
        "reviewer": "codex-visual",
        "checked_at": TIMESTAMP,
    }


def provenance(kind: str, *, character: bool = False) -> dict[str, Any]:
    return {
        "kind": kind,
        "source_note": "User-controlled reference or an approved generated project anchor.",
        "rights_confirmed": True,
        "identity_consent_confirmed": character,
    }


def reference_coverage(asset_type: str) -> dict[str, Any] | None:
    if asset_type == "character_identity_inspector":
        return {
            "policy": "identity_single_solve_inspector",
            "required_views": CHARACTER_VIEWS,
            "present_views": CHARACTER_VIEWS,
            "same_subject_or_geography_pass": True,
            "background_policy": "pure_white",
            "notes": ["One ImageGen call solved the same fictional identity across the complete official two-row sheet."],
        }
    if asset_type == "character_master":
        return {
            "policy": "character_turnaround",
            "required_views": CHARACTER_VIEWS,
            "present_views": CHARACTER_VIEWS,
            "same_subject_or_geography_pass": True,
            "background_policy": "pure_white",
            "notes": ["Same fictional identity across all seven views."],
        }
    if asset_type == "location_master":
        return {
            "policy": "single_view",
            "required_views": ["establishing_wide"],
            "present_views": ["establishing_wide"],
            "same_subject_or_geography_pass": True,
            "background_policy": "on_location_neutral",
            "notes": ["One approved geography seed; multi-axis use requires expanded coverage."],
        }
    return None


def profile(profile_id: str, status: str, look_id: str, variant: str) -> dict[str, Any]:
    strategies = {
        "a": {
            "observer_role": "quiet visitor at the workshop doorway",
            "camera_access": "near-side aisle beside the table",
            "operator_constraint": "shoulder operator cannot cross the courier's work path",
            "allowed_contingency": "a shelf edge may partially occlude the open case",
            "off_frame_context": "another worker continues sorting metal parts behind camera",
            "focal": "moderate focal length from conversational distance",
            "focus": "gradual falloff from eyes to the opened case",
            "support": "restrained shoulder",
            "inertia": "small delayed correction after the courier stops",
            "bias": -0.33,
            "sources": ["north workshop window", "existing desk lamp"],
            "practicals": ["existing desk lamp"],
        },
        "b": {
            "observer_role": "supervisor watching from the far service corner",
            "camera_access": "fixed corner behind a shelving upright",
            "operator_constraint": "tripod footprint cannot block the service door",
            "allowed_contingency": "the courier can drift toward the edge of frame",
            "off_frame_context": "the service door opens intermittently outside frame",
            "focal": "longer observational focal length across the workshop",
            "focus": "hold the courier, allow the foreground shelf to remain soft",
            "support": "locked tripod",
            "inertia": "no reframing after the action begins",
            "bias": 0.0,
            "sources": ["overhead fluorescent spill", "existing desk lamp"],
            "practicals": ["existing desk lamp", "overhead fluorescent strip"],
        },
        "c": {
            "observer_role": "coworker entering immediately behind the courier",
            "camera_access": "narrow moving route through the central aisle",
            "operator_constraint": "handheld operator yields to people and work carts",
            "allowed_contingency": "brief foreground passage and imperfect headroom are allowed",
            "off_frame_context": "a rolling cart approaches from camera right",
            "focal": "wider focal length at close working distance",
            "focus": "human pull that briefly lags when she turns toward the case",
            "support": "handheld body rig",
            "inertia": "footstep-linked weight and a settle after stopping",
            "bias": -0.67,
            "sources": ["north workshop window", "open service doorway"],
            "practicals": [],
        },
    }
    strategy = strategies[variant]
    return {
        "id": profile_id,
        "status": status,
        "scope": "project",
        "scene_ids": [],
        "story_rationale": f"A distinct physically motivated witness strategy for candidate {variant}.",
        "return_to_baseline": "This is a controlled project-baseline candidate.",
        "cinematic_treatment_id": f"treat-base-{variant}",
        "format_plan_id": "format-plan-main-16x9",
        "medium_signature_id": "",
        "capture_circumstance": {
            key: strategy[key]
            for key in ("observer_role", "camera_access", "operator_constraint", "allowed_contingency", "off_frame_context")
        },
        "capture": {
            "medium": "digital",
            "format_class": "Super 35",
            "imaging_width_mm": 27.99,
            "camera_reference": "",
            "behavior": {
                "highlight_rolloff": "gradual practical-light shoulder",
                "shadow_floor": "unlit recesses stay dark without gray HDR lift",
                "color_separation": "restrained but distinct material colors",
                "skin_response": "natural tonal variation without smoothing, pore enhancement or synthetic texture",
                "acutance": "local detail without edge enhancement",
            },
        },
        "optics": {
            "projection": "spherical",
            "lens_reference": "",
            "focal_strategy": strategy["focal"],
            "contrast": "medium contrast",
            "focus_falloff": strategy["focus"],
            "flare": "only if a documented source reaches the lens",
            "distortion": "low, distance-consistent perspective distortion",
            "breathing": "small focus-linked change only during a rack",
            "bokeh": "source-shaped defocus, not uniform cream blur",
            "desqueeze_ratio": None,
            "delivery_crop": "",
        },
        "exposure": {
            "rating": "working sensitivity selected for available room light",
            "bias_stops": strategy["bias"],
            "highlight_priority": "retain existing lamp shape and face detail",
            "shadow_policy": "accept real falloff in corners instead of lifting everything",
        },
        "motion": {
            "base_fps": 24,
            "base_shutter_angle": 180,
            "support": strategy["support"],
            "inertia": strategy["inertia"],
        },
        "lighting": {
            "motivated_sources": strategy["sources"],
            "contrast_strategy": "preserve source direction and room geography",
            "fill_strategy": "only existing wall bounce; no source-free beauty fill",
            "practicals": strategy["practicals"],
            "atmosphere": "ordinary clear occupied air",
        },
        "pipeline": {
            "white_balance": "source-led neutral balance",
            "transform_or_stock": "restrained display transform",
            "palette_response": "separated worn paint, skin and metal",
            "black_level": "firm neutral black",
            "highlight_color": "source-specific daylight and lamp color",
        },
        "texture": {
            "grain_or_noise": "fine exposure-dependent texture only",
            "halation": "none unless an intense source justifies it",
            "gate_weave": "none",
            "artifact_budget": "no global overlays or decorative aberration",
        },
        "look_test_asset_ids": [look_id],
        "approved_look_test_id": look_id if status == "approved" else "",
        "approval_gate_id": "review-foundation-001",
    }


def treatment(variant: str, status: str) -> dict[str, Any]:
    grammars = {
        "a": ("quiet conversational witness", "stable negative space and practical occlusions", "restrained shoulder inertia", "unforced four-second observation"),
        "b": ("distant supervisory witness", "compressed layers through a service corner", "locked tripod", "patient unbroken observation"),
        "c": ("coworker entering with the courier", "close wide perspective with imperfect headroom", "footstep-led handheld", "reactive cadence with a brief focus lag"),
    }
    witness, composition, mobility, cadence = grammars[variant]
    return {
        "id": f"treat-base-{variant}",
        "status": status,
        "scope": "project",
        "scene_ids": [],
        "family": "naturalistic_dialogue",
        "thesis": f"Candidate {variant} observes the discovery as a physically present worker rather than a polished promotional still.",
        "narrative_distance": witness,
        "camera_witness": witness,
        "composition_grammar": composition,
        "optical_spatial_behavior": "distance-led perspective with readable workshop depth and no generic shallow-focus template",
        "motivated_light": "north window and existing practicals only",
        "color_pipeline": "clean source-led digital response with no global texture overlay",
        "camera_mobility": mobility,
        "temporal_cadence": cadence,
        "environmental_medium": "clear occupied interior air",
        "polish_ceiling": "observational drama; no beauty-light or commercial sheen",
        "named_reference_policy": "observable_translation_only",
        "observable_reference_translation": ["camera witness", "source-led lighting", "spatially causal composition"],
        "return_rule": "Remain on the approved project baseline unless a scene-level story change is approved.",
        "approval_gate_id": "review-foundation-001",
    }


class ProjectFixture:
    def __init__(self, root: Path) -> None:
        result = run_cli(
            "init",
            "--root",
            str(root),
            "--title",
            "Validator Feature Test",
            "--slug",
            "validator-feature-test",
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout)
        self.path = root / "validator-feature-test"
        self.identity_inspector_id = "char-hero-inspector--v001"
        self.identity_root_ids = [self.identity_inspector_id]
        self.identity_crop_ids = [
            "char-hero-full-front--v001",
            "char-hero-full-left-profile--v001",
            "char-hero-full-right-profile--v001",
            "char-hero-full-back--v001",
            "char-hero-portrait-front--v001",
            "char-hero-portrait-left-profile--v001",
            "char-hero-portrait-right-profile--v001",
        ]
        project_path = self.path / "project.json"
        project = json.loads(project_path.read_text(encoding="utf-8"))
        project["scenes"] = [
            {
                "id": "sc-010",
                "order": 10,
                "title": "Workshop discovery",
                "summary": "A courier notices that a sealed case has already been opened.",
                "capture_profile_id": "",
                "format_plan_id": "format-plan-main-16x9",
                "environmental_state_id": "env-workshop-clear",
                "scene_state_id": "state-workshop-day",
                "spatial_map_id": "spatial-workshop-day",
                "primary_anchor_asset_id": "prop-red-worktable--v001",
            }
        ]
        project["updated_at"] = TIMESTAMP
        write_json(project_path, project)
        self.approved_paths: dict[str, str] = {}
        self._build_assets()
        self._build_identities_and_world_state()
        self._build_spatial()
        self._build_cinematography()
        self._build_shot()
        self._build_sequences()
        self._build_quality_candidates_reviews()

    def _file(self, relative: str, content: str = "fixture") -> None:
        path = self.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".png" and content == "fixture":
            path.write_bytes(tiny_png_bytes())
        else:
            path.write_text(content, encoding="utf-8")

    def _asset(
        self,
        *,
        asset_id: str,
        role: str,
        asset_type: str,
        status: str,
        generator: str,
        mode: str,
        references: list[str],
        scenes: list[str],
        photo_mode: str,
        auth_mode: str,
        user_decision: str,
        provenance_kind: str,
        profile_id: str = "",
        comparison_id: str = "",
        derived_from: str = "",
        prompt_path: str = "",
        candidate_path: str = "",
        approved_path: str = "",
        scene_state_id: str = "",
        view_role: str = "",
        view_side: str = "",
        spatial_map_id: str = "",
        primary_anchor_asset_id: str = "",
        prompt_strategy_id: str | None = None,
        identity_pack_id: str = "",
        character_state_id: str = "",
        location_world_id: str = "",
        location_state_id: str = "",
        root_reference_ids: list[str] | None = None,
        state_delta: dict[str, Any] | None = None,
        surface_policy: str = "clean_authority",
        identity_view_role: str = "",
        medium_signature_id: str = "",
        localized_story_evidence: list[str] | None = None,
        pose_contact_anchor_ids: list[str] | None = None,
        approval_gate_id: str | None = None,
        quality_profile_id: str = "quality-main",
    ) -> dict[str, Any]:
        if prompt_strategy_id is None and generator == "builtin-imagegen":
            strategy_by_type = {
                "character_identity_inspector": "image2-live-action-identity-inspector-v1.6",
                "character_face_anchor": "image2-live-action-character-face-v1.6",
                "character_body_anchor": "image2-live-action-character-body-v1.6",
                "character_identity_view": "image2-live-action-identity-view-v1.6",
                "character_variant": "image2-live-action-character-state-v1.6",
                "character_state": "image2-live-action-character-state-v1.6",
                "location_master": "image2-live-action-location-v1.6",
                "location_variant": "image2-live-action-location-v1.6",
                "location_plate": IMAGE_STRATEGY,
                "prop": "image2-live-action-object-v1.6",
                "prop_state": "image2-live-action-object-v1.6",
                "pose_contact_anchor": "image2-live-action-pose-contact-v1.6",
                "look_test": IMAGE_STRATEGY,
                "keyframe": IMAGE_STRATEGY,
                "storyboard": IMAGE_STRATEGY,
            }
            prompt_strategy_id = strategy_by_type.get(asset_type, IMAGE_STRATEGY)
        root_reference_ids = list(root_reference_ids or [])
        state_delta = dict(state_delta or {})
        localized_story_evidence = list(localized_story_evidence or [])
        pose_contact_anchor_ids = list(pose_contact_anchor_ids or [])
        human_surface = asset_type in {
            "character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_identity_view", "character_master",
            "character_variant", "character_state", "pose_contact_anchor",
        } or bool(identity_pack_id)
        narrative_surface = asset_type in {"look_test", "location_plate", "storyboard", "keyframe", "key_art"}
        if human_surface and narrative_surface:
            dynamic_range_plan = {
                "policy": "finite_scene_referred",
                "working_latitude_stops": 14.0,
                "upper_latitude_stops": 6.0,
                "lower_latitude_stops": 8.0,
                "scene_contrast_stops_estimate": 15.0,
                "exposure_priority": "protect_skin_and_practicals",
                "middle_gray_anchor": "the courier's face and neutral gray work shirt",
                "highlight_behavior": "the desk-lamp housing rolls gradually while its filament core may clip",
                "shadow_behavior": "unlit shelf gaps fall below the texture floor without gray HDR lift",
                "allowed_clipping": ["small desk-lamp filament core"],
                "allowed_shadow_loss": ["deepest unlit rear-shelf gap"],
                "local_tone_mapping": False,
                "multi_exposure_hdr": False,
                "narrative_reason": "Keep attention on the observed person rather than equalizing the entire set.",
            }
        elif human_surface:
            dynamic_range_plan = {
                "policy": "finite_scene_referred",
                "working_latitude_stops": 14.0,
                "upper_latitude_stops": 6.0,
                "lower_latitude_stops": 8.0,
                "scene_contrast_stops_estimate": 5.0,
                "exposure_priority": "protect_skin",
                "middle_gray_anchor": "the face and neutral garment",
                "highlight_behavior": "the pure-white field approaches the upper diffuse range without flattening facial planes",
                "shadow_behavior": "the deepest garment folds may merge while anatomy remains legible",
                "allowed_clipping": [],
                "allowed_shadow_loss": [],
                "local_tone_mapping": False,
                "multi_exposure_hdr": False,
                "narrative_reason": "A low-contrast identity reference protects skin and geometry without artificial HDR clarity.",
            }
        else:
            dynamic_range_plan = {
                "policy": "finite_scene_referred",
                "working_latitude_stops": 14.0,
                "upper_latitude_stops": 6.0,
                "lower_latitude_stops": 8.0,
                "scene_contrast_stops_estimate": 12.0,
                "exposure_priority": "balanced_middle_tones",
                "middle_gray_anchor": "the primary painted set or object surface",
                "highlight_behavior": "bright window or installed-source cores approach clipping before the set is globally compressed",
                "shadow_behavior": "unlit construction joints may fall below the texture floor",
                "allowed_clipping": ["small visible practical-source core when present"],
                "allowed_shadow_loss": ["deepest unlit construction joint"],
                "local_tone_mapping": False,
                "multi_exposure_hdr": False,
                "narrative_reason": "Preserve readable geography without making every bright and dark surface equally clear.",
            }
        if asset_type in {"look_test", "location_plate", "storyboard", "keyframe", "key_art"} and surface_policy == "clean_authority":
            surface_policy = "clean_narrative"
        active_output = approved_path if status in {"approved", "superseded"} else candidate_path
        reference_inputs = []
        for reference_id in references:
            reference_path = self.approved_paths.get(reference_id, "")
            reference_inputs.append(
                {
                    "asset_id": reference_id,
                    "relative_path": reference_path,
                    "sha256": hashlib.sha256((self.path / reference_path).read_bytes()).hexdigest() if reference_path else "0" * 64,
                }
            )
        generated = generator == "builtin-imagegen"
        deterministic_crop = generator == "deterministic-crop"
        if approval_gate_id is None:
            approval_gate_id = (
                "review-seq-workshop-day-001"
                if asset_type in {"location_plate", "storyboard", "keyframe", "key_art"}
                else "review-foundation-001"
            )
        candidate_set_id = f"cset-{asset_id}" if generated else ""
        generation = {
            "backend": "builtin-imagegen" if generated else "deterministic-crop" if deterministic_crop else "provided",
            "reproducibility_class": "workflow_only" if generated else "source_exact",
            "pixel_reproducible": not generated,
            "operation": mode,
            "prompt_sha256": hashlib.sha256((self.path / prompt_path).read_bytes()).hexdigest() if prompt_path else "",
            "reference_order": list(references),
            "reference_inputs": reference_inputs,
            "output": {
                "relative_path": active_output,
                "sha256": hashlib.sha256((self.path / active_output).read_bytes()).hexdigest() if active_output else "",
                "width_px": 1920 if active_output else 0,
                "height_px": 1080 if active_output else 0,
                "color_mode": "RGB" if active_output else "",
                "mime_type": "image/png" if active_output else "",
            },
            "software_agent": (
                "Codex built-in ImageGen fixture" if generated
                else "cinematic-ai-director deterministic PNG cropper" if deterministic_crop
                else "user-provided fixture"
            ),
        }
        asset = {
            "id": asset_id,
            "role": role,
            "type": asset_type,
            "status": status,
            "revision": 1,
            "generator": generator,
            "mode": mode,
            "derived_from": derived_from,
            "replaces_asset_id": "",
            "reference_asset_ids": references,
            "scene_ids": scenes,
            "capture_profile_id": profile_id,
            "comparison_set_id": comparison_id,
            "scene_state_id": scene_state_id,
            "view_role": view_role,
            "view_side": view_side,
            "identity_view_role": identity_view_role,
            "identity_background_policy": "pure_white" if asset_type in {"character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_identity_view"} else "",
            "spatial_map_id": spatial_map_id,
            "primary_anchor_asset_id": primary_anchor_asset_id,
            "constraints": [LOCKED_BLOCKING] if comparison_id else ["single authoritative production role"],
            "prompt_path": prompt_path,
            "candidate_path": candidate_path,
            "approved_path": approved_path,
            "prompt_strategy_id": prompt_strategy_id if generator == "builtin-imagegen" else "",
            "calibration_family": "image2-live-action-evidence-v1.6" if generator == "builtin-imagegen" else "",
            "candidate_set_id": candidate_set_id,
            "quality_profile_id": quality_profile_id,
            "approval_gate_id": approval_gate_id,
            "identity_pack_id": identity_pack_id,
            "character_state_id": character_state_id,
            "location_world_id": location_world_id,
            "location_state_id": location_state_id,
            "root_reference_ids": root_reference_ids,
            "state_delta": state_delta,
            "surface_policy": surface_policy,
            "medium_signature_id": medium_signature_id,
            "localized_story_evidence": localized_story_evidence,
            "material_response_contract": {
                "skin": "natural source-led tonal response without a synthetic surface film" if human_surface else "not applicable; no visible human skin",
                "hair": "separate strands and clumps governed by real light and gravity" if human_surface else "not applicable",
                "fabric": "weave scale remains distinct from skin and hard surfaces",
                "hard_surfaces": "construction-specific roughness and reflections without copied noise",
                "skin_presence": "present" if human_surface else "absent",
                "skin_key_source": "the documented broad north window or neutral reference panel" if human_surface else "",
                "skin_key_source_size": "broad source larger than the visible face" if human_surface else "",
                "skin_key_direction": "camera-left/front, consistent with the documented source" if human_surface else "",
                "skin_fill_sources": ["low-intensity room bounce from documented pale surfaces"] if human_surface else [],
                "skin_specular_behavior": "broad low-intensity highlights whose extent follows the declared source" if human_surface else "",
                "skin_wetness_state": "natural_dry" if human_surface else "not_applicable",
                "local_contrast_policy": "restrained source-driven local contrast; preserve ordinary facial tone transitions",
                "tone_mapping_policy": "scene-referred highlight rolloff without clarity or HDR shaping",
                "material_roughness_separation": "skin, hair, fabric, glass, paint and metal retain independent roughness responses",
                "color_contamination_sources": ["existing desk lamp at physically reached surfaces"] if human_surface else [],
                "performance_staging_policy": "task-led observational action with unforced posture" if human_surface else "not_applicable",
            },
            "dynamic_range_plan": dynamic_range_plan,
            "pose_contact_anchor_ids": pose_contact_anchor_ids,
            "reference_provenance": provenance(
                provenance_kind,
                character=asset_type in {
                    "character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_identity_view", "character_variant", "character_state", "pose_contact_anchor"
                },
            ),
            "reference_coverage": reference_coverage(asset_type),
            "qa": qa(),
            "photographic_qa": photographic_qa(photo_mode),
            "authenticity_qa": authenticity_qa(auth_mode, user_decision=user_decision),
            "texture_qa": texture_qa(surface_policy, user_decision=user_decision),
            "geometry_qa": geometry_qa(
                human=asset_type in {
                    "character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_identity_view",
                    "character_variant", "character_state", "pose_contact_anchor"
                } or bool(identity_pack_id),
                mode=(
                    "identity_authority" if asset_type in {"character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_identity_view"}
                    else "state_reference" if asset_type in {"character_variant", "character_state"}
                    else "narrative_frame"
                ),
                projection_class=(
                    "neutral_front_or_back" if identity_view_role in {"portrait_front", "full_front", "full_back"}
                    else "side_or_three_quarter" if identity_view_role
                    else "perspective_narrative"
                ),
                user_decision=user_decision,
            ),
            "live_action_quality_qa": live_action_quality_qa(
                human=human_surface,
                narrative=asset_type in {"look_test", "location_plate", "storyboard", "keyframe", "key_art"},
            ),
            "generation_provenance": generation,
            "created_at": TIMESTAMP,
        }
        if generated:
            asset["calibration_family"] = "image2-live-action-evidence-v1.6"
        if approved_path:
            self.approved_paths[asset_id] = approved_path
        return asset

    def _build_assets(self) -> None:
        paths = {
            "char-hero-inspector--v001": "assets/characters/identity-inspectors/char-hero-inspector--v001--approved.png",
            "char-hero-full-front--v001": "assets/characters/identity-views/char-hero-full-front--v001--approved.png",
            "char-hero-full-left-profile--v001": "assets/characters/identity-views/char-hero-full-left-profile--v001--approved.png",
            "char-hero-full-right-profile--v001": "assets/characters/identity-views/char-hero-full-right-profile--v001--approved.png",
            "char-hero-full-back--v001": "assets/characters/identity-views/char-hero-full-back--v001--approved.png",
            "char-hero-portrait-front--v001": "assets/characters/identity-views/char-hero-portrait-front--v001--approved.png",
            "char-hero-portrait-left-profile--v001": "assets/characters/identity-views/char-hero-portrait-left-profile--v001--approved.png",
            "char-hero-portrait-right-profile--v001": "assets/characters/identity-views/char-hero-portrait-right-profile--v001--approved.png",
            "char-hero-state-baseline--v001": "assets/characters/states/char-hero-state-baseline--v001--approved.png",
            "loc-workshop--v001": "assets/locations/loc-workshop--v001--approved.png",
            "prop-red-worktable--v001": "assets/props/prop-red-worktable--v001--approved.png",
            "prop-red-worktable-state-baseline--v001": "assets/props/prop-red-worktable-state-baseline--v001--approved.png",
        }
        for asset_id, relative in paths.items():
            if asset_id == self.identity_inspector_id:
                path = self.path / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tiny_png_bytes((245, 245, 245), width=8, height=4))
            else:
                self._file(relative)
        identity_delta = {
            "wardrobe": "plain navy work shirt and charcoal work trousers",
            "hair_state": "dry hair tied low",
            "age_stage": "adult baseline",
            "injury": "none",
            "wetness": "none",
            "dirt": "none",
            "makeup": "none",
            "story_props": "none",
        }
        location_delta = {
            "time": "day",
            "weather": "dry",
            "dressing": "occupied workshop baseline",
            "damage": "none",
            "lighting_state": "north-window daylight plus existing practicals",
        }
        prop_delta = {"condition": "clean operational baseline", "position": "fixed spatial anchor at world origin"}
        inspector_prompt = "prompts/images/identity-inspectors/char-hero-inspector--v001.txt"
        self._file(
            inspector_prompt,
            image_prompt(strategy="image2-live-action-identity-inspector-v1.6"),
        )
        inspector = self._asset(
            asset_id=self.identity_inspector_id,
            role="char-hero-unified-identity-inspector",
            asset_type="character_identity_inspector",
            status="approved",
            generator="builtin-imagegen",
            mode="generate",
            references=[],
            scenes=["sc-010"],
            prompt_path=inspector_prompt,
            approved_path=paths[self.identity_inspector_id],
            photo_mode="reference_photo",
            auth_mode="neutral_reference",
            user_decision="approved",
            provenance_kind="generated_anchor",
            identity_pack_id="identity-char-hero",
        )
        inspector["identity_inspector_layout"] = {
            "profile": "higgsfield-character-reference-sheet-two-row-single-solve-v1.6",
            "grid": [4, 2],
            "slot_roles": [*CHARACTER_VIEWS, "blank"],
            "single_identity_solve": True,
            "authoritative": True,
        }
        assets = [inspector]
        crop_specs = (
            ("char-hero-full-front--v001", "char-hero-full-front", "full_front", "character_body_anchor", [0, 0, 2, 2]),
            ("char-hero-full-left-profile--v001", "char-hero-full-left-profile", "full_left_profile", "character_identity_view", [2, 0, 2, 2]),
            ("char-hero-full-right-profile--v001", "char-hero-full-right-profile", "full_right_profile", "character_identity_view", [4, 0, 2, 2]),
            ("char-hero-full-back--v001", "char-hero-full-back", "full_back", "character_identity_view", [6, 0, 2, 2]),
            ("char-hero-portrait-front--v001", "char-hero-portrait-front", "portrait_front", "character_face_anchor", [0, 2, 2, 2]),
            ("char-hero-portrait-left-profile--v001", "char-hero-portrait-left-profile", "portrait_left_profile", "character_identity_view", [2, 2, 2, 2]),
            ("char-hero-portrait-right-profile--v001", "char-hero-portrait-right-profile", "portrait_right_profile", "character_identity_view", [4, 2, 2, 2]),
        )
        for asset_id, role, identity_view_role, asset_type, crop_box in crop_specs:
            crop = self._asset(
                asset_id=asset_id,
                role=role,
                asset_type=asset_type,
                status="approved",
                generator="deterministic-crop",
                mode="crop",
                references=[self.identity_inspector_id],
                scenes=["sc-010"],
                derived_from=self.identity_inspector_id,
                approved_path=paths[asset_id],
                photo_mode="reference_photo",
                auth_mode="neutral_reference",
                user_decision="approved",
                provenance_kind="generated_anchor",
                identity_pack_id="identity-char-hero",
                identity_view_role=identity_view_role,
                root_reference_ids=[self.identity_inspector_id],
            )
            crop["generation_provenance"]["crop_box_px"] = crop_box
            assets.append(crop)
        assets.extend([
            self._asset(
                asset_id="char-hero-state-baseline--v001", role="char-hero-state-baseline", asset_type="character_state", status="approved",
                generator="provided", mode="provided",
                references=self.identity_root_ids, scenes=["sc-010"],
                approved_path=paths["char-hero-state-baseline--v001"], photo_mode="reference_photo", auth_mode="neutral_reference",
                user_decision="approved", provenance_kind="user_provided_photo", identity_pack_id="identity-char-hero",
                character_state_id="state-char-hero-baseline",
                root_reference_ids=self.identity_root_ids, state_delta=identity_delta,
            ),
            self._asset(
                asset_id="loc-workshop--v001", role="loc-workshop", asset_type="location_master", status="approved",
                generator="provided", mode="provided", references=[], scenes=["sc-010"], approved_path=paths["loc-workshop--v001"],
                photo_mode="reference_photo", auth_mode="neutral_reference", user_decision="approved",
                provenance_kind="user_provided_photo", location_world_id="world-workshop",
            ),
            self._asset(
                asset_id="prop-red-worktable--v001", role="prop-red-worktable", asset_type="prop", status="approved",
                generator="provided", mode="provided", references=[], scenes=["sc-010"], approved_path=paths["prop-red-worktable--v001"],
                photo_mode="reference_photo", auth_mode="neutral_reference", user_decision="approved", provenance_kind="user_provided_photo",
            ),
            self._asset(
                asset_id="prop-red-worktable-state-baseline--v001", role="prop-red-worktable-state-baseline", asset_type="prop_state", status="approved",
                generator="provided", mode="provided", references=["prop-red-worktable--v001"], scenes=["sc-010"],
                approved_path=paths["prop-red-worktable-state-baseline--v001"], photo_mode="reference_photo",
                auth_mode="neutral_reference", user_decision="approved", provenance_kind="user_provided_photo",
                root_reference_ids=["prop-red-worktable--v001"], state_delta=prop_delta,
            ),
        ])
        character_state_asset = next(item for item in assets if item["id"] == "char-hero-state-baseline--v001")
        character_state_asset["generation_provenance"]["reference_inputs"] = [
            {
                "asset_id": root_id,
                "relative_path": self.approved_paths[root_id],
                "sha256": hashlib.sha256((self.path / self.approved_paths[root_id]).read_bytes()).hexdigest(),
            }
            for root_id in self.identity_root_ids
        ]
        next(item for item in assets if item["id"] == "prop-red-worktable--v001")["reference_coverage"] = {
            "policy": "object_multiview",
            "required_views": ["front", "side", "three_quarter"],
            "present_views": ["front", "side", "three_quarter"],
            "same_subject_or_geography_pass": True,
            "background_policy": "pure_white",
            "notes": ["Same fixed steel worktable with documented approximate dimensions."],
        }

        state_views = (
            (
                "loc-workshop-state-day-est--v001",
                "loc-workshop-state-day-establishing",
                "establishing_wide",
                "not_applicable",
            ),
            (
                "loc-workshop-state-day-side3q--v001",
                "loc-workshop-state-day-side-three-quarter",
                "side_three_quarter_wide",
                "left",
            ),
        )
        for asset_id, role, view_role, view_side in state_views:
            prompt_path = f"prompts/images/{asset_id}.txt"
            image_path = f"assets/locations/state-views/{asset_id}--approved.png"
            self._file(
                prompt_path,
                image_prompt(
                    strategy="image2-live-action-location-v1.6",
                    human_subject=False,
                ),
            )
            self._file(image_path)
            view = self._asset(
                asset_id=asset_id,
                role=role,
                asset_type="location_variant",
                status="approved",
                generator="builtin-imagegen",
                mode="edit",
                references=["loc-workshop--v001", "prop-red-worktable--v001"],
                scenes=["sc-010"],
                photo_mode="reference_photo",
                auth_mode="neutral_reference",
                user_decision="approved",
                provenance_kind="generated_anchor",
                derived_from="loc-workshop--v001",
                prompt_path=prompt_path,
                approved_path=image_path,
                scene_state_id="state-workshop-day",
                view_role=view_role,
                view_side=view_side,
                spatial_map_id="spatial-workshop-day",
                primary_anchor_asset_id="prop-red-worktable--v001",
                location_world_id="world-workshop", location_state_id="state-workshop-day",
                root_reference_ids=["loc-workshop--v001"], state_delta=location_delta,
                prompt_strategy_id="image2-live-action-location-v1.6",
            )
            view["reference_coverage"] = {
                "policy": "single_view",
                "required_views": [view_role],
                "present_views": [view_role],
                "same_subject_or_geography_pass": True,
                "background_policy": "on_location_neutral",
                "notes": ["Independent scene-state view with locked geography and anchor."],
            }
            assets.append(view)

        locked_refs = [
            *self.identity_root_ids,
            "char-hero-state-baseline--v001",
            "loc-workshop--v001",
            "loc-workshop-state-day-est--v001",
            "loc-workshop-state-day-side3q--v001",
            "prop-red-worktable--v001",
            "prop-red-worktable-state-baseline--v001",
        ]
        for suffix, status in (("a", "approved"), ("b", "rejected"), ("c", "rejected")):
            asset_id = f"look-base-{suffix}--v001"
            prompt_path = f"prompts/images/look-tests/{asset_id}.txt"
            state = "approved" if status == "approved" else "candidate"
            image_path = f"assets/look-tests/lookset-base-001/{asset_id}--{state}.png"
            self._file(prompt_path, image_prompt(story_moment=STORY_MOMENT, blocking=LOCKED_BLOCKING))
            self._file(image_path)
            assets.append(
                self._asset(
                    asset_id=asset_id, role=f"look-base-{suffix}", asset_type="look_test", status=status,
                    generator="builtin-imagegen", mode="generate",
                    references=locked_refs, scenes=["sc-010"],
                    profile_id=f"cp-base-{suffix}", comparison_id="lookset-base-001", prompt_path=prompt_path,
                    candidate_path=image_path if status == "rejected" else "",
                    approved_path=image_path if status == "approved" else "", photo_mode="cinematic_frame",
                    auth_mode="narrative_frame", user_decision="approved" if status == "approved" else "rejected",
                    provenance_kind="generated_anchor",
                    scene_state_id="state-workshop-day", spatial_map_id="spatial-workshop-day",
                    primary_anchor_asset_id="prop-red-worktable--v001",
                    identity_pack_id="identity-char-hero", character_state_id="state-char-hero-baseline",
                    location_world_id="world-workshop", location_state_id="state-workshop-day",
                    root_reference_ids=[*self.identity_root_ids, "loc-workshop--v001", "prop-red-worktable--v001"],
                )
            )

        plate_prompt = "prompts/images/loc-workshop-plate--v001.txt"
        plate_image = "assets/locations/plates/loc-workshop-plate--v001--approved.png"
        self._file(plate_prompt, image_prompt())
        self._file(plate_image)
        assets.append(
            self._asset(
                asset_id="loc-workshop-plate--v001", role="loc-workshop-plate", asset_type="location_plate",
                status="approved", generator="builtin-imagegen", mode="edit",
                references=[
                    "loc-workshop--v001",
                    "loc-workshop-state-day-est--v001",
                    "loc-workshop-state-day-side3q--v001",
                    "prop-red-worktable--v001",
                ],
                scenes=["sc-010"], profile_id="cp-base-a", derived_from="loc-workshop--v001",
                prompt_path=plate_prompt, approved_path=plate_image, photo_mode="cinematic_frame",
                auth_mode="narrative_frame", user_decision="approved", provenance_kind="generated_anchor",
                scene_state_id="state-workshop-day", spatial_map_id="spatial-workshop-day",
                primary_anchor_asset_id="prop-red-worktable--v001",
                location_world_id="world-workshop", location_state_id="state-workshop-day",
                root_reference_ids=["loc-workshop--v001"], state_delta=location_delta,
            )
        )

        sequence_anchor_id = "seq-workshop-visual-anchor--v001"
        sequence_anchor_prompt = f"prompts/images/{sequence_anchor_id}.txt"
        sequence_anchor_image = f"assets/keyframes/{sequence_anchor_id}--approved.png"
        self._file(sequence_anchor_prompt, image_prompt())
        self._file(sequence_anchor_image)
        assets.append(
            self._asset(
                asset_id=sequence_anchor_id,
                role="sequence-workshop-joint-visual-anchor",
                asset_type="keyframe",
                status="approved",
                generator="builtin-imagegen",
                mode="generate",
                references=[
                    *self.identity_root_ids,
                    "char-hero-state-baseline--v001",
                    "loc-workshop--v001",
                    "loc-workshop-state-day-est--v001",
                    "loc-workshop-state-day-side3q--v001",
                    "loc-workshop-plate--v001",
                    "prop-red-worktable--v001",
                    "prop-red-worktable-state-baseline--v001",
                ],
                scenes=["sc-010"],
                profile_id="cp-base-a",
                prompt_path=sequence_anchor_prompt,
                approved_path=sequence_anchor_image,
                photo_mode="cinematic_frame",
                auth_mode="narrative_frame",
                user_decision="approved",
                provenance_kind="generated_anchor",
                scene_state_id="state-workshop-day",
                spatial_map_id="spatial-workshop-day",
                primary_anchor_asset_id="prop-red-worktable--v001",
                identity_pack_id="identity-char-hero",
                character_state_id="state-char-hero-baseline",
                location_world_id="world-workshop",
                location_state_id="state-workshop-day",
                root_reference_ids=[*self.identity_root_ids, "loc-workshop--v001", "prop-red-worktable--v001"],
            )
        )

        for label in ("start", "end"):
            asset_id = f"kf-sh-010-010-{label}--v001"
            keyframe_prompt = f"prompts/images/{asset_id}.txt"
            keyframe_image = f"assets/keyframes/{asset_id}--approved.png"
            self._file(keyframe_prompt, image_prompt())
            self._file(keyframe_image)
            assets.append(
                self._asset(
                    asset_id=asset_id, role=f"kf-sh-010-010-{label}", asset_type="keyframe",
                    status="approved", generator="builtin-imagegen", mode="generate",
                    references=[
                        *self.identity_root_ids,
                        "char-hero-state-baseline--v001", "loc-workshop--v001", "loc-workshop-plate--v001",
                        "loc-workshop-state-day-side3q--v001", "prop-red-worktable--v001",
                        "prop-red-worktable-state-baseline--v001",
                    ], scenes=["sc-010"], profile_id="cp-base-a", prompt_path=keyframe_prompt,
                    approved_path=keyframe_image, photo_mode="cinematic_frame", auth_mode="narrative_frame",
                    user_decision="approved", provenance_kind="generated_anchor", scene_state_id="state-workshop-day",
                    spatial_map_id="spatial-workshop-day", primary_anchor_asset_id="prop-red-worktable--v001",
                    identity_pack_id="identity-char-hero", character_state_id="state-char-hero-baseline",
                    location_world_id="world-workshop", location_state_id="state-workshop-day",
                    root_reference_ids=[*self.identity_root_ids, "loc-workshop--v001", "prop-red-worktable--v001"],
                )
            )
        write_json(self.path / "manifests/assets.json", {"schema_version": "1.6", "assets": assets})

    def _build_identities_and_world_state(self) -> None:
        identity_delta = {
            "wardrobe": "plain navy work shirt and charcoal work trousers",
            "hair_state": "dry hair tied low",
            "age_stage": "adult baseline",
            "injury": "none",
            "wetness": "none",
            "dirt": "none",
            "makeup": "none",
            "story_props": "none",
        }
        inspector_path = self.approved_paths[self.identity_inspector_id]
        inspector_sha = hashlib.sha256((self.path / inspector_path).read_bytes()).hexdigest()
        crop_map_path = "assets/reference-boards/identity-char-hero--identity-crops-v001.json"
        crop_source_hashes = {
            role: hashlib.sha256((self.path / self.approved_paths[asset_id]).read_bytes()).hexdigest()
            for role, asset_id in zip(CHARACTER_VIEWS, self.identity_crop_ids)
        }
        write_json(
            self.path / crop_map_path,
            {
                "schema_version": "1.6",
                "identity_pack_id": "identity-char-hero",
                "identity_inspector_asset_id": self.identity_inspector_id,
                "layout_profile": "higgsfield-character-reference-sheet-two-row-single-solve-v1.6",
                "canvas_px": [8, 4],
                "grid": [4, 2],
                "background": "pure_white",
                "authoritative": True,
                "authority_sha256": inspector_sha,
                "generation": "one-imagegen-call-then-deterministic-crops",
                "blank_slot": {"row": 2, "column": 4},
                "slots": [],
            },
        )
        write_json(
            self.path / "manifests/identities.json",
            {
                "schema_version": "1.6",
                "identity_packs": [
                    {
                        "id": "identity-char-hero",
                        "status": "approved",
                        "identity_kind": "fictional",
                        "identity_inspector_asset_id": self.identity_inspector_id,
                        "identity_view_asset_ids": {
                            "full_front": "char-hero-full-front--v001",
                            "full_left_profile": "char-hero-full-left-profile--v001",
                            "full_right_profile": "char-hero-full-right-profile--v001",
                            "full_back": "char-hero-full-back--v001",
                            "portrait_front": "char-hero-portrait-front--v001",
                            "portrait_left_profile": "char-hero-portrait-left-profile--v001",
                            "portrait_right_profile": "char-hero-portrait-right-profile--v001",
                        },
                        "face_anchor_asset_id": "char-hero-portrait-front--v001",
                        "body_anchor_asset_id": "char-hero-full-front--v001",
                        "role_physique_brief": {
                            "id": "role-physique-char-hero-v1",
                            "classification": "aspirational_athletic",
                            "source": "mixed",
                            "narrative_rationale": "The courier is a trained field operative whose lean athletic silhouette must read through practical workwear.",
                            "age_presentation": "healthy adult in the scripted age range",
                            "stature_and_frame": "moderately tall, lean frame with long balanced limbs",
                            "shoulder_waist_hip_relation": "athletic shoulders, defined but natural waist and stable pelvis",
                            "muscle_and_fat_distribution": "functional lean muscle without bodybuilding exaggeration",
                            "posture_and_gait": "upright trained posture, grounded stride and economical weight transfer",
                            "wardrobe_silhouette": "workwear preserves the shoulder line, waist and leg length rather than making the body boxy",
                            "must_have_traits": ["balanced leg-to-torso impression", "athletic shoulder line"],
                            "candidate_rejection_criteria": ["shortened legs or collapsed torso", "boxy untrained silhouette inconsistent with the role"],
                            "visual_body_balance": {
                                "target": "balanced_four_six",
                                "measurement_basis": "crown-to-functional-waist versus functional-waist-to-floor in neutral long-distance front and back authorities",
                                "upper_body_share_range": [0.38, 0.44],
                                "lower_body_share_range": [0.56, 0.62],
                                "perspective_policy": "natural_perspective_only",
                                "story_exception": "",
                            },
                            "quantitative_targets": [
                                {"metric": "head_to_body", "minimum": 0.13, "maximum": 0.145, "unit": "standing_height_1.0", "rationale": "preserve the approved naturally elongated adult proportion"},
                                {"metric": "shoulder_width", "minimum": 0.23, "maximum": 0.25, "unit": "standing_height_1.0", "rationale": "retain the trained shoulder line"},
                            ],
                        },
                        "physique_fit_qa": {
                            "checks": {
                                "narrative_and_casting_fit": True,
                                "quantitative_target_fit": True,
                                "visual_leg_body_balance_fit": True,
                                "silhouette_and_volume_fit": True,
                                "posture_and_gait_fit": True,
                                "wardrobe_silhouette_fit": True,
                                "no_unrequested_body_template": True,
                            },
                            "verdict": "pass",
                            "hard_failures": [],
                            "notes": ["The seven views preserve the role-required lean athletic build."],
                            "checked_at": TIMESTAMP,
                            "reviewer": "codex-visual",
                        },
                        "proportion_signature": {
                            "id": "prop-char-hero-v1",
                            "normalization": "standing_height_1.0",
                            "measurement_asset_ids": ["char-hero-full-front--v001", "char-hero-full-back--v001"],
                            "projection_classes": {
                                role: "measurement" if role in {"full_front", "full_back"} else "silhouette_confirmation"
                                for role in CHARACTER_VIEWS
                            },
                            "confidence": 0.94,
                            "ratios": {
                                "head_to_body": 0.137,
                                "shoulder_width": 0.238,
                                "hip_width": 0.196,
                                "torso_length": 0.303,
                                "upper_arm_length": 0.181,
                                "forearm_length": 0.158,
                                "thigh_length": 0.247,
                                "shin_length": 0.238,
                                "arm_span": 0.985,
                                "hand_length": 0.108,
                                "foot_length": 0.151,
                            },
                            "tolerances": {field: 0.03 for field in (
                                "head_to_body", "shoulder_width", "hip_width", "torso_length",
                                "upper_arm_length", "forearm_length", "thigh_length", "shin_length",
                                "arm_span", "hand_length", "foot_length",
                            )},
                            "intentional_asymmetries": ["left shoulder rests approximately one centimetre lower"],
                            "expected_digit_topology": {"left_hand": 5, "right_hand": 5, "left_foot": 5, "right_foot": 5},
                        },
                        "skeletal_lock": {
                            "locked": True,
                            "soft_tissue_delta_allowed": ["age", "weight", "pregnancy", "swelling", "muscle"],
                            "notes": ["Perspective shortening is projection, not a body-state change."],
                        },
                        "immutable_identity": {
                            "facial_bone_proportions": "narrow lower face, broad cheekbone plane and short chin",
                            "feature_spacing": "documented eye, brow, nose and mouth spacing from the face authority",
                            "body_build_and_height_ratio": "compact athletic build, 7.3-head adult proportion",
                            "skin_tone_range": "documented neutral medium range under neutral exposure",
                            "hairline": "slightly asymmetric left temple and stable center shape",
                            "fixed_marks": "single small mark below the right cheekbone",
                            "handedness": "right-handed",
                        },
                        "reference_board": {
                            "status": "ready",
                            "relative_path": inspector_path,
                            "sha256": inspector_sha,
                            "source_sha256s": crop_source_hashes,
                            "layout_profile": "higgsfield-character-reference-sheet-two-row-single-solve-v1.6",
                            "authoritative": True,
                            "crop_map_path": crop_map_path,
                        },
                        "character_state_ids": ["state-char-hero-baseline"],
                        "approval_gate_id": "review-foundation-001",
                        "qa": approval_qa(("face_identity", "single_solve_identity_board", "seven_deterministic_crops", "role_conditioned_physique", "proportion_signature", "joint_topology", "clean_texture", "live_action_surface")),
                    }
                ],
                "character_states": [
                    {
                        "id": "state-char-hero-baseline",
                        "status": "approved",
                        "identity_pack_id": "identity-char-hero",
                        "authority_asset_id": "char-hero-state-baseline--v001",
                        "state_delta": identity_delta,
                        "soft_tissue_delta": {
                            "kind": "none",
                            "extent": "no change from root identity",
                            "cause": "baseline story state",
                            "first_visible_shot_id": "sh-010-010",
                            "preserve_skeleton": True,
                        },
                        "preserve_immutable": {
                            "facial_bone_proportions": True,
                            "feature_spacing": True,
                            "body_build_and_height_ratio": True,
                            "skin_tone_range": True,
                            "hairline": True,
                            "fixed_marks": True,
                            "handedness": True,
                        },
                        "preserve_proportion_signature": True,
                        "preserve_role_physique": True,
                        "first_visible_shot_id": "sh-010-010",
                        "cause": "Initial persistent character state at the start of the story.",
                        "approval_gate_id": "review-foundation-001",
                        "qa": approval_qa(("root_traceability", "immutable_identity", "role_conditioned_physique", "proportion_signature", "soft_tissue_delta", "anatomy", "clean_texture", "live_action_surface")),
                    }
                ],
            },
        )
        location_delta = {
            "time": "day",
            "weather": "dry",
            "dressing": "occupied workshop baseline",
            "damage": "none",
            "lighting_state": "north-window daylight plus existing practicals",
        }
        prop_delta = {"condition": "clean operational baseline", "position": "fixed spatial anchor at world origin"}
        write_json(
            self.path / "manifests/world-state.json",
            {
                "schema_version": "1.6",
                "production_design_dna": {
                    "period": "contemporary",
                    "socioeconomic_context": "working industrial repair shop with maintained low-cost equipment",
                    "architecture_logic": "retrofitted concrete service bay with exposed utility runs following structural walls",
                    "color_sources": ["red worktable paint", "navy workwear", "neutral concrete"],
                    "material_rules": ["painted steel, concrete, glass and cotton retain distinct scale and reflectance"],
                    "public_infrastructure": ["surface conduit", "service doorway", "north industrial window"],
                    "signage_policy": "functional safety labels only; no invented brands or decorative text",
                    "ageing_policy": "clean authority baseline; any damage must be localized and story-declared",
                },
                "location_worlds": [
                    {
                        "id": "world-workshop",
                        "status": "approved",
                        "location_master_asset_id": "loc-workshop--v001",
                        "immutable_world": {
                            "topology": "rectangular service bay with north window wall and +Y service doorway",
                            "openings": ["north industrial window", "+Y service doorway"],
                            "fixed_facilities": ["surface conduit", "overhead practicals", "wall service outlets"],
                            "primary_anchor_asset_id": "prop-red-worktable--v001",
                            "scale_relations": ["table 1.8 x 0.8 x 0.9 m", "doorway 3.0 m toward +Y from anchor"],
                            "material_baseline": ["uncoated concrete floor", "painted steel table", "clear industrial glass"],
                        },
                        "location_state_ids": ["state-workshop-day"],
                        "approval_gate_id": "review-foundation-001",
                        "qa": approval_qa(("topology", "openings", "fixed_facilities", "anchor_and_scale", "material_baseline", "clean_texture")),
                    }
                ],
                "location_states": [
                    {
                        "id": "state-workshop-day",
                        "status": "approved",
                        "location_world_id": "world-workshop",
                        "scene_ids": ["sc-010"],
                        "authority_asset_ids": [
                            "loc-workshop-state-day-est--v001",
                            "loc-workshop-state-day-side3q--v001",
                            "loc-workshop-plate--v001",
                        ],
                        "state_delta": location_delta,
                        "environmental_state_id": "env-workshop-clear",
                        "special_lighting_event_ids": [],
                        "preserve_immutable": {
                            "topology": True,
                            "openings": True,
                            "fixed_facilities": True,
                            "primary_anchor_asset_id": True,
                            "scale_relations": True,
                            "material_baseline": True,
                        },
                        "first_visible_shot_id": "sh-010-010",
                        "cause": "Initial daytime location state.",
                        "approval_gate_id": "review-foundation-001",
                        "qa": approval_qa(("root_traceability", "topology", "fixed_facilities", "anchor_and_scale", "delta_locality", "clean_texture")),
                    }
                ],
                "prop_states": [
                    {
                        "id": "prop-state-table-baseline",
                        "status": "approved",
                        "root_prop_asset_id": "prop-red-worktable--v001",
                        "authority_asset_id": "prop-red-worktable-state-baseline--v001",
                        "state_delta": prop_delta,
                        "preserve_structure": True,
                        "first_visible_shot_id": "sh-010-010",
                        "cause": "Initial fixed anchor state.",
                        "approval_gate_id": "review-foundation-001",
                        "qa": approval_qa(("root_traceability", "structure_and_scale", "delta_locality", "clean_texture")),
                    }
                ],
                "environmental_states": [
                    {
                        "id": "env-workshop-clear",
                        "status": "approved",
                        "kind": "clear",
                        "scene_ids": ["sc-010"],
                        "source_cause": "ordinary indoor air exchanged through the service doorway",
                        "intensity": "clear air with only natural distance falloff",
                        "visibility_range_m": 30.0,
                        "particle_or_medium_scale": "no visible suspended particles",
                        "direction": "still interior air",
                        "wind": {"direction": "none", "speed_mps": 0.0, "gust_mps": 0.0},
                        "accumulation": "none on floor, skin, hair, wardrobe or equipment",
                        "material_interactions": ["no wetting, settling or coating"],
                        "light_behavior": {
                            "scattering_or_attenuation": "ordinary clean-air attenuation only",
                            "distance_behavior": "contrast decreases only through normal lens and room depth",
                            "readability_source": "window and practical illumination",
                            "reflection_response": "unchanged dry material reflections",
                        },
                        "focus_exposure_effect": "no atmosphere-driven focus or exposure compensation",
                        "sound": ["quiet workshop room tone"],
                        "start_shot_id": "sh-010-010",
                        "end_shot_id": "sh-010-010",
                        "continuity_signature": "clear-dry-still-workshop-v1",
                        "approval_gate_id": "review-foundation-001",
                        "qa": approval_qa((
                            "physical_source", "visibility_and_depth", "advection_and_direction",
                            "accumulation_and_material_interaction", "light_scattering_or_attenuation",
                            "exposure_focus_effect", "temporal_bounds", "sound_and_continuity",
                        )),
                    }
                ],
                "special_lighting_events": [],
            },
        )

    def _build_spatial(self) -> None:
        data = {
            "schema_version": "1.6",
            "spatial_maps": [
                {
                    "id": "spatial-workshop-day",
                    "status": "approved",
                    "scene_id": "sc-010",
                    "scene_state_id": "state-workshop-day",
                    "location_master_asset_id": "loc-workshop--v001",
                    "establishing_view_asset_id": "loc-workshop-state-day-est--v001",
                    "side_three_quarter_view_asset_id": "loc-workshop-state-day-side3q--v001",
                    "additional_view_asset_ids": [],
                    "primary_anchor": {
                        "asset_id": "prop-red-worktable--v001",
                        "selection_source": "script_prop",
                        "selection_rationale": "The immobile red steel worktable is story-relevant, distinctive and scale-legible.",
                        "stability": "fixed",
                        "dimensions_m": {"width": 1.8, "depth": 0.8, "height": 0.9},
                        "orientation": "long edge aligned with +X; drawer side faces -Y",
                    },
                    "coordinate_system": {
                        "origin": "primary_anchor_ground_contact_center",
                        "units": "metres",
                        "precision_m": 0.1,
                        "x_positive_label": "toward the north-window wall",
                        "y_positive_label": "toward the workshop service doorway",
                        "z_positive_label": "upward from the concrete floor",
                    },
                    "landmarks": [
                        {
                            "id": "lm-service-door",
                            "label": "service doorway center",
                            "position_m": {"x": -1.5, "y": 3.0, "z": 0.0},
                            "relation_to_anchor": "behind and left of the table toward +Y",
                        }
                    ],
                    "marks": [
                        {
                            "id": "cam-sh-010-010",
                            "kind": "camera",
                            "asset_id": "",
                            "position_m": {"x": 2.0, "y": -2.0, "z": 1.5},
                            "facing": "toward the anchor origin and slightly toward +Y",
                            "relation_to_anchor": "reachable near-side aisle at +X/-Y",
                        },
                        {
                            "id": "mark-hero-table-near",
                            "kind": "character",
                            "asset_id": self.identity_inspector_id,
                            "position_m": {"x": 0.8, "y": -1.0, "z": 0.0},
                            "facing": "toward +Y, then eyes rotate to the anchor",
                            "relation_to_anchor": "0.8 m toward +X and 1.0 m toward -Y from the table center",
                        },
                    ],
                    "movement_paths": [],
                    "secondary_landmark_ids": ["lm-service-door"],
                    "approval_gate_id": "review-foundation-001",
                    "spatial_qa": {
                        "attempt_index": 1,
                        "escalation": "none",
                        "three_quarter_yaw_deg": -45,
                        "adjacent_planes_visible": True,
                        "geography_consistency_pass": True,
                        "anchor_presence_pass": True,
                        "anchor_position_pass": True,
                        "anchor_scale_pass": True,
                        "anchor_orientation_pass": True,
                        "camera_access_pass": True,
                        "hard_failures": [],
                        "notes": ["Both independent views preserve walls, openings, utilities and anchor placement."],
                        "checked_at": TIMESTAMP,
                    },
                }
            ],
        }
        write_json(self.path / "manifests/spatial.json", data)

    def _build_cinematography(self) -> None:
        data = {
            "schema_version": "1.6",
            "policy": "adaptive-live-action-v1.6",
            "base_profile_id": "cp-base-a",
            "base_treatment_id": "treat-base-a",
            "base_format_plan_id": "format-plan-main-16x9",
            "profiles": [
                profile("cp-base-a", "approved", "look-base-a--v001", "a"),
                profile("cp-base-b", "rejected", "look-base-b--v001", "b"),
                profile("cp-base-c", "rejected", "look-base-c--v001", "c"),
            ],
            "cinematic_treatments": [
                treatment("a", "approved"),
                treatment("b", "rejected"),
                treatment("c", "rejected"),
            ],
            "format_plans": [
                {
                    "id": "format-plan-main-16x9",
                    "status": "approved",
                    "scope": "project",
                    "sequence_ids": [],
                    "narrative_reason": "Default widescreen delivery keeps the workshop geography legible without forcing a genre crop.",
                    "capture_aperture": "16:9",
                    "working_frame": "16:9",
                    "delivery_aspect": "16:9",
                    "crop_extraction": "full working frame",
                    "safe_areas": {"action_percent": 90, "title_percent": 80},
                    "squeeze_ratio": 1.0,
                    "desqueeze_delivery": "none",
                    "reframe_policy": "no automatic reframing; scene compositions honor the approved working frame",
                    "transition_design": "no aspect transition in this project baseline",
                    "return_rule": "all scenes remain at 16:9 unless a sequence override is explicitly approved",
                    "baked_black_bars": False,
                    "approval_gate_id": "review-foundation-001",
                }
            ],
            "medium_signatures": [],
            "comparison_sets": [
                {
                    "id": "lookset-base-001", "status": "approved", "diagnostic_scene_id": "sc-010",
                    "story_moment": STORY_MOMENT,
                    "locked_format_plan_id": "format-plan-main-16x9",
                    "locked_environmental_state_id": "env-workshop-clear",
                    "locked_reference_asset_ids": [
                        *self.identity_root_ids,
                        "char-hero-state-baseline--v001",
                        "loc-workshop--v001",
                        "loc-workshop-state-day-est--v001",
                        "loc-workshop-state-day-side3q--v001",
                        "prop-red-worktable--v001",
                        "prop-red-worktable-state-baseline--v001",
                    ],
                    "locked_blocking": LOCKED_BLOCKING,
                    "candidate_profile_ids": ["cp-base-a", "cp-base-b", "cp-base-c"],
                    "candidate_asset_ids": ["look-base-a--v001", "look-base-b--v001", "look-base-c--v001"],
                    "selected_profile_id": "cp-base-a", "selected_asset_id": "look-base-a--v001",
                    "approval_gate_id": "review-foundation-001",
                }
            ],
        }
        write_json(self.path / "manifests/cinematography.json", data)

    def _build_shot(self) -> None:
        prompt_path = "prompts/video/sh-010-010.txt"
        shot = {
            "id": "sh-010-010", "scene_id": "sc-010", "order": 10,
            "story_beat": "She notices the broken seal.", "duration_s": 4.0, "motion_class": "dialogue",
            "capture_profile_id": "cp-base-a", "quality_profile_id": "quality-main",
            "shot_size": "medium close-up", "focal_length_mm": 40,
            "fov_deg": 38.6, "t_stop": 2.8, "focus_plan": "Hold her eyes, then rack to the seal at 2.0s.",
            "camera_height_cm": 150, "camera_support": "locked tripod",
            "camera_axis": "doorway-to-window",
            "camera_move": "locked off", "exposure_notes": "Protect the lamp and retain rear-wall separation.",
            "dynamic_range_plan": {
                "policy": "finite_scene_referred",
                "working_latitude_stops": 14.0,
                "upper_latitude_stops": 6.0,
                "lower_latitude_stops": 8.0,
                "scene_contrast_stops_estimate": 15.0,
                "exposure_priority": "protect_skin_and_practicals",
                "middle_gray_anchor": "the courier's face and neutral gray work shirt",
                "highlight_behavior": "the lamp housing rolls gradually while its filament core may clip",
                "shadow_behavior": "unlit shelf gaps fall below the texture floor without gray HDR lift",
                "allowed_clipping": ["small desk-lamp filament core"],
                "allowed_shadow_loss": ["deepest unlit rear-shelf gap"],
                "local_tone_mapping": False,
                "multi_exposure_hdr": False,
                "narrative_reason": "Keep attention on the discovery rather than making the whole workshop equally legible.",
            },
            "camera_move_plan": {
                "primitive": "locked",
                "support": "locked tripod",
                "start_camera_mark_id": "cam-sh-010-010",
                "end_camera_mark_id": "cam-sh-010-010",
                "path_points_m": [{"x": 2.0, "y": -2.0, "z": 1.5}],
                "translation_m": 0.0,
                "rotation_deg": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
                "duration_s": 0.0,
                "speed_curve": "constant",
                "peak_speed_mps": 0.0,
                "easing": "none; the camera is physically locked",
                "path_clearance": {"status": "pass", "traversable_region": "tripod footprint in the near-side aisle", "notes": []},
                "horizon_lock": "level horizon locked by the tripod head",
                "axis_lock": "remain on the doorway-to-window side of the action axis",
                "parallax_expectation": "none from the camera; only subject depth changes",
                "subject_screen_occupancy": "courier remains a medium close-up without automatic reframing",
                "occlusion_crossings": [],
                "lens_focus_change": "manual rack from eyes to the broken seal at 2.0 seconds",
                "settle_hold_s": 4.0,
                "operator_contingency": "no correction after record begins",
                "surreal_vfx_exception": {"enabled": False, "rationale": ""},
            },
            "temporal_capture": {
                "capture_fps": 24,
                "delivery_fps": 24,
                "playback_rate": 1.0,
                "shutter_angle": 180,
                "exposure_time_s": 1 / 48,
                "speed_ramp": [],
                "rolling_shutter_allowance": {"mode": "none", "rationale": ""},
            },
            "motion_blur_plan": {
                "source": "subject",
                "direction": "brief head and eye motion blur follows the actual turn toward the case",
                "regions": ["turning facial features during the brief movement"],
                "amount": "low",
                "static_reference_regions": ["red worktable", "service doorway", "locked workshop walls"],
                "occlusion_edge_behavior": "single clean moving edge with no doubled silhouette",
                "reason": "natural 180-degree shutter sampling of a small subject turn",
                "frame_blending_allowed": False,
                "ghosting_allowed": False,
            },
            "spatial_map_id": "spatial-workshop-day",
            "format_plan_id": "format-plan-main-16x9",
            "environmental_state_id": "env-workshop-clear",
            "special_lighting_event_ids": [],
            "camera_mark_id": "cam-sh-010-010",
            "subject_mark_ids": {self.identity_inspector_id: "mark-hero-table-near"},
            "anchor_projection": {
                "visibility": "visible",
                "screen_region": "lower-center foreground and lower-right midground",
                "direction_from_camera": "ahead and slightly camera-left",
                "set_fixed_direction": "origin",
                "set_fixed_relation": "the anchor remains the fixed origin between camera and +Y service doorway",
                "distance_m": 3.2,
            },
            "depth_order": [self.identity_inspector_id, "prop-red-worktable--v001", "lm-service-door"],
            "action_beats": [
                {
                    "start_s": 0.0,
                    "end_s": 2.0,
                    "action": "She remains on her floor mark and settles at the table.",
                    "changes_position": False,
                    "subject_asset_id": "",
                    "start_mark_id": "",
                    "end_mark_id": "",
                },
                {
                    "start_s": 2.0,
                    "end_s": 4.0,
                    "action": "Her focus moves to the broken seal without changing her ground position.",
                    "changes_position": False,
                    "subject_asset_id": "",
                    "start_mark_id": "",
                    "end_mark_id": "",
                },
            ],
            "cast_asset_ids": [self.identity_inspector_id],
            "character_state_bindings": {self.identity_inspector_id: "state-char-hero-baseline"},
            "body_geometry_locks": {
                self.identity_inspector_id: {
                    "proportion_signature_id": "prop-char-hero-v1",
                    "role_physique_brief_id": "role-physique-char-hero-v1",
                    "character_state_id": "state-char-hero-baseline",
                    "pose_projection": "standing three-quarter narrative projection; foreshortening is not a proportion change",
                    "critical_hand_detail": False,
                    "digit_visibility": "partially_resolvable",
                    "relative_height_m": 1.68,
                }
            },
            "pose_contact_anchor_ids": [],
            "material_interaction_plan": {
                "required": False,
                "contacts": ["both shoes remain grounded on the concrete floor"],
                "gravity": "ordinary Earth gravity keeps weight over the planted feet",
                "collision": "no collision event",
                "landing": "no landing event",
                "material_response": "shoe soles compress subtly against dry concrete; clothing remains separate from the body",
            },
            "location_asset_id": "loc-workshop-plate--v001", "location_state_id": "state-workshop-day",
            "prop_asset_ids": ["prop-red-worktable--v001"],
            "prop_state_bindings": {"prop-red-worktable--v001": "prop-state-table-baseline"},
            "sequence_cluster_id": "seq-workshop-day-001",
            "sequence_visual_anchor_asset_id": "seq-workshop-visual-anchor--v001",
            "start_keyframe_id": "kf-sh-010-010-start--v001", "end_keyframe_id": "kf-sh-010-010-end--v001",
            "video_prompt_path": prompt_path, "model_prompt_strategy_id": "shot-model-v1.6",
            "audio": {"dialogue": [], "ambience": ["quiet workshop room tone"],
                      "foley": ["shoe stops on concrete"], "music": [], "silence": []},
            "locks": ["one recurring character", "case remains open", "clean source-led digital response"], "status": "ready",
            "adapter_notes": {"lighting_state": "north-window daylight plus existing practicals"},
        }
        spatial = self.read("manifests/spatial.json")["spatial_maps"][0]
        self._file(prompt_path, video_prompt(shot, spatial))
        write_json(self.path / "manifests/shots.json", {"schema_version": "1.6", "shots": [shot]})

    def _build_sequences(self) -> None:
        reference_order = [
            *self.identity_root_ids,
            "char-hero-state-baseline--v001",
            "loc-workshop-state-day-est--v001",
            "loc-workshop-state-day-side3q--v001",
            "loc-workshop-plate--v001",
            "prop-red-worktable--v001",
            "prop-red-worktable-state-baseline--v001",
            "look-base-a--v001",
            "seq-workshop-visual-anchor--v001",
            "kf-sh-010-010-start--v001",
            "kf-sh-010-010-end--v001",
            "loc-workshop--v001",
        ]
        asset_rows = {item["id"]: item for item in self.read("manifests/assets.json")["assets"]}
        stack_payload = [
            {
                "asset_id": asset_id,
                "sha256": asset_rows[asset_id]["generation_provenance"]["output"]["sha256"],
            }
            for asset_id in reference_order
        ]
        stack_hash = hashlib.sha256(
            json.dumps(stack_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()
        write_json(
            self.path / "manifests/sequences.json",
            {
                "schema_version": "1.6",
                "provider_adapters": {
                    "higgsfield": {
                        "knowledge_snapshot": "2026-08-27",
                        "official_profile_id": "cinema-studio-4-seedance-2.5-official-2026-08-27",
                        "official_source_urls": [
                            "https://higgsfield.ai/blog/seedance-2-5-prompting-guide",
                            "https://higgsfield.ai/blog/ai-short-film-youtube-guide",
                            "https://higgsfield.ai/blog/realistic-ai-human-movement",
                            "https://higgsfield.ai/blog/cinema-studio-4-0",
                        ],
                        "strict_conformance": True,
                        "default_target_workflow": "cinema-studio-4",
                        "default_target_model": "seedance-2.5",
                        "prompt_sections": list(VIDEO_HEADINGS),
                        "reference_limits": {
                            "popcorn": 4,
                            "cinema-studio-3": 9,
                            "seedance-2.5": 50,
                            "cinema-studio-4": 50,
                        },
                        "camera_move_segment_limits": {
                            "popcorn": 1,
                            "cinema-studio-3": 1,
                            "seedance-2.5": 1,
                            "cinema-studio-4": 1,
                        },
                    }
                },
                "sequence_clusters": [
                    {
                        "id": "seq-workshop-day-001",
                        "status": "ready",
                        "scene_ids": ["sc-010"],
                        "shot_ids": ["sh-010-010"],
                        "state_signature": {
                            "location_state_id": "state-workshop-day",
                            "environmental_state_id": "env-workshop-clear",
                            "special_lighting_event_ids": [],
                            "character_state_ids": ["state-char-hero-baseline"],
                            "prop_state_ids": ["prop-state-table-baseline"],
                            "capture_profile_id": "cp-base-a",
                            "format_plan_id": "format-plan-main-16x9",
                            "temporal_capture_signature": {
                                "capture_fps": 24,
                                "delivery_fps": 24,
                                "playback_rate": 1.0,
                                "shutter_angle": 180,
                            },
                            "lighting_state": "north-window daylight plus existing practicals",
                        },
                        "first_keyframe_id": "kf-sh-010-010-start--v001",
                        "end_keyframe_id": "kf-sh-010-010-end--v001",
                        "bridge_from_sequence_id": "",
                        "bridge_frame_asset_id": "",
                        "target_workflow": "cinema-studio-4",
                        "target_model": "seedance-2.5",
                        "official_conformance_profile_id": "cinema-studio-4-seedance-2.5-official-2026-08-27",
                        "reference_limit": 50,
                        "boundary_reason": "Initial sequence cluster with one stable state signature.",
                        "quality_profile_id": "quality-main",
                        "sequence_visual_anchor_asset_id": "seq-workshop-visual-anchor--v001",
                        "reference_order": reference_order,
                        "reference_stack_sha256": stack_hash,
                        "approval_gate_id": "review-seq-workshop-day-001",
                        "qa": approval_qa((
                            "state_uniformity", "identity_consistency", "location_world_consistency",
                            "environment_continuity", "format_and_temporal_uniformity",
                            "first_end_keyframes", "reference_budget",
                        )),
                    }
                ],
            },
        )

    def _build_quality_candidates_reviews(self) -> None:
        asset_manifest = self.read("manifests/assets.json")
        assets = [item for item in asset_manifest["assets"] if isinstance(item, dict)]
        candidate_sets: list[dict[str, Any]] = []
        for asset in assets:
            if asset["generator"] != "builtin-imagegen":
                continue
            set_id = asset["candidate_set_id"]
            set_root = f"assets/candidates/{set_id}"
            selected_id = f"{set_id}-candidate-01"
            active_path = asset["approved_path"] if asset["status"] == "approved" else asset["candidate_path"]
            selected_path = f"{set_root}/{selected_id}.png"
            selected_bytes = (self.path / active_path).read_bytes()
            selected_file = self.path / selected_path
            selected_file.parent.mkdir(parents=True, exist_ok=True)
            selected_file.write_bytes(selected_bytes)
            identity_single_solve = asset["type"] == "character_identity_inspector"
            critical = asset["type"] in {"look_test", "keyframe", "key_art"}
            count = 1 if identity_single_solve else 3 if critical else 2
            variants = [
                {
                    "id": selected_id,
                    "status": "selected",
                    "path": selected_path,
                    "sha256": hashlib.sha256(selected_bytes).hexdigest(),
                    "operation": "generate",
                    "derived_from_candidate_id": "",
                    "prompt_sha256": hashlib.sha256((self.path / asset["prompt_path"]).read_bytes()).hexdigest(),
                    "reference_order": list(asset["reference_asset_ids"]),
                    "quality_verdict": "pass",
                    "hard_failures": [],
                    "diagnostic_regions": {
                        "face": [{"label": "visible face", "x": 0.25, "y": 0.1, "width": 0.5, "height": 0.45}] if asset.get("identity_pack_id") else [],
                        "hands": [{"label": "visible hand/contact area", "x": 0.2, "y": 0.4, "width": 0.6, "height": 0.5}] if asset.get("identity_pack_id") else [],
                        "materials": [{"label": "material separation", "x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}],
                        "highlights": [{"label": "source-shaped highlight", "x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5}],
                        "shadows": [{"label": "shadow transition", "x": 0.5, "y": 0.5, "width": 0.5, "height": 0.5}],
                    },
                    "reviewed_at": TIMESTAMP,
                }
            ]
            for index in range(2, count + 1):
                failed_id = f"{set_id}-candidate-{index:02d}"
                failed_path = f"{set_root}/{failed_id}.png"
                failed_bytes = tiny_png_bytes((120 + index, 110, 100))
                (self.path / failed_path).write_bytes(failed_bytes)
                variants.append(
                    {
                        "id": failed_id,
                        "status": "failed",
                        "path": failed_path,
                        "sha256": hashlib.sha256(failed_bytes).hexdigest(),
                        "operation": "generate",
                        "derived_from_candidate_id": "",
                        "prompt_sha256": hashlib.sha256((self.path / asset["prompt_path"]).read_bytes()).hexdigest(),
                        "reference_order": list(asset["reference_asset_ids"]),
                        "quality_verdict": "fail",
                        "hard_failures": ["fixture candidate isolated from authority due to synthetic surface"],
                        "diagnostic_regions": {kind: [] for kind in ("face", "hands", "materials", "highlights", "shadows")},
                        "reviewed_at": TIMESTAMP,
                    }
                )
            candidate_sets.append(
                {
                    "id": set_id,
                    "target_asset_id": asset["id"],
                    "tier": "identity_single_solve" if identity_single_solve else "critical" if critical else "derivative",
                    "status": "selected",
                    "operation": "generate",
                    "approval_gate_id": asset["approval_gate_id"],
                    "prompt_path": asset["prompt_path"],
                    "reference_asset_ids": list(asset["reference_asset_ids"]),
                    "batches": [{"index": 1, "reason": "initial independent candidate pool", "changed_variable": "", "candidates": variants}],
                    "selected_candidate_id": selected_id,
                    "selection_reason": "Only this candidate passes the four-scale live-action, geometry and photographic gates.",
                    "reviewer": "codex-visual",
                    "reviewed_at": TIMESTAMP,
                }
            )
        write_json(
            self.path / "manifests/candidates.json",
            {
                "schema_version": "1.6",
                "policy": {
                    "identity_inspector_initial_count": 1,
                    "identity_inspector_max_batches": 1,
                    "critical_initial_count": 3,
                    "derivative_initial_count": 2,
                    "retry_count": 2,
                    "max_batches": 2,
                    "failed_candidates_visible_by_default": False,
                },
                "candidate_sets": candidate_sets,
            },
        )

        quality = self.read("manifests/quality.json")
        quality["project_quality_profiles"] = [
            {
                "id": "quality-main",
                "status": "approved",
                "quality_floor_id": "clean-observational-live-action-v001",
                "scope": "project",
                "scene_ids": ["sc-010"],
                "sequence_ids": ["seq-workshop-day-001"],
                "approval_gate_id": "review-foundation-001",
                "treatment_family": "naturalistic_dialogue",
                "environment_module_ids": [],
                "capture_circumstance": "A quiet human observer occupies the reachable near-side aisle and accepts ordinary occlusion and focus compromise.",
                "illumination_contract": "The north window and existing desk lamp are the only shape-producing sources; no invented beauty or rim light.",
                "skin_response_contract": "Natural dry skin retains continuous hue/value transitions and broad source-shaped highlights without uniform oil film.",
                "material_response_contract": "Skin, hair, cotton, concrete, painted steel, glass and wood preserve independent roughness, edge and reflection behavior.",
                "tone_contrast_contract": "Protected middle tones, restrained local contrast and gradual source-specific highlight transition.",
                "dynamic_range_contract": {
                    "policy": "finite_scene_referred",
                    "working_latitude_stops": 14.0,
                    "upper_latitude_stops": 6.0,
                    "lower_latitude_stops": 8.0,
                    "scene_contrast_stops_estimate": 15.0,
                    "exposure_priority": "protect_skin_and_practicals",
                    "middle_gray_anchor": "the courier's face and neutral gray work shirt",
                    "highlight_behavior": "the lamp housing rolls gradually while its filament core may clip",
                    "shadow_behavior": "unlit shelf gaps fall below the texture floor without gray HDR lift",
                    "allowed_clipping": ["small desk-lamp filament core"],
                    "allowed_shadow_loss": ["deepest unlit rear-shelf gap"],
                    "local_tone_mapping": False,
                    "multi_exposure_hdr": False,
                    "narrative_reason": "Keep attention on the discovery rather than making the whole workshop equally legible.",
                },
                "focus_optics_contract": "Conversational perspective with motivated focus falloff and no universal shallow-depth template.",
                "set_causality_contract": "Every utility, object, contact, age trace and dressing choice follows workshop use and construction.",
                "performance_composition_contract": "Task-led observed behavior with plausible unused space, mild occlusion and no publicity pose.",
                "polish_ceiling": "grounded observational drama",
                "anchor_asset_ids": [self.identity_inspector_id, "loc-workshop--v001"],
                "calibration_family_ids": [],
            }
        ]
        quality["calibration_families"] = []
        write_json(self.path / "manifests/quality.json", quality)

        gate_assets = {
            "review-foundation-001": [item["id"] for item in assets if item["approval_gate_id"] == "review-foundation-001"],
            "review-seq-workshop-day-001": [item["id"] for item in assets if item["approval_gate_id"] == "review-seq-workshop-day-001"],
        }
        gate_candidate_sets = {
            gate_id: [item["id"] for item in candidate_sets if item["approval_gate_id"] == gate_id]
            for gate_id in gate_assets
        }
        gates = []
        for gate_id, gate_type, sequence_id in (
            ("review-foundation-001", "foundation", ""),
            ("review-seq-workshop-day-001", "sequence", "seq-workshop-day-001"),
        ):
            board_root = f"assets/review-boards/{gate_id}--fixture"
            overview = f"{board_root}/overview.png"
            self._file(overview)
            diagnostic_paths = {}
            for kind in ("face", "hands", "materials", "highlights", "shadows"):
                relative = f"{board_root}/{kind}.png"
                self._file(relative)
                diagnostic_paths[kind] = relative
            gates.append(
                {
                    "id": gate_id,
                    "type": gate_type,
                    "status": "approved",
                    "sequence_cluster_id": sequence_id,
                    "asset_ids": gate_assets[gate_id],
                    "profile_ids": ["cp-base-a", "cp-base-b", "cp-base-c"] if gate_type == "foundation" else [],
                    "quality_profile_ids": ["quality-main"] if gate_type == "foundation" else [],
                    "treatment_ids": ["treat-base-a", "treat-base-b", "treat-base-c"] if gate_type == "foundation" else [],
                    "format_plan_ids": ["format-plan-main-16x9"] if gate_type == "foundation" else [],
                    "comparison_set_ids": ["lookset-base-001"] if gate_type == "foundation" else [],
                    "candidate_set_ids": gate_candidate_sets[gate_id],
                    "review_board_path": overview,
                    "diagnostic_board_paths": diagnostic_paths,
                    "decision": "approved",
                    "decision_notes": ["Fixture gate approved after internal candidate isolation."],
                    "decided_at": TIMESTAMP,
                    "selections": {"lookset-base-001": "cp-base-a"} if gate_type == "foundation" else {},
                    "affected_ids": [],
                    "created_at": TIMESTAMP,
                }
            )
        write_json(self.path / "manifests/reviews.json", {"schema_version": "1.6", "review_gates": gates})

    def read(self, relative: str) -> dict[str, Any]:
        return json.loads((self.path / relative).read_text(encoding="utf-8"))

    def write(self, relative: str, value: dict[str, Any]) -> None:
        write_json(self.path / relative, value)

    def validate(self) -> dict[str, Any]:
        result = run_cli("validate", str(self.path), "--json")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise AssertionError(result.stderr or result.stdout) from exc
        payload["returncode"] = result.returncode
        return payload


class FilmProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="cinematic-ai-director-test-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def fixture(self) -> ProjectFixture:
        return ProjectFixture(self.root)

    def assert_error(self, payload: dict[str, Any], code: str) -> None:
        self.assertFalse(payload["valid"], payload)
        self.assertIn(code, [item["code"] for item in payload["errors"]], payload)

    def prepare_gate_for_board(self, fixture: ProjectFixture, gate_id: str) -> None:
        reviews = fixture.read("manifests/reviews.json")
        gate = next(item for item in reviews["review_gates"] if item["id"] == gate_id)
        gate["status"] = "building"
        gate["decision"] = "pending"
        gate["decision_notes"] = []
        gate["decided_at"] = ""
        gate["selections"] = {}
        gate["review_board_path"] = ""
        gate["diagnostic_board_paths"] = {}
        fixture.write("manifests/reviews.json", reviews)
        assets = fixture.read("manifests/assets.json")
        for asset in assets["assets"]:
            if asset.get("approval_gate_id") == gate_id and asset.get("status") == "rejected":
                asset["status"] = "qualified"
        fixture.write("manifests/assets.json", assets)

    def prepare_foundation_for_record_review(self, fixture: ProjectFixture) -> None:
        gate_id = "review-foundation-001"
        reviews = fixture.read("manifests/reviews.json")
        gate = next(item for item in reviews["review_gates"] if item["id"] == gate_id)
        gate["status"] = "ready_for_review"
        gate["decision"] = "pending"
        gate["decision_notes"] = []
        gate["decided_at"] = ""
        gate["selections"] = {}
        gate["affected_ids"] = []
        fixture.write("manifests/reviews.json", reviews)

        candidates = fixture.read("manifests/candidates.json")
        candidate_sets = {item["id"]: item for item in candidates["candidate_sets"]}
        assets = fixture.read("manifests/assets.json")
        for asset in assets["assets"]:
            if asset.get("approval_gate_id") != gate_id:
                continue
            previous_approved = asset.get("approved_path", "")
            asset["status"] = "qualified"
            candidate_set = candidate_sets.get(asset.get("candidate_set_id"))
            if candidate_set:
                selected = next(
                    variant
                    for batch in candidate_set["batches"]
                    for variant in batch["candidates"]
                    if variant["id"] == candidate_set["selected_candidate_id"]
                )
                asset["candidate_path"] = selected["path"]
            else:
                source = fixture.path / previous_approved
                candidate_relative = f"assets/candidates/provided-foundation/{asset['id']}.png"
                target = fixture.path / candidate_relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
                asset["candidate_path"] = candidate_relative
            if previous_approved:
                (fixture.path / previous_approved).unlink(missing_ok=True)
            output = asset["generation_provenance"]["output"]
            output["relative_path"] = asset["candidate_path"]
            output["sha256"] = hashlib.sha256((fixture.path / asset["candidate_path"]).read_bytes()).hexdigest()
        fixture.write("manifests/assets.json", assets)

        cinema = fixture.read("manifests/cinematography.json")
        for collection in ("profiles", "cinematic_treatments", "format_plans", "comparison_sets"):
            for record in cinema[collection]:
                if record.get("approval_gate_id") == gate_id:
                    record["status"] = "qualified"
        for profile in cinema["profiles"]:
            if profile.get("approval_gate_id") == gate_id:
                profile["approved_look_test_id"] = ""
        for comparison in cinema["comparison_sets"]:
            if comparison.get("approval_gate_id") == gate_id:
                comparison["selected_profile_id"] = ""
                comparison["selected_asset_id"] = ""
        fixture.write("manifests/cinematography.json", cinema)

        quality = fixture.read("manifests/quality.json")
        for profile in quality["project_quality_profiles"]:
            if profile.get("approval_gate_id") == gate_id:
                profile["status"] = "qualified"
        fixture.write("manifests/quality.json", quality)

        identities = fixture.read("manifests/identities.json")
        for collection in ("identity_packs", "character_states"):
            for record in identities[collection]:
                if record.get("approval_gate_id") == gate_id:
                    record["status"] = "qualified"
        fixture.write("manifests/identities.json", identities)

        world = fixture.read("manifests/world-state.json")
        for collection in ("location_worlds", "location_states", "prop_states", "environmental_states", "special_lighting_events"):
            for record in world[collection]:
                if record.get("approval_gate_id") == gate_id:
                    record["status"] = "qualified"
        fixture.write("manifests/world-state.json", world)

        spatial = fixture.read("manifests/spatial.json")
        for record in spatial["spatial_maps"]:
            if record.get("approval_gate_id") == gate_id:
                record["status"] = "qualified"
        fixture.write("manifests/spatial.json", spatial)

    def test_init_empty_project_and_refuse_overwrite(self) -> None:
        result = run_cli("init", "--root", str(self.root), "--title", "Empty", "--slug", "empty")
        self.assertEqual(result.returncode, 0, result.stderr)
        validation = run_cli("validate", str(self.root / "empty"), "--json")
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertTrue(json.loads(validation.stdout)["valid"])
        duplicate = run_cli("init", "--root", str(self.root), "--title", "Empty", "--slug", "empty")
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn("refusing to overwrite", duplicate.stderr)

    def test_full_v15_project_is_valid(self) -> None:
        payload = self.fixture().validate()
        self.assertTrue(payload["valid"], payload)
        self.assertEqual(payload["errors"], [])

    def test_base_profile_is_required_for_narrative_assets(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/cinematography.json")
        data["base_profile_id"] = ""
        fixture.write("manifests/cinematography.json", data)
        self.assert_error(fixture.validate(), "MISSING_PROFILE")

    def test_comparison_requires_exactly_three_candidates(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/cinematography.json")
        data["comparison_sets"][0]["candidate_profile_ids"].pop()
        data["comparison_sets"][0]["candidate_asset_ids"].pop()
        fixture.write("manifests/cinematography.json", data)
        self.assert_error(fixture.validate(), "LOOK_COMPARISON")

    def test_profile_requires_observable_camera_behavior(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/cinematography.json")
        data["profiles"][0]["capture"]["behavior"]["acutance"] = ""
        fixture.write("manifests/cinematography.json", data)
        payload = fixture.validate()
        self.assertTrue(any("acutance" in item["message"] for item in payload["errors"]), payload)

    def test_each_identity_view_requires_a_pure_white_background(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        character = next(item for item in data["assets"] if item.get("identity_view_role") == "full_back")
        character["identity_background_policy"] = "neutral_light"
        fixture.write("manifests/assets.json", data)
        self.assert_error(fixture.validate(), "IDENTITY_VIEW")

    def test_location_variant_requires_declared_reference_coverage(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        view = next(item for item in data["assets"] if item.get("view_role") == "establishing_wide")
        view["reference_coverage"] = None
        fixture.write("manifests/assets.json", data)
        self.assert_error(fixture.validate(), "REFERENCE_COVERAGE")

    def test_spatial_map_requires_independent_side_three_quarter_view(self) -> None:
        fixture = self.fixture()
        spatial = fixture.read("manifests/spatial.json")
        spatial["spatial_maps"][0]["side_three_quarter_view_asset_id"] = ""
        fixture.write("manifests/spatial.json", spatial)
        self.assert_error(fixture.validate(), "SCENE_STATE_VIEW")

    def test_fake_three_quarter_angle_and_missing_adjacent_plane_fail(self) -> None:
        fixture = self.fixture()
        spatial = fixture.read("manifests/spatial.json")
        spatial["spatial_maps"][0]["spatial_qa"]["three_quarter_yaw_deg"] = 8
        spatial["spatial_maps"][0]["spatial_qa"]["adjacent_planes_visible"] = False
        fixture.write("manifests/spatial.json", spatial)
        payload = fixture.validate()
        self.assert_error(payload, "THREE_QUARTER_VIEW")
        self.assertIn("SPATIAL_QA", [item["code"] for item in payload["errors"]])

    def test_scene_state_views_must_be_independent_builtin_imagegen_edits(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        view = next(item for item in assets["assets"] if item["view_role"] == "side_three_quarter_wide")
        view["generator"] = "provided"
        view["mode"] = "provided"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "SCENE_STATE_VIEW")

    def test_primary_anchor_must_be_approved_unique_scene_authority(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        anchor = next(item for item in assets["assets"] if item["id"] == "prop-red-worktable--v001")
        anchor["status"] = "qualified"
        anchor["candidate_path"] = anchor["approved_path"]
        anchor["approved_path"] = ""
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "UNAPPROVED_REFERENCE")

        fixture = ProjectFixture(self.root / "anchor-mismatch")
        project = fixture.read("project.json")
        project["scenes"][0]["primary_anchor_asset_id"] = "loc-workshop--v001"
        fixture.write("project.json", project)
        self.assert_error(fixture.validate(), "SPATIAL_ANCHOR")

    def test_anchor_must_not_drift_between_scene_state_views(self) -> None:
        fixture = self.fixture()
        spatial = fixture.read("manifests/spatial.json")
        qa_data = spatial["spatial_maps"][0]["spatial_qa"]
        qa_data["anchor_position_pass"] = False
        qa_data["hard_failures"] = ["Anchor moved 0.8 m toward the service door in the side view."]
        fixture.write("manifests/spatial.json", spatial)
        self.assert_error(fixture.validate(), "SPATIAL_QA")

    def test_anchor_must_be_direct_reference_in_both_required_views(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        side = next(item for item in assets["assets"] if item["view_role"] == "side_three_quarter_wide")
        side["reference_asset_ids"] = []
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "SPATIAL_ANCHOR")

    def test_spatial_failure_twice_requires_real_reference_or_floor_plan(self) -> None:
        fixture = self.fixture()
        spatial = fixture.read("manifests/spatial.json")
        spatial_map = spatial["spatial_maps"][0]
        spatial_map["status"] = "blocked"
        spatial_map["spatial_qa"]["attempt_index"] = 2
        spatial_map["spatial_qa"]["geography_consistency_pass"] = False
        spatial_map["spatial_qa"]["hard_failures"] = ["Door and window topology still conflict."]
        spatial_map["spatial_qa"]["escalation"] = "none"
        fixture.write("manifests/spatial.json", spatial)
        self.assert_error(fixture.validate(), "SPATIAL_ESCALATION")

    def test_ready_shot_requires_camera_and_subject_marks(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["camera_mark_id"] = "missing-camera"
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "CAMERA_MARK")

        fixture = ProjectFixture(self.root / "subject-mark")
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["subject_mark_ids"]["char-hero-body--v001"] = "missing-subject"
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "SUBJECT_MARK")

    def test_offscreen_anchor_requires_direction_distance_and_fixed_relation(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        projection = shots["shots"][0]["anchor_projection"]
        projection["visibility"] = "offscreen"
        projection["screen_region"] = ""
        projection["direction_from_camera"] = ""
        projection["set_fixed_direction"] = ""
        projection["set_fixed_relation"] = "screen left"
        projection["distance_m"] = None
        fixture.write("manifests/shots.json", shots)
        payload = fixture.validate()
        self.assert_error(payload, "ANCHOR_PROJECTION")
        codes = [item["code"] for item in payload["errors"]]
        self.assertIn("SPATIAL_DISTANCE", codes)
        self.assertIn("ENUM", codes)
        self.assertIn("SET_FIXED_RELATION", codes)

    def test_video_prompt_must_match_deterministic_spatial_map(self) -> None:
        fixture = self.fixture()
        prompt = fixture.path / "prompts/video/sh-010-010.txt"
        prompt.write_text(
            prompt.read_text(encoding="utf-8").replace("(2.0, -2.0, 1.5) m", "(9.0, 9.0, 9.0) m"),
            encoding="utf-8",
        )
        self.assert_error(fixture.validate(), "SPATIAL_PROMPT")

    def test_video_prompt_requires_skin_light_and_material_contract(self) -> None:
        fixture = self.fixture()
        prompt = fixture.path / "prompts/video/sh-010-010.txt"
        prompt.write_text(
            prompt.read_text(encoding="utf-8").replace("skin key source", "subject illumination"),
            encoding="utf-8",
        )
        self.assert_error(fixture.validate(), "SKIN_VIDEO_PROMPT")

    def test_video_prompt_rejects_synthetic_cinematic_shortcuts(self) -> None:
        fixture = self.fixture()
        prompt = fixture.path / "prompts/video/sh-010-010.txt"
        prompt.write_text(
            prompt.read_text(encoding="utf-8").replace(
                "Clean source-led digital response.",
                "Clean source-led digital response with dramatic rim light and a heroic composition.",
            ),
            encoding="utf-8",
        )
        self.assert_error(fixture.validate(), "UNCALIBRATED_RENDER_CUE")

    def test_position_changing_action_requires_manifested_start_end_path(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        beat = shots["shots"][0]["action_beats"][0]
        beat.update(
            {
                "changes_position": True,
                "subject_asset_id": fixture.identity_inspector_id,
                "start_mark_id": "mark-hero-table-near",
                "end_mark_id": "mark-hero-table-near",
            }
        )
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "MOVEMENT_PATH")

    def test_look_test_references_must_match_locked_set(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        look = next(item for item in data["assets"] if item["id"] == "look-base-a--v001")
        look["reference_asset_ids"] = ["char-hero-body--v001"]
        fixture.write("manifests/assets.json", data)
        self.assert_error(fixture.validate(), "LOOK_CONTROL")

    def test_look_prompt_repeats_story_and_blocking(self) -> None:
        fixture = self.fixture()
        prompt = fixture.path / "prompts/images/look-tests/look-base-b--v001.txt"
        prompt.write_text(prompt.read_text(encoding="utf-8").replace(STORY_MOMENT, "Another moment."), encoding="utf-8")
        self.assert_error(fixture.validate(), "LOOK_CONTROL")

    def test_look_candidate_cannot_be_an_edit_or_derivative(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        look = next(item for item in data["assets"] if item["id"] == "look-base-b--v001")
        look["mode"] = "edit"
        look["derived_from"] = "char-hero-body--v001"
        fixture.write("manifests/assets.json", data)
        self.assert_error(fixture.validate(), "LOOK_INDEPENDENCE")

    def test_profiles_must_differ_beyond_lut_or_grain(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/cinematography.json")
        baseline, shallow = data["profiles"][0], data["profiles"][1]
        for key in ("capture_circumstance", "optics", "exposure", "motion", "lighting"):
            shallow[key] = copy.deepcopy(baseline[key])
        shallow["pipeline"]["palette_response"] = "a different LUT-like color response"
        shallow["texture"]["grain_or_noise"] = "more grain"
        fixture.write("manifests/cinematography.json", data)
        self.assert_error(fixture.validate(), "LOOK_VARIATION_TOO_SHALLOW")

    def test_approved_comparison_allows_only_one_approved_candidate(self) -> None:
        fixture = self.fixture()
        cinema = fixture.read("manifests/cinematography.json")
        cinema["profiles"][1]["status"] = "approved"
        cinema["profiles"][1]["approved_look_test_id"] = "look-base-b--v001"
        fixture.write("manifests/cinematography.json", cinema)
        assets = fixture.read("manifests/assets.json")
        look = next(item for item in assets["assets"] if item["id"] == "look-base-b--v001")
        look["status"], look["approved_path"], look["candidate_path"] = "approved", look["candidate_path"], ""
        look["authenticity_qa"]["user_decision"] = "approved"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "LOOK_COMPARISON")

    def test_image_prompt_requires_strategy_sections(self) -> None:
        fixture = self.fixture()
        prompt = fixture.path / "prompts/images/loc-workshop-plate--v001.txt"
        prompt.write_text(prompt.read_text(encoding="utf-8").replace("SOURCE LIGHT AND MATERIAL RESPONSE", ""), encoding="utf-8")
        self.assert_error(fixture.validate(), "IMAGE_PROMPT_SECTION")

    def test_photographic_qa_blocks_approval(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        keyframe = next(item for item in data["assets"] if item["type"] == "keyframe")
        keyframe["photographic_qa"] = photographic_qa("cinematic_frame", passed=False)
        fixture.write("manifests/assets.json", data)
        self.assert_error(fixture.validate(), "PHOTO_QA")

    def test_live_action_quality_qa_blocks_ai_smell(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        keyframe = next(item for item in data["assets"] if item["type"] == "keyframe")
        keyframe["live_action_quality_qa"] = live_action_quality_qa(human=True, narrative=True, passed=False)
        fixture.write("manifests/assets.json", data)
        self.assert_error(fixture.validate(), "QUALITY_GATE")

    def test_foundation_gate_approval_is_required_for_authoritative_asset(self) -> None:
        fixture = self.fixture()
        reviews = fixture.read("manifests/reviews.json")
        gate = next(item for item in reviews["review_gates"] if item["type"] == "foundation")
        gate["status"] = "ready_for_review"
        gate["decision"] = "pending"
        gate["decided_at"] = ""
        gate["selections"] = {}
        fixture.write("manifests/reviews.json", reviews)
        self.assert_error(fixture.validate(), "REVIEW_GATE")

    def test_reference_rights_and_identity_consent_are_required(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        character = next(item for item in data["assets"] if item["type"] == "character_identity_inspector")
        character["reference_provenance"]["kind"] = "mixed"
        character["reference_provenance"]["rights_confirmed"] = False
        character["reference_provenance"]["identity_consent_confirmed"] = False
        fixture.write("manifests/assets.json", data)
        payload = fixture.validate()
        self.assert_error(payload, "REFERENCE_RIGHTS")
        self.assertIn("IDENTITY_CONSENT", [item["code"] for item in payload["errors"]])

    def test_two_failed_candidate_batches_require_model_blocked_escalation(self) -> None:
        fixture = self.fixture()
        candidates = fixture.read("manifests/candidates.json")
        candidate_set = next(item for item in candidates["candidate_sets"] if item["target_asset_id"] == "loc-workshop-state-day-est--v001")
        candidate_set["status"] = "model_blocked"
        fixture.write("manifests/candidates.json", candidates)
        self.assert_error(fixture.validate(), "MODEL_BLOCKED")

    def test_ready_shot_cannot_reference_failed_live_action_quality_asset(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/assets.json")
        plate = next(item for item in data["assets"] if item["type"] == "location_plate")
        plate["live_action_quality_qa"] = live_action_quality_qa(human=False, narrative=True, passed=False)
        fixture.write("manifests/assets.json", data)
        self.assert_error(fixture.validate(), "QUALITY_GATE")

    def test_ready_shot_requires_v15_model_prompt_strategy(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/shots.json")
        data["shots"][0]["model_prompt_strategy_id"] = "legacy-long-form"
        fixture.write("manifests/shots.json", data)
        self.assert_error(fixture.validate(), "VIDEO_PROMPT_STRATEGY")

    def test_multiple_camera_axes_require_location_multiview_coverage(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        reverse = copy.deepcopy(shots["shots"][0])
        reverse["id"] = "sh-010-020"
        reverse["order"] = 20
        reverse["camera_axis"] = "window-to-doorway"
        shots["shots"].append(reverse)
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "LOCATION_MULTIVIEW_REQUIRED")

        assets = fixture.read("manifests/assets.json")
        additional_ids = []
        for suffix, role, side in (
            ("front", "front_wide", "not_applicable"),
            ("right3q", "right_three_quarter_wide", "right"),
            ("reverse", "reverse_wide", "not_applicable"),
        ):
            asset_id = f"loc-workshop-state-day-{suffix}--v001"
            prompt_path = f"prompts/images/{asset_id}.txt"
            approved_path = f"assets/locations/state-views/{asset_id}--approved.png"
            fixture._file(
                prompt_path,
                image_prompt(
                    strategy="image2-live-action-location-v1.6",
                    human_subject=False,
                ),
            )
            fixture._file(approved_path)
            view = fixture._asset(
                asset_id=asset_id,
                role=f"loc-workshop-state-day-{suffix}",
                asset_type="location_variant",
                status="approved",
                generator="builtin-imagegen",
                mode="edit",
                references=["loc-workshop--v001", "prop-red-worktable--v001"],
                scenes=["sc-010"],
                photo_mode="reference_photo",
                auth_mode="neutral_reference",
                user_decision="approved",
                provenance_kind="generated_anchor",
                derived_from="loc-workshop--v001",
                prompt_path=prompt_path,
                approved_path=approved_path,
                scene_state_id="state-workshop-day",
                view_role=role,
                view_side=side,
                spatial_map_id="spatial-workshop-day",
                primary_anchor_asset_id="prop-red-worktable--v001",
                location_world_id="world-workshop",
                location_state_id="state-workshop-day",
                root_reference_ids=["loc-workshop--v001"],
                state_delta={
                    "time": "day", "weather": "dry", "dressing": "occupied workshop baseline",
                    "damage": "none", "lighting_state": "north-window daylight plus existing practicals",
                },
            )
            view["reference_coverage"] = {
                "policy": "single_view",
                "required_views": [role],
                "present_views": [role],
                "same_subject_or_geography_pass": True,
                "background_policy": "on_location_neutral",
                "notes": ["Independent multi-axis scene-state view."],
            }
            assets["assets"].append(view)
            additional_ids.append(asset_id)
        fixture.write("manifests/assets.json", assets)
        spatial = fixture.read("manifests/spatial.json")
        spatial["spatial_maps"][0]["additional_view_asset_ids"] = additional_ids
        fixture.write("manifests/spatial.json", spatial)
        world = fixture.read("manifests/world-state.json")
        world["location_states"][0]["authority_asset_ids"].extend(additional_ids)
        fixture.write("manifests/world-state.json", world)

        assets = fixture.read("manifests/assets.json")
        sequence_anchor = next(item for item in assets["assets"] if item["id"] == "seq-workshop-visual-anchor--v001")
        insert_at = sequence_anchor["reference_asset_ids"].index("loc-workshop-plate--v001")
        sequence_anchor["reference_asset_ids"][insert_at:insert_at] = additional_ids
        sequence_anchor["generation_provenance"]["reference_order"] = list(sequence_anchor["reference_asset_ids"])
        sequence_anchor["generation_provenance"]["reference_inputs"] = [
            {
                "asset_id": asset_id,
                "relative_path": next(item for item in assets["assets"] if item["id"] == asset_id)["approved_path"],
                "sha256": next(item for item in assets["assets"] if item["id"] == asset_id)["generation_provenance"]["output"]["sha256"],
            }
            for asset_id in sequence_anchor["reference_asset_ids"]
        ]
        fixture.write("manifests/assets.json", assets)
        fixture._build_quality_candidates_reviews()

        sequences = fixture.read("manifests/sequences.json")
        sequences["sequence_clusters"][0]["shot_ids"].append("sh-010-020")
        reference_order = [
            *fixture.identity_root_ids,
            "char-hero-state-baseline--v001",
            "loc-workshop-state-day-est--v001",
            "loc-workshop-state-day-side3q--v001",
            "loc-workshop-plate--v001",
            *additional_ids,
            "prop-red-worktable--v001",
            "prop-red-worktable-state-baseline--v001",
            "look-base-a--v001",
            "seq-workshop-visual-anchor--v001",
            "kf-sh-010-010-start--v001",
            "kf-sh-010-010-end--v001",
            "loc-workshop--v001",
        ]
        asset_rows = {item["id"]: item for item in assets["assets"]}
        stack_payload = [
            {"asset_id": asset_id, "sha256": asset_rows[asset_id]["generation_provenance"]["output"]["sha256"]}
            for asset_id in reference_order
        ]
        sequences["sequence_clusters"][0]["reference_order"] = reference_order
        sequences["sequence_clusters"][0]["reference_stack_sha256"] = hashlib.sha256(
            json.dumps(stack_payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()
        fixture.write("manifests/sequences.json", sequences)
        payload = fixture.validate()
        self.assertTrue(payload["valid"], payload)

    def test_fov_mismatch_is_an_error(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/shots.json")
        data["shots"][0]["fov_deg"] = 100
        fixture.write("manifests/shots.json", data)
        self.assert_error(fixture.validate(), "FOV_MISMATCH")

    def test_scene_cannot_use_rejected_override(self) -> None:
        fixture = self.fixture()
        project = fixture.read("project.json")
        project["scenes"][0]["capture_profile_id"] = "cp-base-b"
        fixture.write("project.json", project)
        self.assert_error(fixture.validate(), "UNAPPROVED_REFERENCE")

    def test_four_live_action_genres_keep_distinct_capture_families(self) -> None:
        scenarios = {
            "dialogue": ("digital", "Super 35", 27.99, 40, 38.6, "available-light interior", "fine digital texture"),
            "night-crime": ("digital", "Large Format", 36.0, 50, 39.6, "high-sensitivity night", "shadow-dependent sensor noise"),
            "period-documentary": ("16mm", "Super 16", 12.52, 16, 42.7, "high-speed 16mm", "exposure-dependent 16mm grain"),
            "precision-ad": ("digital", "Large Format", 36.0, 65, 31.0, "low-noise controlled stage", "minimal sensor texture"),
        }
        signatures: set[tuple[Any, ...]] = set()
        for name, values in scenarios.items():
            with self.subTest(name=name):
                fixture = ProjectFixture(self.root / name)
                medium, format_class, width, focal, fov, rating, texture = values
                cinema = fixture.read("manifests/cinematography.json")
                selected = cinema["profiles"][0]
                selected["capture"]["medium"], selected["capture"]["format_class"] = medium, format_class
                selected["capture"]["imaging_width_mm"], selected["exposure"]["rating"] = width, rating
                selected["texture"]["grain_or_noise"] = texture
                fixture.write("manifests/cinematography.json", cinema)
                shots = fixture.read("manifests/shots.json")
                shots["shots"][0]["focal_length_mm"], shots["shots"][0]["fov_deg"] = focal, fov
                fixture.write("manifests/shots.json", shots)
                payload = fixture.validate()
                self.assertTrue(payload["valid"], payload)
                signatures.add((medium, format_class, width, focal, rating, texture))
        self.assertEqual(len(signatures), 4)

    def test_ready_shot_requires_focus_and_exposure_fields(self) -> None:
        fixture = self.fixture()
        data = fixture.read("manifests/shots.json")
        data["shots"][0]["focus_plan"] = ""
        data["shots"][0]["exposure_notes"] = ""
        fixture.write("manifests/shots.json", data)
        self.assert_error(fixture.validate(), "TYPE")

    def test_every_photographic_asset_requires_its_own_dynamic_range_plan(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        location = next(item for item in assets["assets"] if item["id"] == "loc-workshop-state-day-est--v001")
        del location["dynamic_range_plan"]
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "MISSING_FIELD")

    def test_scene_contrast_over_latitude_requires_an_explicit_tonal_sacrifice(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        plan = shots["shots"][0]["dynamic_range_plan"]
        plan["scene_contrast_stops_estimate"] = 18.0
        plan["allowed_clipping"] = []
        plan["allowed_shadow_loss"] = []
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "DYNAMIC_RANGE_SACRIFICE")

    def test_local_tone_mapping_or_hdr_merge_is_not_a_live_action_exposure(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        location = next(item for item in assets["assets"] if item["id"] == "loc-workshop-state-day-est--v001")
        location["dynamic_range_plan"]["local_tone_mapping"] = True
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "DYNAMIC_RANGE")

    def test_global_hdr_behavior_fails_pixel_quality_evidence(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["live_action_quality_qa"]["dynamic_range_evidence"]["global_tone_mapping_detected"] = True
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "DYNAMIC_RANGE")

    def test_higgsfield_export_is_portable_deterministic_and_verifiable(self) -> None:
        fixture = self.fixture()
        first = self.root / "portable-export-a"
        second = self.root / "portable-export-b"
        result_a = run_cli("export-higgsfield", str(fixture.path), "--output", str(first))
        self.assertEqual(result_a.returncode, 0, result_a.stdout + result_a.stderr)
        result_b = run_cli("export-higgsfield", str(fixture.path), "--output", str(second))
        self.assertEqual(result_b.returncode, 0, result_b.stdout + result_b.stderr)

        files_a = {
            path.relative_to(first).as_posix(): path.read_bytes()
            for path in first.rglob("*")
            if path.is_file()
        }
        files_b = {
            path.relative_to(second).as_posix(): path.read_bytes()
            for path in second.rglob("*")
            if path.is_file()
        }
        self.assertEqual(files_a, files_b)
        self.assertIn("upload-order.csv", files_a)
        self.assertIn("official-conformance.json", files_a)
        self.assertIn("shot-list.csv", files_a)
        self.assertIn("reference-map.json", files_a)
        self.assertIn("shots/sc-010/sh-010-010/prompt.txt", files_a)
        self.assertIn("shots/sc-010/sh-010-010/settings.json", files_a)
        self.assertIn("shots/sc-010/sh-010-010/spatial-map.json", files_a)
        self.assertIn("shots/sc-010/sh-010-010/format-plan.json", files_a)
        self.assertIn("shots/sc-010/sh-010-010/camera-path.json", files_a)
        self.assertIn("shots/sc-010/sh-010-010/environment-state.json", files_a)
        self.assertIn("shots/sc-010/sh-010-010/dynamic-range.json", files_a)
        self.assertIn("shots/sc-010/sh-010-010/temporal-lock.json", files_a)
        self.assertIn("production/creative-bible.md", files_a)
        self.assertIn("production/edit-plan.md", files_a)
        self.assertIn("production/manifests/spatial.json", files_a)
        self.assertIn("production/manifests/shots.json", files_a)
        self.assertIn("production/qa/spatial-review.md", files_a)
        self.assertIn("production/manifests/identities.json", files_a)
        self.assertIn("production/manifests/world-state.json", files_a)
        self.assertIn("production/manifests/sequences.json", files_a)
        self.assertIn("production/manifests/takes.json", files_a)
        self.assertIn("production/manifests/quality.json", files_a)
        self.assertIn("production/manifests/candidates.json", files_a)
        self.assertIn("production/manifests/reviews.json", files_a)
        self.assertIn("production/qa/cross-scene-review.md", files_a)
        self.assertIn("production/qa/proportion-review.md", files_a)
        self.assertIn("production/qa/quality-review.md", files_a)
        self.assertIn("production/qa/environment-review.md", files_a)
        self.assertIn("production/qa/temporal-review.md", files_a)
        self.assertIn("sequences/seq-workshop-day-001/reference-map.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/state-lock.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/spatial-map.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/format-plan.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/camera-path.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/environment-state.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/dynamic-range.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/temporal-lock.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/quality-profile.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/sequence-anchor.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/settings.json", files_a)
        self.assertIn("sequences/seq-workshop-day-001/prompt.txt", files_a)
        self.assertIn("sequences/seq-workshop-day-001/verify.py", files_a)
        self.assertIn("soul-id-prep.json", files_a)
        self.assertIn("elements-soul-cast-prep.json", files_a)
        self.assertNotIn(str(self.root).encode("utf-8"), b"\n".join(files_a.values()))

        prompt_text = files_a["shots/sc-010/sh-010-010/prompt.txt"].decode("utf-8")
        official = json.loads(files_a["official-conformance.json"])
        self.assertEqual(official["profile_id"], "cinema-studio-4-seedance-2.5-official-2026-08-27")
        self.assertEqual(official["target"], {"model": "seedance-2.5", "workflow": "cinema-studio-4"})
        capabilities = official["verified_contract"]["published_capabilities"]
        self.assertEqual(capabilities["maximum_reference_inputs"], 50)
        self.assertEqual(capabilities["maximum_duration_s"], 30)
        self.assertEqual(capabilities["maximum_native_resolution"], "1080p")
        self.assertEqual(capabilities["aspect_ratio_range"], "9:16 through 21:9")
        self.assertTrue(capabilities["native_audio"])
        self.assertTrue(prompt_text.startswith("GLOBAL STYLE\n"))
        self.assertIn("@prop-red-worktable", prompt_text)
        references_text = files_a["shots/sc-010/sh-010-010/references.csv"].decode("utf-8")
        self.assertLess(references_text.index("identity_inspector_primary"), references_text.index("current_character_state"))
        self.assertLess(references_text.index("location_shot_view"), references_text.index("location_three_quarter"))
        self.assertLess(references_text.index("location_three_quarter"), references_text.index("spatial_anchor"))
        spatial_payload = json.loads(files_a["shots/sc-010/sh-010-010/spatial-map.json"])
        self.assertEqual(spatial_payload["primary_anchor"]["asset_id"], "prop-red-worktable--v001")
        self.assertEqual(spatial_payload["camera_mark"]["id"], "cam-sh-010-010")
        settings_payload = json.loads(files_a["shots/sc-010/sh-010-010/settings.json"])
        self.assertEqual(settings_payload["spatial_translation"]["spatial_map_id"], "spatial-workshop-day")
        self.assertEqual(settings_payload["format"]["exposure_time_s"], 1 / 48)
        self.assertEqual(settings_payload["state_lock"]["environmental_state_id"], "env-workshop-clear")
        self.assertEqual(settings_payload["dynamic_range_file"], "shots/sc-010/sh-010-010/dynamic-range.json")
        dynamic_payload = json.loads(files_a["shots/sc-010/sh-010-010/dynamic-range.json"])
        self.assertEqual(dynamic_payload["plan"]["exposure_priority"], "protect_skin_and_practicals")
        self.assertFalse(dynamic_payload["plan"]["local_tone_mapping"])
        self.assertFalse(dynamic_payload["plan"]["multi_exposure_hdr"])
        temporal_payload = json.loads(files_a["shots/sc-010/sh-010-010/temporal-lock.json"])
        self.assertFalse(temporal_payload["motion_blur_plan"]["frame_blending_allowed"])
        sequence_lock = json.loads(files_a["sequences/seq-workshop-day-001/state-lock.json"])
        self.assertEqual(sequence_lock["state_signature"]["character_state_ids"], ["state-char-hero-baseline"])
        self.assertFalse(sequence_lock["bridge"]["may_replace_root_authorities"])
        sequence_verify = subprocess.run(
            [sys.executable, str(first / "sequences/seq-workshop-day-001/verify.py")],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(sequence_verify.returncode, 0, sequence_verify.stdout + sequence_verify.stderr)

        verify = subprocess.run(
            [sys.executable, str(first / "verify_package.py")],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        self.assertIn("VALID package", verify.stdout)

        duplicate = run_cli("export-higgsfield", str(fixture.path), "--output", str(first))
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn("refusing to overwrite", duplicate.stderr)

    def test_higgsfield_export_blocks_invalid_or_unready_projects(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        character = next(item for item in assets["assets"] if item.get("identity_view_role") == "full_back")
        character["identity_background_policy"] = "neutral_light"
        fixture.write("manifests/assets.json", assets)
        output = self.root / "must-not-exist"
        invalid = run_cli("export-higgsfield", str(fixture.path), "--output", str(output))
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("validation failed", invalid.stderr)
        self.assertFalse(output.exists())

        fixture = ProjectFixture(self.root / "no-ready")
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["status"] = "planned"
        fixture.write("manifests/shots.json", shots)
        sequences = fixture.read("manifests/sequences.json")
        sequences["sequence_clusters"][0]["status"] = "planned"
        fixture.write("manifests/sequences.json", sequences)
        output = self.root / "no-ready-export"
        empty = run_cli("export-higgsfield", str(fixture.path), "--output", str(output))
        self.assertEqual(empty.returncode, 1)
        self.assertIn("no ready/generated/selected shots", empty.stderr)
        self.assertFalse(output.exists())

    def test_higgsfield_export_rejects_machine_specific_paths_in_production_facts(self) -> None:
        fixture = self.fixture()
        bible = fixture.path / "creative-bible.md"
        bible.write_text(
            bible.read_text(encoding="utf-8") + "\nMachine note: /Users/example/Desktop/private-frame.png\n",
            encoding="utf-8",
        )
        output = self.root / "unsafe-export"
        result = run_cli("export-higgsfield", str(fixture.path), "--output", str(output))
        self.assertEqual(result.returncode, 2)
        self.assertIn("machine-specific absolute path", result.stderr)
        self.assertFalse(output.exists())

    def test_quality_gate_rejects_smear_at_any_required_scale(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["live_action_quality_qa"] = live_action_quality_qa(human=True, narrative=True, passed=False)
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "QUALITY_GATE")

    def test_cross_material_repeating_texture_is_a_hard_failure(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        location = next(item for item in assets["assets"] if item["id"] == "loc-workshop--v001")
        location["live_action_quality_qa"]["material_pairs"][0]["same_repeating_texture"] = True
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "QUALITY_HARD_FAIL")

    def test_uncalibrated_generic_dirty_texture_word_is_rejected(self) -> None:
        fixture = self.fixture()
        prompt = fixture.path / "prompts/images/loc-workshop-state-day-est--v001.txt"
        prompt.write_text(
            prompt.read_text(encoding="utf-8").replace(
                "Existing north window and desk lamp shape",
                "Make every surface weathered and gritty. Existing north window and desk lamp shape",
            ),
            encoding="utf-8",
        )
        self.assert_error(fixture.validate(), "UNCALIBRATED_TEXTURE_CUE")

    def test_uncalibrated_game_cinematic_and_fake_rim_light_cues_are_rejected(self) -> None:
        fixture = self.fixture()
        prompt = fixture.path / "prompts/images/kf-sh-010-010-start--v001.txt"
        prompt.write_text(
            prompt.read_text(encoding="utf-8").replace(
                "A physically present production camera records an observed event.",
                "A physically present production camera records an observed event. "
                "Use game cinematic rendering, synthetic glossy skin and a heroic composition.",
            ),
            encoding="utf-8",
        )
        self.assert_error(fixture.validate(), "UNCALIBRATED_RENDER_CUE")

    def test_human_asset_requires_explicit_skin_illumination_contract(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["material_response_contract"]["skin_key_source"] = ""
        keyframe["material_response_contract"]["skin_key_source_size"] = ""
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "SKIN_ILLUMINATION")

    def test_dry_skin_contract_rejects_unmotivated_oil_sheen(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["material_response_contract"]["skin_specular_behavior"] = "Add a uniform oil sheen over the face."
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "SKIN_ILLUMINATION")

    def test_promotional_game_pose_in_material_contract_is_rejected(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["material_response_contract"]["performance_staging_policy"] = "A heroic pose arranged like a trailer still."
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "MATERIAL_RESPONSE")

    def test_state_asset_cannot_recursively_derive_from_another_state(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        state = next(item for item in assets["assets"] if item["type"] == "character_state")
        state["derived_from"] = "char-hero-state-baseline--v001"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "RECURSIVE_STATE")

    def test_character_state_delta_cannot_modify_immutable_identity(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        identities["character_states"][0]["state_delta"]["feature_spacing"] = "wider eye spacing"
        fixture.write("manifests/identities.json", identities)
        assets = fixture.read("manifests/assets.json")
        state = next(item for item in assets["assets"] if item["type"] == "character_state")
        state["state_delta"]["feature_spacing"] = "wider eye spacing"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "IMMUTABLE_IDENTITY")

    def test_location_state_delta_cannot_change_world_topology(self) -> None:
        fixture = self.fixture()
        world = fixture.read("manifests/world-state.json")
        world["location_states"][0]["state_delta"]["topology"] = "new doorway"
        fixture.write("manifests/world-state.json", world)
        assets = fixture.read("manifests/assets.json")
        for asset in assets["assets"]:
            if asset.get("location_state_id") == "state-workshop-day" and asset["type"] in {"location_variant", "location_plate"}:
                asset["state_delta"]["topology"] = "new doorway"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "LOCATION_DRIFT")

    def test_ready_shot_requires_exact_character_location_and_prop_state_bindings(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["character_state_bindings"] = {}
        shots["shots"][0]["location_state_id"] = ""
        shots["shots"][0]["prop_state_bindings"] = {}
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "STATE_BINDING")

    def test_sequence_cluster_rejects_mixed_state_signature(self) -> None:
        fixture = self.fixture()
        sequences = fixture.read("manifests/sequences.json")
        sequences["sequence_clusters"][0]["state_signature"]["lighting_state"] = "unmotivated alternate light"
        fixture.write("manifests/sequences.json", sequences)
        self.assert_error(fixture.validate(), "SEQUENCE_STATE_MISMATCH")

    def test_higgsfield_adapter_reference_limit_blocks_oversubscribed_sequence(self) -> None:
        fixture = self.fixture()
        sequences = fixture.read("manifests/sequences.json")
        sequences["sequence_clusters"][0]["target_workflow"] = "popcorn"
        sequences["sequence_clusters"][0]["reference_limit"] = 4
        fixture.write("manifests/sequences.json", sequences)
        self.assert_error(fixture.validate(), "REFERENCE_LIMIT")

    def test_generated_asset_records_workflow_only_not_pixel_reproducibility(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        look = next(item for item in assets["assets"] if item["id"] == "look-base-a--v001")
        look["generation_provenance"]["pixel_reproducible"] = True
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "REPRODUCIBILITY")

    def test_generation_provenance_hash_detects_changed_asset_bytes(self) -> None:
        fixture = self.fixture()
        path = fixture.path / "assets/keyframes/kf-sh-010-010-start--v001--approved.png"
        path.write_text("bytes changed after approval", encoding="utf-8")
        self.assert_error(fixture.validate(), "PROVENANCE_HASH")

    def test_invalid_model_blocked_status_requires_two_all_fail_batches(self) -> None:
        fixture = self.fixture()
        candidates = fixture.read("manifests/candidates.json")
        candidate_set = next(item for item in candidates["candidate_sets"] if item["target_asset_id"] == "loc-workshop-state-day-est--v001")
        candidate_set["status"] = "model_blocked"
        fixture.write("manifests/candidates.json", candidates)
        self.assert_error(fixture.validate(), "MODEL_BLOCKED")

    def test_identity_pack_requires_face_body_and_seven_view_authorities(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        identities["identity_packs"][0]["face_anchor_asset_id"] = ""
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "IDENTITY_AUTHORITY")

    def test_identity_pack_rejects_a_missing_canonical_view(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        identities["identity_packs"][0]["identity_view_asset_ids"].pop("portrait_right_profile")
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "IDENTITY_VIEW")

    def test_identity_view_cannot_recursively_derive_from_another_angle(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        view = next(item for item in assets["assets"] if item.get("identity_view_role") == "full_back")
        view["derived_from"] = "char-hero-full-front--v001"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "IDENTITY_CROP")

    def test_geometry_measurement_drift_is_a_hard_failure(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        body = next(item for item in assets["assets"] if item["id"] == "char-hero-full-front--v001")
        body["geometry_qa"]["measurements_compared"][0]["observed"] = 0.19
        body["geometry_qa"]["measurements_compared"][0]["pass"] = False
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "PROPORTION_DRIFT")

    def test_identity_skeleton_and_character_state_must_preserve_proportions(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        identities["identity_packs"][0]["skeletal_lock"]["locked"] = False
        identities["character_states"][0]["preserve_proportion_signature"] = False
        identities["character_states"][0]["soft_tissue_delta"]["preserve_skeleton"] = False
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PROPORTION_DRIFT")

    def test_live_action_quality_gate_rejects_animation_or_cg_prior(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["live_action_quality_qa"] = live_action_quality_qa(human=True, narrative=True, passed=False)
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "QUALITY_GATE")

    def test_live_action_quality_gate_rejects_synthetic_skin_highlight_topology(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["live_action_quality_qa"]["checks"]["skin_specular_topology"] = "fail"
        keyframe["live_action_quality_qa"]["verdict"] = "fail"
        keyframe["live_action_quality_qa"]["hard_failures"] = ["face carries small glossy highlights unrelated to any declared source"]
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "QUALITY_GATE")

    def test_live_action_quality_gate_rejects_game_cinematic_staging(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["live_action_quality_qa"]["checks"]["photographic_event_plausibility"] = "fail"
        keyframe["live_action_quality_qa"]["checks"]["performance_observation_not_promo_pose"] = "fail"
        keyframe["live_action_quality_qa"]["verdict"] = "fail"
        keyframe["live_action_quality_qa"]["hard_failures"] = ["game-trailer render signature and publicity pose"]
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "QUALITY_GATE")

    def test_clean_authority_cannot_enable_a_medium_signature(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        face = next(item for item in assets["assets"] if item["id"] == fixture.identity_inspector_id)
        face["surface_policy"] = "calibrated_medium_signature"
        face["medium_signature_id"] = "medium-test"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "SURFACE_POLICY")

    def test_unstable_medium_signature_cannot_reach_a_narrative_asset(self) -> None:
        fixture = self.fixture()
        cinema = fixture.read("manifests/cinematography.json")
        cinema["profiles"][0]["medium_signature_id"] = "medium-unstable"
        cinema["medium_signatures"].append(
            {
                "id": "medium-unstable",
                "status": "calibrating",
                "asset_families": ["keyframe"],
                "story_use": "diagnostic only",
                "rationale": "not yet stable across independent runs",
                "prompt_terms": ["controlled medium behavior"],
                "protected_regions": ["skin", "eyes", "fabric"],
                "calibration_runs": [],
                "fallback_policy": "clean_narrative_after_one_artifact_failure",
            }
        )
        fixture.write("manifests/cinematography.json", cinema)
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["surface_policy"] = "calibrated_medium_signature"
        keyframe["medium_signature_id"] = "medium-unstable"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "MEDIUM_CALIBRATION")

    def test_nonclear_environment_requires_material_and_distance_physics(self) -> None:
        fixture = self.fixture()
        world = fixture.read("manifests/world-state.json")
        environment = world["environmental_states"][0]
        environment["kind"] = "fog"
        environment["material_interactions"] = []
        environment["light_behavior"]["distance_behavior"] = ""
        fixture.write("manifests/world-state.json", world)
        self.assert_error(fixture.validate(), "ENVIRONMENT_PHYSICS")

    def test_format_plan_rejects_baked_black_bars(self) -> None:
        fixture = self.fixture()
        cinema = fixture.read("manifests/cinematography.json")
        cinema["format_plans"][0]["baked_black_bars"] = True
        fixture.write("manifests/cinematography.json", cinema)
        self.assert_error(fixture.validate(), "FORMAT_PLAN")

    def test_locked_camera_path_rejects_translation_or_rotation(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["camera_move_plan"]["translation_m"] = 1.0
        shots["shots"][0]["camera_move_plan"]["rotation_deg"]["yaw"] = 15.0
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "CAMERA_PATH")

    def test_shutter_formula_is_enforced(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["temporal_capture"]["exposure_time_s"] = 1 / 24
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "SHUTTER_EXPOSURE_MISMATCH")

    def test_speed_ramp_times_must_increase(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["temporal_capture"]["speed_ramp"] = [
            {"time_s": 3.0, "playback_rate": 1.0},
            {"time_s": 2.0, "playback_rate": 0.5},
        ]
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "SPEED_RAMP")

    def test_locked_camera_cannot_claim_camera_induced_motion_blur(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["motion_blur_plan"]["source"] = "camera"
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "MOTION_BLUR")

    def test_motion_blur_forbids_frame_blending_and_ghosting(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["motion_blur_plan"]["frame_blending_allowed"] = True
        shots["shots"][0]["motion_blur_plan"]["ghosting_allowed"] = True
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "MOTION_BLUR")

    def test_higgsfield_camera_move_segment_limit_is_enforced(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["adapter_notes"]["higgsfield"] = {
            "camera_path_segments": ["dolly in", "pan", "orbit", "settle"]
        }
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "CAMERA_PATH_LIMIT")

    def test_high_risk_action_requires_a_pose_contact_anchor(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shot = shots["shots"][0]
        shot["motion_class"] = "action"
        shot["material_interaction_plan"]["required"] = True
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "POSE_CONTACT_ANCHOR")

    def test_video_prompt_must_carry_physical_motion_blur_direction(self) -> None:
        fixture = self.fixture()
        prompt_path = fixture.path / "prompts/video/sh-010-010.txt"
        prompt = prompt_path.read_text(encoding="utf-8")
        prompt_path.write_text(
            prompt.replace(
                "brief head and eye motion blur follows the actual turn toward the case",
                "generic cinematic motion blur",
            ),
            encoding="utf-8",
        )
        self.assert_error(fixture.validate(), "MOTION_BLUR_PROMPT")

    def test_take_temporal_qa_requires_all_event_and_interval_checks(self) -> None:
        fixture = self.fixture()
        fixture._file("takes/sh-010-010--take-001.mp4", "video fixture")
        takes = {
            "schema_version": "1.6",
            "takes": [
                {
                    "id": "take-sh-010-010-001",
                    "shot_id": "sh-010-010",
                    "status": "approved",
                    "source_path": "takes/sh-010-010--take-001.mp4",
                    "source_provider": "Higgsfield manual user generation",
                    "automatic_platform_call": False,
                    "credits_consumed_by_skill": False,
                    "temporal_qa": {
                        "sample_points": {"start": 0.0, "25_percent": 1.0, "50_percent": 2.0, "75_percent": 3.0, "end": 4.0},
                        "event_samples": [{"event": "focus rack", "time_s": 2.0}],
                        "checks": {name: "pass" for name in TEMPORAL_TAKE_CHECKS},
                        "verdict": "pass",
                        "hard_failures": [],
                        "notes": [],
                        "checked_at": TIMESTAMP,
                        "reviewer": "codex-visual",
                    },
                    "created_at": TIMESTAMP,
                }
            ],
        }
        fixture.write("manifests/takes.json", takes)
        self.assertTrue(fixture.validate()["valid"], fixture.validate())
        takes["takes"][0]["temporal_qa"]["checks"]["texture_crawl_and_flicker"] = "fail"
        fixture.write("manifests/takes.json", takes)
        self.assert_error(fixture.validate(), "TEMPORAL_GATE")

    def test_reference_board_is_deterministic_and_never_repaints_identity(self) -> None:
        def reset_for_crop_build(fixture: ProjectFixture) -> tuple[Path, bytes]:
            assets = fixture.read("manifests/assets.json")
            inspector = next(item for item in assets["assets"] if item["id"] == fixture.identity_inspector_id)
            inspector_path = fixture.path / inspector["approved_path"]
            width = 8
            rows = [
                *((72, 78, 86),) * 10,
                *((255, 255, 255),) * 2,
                *((96, 102, 110),) * 8,
            ]
            raw = b"".join(bytes([0]) + bytes(rgb) * width for rgb in rows)
            header = struct.pack(">IIBBBBB", width, len(rows), 8, 2, 0, 0, 0)

            def chunk(kind: bytes, payload: bytes) -> bytes:
                return (
                    struct.pack(">I", len(payload))
                    + kind
                    + payload
                    + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
                )

            inspector_bytes = (
                b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(raw))
                + chunk(b"IEND", b"")
            )
            inspector_path.write_bytes(inspector_bytes)
            output = inspector["generation_provenance"]["output"]
            output["sha256"] = hashlib.sha256(inspector_bytes).hexdigest()
            output["width_px"] = width
            output["height_px"] = len(rows)
            for asset in assets["assets"]:
                if asset.get("generator") != "deterministic-crop":
                    continue
                existing = fixture.path / asset["approved_path"]
                existing.unlink()
                asset["candidate_path"] = asset["approved_path"]
                asset["approved_path"] = ""
                asset["status"] = "planned"
            fixture.write("manifests/assets.json", assets)
            identities = fixture.read("manifests/identities.json")
            pack = identities["identity_packs"][0]
            map_path = fixture.path / pack["reference_board"]["crop_map_path"]
            map_path.unlink()
            pack["status"] = "qualified"
            pack["reference_board"] = {
                "status": "planned",
                "relative_path": "",
                "sha256": "",
                "source_sha256s": {},
                "layout_profile": "higgsfield-character-reference-sheet-two-row-single-solve-v1.6",
                "authoritative": True,
                "crop_map_path": "",
            }
            fixture.write("manifests/identities.json", identities)
            return inspector_path, inspector_bytes

        fixture = self.fixture()
        inspector_path, inspector_before = reset_for_crop_build(fixture)
        result = run_cli(
            "build-reference-board",
            str(fixture.path),
            "--identity-pack",
            "identity-char-hero",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        board_map = fixture.path / "assets/reference-boards/identity-char-hero--identity-crops-v001.json"
        self.assertEqual(inspector_before, inspector_path.read_bytes())
        metadata = json.loads(board_map.read_text(encoding="utf-8"))
        self.assertTrue(metadata["authoritative"])
        self.assertEqual(metadata["generation"], "one-imagegen-call-then-deterministic-crops")
        self.assertEqual(len(metadata["slots"]), 7)
        self.assertEqual(metadata["identity_inspector_asset_id"], fixture.identity_inspector_id)
        self.assertEqual(metadata["row_split_px"], 11)
        self.assertEqual(metadata["gutter_detection"]["accepted_gutter_rows_px"], [10, 12])
        self.assertEqual(metadata["slots"][0]["crop_box_px"], [0, 0, 2, 11])
        self.assertEqual(metadata["slots"][4]["crop_box_px"], [0, 11, 2, 9])
        first_crops = {
            slot["role"]: (fixture.path / next(
                item["candidate_path"] for item in fixture.read("manifests/assets.json")["assets"]
                if item["id"] == slot["asset_id"]
            )).read_bytes()
            for slot in metadata["slots"]
        }

        second = ProjectFixture(self.root / "second-board")
        _, second_inspector_before = reset_for_crop_build(second)
        second_result = run_cli(
            "build-reference-board",
            str(second.path),
            "--identity-pack",
            "identity-char-hero",
        )
        self.assertEqual(second_result.returncode, 0, second_result.stdout + second_result.stderr)
        second_map = json.loads((second.path / "assets/reference-boards/identity-char-hero--identity-crops-v001.json").read_text(encoding="utf-8"))
        self.assertEqual(inspector_before, second_inspector_before)
        second_assets = second.read("manifests/assets.json")["assets"]
        second_crops = {
            slot["role"]: (second.path / next(item["candidate_path"] for item in second_assets if item["id"] == slot["asset_id"])).read_bytes()
            for slot in second_map["slots"]
        }
        self.assertEqual(first_crops, second_crops)
        duplicate = run_cli(
            "build-reference-board",
            str(fixture.path),
            "--identity-pack",
            "identity-char-hero",
        )
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn("refusing to overwrite", duplicate.stderr)

    def test_identity_gutter_detector_rejects_a_board_without_a_clear_split(self) -> None:
        pixels = bytes((72, 78, 86)) * 8 * 10
        with self.assertRaisesRegex(ValueError, "no deterministic near-white horizontal gutter"):
            _detect_horizontal_gutter_split(8, 10, pixels)

    def test_aspirational_role_physique_requires_measurable_targets(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        identities["identity_packs"][0]["role_physique_brief"]["quantitative_targets"] = []
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PHYSIQUE_TARGET")

    def test_fashion_model_physique_is_also_target_driven(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        brief = identities["identity_packs"][0]["role_physique_brief"]
        brief["classification"] = "fashion_model"
        brief["quantitative_targets"] = brief["quantitative_targets"][:1]
        brief["candidate_rejection_criteria"] = brief["candidate_rejection_criteria"][:1]
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PHYSIQUE_TARGET")

    def test_role_physique_target_cannot_use_an_unmeasured_composite(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        target = identities["identity_packs"][0]["role_physique_brief"]["quantitative_targets"][0]
        target["metric"] = "leg_to_height"
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PHYSIQUE_TARGET")

    def test_role_physique_target_must_match_approved_body_signature(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        target = identities["identity_packs"][0]["role_physique_brief"]["quantitative_targets"][0]
        target["minimum"] = 0.16
        target["maximum"] = 0.18
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PHYSIQUE_MISMATCH")

    def test_unintended_five_five_visual_balance_is_blocked(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        balance = identities["identity_packs"][0]["role_physique_brief"]["visual_body_balance"]
        balance["upper_body_share_range"] = [0.48, 0.52]
        balance["lower_body_share_range"] = [0.48, 0.52]
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PHYSIQUE_BALANCE")

    def test_role_physique_fit_qa_rejects_bad_wardrobe_silhouette(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        fit = identities["identity_packs"][0]["physique_fit_qa"]
        fit["checks"]["wardrobe_silhouette_fit"] = False
        fit["verdict"] = "fail"
        fit["hard_failures"] = ["Boxy garment generation hides the role-required leg, waist and shoulder proportions."]
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PHYSIQUE_GATE")

    def test_ready_shot_requires_exact_role_physique_lock(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["body_geometry_locks"][fixture.identity_inspector_id]["role_physique_brief_id"] = "generic-body"
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "PHYSIQUE_LOCK")

    def test_character_state_cannot_drop_role_physique(self) -> None:
        fixture = self.fixture()
        identities = fixture.read("manifests/identities.json")
        identities["character_states"][0]["preserve_role_physique"] = False
        fixture.write("manifests/identities.json", identities)
        self.assert_error(fixture.validate(), "PHYSIQUE_DRIFT")

    def test_critical_candidate_pool_requires_three_independent_generations(self) -> None:
        fixture = self.fixture()
        candidates = fixture.read("manifests/candidates.json")
        look_set = next(item for item in candidates["candidate_sets"] if item["target_asset_id"] == "look-base-a--v001")
        look_set["batches"][0]["candidates"].pop()
        fixture.write("manifests/candidates.json", candidates)
        self.assert_error(fixture.validate(), "CANDIDATE_COUNT")

    def test_derivative_candidate_pool_requires_two_independent_generations(self) -> None:
        fixture = self.fixture()
        candidates = fixture.read("manifests/candidates.json")
        view_set = next(item for item in candidates["candidate_sets"] if item["target_asset_id"] == "loc-workshop-state-day-est--v001")
        view_set["batches"][0]["candidates"].pop()
        fixture.write("manifests/candidates.json", candidates)
        self.assert_error(fixture.validate(), "CANDIDATE_COUNT")

    def test_candidate_must_not_edit_or_derive_from_another_candidate(self) -> None:
        fixture = self.fixture()
        candidates = fixture.read("manifests/candidates.json")
        candidate_set = next(item for item in candidates["candidate_sets"] if len(item["batches"][0]["candidates"]) > 1)
        variant = candidate_set["batches"][0]["candidates"][1]
        variant["operation"] = "edit"
        variant["derived_from_candidate_id"] = candidate_set["batches"][0]["candidates"][0]["id"]
        fixture.write("manifests/candidates.json", candidates)
        self.assert_error(fixture.validate(), "CANDIDATE_INDEPENDENCE")

    def test_retry_batch_is_forbidden_when_first_batch_has_a_pass(self) -> None:
        fixture = self.fixture()
        candidates = fixture.read("manifests/candidates.json")
        candidate_set = next(item for item in candidates["candidate_sets"] if item["target_asset_id"] == "loc-workshop-state-day-est--v001")
        retry_variants = []
        for index in (1, 2):
            relative = f"assets/candidates/{candidate_set['id']}/retry-{index}.png"
            data = tiny_png_bytes((90 + index, 80, 70))
            path = fixture.path / relative
            path.write_bytes(data)
            retry_variants.append({
                "id": f"{candidate_set['id']}-retry-{index}",
                "status": "failed",
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
                "operation": "generate",
                "derived_from_candidate_id": "",
                "prompt_sha256": candidate_set["batches"][0]["candidates"][0]["prompt_sha256"],
                "reference_order": list(candidate_set["reference_asset_ids"]),
                "quality_verdict": "fail",
                "hard_failures": ["retry fixture failure"],
                "diagnostic_regions": {kind: [] for kind in ("face", "hands", "materials", "highlights", "shadows")},
                "reviewed_at": TIMESTAMP,
            })
        candidate_set["batches"].append({
            "index": 2,
            "reason": "invalid retry despite a passing first candidate",
            "changed_variable": "lighting phrase",
            "candidates": retry_variants,
        })
        fixture.write("manifests/candidates.json", candidates)
        self.assert_error(fixture.validate(), "CANDIDATE_RETRY")

    def test_failed_candidates_never_occupy_authoritative_asset_roles(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")["assets"]
        candidates = fixture.read("manifests/candidates.json")
        authoritative_ids = {item["id"] for item in assets}
        failed = [
            variant
            for candidate_set in candidates["candidate_sets"]
            for batch in candidate_set["batches"]
            for variant in batch["candidates"]
            if variant["status"] == "failed"
        ]
        self.assertTrue(failed)
        self.assertTrue(all(item["id"] not in authoritative_ids for item in failed))
        self.assertFalse(candidates["policy"]["failed_candidates_visible_by_default"])

    def test_live_action_quality_requires_positive_evidence_not_only_absence(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        keyframe["live_action_quality_qa"]["positive_evidence"]["skin_specular_topology"] = ""
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "QUALITY_GATE")

    def test_non_default_skin_state_requires_cause_and_bounded_regions(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        keyframe = next(item for item in assets["assets"] if item["id"] == "kf-sh-010-010-start--v001")
        quality = keyframe["live_action_quality_qa"]
        quality["skin_surface_state"] = "perspiration"
        quality["skin_state_cause"] = ""
        quality["skin_state_regions"] = []
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "SKIN_STATE")

    def test_quality_qa_cannot_store_duplicate_user_decisions(self) -> None:
        fixture = self.fixture()
        assets = fixture.read("manifests/assets.json")
        assets["assets"][0]["live_action_quality_qa"]["user_decision"] = "approved"
        fixture.write("manifests/assets.json", assets)
        self.assert_error(fixture.validate(), "APPROVAL_SCOPE")

    def test_compile_prompts_is_deterministic_updates_hashes_and_refuses_overwrite(self) -> None:
        first = self.fixture()
        second = ProjectFixture(self.root / "compiled-second")
        first_result = run_cli("compile-prompts", str(first.path), "--gate", "review-foundation-001")
        second_result = run_cli("compile-prompts", str(second.path), "--gate", "review-foundation-001")
        self.assertEqual(first_result.returncode, 0, first_result.stdout + first_result.stderr)
        self.assertEqual(second_result.returncode, 0, second_result.stdout + second_result.stderr)
        first_root = first.path / "prompts/compiled/review-foundation-001--v001"
        second_root = second.path / "prompts/compiled/review-foundation-001--v001"
        first_files = {path.relative_to(first_root).as_posix(): path.read_bytes() for path in first_root.rglob("*") if path.is_file()}
        second_files = {path.relative_to(second_root).as_posix(): path.read_bytes() for path in second_root.rglob("*") if path.is_file()}
        self.assertEqual(first_files, second_files)
        validation = first.validate()
        self.assertTrue(validation["valid"], validation)
        self.assertNotIn("PATH_CONVENTION", [item["code"] for item in validation["warnings"]], validation)
        duplicate = run_cli("compile-prompts", str(first.path), "--gate", "review-foundation-001")
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn("never overwritten", duplicate.stderr)

    def test_compiled_empty_location_prompt_does_not_inject_human_surface_terms(self) -> None:
        fixture = self.fixture()
        result = run_cli("compile-prompts", str(fixture.path), "--gate", "review-foundation-001")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        prompt = (
            fixture.path
            / "prompts/compiled/review-foundation-001--v001/images/loc-workshop-state-day-est--v001.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("No person is present", prompt)
        self.assertNotIn("skin", prompt.casefold())

    def test_compiled_identity_root_uses_neutral_reference_not_project_scene_mood(self) -> None:
        fixture = self.fixture()
        result = run_cli("compile-prompts", str(fixture.path), "--gate", "review-foundation-001")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        prompt = (
            fixture.path
            / "prompts/compiled/review-foundation-001--v001/images/char-hero-inspector--v001.txt"
        ).read_text(encoding="utf-8")
        self.assertIn("single four-column, two-row pure-white technical reference sheet", prompt)
        self.assertIn("full-body front, full-body left profile, full-body right profile, full-body back", prompt)
        self.assertIn("face close-up front, face close-up left profile, face close-up right profile", prompt)
        self.assertIn("one empty white cell", prompt)
        self.assertIn("continuous unambiguous pure-white horizontal gutter", prompt)
        self.assertIn("complete hair and footwear", prompt)
        self.assertIn("same face", prompt)
        self.assertNotIn("near-side aisle", prompt)
        self.assertNotIn("north window and existing desk lamp", prompt)
        self.assertNotIn("concrete", prompt.casefold())

    def test_compiled_sequence_prompt_carries_quality_physique_anchor_and_blur(self) -> None:
        fixture = self.fixture()
        result = run_cli("compile-prompts", str(fixture.path), "--gate", "review-seq-workshop-day-001")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        prompt = (fixture.path / "prompts/compiled/review-seq-workshop-day-001--v001/video/sh-010-010.txt").read_text(encoding="utf-8")
        for value in (
            "GLOBAL STYLE", "CHARACTERS", "LOCATION", "Shot 1", "LIGHTING",
            "role-physique-char-hero-v1", "seq-workshop-visual-anchor--v001",
            "brief head and eye motion blur follows the actual turn toward the case",
        ):
            self.assertIn(value, prompt)
        self.assertNotIn("quality-main", prompt)
        self.assertNotIn("Prompt strategy", prompt)
        self.assertNotIn("\nDYNAMIC RANGE\n", prompt)
        lighting = prompt.split("\nLIGHTING\n", 1)[1].split("\nAUDIO\n", 1)[0]
        self.assertIn("Finite scene-referred capture", lighting)
        self.assertIn("Allowed clipping", lighting)
        self.assertIn("Allowed shadow loss", lighting)
        self.assertIn("no multi-exposure HDR merge", lighting)
        self.assertTrue(fixture.validate()["valid"], fixture.validate())

    def test_review_board_uses_selected_originals_and_refuses_overwrite(self) -> None:
        fixture = self.fixture()
        self.prepare_gate_for_board(fixture, "review-foundation-001")
        result = run_cli("build-review-board", str(fixture.path), "--gate", "review-foundation-001")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        root = fixture.path / "assets/review-boards/review-foundation-001--v001"
        for name in ("overview.png", "face.png", "hands.png", "materials.png", "highlights.png", "shadows.png", "board-map.json"):
            self.assertTrue((root / name).is_file(), name)
        board_map = json.loads((root / "board-map.json").read_text(encoding="utf-8"))
        self.assertEqual(board_map["layout"], "deterministic-original-pixel-contact-and-declared-crops-v1.6")
        duplicate = run_cli("build-review-board", str(fixture.path), "--gate", "review-foundation-001")
        self.assertEqual(duplicate.returncode, 2)
        self.assertIn("never overwritten", duplicate.stderr)

    def test_changes_requested_requires_scoped_ids_and_does_not_mutate_assets(self) -> None:
        fixture = self.fixture()
        self.prepare_gate_for_board(fixture, "review-seq-workshop-day-001")
        reviews = fixture.read("manifests/reviews.json")
        gate = next(item for item in reviews["review_gates"] if item["id"] == "review-seq-workshop-day-001")
        gate["status"] = "ready_for_review"
        fixture.write("manifests/reviews.json", reviews)
        before = (fixture.path / "manifests/assets.json").read_bytes()
        rejected = run_cli("record-review", str(fixture.path), "--gate", gate["id"], "--decision", "changes_requested")
        self.assertEqual(rejected.returncode, 2)
        accepted = run_cli(
            "record-review", str(fixture.path), "--gate", gate["id"], "--decision", "changes_requested",
            "--affected", "kf-sh-010-010-end--v001", "--note", "Correct only the hand contact edge.",
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertEqual(before, (fixture.path / "manifests/assets.json").read_bytes())
        updated = fixture.read("manifests/reviews.json")["review_gates"][1]
        self.assertEqual(updated["affected_ids"], ["kf-sh-010-010-end--v001"])

    def test_strict_higgsfield_profile_mismatch_blocks_validation(self) -> None:
        fixture = self.fixture()
        project = fixture.read("project.json")
        project["higgsfield_conformance"]["official_profile_id"] = "future-unverified-profile"
        fixture.write("project.json", project)
        self.assert_error(fixture.validate(), "HIGGSFIELD_OFFICIAL_PROFILE")

    def test_sequence_cannot_downgrade_from_cinema_studio_4_strict_workflow(self) -> None:
        fixture = self.fixture()
        sequences = fixture.read("manifests/sequences.json")
        cluster = sequences["sequence_clusters"][0]
        cluster["target_workflow"] = "seedance-2.5"
        cluster["reference_limit"] = 50
        fixture.write("manifests/sequences.json", sequences)
        self.assert_error(fixture.validate(), "HIGGSFIELD_OFFICIAL_CONFORMANCE")

    def test_seedance_shot_over_thirty_seconds_is_blocked(self) -> None:
        fixture = self.fixture()
        shots = fixture.read("manifests/shots.json")
        shots["shots"][0]["duration_s"] = 30.1
        shots["shots"][0]["camera_move_plan"]["duration_s"] = 30.1
        fixture.write("manifests/shots.json", shots)
        self.assert_error(fixture.validate(), "HIGGSFIELD_DURATION")

    def test_strict_higgsfield_aspect_outside_published_range_is_blocked(self) -> None:
        fixture = self.fixture()
        project = fixture.read("project.json")
        project["aspect_ratio"] = "1:2"
        fixture.write("project.json", project)
        self.assert_error(fixture.validate(), "HIGGSFIELD_ASPECT")

    def test_second_identity_inspector_generation_batch_is_forbidden(self) -> None:
        fixture = self.fixture()
        candidates = fixture.read("manifests/candidates.json")
        identity_set = next(item for item in candidates["candidate_sets"] if item["tier"] == "identity_single_solve")
        identity_set["batches"].append(json.loads(json.dumps(identity_set["batches"][0])))
        identity_set["batches"][1]["batch_index"] = 2
        fixture.write("manifests/candidates.json", candidates)
        self.assert_error(fixture.validate(), "IDENTITY_SINGLE_SOLVE")

    def test_foundation_record_review_promotes_qualified_records_as_one_transaction(self) -> None:
        fixture = self.fixture()
        self.prepare_foundation_for_record_review(fixture)
        result = run_cli(
            "record-review", str(fixture.path), "--gate", "review-foundation-001", "--decision", "approved",
            "--selection", "lookset-base-001=cp-base-a", "--note", "Approve the screened foundation.",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        gate = fixture.read("manifests/reviews.json")["review_gates"][0]
        self.assertEqual(gate["status"], "approved")
        self.assertEqual(gate["selections"], {"lookset-base-001": "cp-base-a"})
        assets = fixture.read("manifests/assets.json")["assets"]
        self.assertTrue(all(item["status"] in {"approved", "rejected"} for item in assets if item["approval_gate_id"] == gate["id"]))
        self.assertTrue(fixture.validate()["valid"], fixture.validate())

    def test_legacy_v10_through_v15_projects_are_not_modified(self) -> None:
        for version in ("1.0", "1.1", "1.2", "1.3", "1.4", "1.5"):
            with self.subTest(version=version):
                project = self.root / f"legacy-{version.replace('.', '-')}"
                project.mkdir()
                write_json(project / "project.json", {"schema_version": version})
                sentinel = project / "sentinel.txt"
                sentinel.write_text("do not change", encoding="utf-8")
                before = sentinel.read_bytes()
                result = run_cli("validate", str(project), "--json")
                payload = json.loads(result.stdout)
                self.assert_error(payload, "LEGACY_SCHEMA")
                self.assertEqual(before, sentinel.read_bytes())
                self.assertEqual(sorted(path.name for path in project.iterdir()), ["project.json", "sentinel.txt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
