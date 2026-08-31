"""Focused tests for the v1.7 offline three-skill method layer."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from cinematic_ai_director.provider_methods import validate_higgsfield_methods  # noqa: E402
from cinematic_ai_director.schema import (  # noqa: E402
    HIGGSFIELD_METHOD_EXECUTION_BOUNDARY,
    HIGGSFIELD_METHOD_PROFILE_ID,
    HIGGSFIELD_METHOD_SKILLS,
    HIGGSFIELD_METHOD_SOURCE_URLS,
    HIGGSFIELD_METHODS_POLICY,
    HIGGSFIELD_SKILLS_KNOWLEDGE_SNAPSHOT,
    HIGGSFIELD_SKILLS_SNAPSHOT_VERSION,
    PRODUCT_FIDELITY_QA_CHECKS,
    PRODUCT_TRUTH_FIELDS,
    SOUL_COVERAGE_FIELDS,
    Report,
)

SCRIPT = ROOT / "scripts" / "film_project.py"


def error_codes(report: Report) -> set[str]:
    return {item["code"] for item in report.errors}


def base_manifest() -> dict:
    return {
        "schema_version": "1.6",
        "policy": HIGGSFIELD_METHODS_POLICY,
        "status": "planning",
        "method_profile": {
            "id": HIGGSFIELD_METHOD_PROFILE_ID,
            "skills_version": HIGGSFIELD_SKILLS_SNAPSHOT_VERSION,
            "knowledge_snapshot": HIGGSFIELD_SKILLS_KNOWLEDGE_SNAPSHOT,
            "skills": list(HIGGSFIELD_METHOD_SKILLS),
            "source_urls": list(HIGGSFIELD_METHOD_SOURCE_URLS),
            "evidence_policy": "translate-observable-methods-never-emulate-provider-backends",
        },
        "execution_boundary": dict(HIGGSFIELD_METHOD_EXECUTION_BOUNDARY),
        "adoption_matrix": {
            "adopted": ["Intent-first routing"],
            "translated": ["Schema discovery becomes operator preflight"],
            "provider_only_not_emulated": [
                "Soul model training and reusable reference-id creation",
                "Product Photoshoot backend prompt enhancement",
            ],
        },
        "generation_routes": [],
        "soul_readiness_records": [],
        "product_authorities": [],
        "product_photoshoot_briefs": [],
    }


def soul_record(photo_ids: list[str]) -> dict:
    return {
        "id": "soul-ready-hero",
        "status": "qualified",
        "identity_pack_id": "identity-hero",
        "intended_variant": "soul_cinematic",
        "photo_asset_ids": photo_ids,
        "coverage": {field: True for field in SOUL_COVERAGE_FIELDS},
        "rights_confirmed": True,
        "likeness_consent_confirmed": True,
        "unified_board_role": "continuity-authority-not-training-substitute",
        "platform_training_performed": False,
        "notes": ["Offline readiness only."],
    }


def product_authority() -> dict:
    truth = {field: f"locked {field}" for field in PRODUCT_TRUTH_FIELDS}
    truth["must_preserve"] = ["silhouette", "front label"]
    truth["allowed_state_changes"] = ["localized condensation"]
    return {
        "id": "product-bottle",
        "status": "approved",
        "name": "North Bottle",
        "category": "beverage",
        "master_asset_id": "asset-product-front",
        "reference_asset_ids": ["asset-product-front"],
        "truth_lock": truth,
        "rights_confirmed": True,
        "qa": {
            "checks": {field: "pass" for field in PRODUCT_FIDELITY_QA_CHECKS},
            "verdict": "pass",
            "hard_failures": [],
            "notes": ["Geometry and copy match."],
            "checked_at": "2026-08-31T08:00:00Z",
            "reviewer": "codex-visual",
        },
    }


class HiggsfieldMethodsTests(unittest.TestCase):
    def test_init_creates_all_false_offline_method_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cad-methods-init-") as directory:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "init",
                    "--root",
                    directory,
                    "--title",
                    "Method Test",
                    "--slug",
                    "method-test",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            project = Path(directory) / "method-test"
            methods = json.loads((project / "manifests/higgsfield-methods.json").read_text(encoding="utf-8"))
            self.assertEqual(methods["execution_boundary"], HIGGSFIELD_METHOD_EXECUTION_BOUNDARY)
            self.assertTrue(all(value is False for key, value in methods["execution_boundary"].items() if key != "mode"))
            self.assertTrue((project / "qa/higgsfield-methods-review.md").is_file())

    def test_any_platform_operation_is_blocked(self) -> None:
        data = base_manifest()
        data["execution_boundary"]["upload"] = True
        report = Report()
        validate_higgsfield_methods(data, {}, {}, None, report)
        self.assertIn("HIGGSFIELD_EXECUTION_BOUNDARY", error_codes(report))

    def test_soul_requires_five_to_twenty_lawful_real_photos(self) -> None:
        data = base_manifest()
        data["soul_readiness_records"] = [soul_record([f"photo-{index}" for index in range(4)])]
        assets = {f"photo-{index}": {"status": "approved", "generator": "provided"} for index in range(4)}
        report = Report()
        validate_higgsfield_methods(data, assets, {"identity-hero": {"identity_kind": "real_person"}}, None, report)
        self.assertIn("SOUL_PHOTO_COUNT", error_codes(report))

    def test_generated_identity_board_cannot_masquerade_as_soul_photos(self) -> None:
        photo_ids = [f"photo-{index}" for index in range(5)]
        data = base_manifest()
        data["soul_readiness_records"] = [soul_record(photo_ids)]
        assets = {asset_id: {"status": "approved", "generator": "builtin-imagegen"} for asset_id in photo_ids}
        report = Report()
        validate_higgsfield_methods(data, assets, {"identity-hero": {"identity_kind": "real_person"}}, None, report)
        self.assertIn("SOUL_PHOTO_SOURCE", error_codes(report))

    def test_valid_offline_soul_readiness_does_not_train(self) -> None:
        photo_ids = [f"photo-{index}" for index in range(5)]
        data = base_manifest()
        data["soul_readiness_records"] = [soul_record(photo_ids)]
        assets = {asset_id: {"status": "approved", "generator": "provided"} for asset_id in photo_ids}
        report = Report()
        validate_higgsfield_methods(data, assets, {"identity-hero": {"identity_kind": "real_person"}}, None, report)
        self.assertEqual(report.errors, [])

    def test_product_backend_prompt_may_not_be_fabricated(self) -> None:
        data = base_manifest()
        data["product_authorities"] = [product_authority()]
        data["product_photoshoot_briefs"] = [
            {
                "id": "brief-hero",
                "status": "approved",
                "mode": "hero_banner",
                "product_authority_ids": ["product-bottle"],
                "short_intent": "Wide campaign header with the bottle in credible use.",
                "placement": "website hero",
                "count": 1,
                "aspect_ratio": "16:9",
                "reference_asset_ids": ["asset-product-front"],
                "backend_prompt_owner": "local-freehand-prompt",
                "enhanced_prompt_exported": True,
                "platform_generation_performed": False,
                "qa_notes": ["Product stays readable."],
            }
        ]
        assets = {"asset-product-front": {"status": "approved", "generator": "provided"}}
        report = Report()
        validate_higgsfield_methods(data, assets, {}, None, report)
        self.assertIn("PRODUCT_PROMPT_OWNERSHIP", error_codes(report))

    def test_product_derivative_requires_approved_truth_and_mode(self) -> None:
        data = base_manifest()
        product = product_authority()
        product["truth_lock"]["geometry"] = ""
        data["product_authorities"] = [product]
        data["product_photoshoot_briefs"] = [
            {
                "id": "brief-invalid",
                "status": "qualified",
                "mode": "generic_cinematic",
                "product_authority_ids": ["product-bottle"],
                "short_intent": "Campaign still.",
                "placement": "paid social",
                "count": 1,
                "aspect_ratio": "1:1",
                "reference_asset_ids": ["asset-product-front"],
                "backend_prompt_owner": "higgsfield-product-photoshoot-backend-enhancer",
                "enhanced_prompt_exported": False,
                "platform_generation_performed": False,
                "qa_notes": ["Pending route correction."],
            }
        ]
        report = Report()
        validate_higgsfield_methods(
            data,
            {"asset-product-front": {"status": "approved", "generator": "provided"}},
            {},
            None,
            report,
        )
        self.assertIn("PRODUCT_TRUTH", error_codes(report))
        self.assertIn("PRODUCT_PHOTOSHOOT", error_codes(report))

    def test_audio_route_rejects_mutually_exclusive_reference_families(self) -> None:
        data = base_manifest()
        data["generation_routes"] = [
            {
                "id": "route-audio",
                "status": "qualified",
                "task_kind": "audio",
                "intent": "Generate restrained location ambience.",
                "capability_family": "audio_generation",
                "scope_ids": ["sh-001"],
                "reference_asset_ids": ["audio-ref", "image-ref"],
                "reference_roles": ["audio_references", "image_references"],
                "model_advisory": "seed_audio",
                "model_schema_verification_required": True,
                "prompt_contract": {
                    "mode": "visible-model-facts-only",
                    "preferred_max_tokens": 180,
                    "overage_reason": "",
                },
                "output_contract": "One ambience stem aligned to shot duration.",
                "platform_operation": "not_performed",
            }
        ]
        assets = {
            "audio-ref": {"status": "approved", "generator": "provided"},
            "image-ref": {"status": "approved", "generator": "provided"},
        }
        report = Report()
        validate_higgsfield_methods(data, assets, {}, None, report)
        self.assertIn("HIGGSFIELD_AUDIO_REFERENCES", error_codes(report))

    def test_generation_route_requires_nonempty_scope(self) -> None:
        data = base_manifest()
        data["generation_routes"] = [
            {
                "id": "route-empty-scope",
                "status": "planning",
                "task_kind": "image",
                "intent": "Prepare one approved location authority.",
                "capability_family": "image_generation",
                "scope_ids": [],
                "reference_asset_ids": [],
                "reference_roles": [],
                "model_advisory": "Verify the current live model schema later.",
                "model_schema_verification_required": True,
                "prompt_contract": {
                    "mode": "visible-model-facts-only",
                    "preferred_max_tokens": 180,
                    "overage_reason": "",
                },
                "output_contract": "One local candidate set; no platform operation.",
                "platform_operation": "not_performed",
            }
        ]
        report = Report()
        validate_higgsfield_methods(data, {}, {}, None, report)
        self.assertIn("HIGGSFIELD_ROUTE", error_codes(report))


if __name__ == "__main__":
    unittest.main()
