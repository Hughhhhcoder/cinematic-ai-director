"""Offline adoption of official Higgsfield skill methods.

This module deliberately validates preparation facts only.  It contains no
network client, credential handling, subprocess execution, upload, training,
generation, polling, or credit-spending code.
"""

from __future__ import annotations

from .schema import *


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty(item) for item in value)


def _require_fields(value: Any, fields: tuple[str, ...], where: str, report: Report) -> bool:
    if not isinstance(value, dict):
        report.error("TYPE", f"{where} must be an object.")
        return False
    missing = [field for field in fields if field not in value]
    if missing:
        report.error("MISSING_FIELD", f"{where} is missing: {', '.join(missing)}.")
        return False
    return True


def _duplicate_id(index: dict[str, dict[str, Any]], item: dict[str, Any], where: str, report: Report) -> str:
    item_id = item.get("id")
    if not _nonempty(item_id):
        report.error("TYPE", f"{where}.id must be a non-empty string.")
        return ""
    if item_id in index:
        report.error("DUPLICATE_ID", f"Duplicate Higgsfield method record id: {item_id}.")
    index[item_id] = item
    return str(item_id)


def _validate_method_profile(value: Any, report: Report) -> None:
    where = "manifests/higgsfield-methods.json.method_profile"
    fields = ("id", "skills_version", "knowledge_snapshot", "skills", "source_urls", "evidence_policy")
    if not _require_fields(value, fields, where, report):
        return
    if value.get("id") != HIGGSFIELD_METHOD_PROFILE_ID:
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.id must be {HIGGSFIELD_METHOD_PROFILE_ID}.")
    if value.get("skills_version") != HIGGSFIELD_SKILLS_SNAPSHOT_VERSION:
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.skills_version must be {HIGGSFIELD_SKILLS_SNAPSHOT_VERSION}.")
    if value.get("knowledge_snapshot") != HIGGSFIELD_SKILLS_KNOWLEDGE_SNAPSHOT:
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.knowledge_snapshot must be {HIGGSFIELD_SKILLS_KNOWLEDGE_SNAPSHOT}.")
    if value.get("skills") != list(HIGGSFIELD_METHOD_SKILLS):
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.skills must contain the three official skills in release order.")
    if value.get("source_urls") != list(HIGGSFIELD_METHOD_SOURCE_URLS):
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.source_urls do not match the versioned primary-source set.")
    if value.get("evidence_policy") != "translate-observable-methods-never-emulate-provider-backends":
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.evidence_policy must preserve provider-specific boundaries.")


def _validate_execution_boundary(value: Any, report: Report) -> None:
    where = "manifests/higgsfield-methods.json.execution_boundary"
    if not isinstance(value, dict):
        report.error("HIGGSFIELD_EXECUTION_BOUNDARY", f"{where} must be an object.")
        return
    if value != HIGGSFIELD_METHOD_EXECUTION_BOUNDARY:
        report.error(
            "HIGGSFIELD_EXECUTION_BOUNDARY",
            "The method-fusion manifest must remain methods-only and may not install, authenticate, upload, train, submit, poll, or consume credits.",
        )


