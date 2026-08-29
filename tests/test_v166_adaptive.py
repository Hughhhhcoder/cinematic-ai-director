"""Focused v1.6.6 tests for adaptive commercial direction and native detail."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from cinematic_ai_director.prompts import _compile_image_prompt  # noqa: E402
from cinematic_ai_director.schema import (  # noqa: E402
    COMMERCIAL_QA_CHECKS,
    IDENTITY_LAYOUT_PROFILE,
    IDENTITY_VIEW_ROLES,
    RESOLUTION_QA_CHECKS,
    Report,
    identity_layout_spec,
)
from cinematic_ai_director.validation import (  # noqa: E402
    validate_commercial_manifest,
    validate_resolution_qa,
)

SCRIPT = ROOT / "scripts" / "film_project.py"
TIMESTAMP = "2026-08-29T12:00:00Z"


def error_codes(report: Report) -> set[str]:
    return {item["code"] for item in report.errors}


def solid_png(path: Path, width: int, height: int) -> None:
    """Write a compact native-size RGB PNG without image-library dependencies."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    row = bytes([0]) + bytes((184, 178, 168)) * width
    payload = b"\x89PNG\r\n\x1a\n"
    payload += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += chunk(b"IDAT", zlib.compress(row * height, level=9))
    payload += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def commercial_fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    project = {"production_kind": "commercial_tvc"}
    shot = {
        "id": "sh-001",
        "status": "ready",
        "duration_s": 30.0,
        "temporal_capture": {
            "capture_fps": 60,
            "delivery_fps": 24,
            "playback_rate": 0.4,
            "shutter_angle": 180,
            "exposure_time_s": 1 / 120,
        },
    }
    data = {
        "schema_version": "1.6",
        "mode": "commercial_tvc",
        "status": "approved",
        "commercial_brief": {
            "category": "brand",
            "objective": "Make the product's quiet mechanical precision memorable.",
            "audience": "Urban design-conscious adults buying their first premium watch.",
            "placement": "Thirty-second broadcast and connected-TV master.",
            "runtime_s": 30,
            "single_proposition": "Precision can feel effortless.",
            "reasons_to_believe": ["Visible mechanical movement", "Five-year service promise"],
            "mandatory_elements": ["Product face", "Brand endboard"],
            "brand_codes": ["Calm measured gesture", "Warm brushed metal"],
            "prohibited_generic_codes": ["Generic luxury rim light", "Unmotivated slow motion"],
            "success_measure": "Product and brand are correctly recalled after one viewing.",
        },
        "creative_routes": [
            {
                "id": "route-measured-day",
                "status": "approved",
                "name": "Measured Day",
                "concept": "Every daily action resolves on a precise product event.",
                "brand_link": "The mechanism controls the film's temporal grammar.",
                "visual_logic": "Reachable observational camera positions and exact action peaks.",
                "product_or_wardrobe_proof": "Macro movement and wrist-fit proof are story beats.",
                "audience_mechanism": "Recognition of ordinary pressure answered by reliable precision.",
                "distinguishing_axes": ["temporal mechanism", "daily-use proof"],
                "competitor_swap_result": "not swappable",
                "script_or_board_summary": "A deadline fragments the day until the watch restores cadence.",
            },
            {
                "id": "route-shared-second",
                "status": "rejected",
                "name": "Shared Second",
                "concept": "Two people separated by distance act within the same measured second.",
                "brand_link": "Precision creates human connection.",
                "visual_logic": "Matched spatial gestures rather than cosmetic grade matching.",
                "product_or_wardrobe_proof": "Two environments reveal legibility and finish under different light.",
                "audience_mechanism": "Emotional payoff through synchronized action.",
                "distinguishing_axes": ["parallel narrative", "cross-light product proof"],
                "competitor_swap_result": "fail",
                "script_or_board_summary": "Separate routines synchronize at the product reveal.",
            },
        ],
        "selected_route_id": "route-measured-day",
        "brand_assets": [],
        "wardrobe_looks": [],
        "rhythm_plan": {
            "music": {
                "usage": "score",
                "bpm": 121.5,
                "meter": "4/4",
                "downbeat_s": 0.0,
                "energy_curve": [{"time_s": 0.0, "level": "high"}, {"time_s": 30.0, "level": "burst"}],
            },
            "tempo_motion_relationship": "synchronous",
            "relationship_reason": "Action peaks and cuts answer the score's measured pulse.",
            "edit_strategy": "Use real-time detail proof between selective overcranked moments.",
            "speed_palette": [
                {
                    "id": "speed-slow-60",
                    "regime": "overcranked_slow",
                    "capture_fps": 60,
                    "delivery_fps": 24,
                    "playback_rate": 0.4,
                    "shutter_angle": 180,
                    "exposure_time_s": 1 / 120,
                    "intended_motion": "A restrained wrist turn.",
                    "blur_logic": "Short source exposure preserves one readable hand edge without frame blending.",
                }
            ],
            "shot_rhythm": [
                {
                    "shot_id": "sh-001",
                    "function": "product_reveal",
                    "duration_s": 30.0,
                    "duration_frames": 720,
                    "beat_start": 0.0,
                    "beat_end": 60.75,
                    "action_peak_s": 15.0,
                    "cut_relation": "Cut on the resolved wrist stop.",
                    "energy": "low",
                    "speed_palette_id": "speed-slow-60",
                    "internal_rhythmic_events": [],
                    "removal_test": "Without this shot the product is never clearly revealed.",
                }
            ],
        },
        "audio_plan": {
            "dialogue_vo": [],
            "music": ["Edit score stems around product and transition events."],
            "ambience": ["Maintain location air beneath music."],
            "foley": ["Record crown click and sleeve movement."],
            "transition_accents": ["One restrained mechanical accent at reveal."],
            "brand_mnemonic": ["Three-note mnemonic at endboard."],
            "mix_hierarchy": ["Product proof above music at reveal; mnemonic resolves last."],
        },
        "deliverables": [
            {
                "id": "master-30",
                "kind": "master",
                "destination": "broadcast-connected-tv",
                "width_px": 1920,
                "height_px": 1080,
                "aspect_ratio": "16:9",
                "delivery_fps": 24,
                "duration_s": 30,
                "frame_count": 720,
                "audio_sample_rate_hz": 48000,
                "audio_channels": 2,
                "codec": "ProRes 422 HQ",
                "color_space": "Rec.709 Gamma 2.4",
                "safe_area": "destination title/action safe",
                "exact_runtime": True,
                "spec_source": "commissioned delivery brief",
                "spec_override_reason": "",
                "notes": [],
            }
        ],
        "qa": {
            "checks": {name: True for name in COMMERCIAL_QA_CHECKS},
            "hard_failures": [],
            "notes": [],
            "checked_at": TIMESTAMP,
            "reviewer": "codex-structural",
        },
    }
    return project, data, {"sh-001": shot}


class V166AdaptiveTests(unittest.TestCase):
    def test_init_selects_adaptive_commercial_mode_and_new_identity_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-v166-init-") as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "init",
                    "--root",
                    directory,
                    "--title",
                    "Measured Day",
                    "--slug",
                    "measured-day",
                    "--project-kind",
                    "commercial-tvc",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            project_dir = Path(directory) / "measured-day"
            project = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
            commercial = json.loads((project_dir / "manifests/commercial.json").read_text(encoding="utf-8"))
            self.assertEqual(project["production_kind"], "commercial_tvc")
            self.assertEqual(project["identity_layout_policy"]["default_profile"], IDENTITY_LAYOUT_PROFILE)
            self.assertEqual(project["resolution_policy"]["minimum_identity_board_px"], [1536, 1024])
            self.assertEqual(commercial["mode"], "commercial_tvc")
            self.assertTrue((project_dir / "qa/commercial-review.md").is_file())

    def test_default_identity_board_is_one_large_three_by_two_solve(self) -> None:
        spec = identity_layout_spec(IDENTITY_LAYOUT_PROFILE)
        self.assertEqual(spec["grid"], [3, 2])
        self.assertEqual(tuple(spec["roles"]), IDENTITY_VIEW_ROLES)
        self.assertIsNone(spec["blank_slot"])
        self.assertEqual(
            tuple(spec["roles"]),
            (
                "full_front",
                "full_primary_profile",
                "full_back",
                "portrait_front",
                "portrait_left_profile",
                "portrait_right_profile",
            ),
        )

    def test_identity_prompt_requests_six_shared_solve_views_at_native_detail(self) -> None:
        prompt = _compile_image_prompt(
            {
                "id": "identity-hero-v001",
                "role": "fictional adult lead",
                "type": "character_identity_inspector",
                "prompt_strategy_id": "image2-live-action-identity-inspector-v1.6.6",
                "scene_ids": [],
                "identity_inspector_layout": {
                    "profile": IDENTITY_LAYOUT_PROFILE,
                    "primary_profile_side": "right",
                },
                "dynamic_range_plan": {
                    "policy": "finite_scene_referred",
                    "working_latitude_stops": 12,
                    "upper_latitude_stops": 5,
                    "lower_latitude_stops": 7,
                    "scene_contrast_stops_estimate": 8,
                    "exposure_priority": "middle_tones",
                    "middle_gray_anchor": "neutral face and white-board exposure",
                    "highlight_behavior": "soft source highlights roll naturally",
                    "shadow_behavior": "restrained readable reference shadows",
                    "allowed_clipping": ["pure white background beyond subject edge"],
                    "allowed_shadow_loss": [],
                    "local_tone_mapping": False,
                    "multi_exposure_hdr": False,
                    "narrative_reason": "Neutral casting evidence, not a mood image.",
                },
            },
            {},
            None,
            None,
        )
        self.assertIn("three-column, two-row", prompt)
        self.assertIn("complete full-body right profile", prompt)
        self.assertIn("large face close-up left profile", prompt)
        self.assertIn("all 6 panels", prompt)
        self.assertIn("Native detail must be present at generation", prompt)
        self.assertIn("topographic contour", prompt)
        self.assertNotIn("empty white cell", prompt)

    def test_fast_music_with_uniform_slow_low_energy_is_blocked(self) -> None:
        project, data, shots = commercial_fixture()
        report = Report()
        validate_commercial_manifest(project, data, shots, {}, {}, report)
        self.assertIn("RHYTHM_MISMATCH", error_codes(report), report.errors)

    def test_deliberate_counterpoint_needs_and_accepts_internal_events(self) -> None:
        project, data, shots = commercial_fixture()
        data["rhythm_plan"]["tempo_motion_relationship"] = "counterpoint"
        data["rhythm_plan"]["relationship_reason"] = (
            "The slow gesture deliberately resists the score while mechanical micro-events answer each half beat."
        )
        data["rhythm_plan"]["shot_rhythm"][0]["internal_rhythmic_events"] = [
            "0.5 s sleeve edge crosses dial",
            "1.25 s wrist stop",
            "2.0 s crown click",
        ]
        report = Report()
        validate_commercial_manifest(project, data, shots, {}, {}, report)
        self.assertNotIn("RHYTHM_MISMATCH", error_codes(report), report.errors)
        self.assertFalse(report.errors, report.errors)

    def test_speed_sampling_formula_is_not_free_text(self) -> None:
        project, data, shots = commercial_fixture()
        data["rhythm_plan"]["speed_palette"][0]["playback_rate"] = 0.5
        report = Report()
        validate_commercial_manifest(project, data, shots, {}, {}, report)
        self.assertIn("SPEED_SAMPLING", error_codes(report), report.errors)

    def test_shot_beat_range_and_total_edit_runtime_are_mathematical(self) -> None:
        project, data, shots = commercial_fixture()
        data["rhythm_plan"]["shot_rhythm"][0]["beat_end"] = 48.0
        data["rhythm_plan"]["shot_rhythm"][0]["duration_s"] = 29.0
        shots["sh-001"]["duration_s"] = 29.0
        data["rhythm_plan"]["shot_rhythm"][0]["duration_frames"] = 696
        report = Report()
        validate_commercial_manifest(project, data, shots, {}, {}, report)
        codes = error_codes(report)
        self.assertIn("RHYTHM_TIMING", codes, report.errors)
        self.assertIn("EDIT_RUNTIME", codes, report.errors)

    def test_review_proxy_specs_cannot_be_declared_as_master(self) -> None:
        project, data, shots = commercial_fixture()
        delivery = data["deliverables"][0]
        delivery["width_px"] = 1280
        delivery["height_px"] = 720
        delivery["audio_sample_rate_hz"] = 32000
        report = Report()
        validate_commercial_manifest(project, data, shots, {}, {}, report)
        self.assertIn("DELIVERY_MASTER", error_codes(report), report.errors)

    def test_native_detail_gate_rejects_small_or_dimension_only_enlarged_board(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-v166-resolution-") as directory:
            project_dir = Path(directory)
            image_path = project_dir / "assets/characters/identity-inspectors/hero.png"
            solid_png(image_path, 1200, 800)
            asset = {
                "id": "identity-hero-v001",
                "type": "character_identity_inspector",
                "status": "approved",
                "mode": "generate",
                "created_at": TIMESTAMP,
                "approved_path": "assets/characters/identity-inspectors/hero.png",
                "identity_inspector_layout": {
                    "profile": IDENTITY_LAYOUT_PROFILE,
                    "primary_profile_side": "left",
                },
                "generation_provenance": {
                    "output": {"width_px": 1200, "height_px": 800},
                },
                "resolution_qa": {
                    "mode": "native_detail",
                    "source_dimensions_px": [600, 400],
                    "delivered_dimensions_px": [1200, 800],
                    "subject_coverage_px": {
                        "full_body_subject_height_px": 420,
                        "portrait_face_height_px": 190,
                    },
                    "native_generation_or_source": False,
                    "dimension_only_upscale": True,
                    "checks": {name: "pass" for name in RESOLUTION_QA_CHECKS},
                    "verdict": "pass",
                    "hard_failures": [],
                    "notes": [],
                    "checked_at": TIMESTAMP,
                    "reviewer": "codex-visual",
                },
            }
            policy = {
                "mode": "strict_native_detail_v1.6.6",
                "effective_at": "2026-08-29T00:00:00Z",
                "minimum_identity_board_px": [1536, 1024],
                "minimum_identity_cell_width_px": 512,
                "minimum_full_body_subject_height_px": 560,
                "minimum_portrait_face_height_px": 300,
                "minimum_authority_long_edge_px": 1536,
                "minimum_narrative_long_edge_px": 1920,
                "minimum_narrative_short_edge_px": 1080,
            }
            report = Report()
            validate_resolution_qa(project_dir, asset, "asset", policy, report)
            codes = error_codes(report)
            self.assertIn("RESOLUTION_GATE", codes, report.errors)
            self.assertIn("RESOLUTION_UPSCALE", codes, report.errors)

    def test_fashion_commercial_requires_per_look_material_and_detail_proof(self) -> None:
        project, data, shots = commercial_fixture()
        data["commercial_brief"]["category"] = "fashion"
        report = Report()
        validate_commercial_manifest(project, data, shots, {}, {}, report)
        self.assertIn("WARDROBE_PROOF", error_codes(report), report.errors)


if __name__ == "__main__":
    unittest.main()