def _validate_route(
    route: dict[str, Any],
    where: str,
    assets: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    fields = (
        "id", "status", "task_kind", "intent", "capability_family", "scope_ids",
        "reference_asset_ids", "reference_roles", "model_advisory", "model_schema_verification_required",
        "prompt_contract", "output_contract", "platform_operation",
    )
    if not _require_fields(route, fields, where, report):
        return
    if route.get("status") not in HIGGSFIELD_ROUTE_STATUSES:
        report.error("HIGGSFIELD_ROUTE", f"{where}.status is invalid.")
    if route.get("task_kind") not in HIGGSFIELD_ROUTE_TASK_KINDS:
        report.error("HIGGSFIELD_ROUTE", f"{where}.task_kind is invalid.")
    if route.get("capability_family") not in HIGGSFIELD_ROUTE_CAPABILITY_FAMILIES:
        report.error("HIGGSFIELD_ROUTE", f"{where}.capability_family is invalid.")
    for field in ("intent", "model_advisory", "output_contract"):
        if not _nonempty(route.get(field)):
            report.error("HIGGSFIELD_ROUTE", f"{where}.{field} must be a non-empty string.")
    if not _string_list(route.get("scope_ids")) or not route.get("scope_ids"):
        report.error("HIGGSFIELD_ROUTE", f"{where}.scope_ids must be a non-empty string array.")
    reference_ids = route.get("reference_asset_ids")
    if not isinstance(reference_ids, list) or any(not _nonempty(item) for item in reference_ids):
        report.error("HIGGSFIELD_ROUTE", f"{where}.reference_asset_ids must be a string array.")
        reference_ids = []
    for asset_id in reference_ids:
        asset = assets.get(asset_id)
        if asset is None:
            report.error("MISSING_REFERENCE", f"{where} references missing asset {asset_id}.")
        elif route.get("status") in {"qualified", "approved"} and asset.get("status") != "approved":
            report.error("UNAPPROVED_REFERENCE", f"{where} uses unapproved asset {asset_id}.")
    roles = route.get("reference_roles")
    if not isinstance(roles, list) or any(role not in HIGGSFIELD_REFERENCE_ROLES for role in roles):
        report.error("HIGGSFIELD_ROUTE", f"{where}.reference_roles contain an unsupported responsibility.")
    if len(roles or []) != len(reference_ids):
        report.error("HIGGSFIELD_ROUTE", f"{where} must assign exactly one reference role to each reference asset.")
    if route.get("model_schema_verification_required") is not True:
        report.error("HIGGSFIELD_ROUTE", f"{where} must require a current live model-schema check by the operator.")
    if route.get("platform_operation") != "not_performed":
        report.error("HIGGSFIELD_EXECUTION_BOUNDARY", f"{where}.platform_operation must be not_performed.")
    prompt = route.get("prompt_contract")
    if _require_fields(prompt, ("mode", "preferred_max_tokens", "overage_reason"), f"{where}.prompt_contract", report):
        if prompt.get("mode") != "visible-model-facts-only":
            report.error("HIGGSFIELD_PROMPT_METHOD", f"{where}.prompt_contract.mode must keep internal QA out of model prompts.")
        preferred = prompt.get("preferred_max_tokens")
        if not isinstance(preferred, int) or isinstance(preferred, bool) or preferred <= 0 or preferred > 260:
            report.error("HIGGSFIELD_PROMPT_METHOD", f"{where}.preferred_max_tokens must be between 1 and 260.")
        if isinstance(preferred, int) and preferred > 200 and not _nonempty(prompt.get("overage_reason")):
            report.error("HIGGSFIELD_PROMPT_METHOD", f"{where} exceeds the official general ~200-token guidance without a task-specific reason.")
    if route.get("task_kind") == "audio":
        role_set = set(roles or [])
        if "audio_references" in role_set and "image_references" in role_set:
            report.error("HIGGSFIELD_AUDIO_REFERENCES", f"{where} mixes mutually exclusive audio and image reference families.")


def _validate_soul_record(
    record: dict[str, Any],
    where: str,
    assets: dict[str, dict[str, Any]],
    identity_packs: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    fields = (
        "id", "status", "identity_pack_id", "intended_variant", "photo_asset_ids", "coverage",
        "rights_confirmed", "likeness_consent_confirmed", "unified_board_role",
        "platform_training_performed", "notes",
    )
    if not _require_fields(record, fields, where, report):
        return
    status = record.get("status")
    if status not in SOUL_READINESS_STATUSES:
        report.error("SOUL_READINESS", f"{where}.status is invalid.")
    if record.get("intended_variant") not in SOUL_VARIANTS:
        report.error("SOUL_READINESS", f"{where}.intended_variant is invalid.")
    if record.get("unified_board_role") != "continuity-authority-not-training-substitute":
        report.error("SOUL_READINESS", f"{where} must not claim that the generated identity board replaces a varied real-photo training set.")
    if record.get("platform_training_performed") is not False:
        report.error("HIGGSFIELD_EXECUTION_BOUNDARY", f"{where}.platform_training_performed must be false.")
    if not isinstance(record.get("notes"), list) or any(not _nonempty(item) for item in record.get("notes", [])):
        report.error("SOUL_READINESS", f"{where}.notes must be a string array.")
    identity_pack = identity_packs.get(record.get("identity_pack_id"))
    if identity_pack is None:
        report.error("MISSING_REFERENCE", f"{where} references missing identity pack {record.get('identity_pack_id')}.")
    photo_ids = record.get("photo_asset_ids")
    if not isinstance(photo_ids, list) or any(not _nonempty(item) for item in photo_ids):
        report.error("SOUL_READINESS", f"{where}.photo_asset_ids must be a string array.")
        photo_ids = []
    coverage = record.get("coverage")
    if not _require_fields(coverage, SOUL_COVERAGE_FIELDS, f"{where}.coverage", report):
        coverage = {}
    for field in SOUL_COVERAGE_FIELDS:
        if field in coverage and coverage.get(field) not in {True, False}:
            report.error("SOUL_READINESS", f"{where}.coverage.{field} must be boolean.")
    if status == "qualified":
        if not identity_pack or identity_pack.get("identity_kind") != "real_person":
            report.error("SOUL_READINESS", f"{where} may be qualified only for a consented real-person identity.")
        if not SOUL_TRAINING_PHOTO_MIN <= len(photo_ids) <= SOUL_TRAINING_PHOTO_MAX:
            report.error("SOUL_PHOTO_COUNT", f"{where} requires {SOUL_TRAINING_PHOTO_MIN}-{SOUL_TRAINING_PHOTO_MAX} unique real photographs.")
        if len(set(photo_ids)) != len(photo_ids):
            report.error("SOUL_PHOTO_COUNT", f"{where} contains duplicate photo assets.")
        if record.get("rights_confirmed") is not True or record.get("likeness_consent_confirmed") is not True:
            report.error("SOUL_CONSENT", f"{where} requires both usage rights and likeness consent.")
        if any(coverage.get(field) is not True for field in SOUL_COVERAGE_FIELDS):
            report.error("SOUL_PHOTO_QUALITY", f"{where} must pass every official photo-readiness coverage check.")
        for asset_id in photo_ids:
            asset = assets.get(asset_id)
            if asset is None:
                report.error("MISSING_REFERENCE", f"{where} references missing photo asset {asset_id}.")
                continue
            if asset.get("status") != "approved" or asset.get("generator") != "provided":
                report.error("SOUL_PHOTO_SOURCE", f"{where} photo {asset_id} must be an approved provided photograph, never a generated identity derivative.")


def _validate_product_authority(
    record: dict[str, Any],
    where: str,
    assets: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    fields = (
        "id", "status", "name", "category", "master_asset_id", "reference_asset_ids",
        "truth_lock", "rights_confirmed", "qa",
    )
    if not _require_fields(record, fields, where, report):
        return
    status = record.get("status")
    if status not in PRODUCT_AUTHORITY_STATUSES:
        report.error("PRODUCT_AUTHORITY", f"{where}.status is invalid.")
    for field in ("name", "category"):
        if not _nonempty(record.get(field)):
            report.error("PRODUCT_AUTHORITY", f"{where}.{field} must be a non-empty string.")
    reference_ids = record.get("reference_asset_ids")
    if not isinstance(reference_ids, list) or any(not _nonempty(item) for item in reference_ids):
        report.error("PRODUCT_AUTHORITY", f"{where}.reference_asset_ids must be a string array.")
        reference_ids = []
    master_id = record.get("master_asset_id")
    if _nonempty(master_id) and master_id not in reference_ids:
        report.error("PRODUCT_AUTHORITY", f"{where}.master_asset_id must be included in reference_asset_ids.")
    truth = record.get("truth_lock")
    if not _require_fields(truth, PRODUCT_TRUTH_FIELDS, f"{where}.truth_lock", report):
        truth = {}
    for field in PRODUCT_TRUTH_FIELDS:
        value = truth.get(field)
        if field in {"must_preserve", "allowed_state_changes"}:
            if not isinstance(value, list) or any(not _nonempty(item) for item in value):
                report.error("PRODUCT_TRUTH", f"{where}.truth_lock.{field} must be a string array.")
        elif not _nonempty(value):
            report.error("PRODUCT_TRUTH", f"{where}.truth_lock.{field} must be a non-empty string.")
    qa = record.get("qa")
    if not _require_fields(qa, ("checks", "verdict", "hard_failures", "notes", "checked_at", "reviewer"), f"{where}.qa", report):
        qa = {}
    checks = qa.get("checks") if isinstance(qa.get("checks"), dict) else {}
    for check in PRODUCT_FIDELITY_QA_CHECKS:
        if check not in checks or checks.get(check) not in {"pending", "pass", "fail"}:
            report.error("PRODUCT_QA", f"{where}.qa.checks.{check} must be pending, pass, or fail.")
    if not isinstance(qa.get("hard_failures"), list) or not isinstance(qa.get("notes"), list):
        report.error("PRODUCT_QA", f"{where}.qa hard_failures and notes must be arrays.")
    complete = status in {"qualified", "approved"}
    if complete:
        if record.get("rights_confirmed") is not True:
            report.error("PRODUCT_RIGHTS", f"{where} requires confirmed product-reference usage rights.")
        if not reference_ids:
            report.error("PRODUCT_AUTHORITY", f"{where} requires at least one approved product reference.")
        for asset_id in reference_ids:
            asset = assets.get(asset_id)
            if asset is None:
                report.error("MISSING_REFERENCE", f"{where} references missing product asset {asset_id}.")
            elif asset.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"{where} references unapproved product asset {asset_id}.")
        if qa.get("verdict") != "pass" or qa.get("hard_failures") or any(checks.get(name) != "pass" for name in PRODUCT_FIDELITY_QA_CHECKS):
            report.error("PRODUCT_QA", f"{where} must pass product fidelity QA before downstream use.")


def _validate_photoshoot_brief(
    brief: dict[str, Any],
    where: str,
    assets: dict[str, dict[str, Any]],
    products: dict[str, dict[str, Any]],
    report: Report,
) -> None:
    fields = (
        "id", "status", "mode", "product_authority_ids", "short_intent", "placement",
        "count", "aspect_ratio", "reference_asset_ids", "backend_prompt_owner",
        "enhanced_prompt_exported", "platform_generation_performed", "qa_notes",
    )
    if not _require_fields(brief, fields, where, report):
        return
    status = brief.get("status")
    if status not in PRODUCT_PHOTOSHOOT_STATUSES:
        report.error("PRODUCT_PHOTOSHOOT", f"{where}.status is invalid.")
    if brief.get("mode") not in PRODUCT_PHOTOSHOOT_MODES:
        report.error("PRODUCT_PHOTOSHOOT", f"{where}.mode is invalid.")
    for field in ("short_intent", "placement"):
        if not _nonempty(brief.get(field)):
            report.error("PRODUCT_PHOTOSHOOT", f"{where}.{field} must be a non-empty string.")
    count = brief.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 10:
        report.error("PRODUCT_PHOTOSHOOT", f"{where}.count must be an integer from 1 to 10.")
    if brief.get("mode") in {"social_carousel", "ad_creative_pack"} and isinstance(count, int) and count < 3:
        report.error("PRODUCT_PHOTOSHOOT", f"{where} requires at least three connected slides/variants for this mode.")
    if brief.get("aspect_ratio") not in PRODUCT_PHOTOSHOOT_ASPECTS:
        report.error("PRODUCT_PHOTOSHOOT", f"{where}.aspect_ratio is unsupported by the official skill snapshot.")
    if brief.get("backend_prompt_owner") != "higgsfield-product-photoshoot-backend-enhancer":
        report.error("PRODUCT_PROMPT_OWNERSHIP", f"{where} must leave the final provider prompt to the official backend enhancer.")
    if brief.get("enhanced_prompt_exported") is not False:
        report.error("PRODUCT_PROMPT_OWNERSHIP", f"{where} may export only the short production intent, never a fabricated enhanced provider prompt.")
    if brief.get("platform_generation_performed") is not False:
        report.error("HIGGSFIELD_EXECUTION_BOUNDARY", f"{where}.platform_generation_performed must be false.")
    product_ids = brief.get("product_authority_ids")
    if not isinstance(product_ids, list) or any(not _nonempty(item) for item in product_ids):
        report.error("PRODUCT_PHOTOSHOOT", f"{where}.product_authority_ids must be a string array.")
        product_ids = []
    refs = brief.get("reference_asset_ids")
    if not isinstance(refs, list) or any(not _nonempty(item) for item in refs):
        report.error("PRODUCT_PHOTOSHOOT", f"{where}.reference_asset_ids must be a string array.")
        refs = []
    if not isinstance(brief.get("qa_notes"), list) or any(not _nonempty(item) for item in brief.get("qa_notes", [])):
        report.error("PRODUCT_PHOTOSHOOT", f"{where}.qa_notes must be a string array.")
    if status in {"qualified", "approved"}:
        if not product_ids:
            report.error("PRODUCT_PHOTOSHOOT", f"{where} requires at least one product authority.")
        for product_id in product_ids:
            product = products.get(product_id)
            if product is None:
                report.error("MISSING_REFERENCE", f"{where} references missing product authority {product_id}.")
            elif product.get("status") not in {"qualified", "approved"}:
                report.error("PRODUCT_AUTHORITY", f"{where} references product authority {product_id} before it passes fidelity QA.")
        for asset_id in refs:
            asset = assets.get(asset_id)
            if asset is None:
                report.error("MISSING_REFERENCE", f"{where} references missing asset {asset_id}.")
            elif asset.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"{where} references unapproved asset {asset_id}.")


def validate_higgsfield_methods(
    data: dict[str, Any] | None,
    assets: dict[str, dict[str, Any]],
    identity_packs: dict[str, dict[str, Any]],
    commercial: dict[str, Any] | None,
    report: Report,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Validate the optional v1.7 method-fusion manifest.

    Schema v1.6 projects made before this feature remain readable.  A warning
    makes the missing method layer explicit without silently rewriting them.
    """

    result = {"routes": {}, "souls": {}, "products": {}, "photoshoots": {}}
    if data is None:
        report.warning(
            "HIGGSFIELD_METHODS_MISSING",
            "This schema v1.6 project predates the v1.7 offline method-fusion manifest; initialize a new project to use the three-skill method layer.",
        )
        return result
    where = "manifests/higgsfield-methods.json"
    fields = (
        "schema_version", "policy", "status", "method_profile", "execution_boundary",
        "adoption_matrix", "generation_routes", "soul_readiness_records",
        "product_authorities", "product_photoshoot_briefs",
    )
    if not _require_fields(data, fields, where, report):
        return result
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"{where}.schema_version must be {SCHEMA_VERSION}.")
    if data.get("policy") != HIGGSFIELD_METHODS_POLICY:
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.policy must be {HIGGSFIELD_METHODS_POLICY}.")
    if data.get("status") not in HIGGSFIELD_METHOD_MANIFEST_STATUSES:
        report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.status is invalid.")
    _validate_method_profile(data.get("method_profile"), report)
    _validate_execution_boundary(data.get("execution_boundary"), report)
    adoption = data.get("adoption_matrix")
    if _require_fields(adoption, ("adopted", "translated", "provider_only_not_emulated"), f"{where}.adoption_matrix", report):
        for field in ("adopted", "translated", "provider_only_not_emulated"):
            if not _string_list(adoption.get(field)):
                report.error("HIGGSFIELD_METHOD_PROFILE", f"{where}.adoption_matrix.{field} must be a non-empty string array.")
        provider_only = "Soul model training and reusable reference-id creation" in adoption.get("provider_only_not_emulated", [])
        provider_only = provider_only and "Product Photoshoot backend prompt enhancement" in adoption.get("provider_only_not_emulated", [])
        if not provider_only:
            report.error("HIGGSFIELD_METHOD_PROFILE", f"{where} must explicitly preserve both provider-only backend boundaries.")

    for index, route in enumerate(data.get("generation_routes", []) if isinstance(data.get("generation_routes"), list) else []):
        route_where = f"{where}.generation_routes[{index}]"
        if not isinstance(route, dict):
            report.error("TYPE", f"{route_where} must be an object.")
            continue
        route_id = _duplicate_id(result["routes"], route, route_where, report)
        if route_id:
            _validate_route(route, route_where, assets, report)
    if not isinstance(data.get("generation_routes"), list):
        report.error("TYPE", f"{where}.generation_routes must be an array.")

    for index, record in enumerate(data.get("soul_readiness_records", []) if isinstance(data.get("soul_readiness_records"), list) else []):
        record_where = f"{where}.soul_readiness_records[{index}]"
        if not isinstance(record, dict):
            report.error("TYPE", f"{record_where} must be an object.")
            continue
        record_id = _duplicate_id(result["souls"], record, record_where, report)
        if record_id:
            _validate_soul_record(record, record_where, assets, identity_packs, report)
    if not isinstance(data.get("soul_readiness_records"), list):
        report.error("TYPE", f"{where}.soul_readiness_records must be an array.")

    for index, product in enumerate(data.get("product_authorities", []) if isinstance(data.get("product_authorities"), list) else []):
        product_where = f"{where}.product_authorities[{index}]"
        if not isinstance(product, dict):
            report.error("TYPE", f"{product_where} must be an object.")
            continue
        product_id = _duplicate_id(result["products"], product, product_where, report)
        if product_id:
            _validate_product_authority(product, product_where, assets, report)
    if not isinstance(data.get("product_authorities"), list):
        report.error("TYPE", f"{where}.product_authorities must be an array.")

    for index, brief in enumerate(data.get("product_photoshoot_briefs", []) if isinstance(data.get("product_photoshoot_briefs"), list) else []):
        brief_where = f"{where}.product_photoshoot_briefs[{index}]"
        if not isinstance(brief, dict):
            report.error("TYPE", f"{brief_where} must be an object.")
            continue
        brief_id = _duplicate_id(result["photoshoots"], brief, brief_where, report)
        if brief_id:
            _validate_photoshoot_brief(brief, brief_where, assets, result["products"], report)
    if not isinstance(data.get("product_photoshoot_briefs"), list):
        report.error("TYPE", f"{where}.product_photoshoot_briefs must be an array.")

    if data.get("status") == "approved":
        approved_routes = [item for item in result["routes"].values() if item.get("status") == "approved"]
        if not approved_routes:
            report.error("HIGGSFIELD_METHOD_GATE", "An approved method-fusion manifest requires at least one approved generation route.")
        if isinstance(commercial, dict) and commercial.get("status") == "approved":
            brief = commercial.get("commercial_brief") if isinstance(commercial.get("commercial_brief"), dict) else {}
            if brief.get("category") == "product":
                if not any(item.get("status") == "approved" for item in result["products"].values()):
                    report.error("PRODUCT_METHOD_GATE", "An approved product commercial requires an approved product authority.")
                if not any(item.get("status") == "approved" for item in result["photoshoots"].values()):
                    report.error("PRODUCT_METHOD_GATE", "An approved product commercial requires an approved offline Product Photoshoot intent brief.")
    return result


__all__ = [name for name in globals() if not name.startswith("__")]
