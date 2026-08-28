"""Schema, provenance, continuity, and production-gate validation."""

from __future__ import annotations

from .schema import *


def require_keys(value: Any, keys: tuple[str, ...], where: str, report: Report) -> bool:
    if not isinstance(value, dict):
        report.error("TYPE", f"{where} must be an object.")
        return False
    missing = [key for key in keys if key not in value]
    if missing:
        report.error("MISSING_FIELD", f"{where} is missing: {', '.join(missing)}.")
        return False
    return True


def require_string(value: Any, where: str, report: Report, allow_empty: bool = False) -> bool:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        report.error("TYPE", f"{where} must be {'a string' if allow_empty else 'a non-empty string'}.")
        return False
    return True


def require_string_list(value: Any, where: str, report: Report) -> bool:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        report.error("TYPE", f"{where} must be an array of strings.")
        return False
    return True


def load_json(path: Path, where: str, report: Report) -> dict[str, Any] | None:
    if not path.is_file():
        report.error("MISSING_FILE", f"Missing {where}: {path}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error("INVALID_JSON", f"Cannot read {where}: {exc}")
        return None
    if not isinstance(value, dict):
        report.error("TYPE", f"{where} must contain a JSON object.")
        return None
    return value


def check_relative_file(
    project_dir: Path,
    value: Any,
    where: str,
    report: Report,
    *,
    required: bool,
) -> Path | None:
    if value in (None, ""):
        if required:
            report.error("MISSING_PATH", f"{where} is required.")
        return None
    if not isinstance(value, str):
        report.error("TYPE", f"{where} must be a project-relative string path.")
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        report.error("UNSAFE_PATH", f"{where} must stay inside the project: {value}")
        return None
    root = project_dir.resolve()
    full = (project_dir / relative).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        report.error("UNSAFE_PATH", f"{where} escapes the project: {value}")
        return None
    if not full.is_file():
        report.error("MISSING_FILE", f"{where} does not exist: {value}")
        return None
    return full


def is_compiled_prompt_path(value: Any, kind: str) -> bool:
    """Recognize versioned output such as prompts/compiled/<gate>--v001/images/..."""
    if not isinstance(value, str):
        return False
    parts = value.replace("\\", "/").split("/")
    return len(parts) >= 5 and parts[0:2] == ["prompts", "compiled"] and parts[3] == kind


def portable_manifest_path(value: Any) -> str:
    """Normalize a manifest path for policy checks without using host path rules."""
    return value.replace("\\", "/") if isinstance(value, str) else ""


def validate_layout(project_dir: Path, report: Report) -> None:
    for relative in REQUIRED_DIRS:
        if not (project_dir / relative).is_dir():
            report.error("MISSING_DIR", f"Missing required directory: {relative}")
    for relative in REQUIRED_FILES:
        if not (project_dir / relative).is_file():
            report.error("MISSING_FILE", f"Missing required file: {relative}")


def validate_project_metadata(
    project: dict[str, Any] | None, report: Report
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    scenes_by_id: dict[str, dict[str, Any]] = {}
    scene_orders: dict[str, int] = {}
    if project is None:
        return scenes_by_id, scene_orders
    required = (
        "schema_version",
        "id",
        "title",
        "slug",
        "aspect_ratio",
        "interaction_language",
        "prompt_language",
        "production_mode",
        "capture_policy",
        "dynamic_range_policy",
        "static_generator",
        "video_generation",
        "approval_mode",
        "image_prompt_strategy",
        "video_prompt_strategy",
        "higgsfield_conformance",
        "candidate_policy",
        "motion_baseline",
        "reproducibility",
        "created_at",
        "updated_at",
        "scenes",
    )
    if not require_keys(project, required, "project.json", report):
        return scenes_by_id, scene_orders

    if project.get("schema_version") in LEGACY_SCHEMA_VERSIONS:
        report.error(
            "LEGACY_SCHEMA",
            f"project.json uses legacy schema {project.get('schema_version')}; cinematic-ai-director v1.6 does not migrate or modify v1.0-v1.5 projects.",
        )
    elif project.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"project.json schema_version must be {SCHEMA_VERSION}.")
    for field in ("id", "title", "slug", "aspect_ratio", "interaction_language", "prompt_language"):
        require_string(project.get(field), f"project.json.{field}", report)
    slug = project.get("slug")
    if isinstance(slug, str) and not SLUG_RE.fullmatch(slug):
        report.error("INVALID_SLUG", f"Invalid project slug: {slug}")
    aspect = project.get("aspect_ratio")
    if isinstance(aspect, str) and not ASPECT_RE.fullmatch(aspect):
        report.error("INVALID_ASPECT", f"Invalid aspect_ratio: {aspect}")
    elif isinstance(aspect, str):
        width_text, height_text = aspect.split(":", 1)
        ratio = int(width_text) / int(height_text)
        if not (9 / 16 <= ratio <= 21 / 9):
            report.error(
                "HIGGSFIELD_ASPECT",
                "Strict Seedance 2.5 delivery must stay within the officially published 9:16 to 21:9 aspect range.",
            )
    if project.get("static_generator") != "builtin-imagegen":
        report.error("BOUNDARY", "static_generator must be builtin-imagegen.")
    if project.get("production_mode") != "live-action":
        report.error("BOUNDARY", "production_mode must be live-action.")
    if project.get("capture_policy") != "adaptive-live-action-v1.6":
        report.error("BOUNDARY", "capture_policy must be adaptive-live-action-v1.6.")
    dynamic_range_policy = project.get("dynamic_range_policy")
    if require_keys(
        dynamic_range_policy,
        ("mode", "infinite_hdr_forbidden", "multi_exposure_merge_forbidden", "rule"),
        "project.json.dynamic_range_policy",
        report,
    ):
        if dynamic_range_policy.get("mode") != "finite_scene_referred":
            report.error("DYNAMIC_RANGE", "dynamic_range_policy.mode must be finite_scene_referred.")
        if dynamic_range_policy.get("infinite_hdr_forbidden") is not True:
            report.error("DYNAMIC_RANGE", "Infinite-HDR rendering must be forbidden.")
        if dynamic_range_policy.get("multi_exposure_merge_forbidden") is not True:
            report.error("DYNAMIC_RANGE", "Unrecorded multi-exposure HDR merging must be forbidden.")
        require_string(dynamic_range_policy.get("rule"), "project.json.dynamic_range_policy.rule", report)
    if project.get("video_generation") != "package-only":
        report.error("BOUNDARY", "video_generation must be package-only.")
    if project.get("approval_mode") != "foundation-and-sequence-gates":
        report.error("BOUNDARY", "approval_mode must be foundation-and-sequence-gates.")
    if project.get("image_prompt_strategy") != "image2-live-action-evidence-v1.6":
        report.error("BOUNDARY", "image_prompt_strategy must be image2-live-action-evidence-v1.6.")
    if project.get("video_prompt_strategy") != "shot-model-v1.6":
        report.error("BOUNDARY", "video_prompt_strategy must be shot-model-v1.6.")
    higgsfield_conformance = project.get("higgsfield_conformance")
    if require_keys(
        higgsfield_conformance,
        (
            "official_profile_id", "knowledge_snapshot", "target_workflow", "target_model",
            "strict", "version_policy", "source_urls",
        ),
        "project.json.higgsfield_conformance",
        report,
    ):
        if higgsfield_conformance.get("official_profile_id") != HIGGSFIELD_OFFICIAL_PROFILE_ID:
            report.error("HIGGSFIELD_OFFICIAL_PROFILE", "Project official Higgsfield profile does not match this Skill release.")
        if higgsfield_conformance.get("knowledge_snapshot") != HIGGSFIELD_KNOWLEDGE_SNAPSHOT:
            report.error("HIGGSFIELD_SNAPSHOT", "Project Higgsfield knowledge snapshot does not match this Skill release.")
        if higgsfield_conformance.get("target_workflow") != "cinema-studio-4":
            report.error("HIGGSFIELD_WORKFLOW", "Strict v1.6 projects must target Cinema Studio 4.")
        if higgsfield_conformance.get("target_model") != "seedance-2.5":
            report.error("HIGGSFIELD_MODEL", "Strict v1.6 projects must target Seedance 2.5.")
        if higgsfield_conformance.get("strict") is not True:
            report.error("HIGGSFIELD_STRICT", "Higgsfield strict conformance must be enabled.")
        if higgsfield_conformance.get("version_policy") != "snapshot-must-match-or-block":
            report.error("HIGGSFIELD_VERSION_POLICY", "Higgsfield exports must block on an unverified platform snapshot.")
        if higgsfield_conformance.get("source_urls") != list(HIGGSFIELD_OFFICIAL_SOURCE_URLS):
            report.error("HIGGSFIELD_OFFICIAL_SOURCES", "Project official Higgsfield source set is incomplete or out of order.")
    candidate_policy = project.get("candidate_policy")
    if require_keys(
        candidate_policy,
        (
            "identity_inspector_initial_count", "identity_inspector_max_batches",
            "critical_initial_count", "derivative_initial_count", "retry_count", "max_batches",
            "reviewer", "expose_failed_candidates",
        ),
        "project.json.candidate_policy",
        report,
    ):
        expected_counts = {
            "identity_inspector_initial_count": 1,
            "identity_inspector_max_batches": 1,
            "critical_initial_count": 3,
            "derivative_initial_count": 2,
            "retry_count": 2,
            "max_batches": 2,
        }
        for field, expected in expected_counts.items():
            if candidate_policy.get(field) != expected:
                report.error("CANDIDATE_POLICY", f"project.json.candidate_policy.{field} must be {expected}.")
        if candidate_policy.get("reviewer") != "codex-visual":
            report.error("CANDIDATE_POLICY", "candidate_policy.reviewer must be codex-visual.")
        if candidate_policy.get("expose_failed_candidates") is not False:
            report.error("CANDIDATE_POLICY", "Failed candidates must stay hidden by default.")
    reproducibility = project.get("reproducibility")
    if require_keys(
        reproducibility,
        ("backend", "reproducibility_class", "pixel_reproducible"),
        "project.json.reproducibility",
        report,
    ):
        if reproducibility.get("backend") != "builtin-imagegen":
            report.error("REPRODUCIBILITY", "project reproducibility backend must be builtin-imagegen.")
        if reproducibility.get("reproducibility_class") != "workflow_only":
            report.error("REPRODUCIBILITY", "built-in ImageGen projects must use workflow_only reproducibility.")
        if reproducibility.get("pixel_reproducible") is not False:
            report.error("REPRODUCIBILITY", "pixel_reproducible must be false; the built-in model exposes no stable seed or snapshot pin.")
    motion_baseline = project.get("motion_baseline")
    if require_keys(
        motion_baseline,
        ("capture_fps", "delivery_fps", "shutter_angle", "exposure_time_s"),
        "project.json.motion_baseline",
        report,
    ):
        fps = motion_baseline.get("capture_fps")
        delivery_fps = motion_baseline.get("delivery_fps")
        shutter = motion_baseline.get("shutter_angle")
        if not is_number(fps) or fps <= 0:
            report.error("CAMERA", "project.json.motion_baseline.capture_fps must be positive.")
        if not is_number(delivery_fps) or delivery_fps <= 0:
            report.error("CAMERA", "project.json.motion_baseline.delivery_fps must be positive.")
        if not is_number(shutter) or not 1 <= shutter <= 360:
            report.error("CAMERA", "project.json.motion_baseline.shutter_angle must be between 1 and 360.")
        exposure = motion_baseline.get("exposure_time_s")
        if not is_number(exposure) or exposure <= 0:
            report.error("TEMPORAL_CAPTURE", "project.json.motion_baseline.exposure_time_s must be positive.")
        elif is_number(fps) and fps > 0 and is_number(shutter):
            expected = float(shutter) / (360.0 * float(fps))
            if abs(float(exposure) - expected) > max(0.0001, expected * 0.01):
                report.error(
                    "SHUTTER_EXPOSURE_MISMATCH",
                    f"project.json.motion_baseline.exposure_time_s must equal shutter_angle/(360*capture_fps), expected {expected:.8f}.",
                )
    for field in ("created_at", "updated_at"):
        if not valid_timestamp(project.get(field)):
            report.error("TIMESTAMP", f"project.json.{field} must be a valid ISO-8601 timestamp.")

    scenes = project.get("scenes")
    if not isinstance(scenes, list):
        report.error("TYPE", "project.json.scenes must be an array.")
        return scenes_by_id, scene_orders

    used_orders: dict[int, str] = {}
    for index, scene in enumerate(scenes):
        where = f"project.json.scenes[{index}]"
        if not require_keys(
            scene,
            (
                "id",
                "order",
                "title",
                "summary",
                "capture_profile_id",
                "scene_state_id",
                "spatial_map_id",
                "primary_anchor_asset_id",
                "format_plan_id",
                "environmental_state_id",
            ),
            where,
            report,
        ):
            continue
        scene_id = scene.get("id")
        if not require_string(scene_id, f"{where}.id", report):
            continue
        if not ID_RE.fullmatch(scene_id):
            report.error("INVALID_ID", f"Invalid scene id: {scene_id}")
        if scene_id in scenes_by_id:
            report.error("DUPLICATE_ID", f"Duplicate scene id: {scene_id}")
        else:
            scenes_by_id[scene_id] = scene
        order = scene.get("order")
        if not is_integer(order):
            report.error("TYPE", f"{where}.order must be an integer.")
        elif order in used_orders:
            report.error("DUPLICATE_ORDER", f"Scene order {order} is shared by {used_orders[order]} and {scene_id}.")
        else:
            used_orders[order] = scene_id
            scene_orders[scene_id] = order
        require_string(scene.get("title"), f"{where}.title", report)
        require_string(scene.get("summary"), f"{where}.summary", report)
        require_string(scene.get("capture_profile_id"), f"{where}.capture_profile_id", report, allow_empty=True)
        require_string(scene.get("scene_state_id"), f"{where}.scene_state_id", report)
        require_string(scene.get("spatial_map_id"), f"{where}.spatial_map_id", report)
        require_string(scene.get("primary_anchor_asset_id"), f"{where}.primary_anchor_asset_id", report)
        require_string(scene.get("format_plan_id"), f"{where}.format_plan_id", report)
        require_string(scene.get("environmental_state_id"), f"{where}.environmental_state_id", report)
    return scenes_by_id, scene_orders


def validate_manifest_header(data: dict[str, Any] | None, list_key: str, where: str, report: Report) -> list[Any]:
    if data is None:
        return []
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"{where}.schema_version must be {SCHEMA_VERSION}.")
    value = data.get(list_key)
    if not isinstance(value, list):
        report.error("TYPE", f"{where}.{list_key} must be an array.")
        return []
    return value


def live_action_quality_passed(asset: dict[str, Any]) -> bool:
    quality = asset.get("live_action_quality_qa")
    if not isinstance(quality, dict):
        return False
    if quality.get("mode") == "not_applicable":
        return quality.get("verdict") == "not_applicable" and not quality.get("hard_failures")
    if quality.get("verdict") != "pass" or quality.get("hard_failures"):
        return False
    checks = quality.get("checks")
    evidence = quality.get("positive_evidence")
    scales = quality.get("scales_checked")
    if not isinstance(checks, dict) or any(checks.get(name) != "pass" for name in LIVE_ACTION_QUALITY_CHECKS):
        return False
    if not isinstance(evidence, dict) or any(not isinstance(evidence.get(name), str) or not evidence[name].strip() for name in LIVE_ACTION_QUALITY_CHECKS):
        return False
    dynamic_range = quality.get("dynamic_range_evidence")
    if not isinstance(dynamic_range, dict):
        return False
    if dynamic_range.get("exposure_priority") not in DYNAMIC_RANGE_PRIORITIES:
        return False
    for field in ("middle_tone_anchor", "highlight_loss_or_rolloff", "shadow_loss_or_floor"):
        if not isinstance(dynamic_range.get(field), str) or not dynamic_range[field].strip():
            return False
    if dynamic_range.get("global_tone_mapping_detected") is not False:
        return False
    return isinstance(scales, dict) and all(scales.get(scale) is True for scale in TEXTURE_QA_SCALES)


def authenticity_passed(asset: dict[str, Any], *, require_user_approval: bool) -> bool:
    del require_user_approval
    return live_action_quality_passed(asset)


def photographic_qa_passed(asset: dict[str, Any]) -> bool:
    photo = asset.get("photographic_qa")
    if not isinstance(photo, dict) or photo.get("reconstruction_pass") is not True or photo.get("hard_failures"):
        return False
    checks = photo.get("checks")
    return isinstance(checks, dict) and all(checks.get(name) == "pass" for name in PHOTO_QA_CHECKS)


def texture_qa_passed(asset: dict[str, Any], *, require_user_approval: bool) -> bool:
    del require_user_approval
    return live_action_quality_passed(asset)


def validate_texture_qa(asset: dict[str, Any], where: str, report: Report) -> None:
    texture = asset.get("texture_qa")
    required = (
        "mode",
        "attempt_index",
        "scales_checked",
        "checks",
        "verdict",
        "cross_material_pairs",
        "hard_failures",
        "notes",
        "checked_at",
        "user_decision",
        "user_decided_at",
        "escalation",
    )
    if not require_keys(texture, required, f"{where}.texture_qa", report):
        return
    mode = texture.get("mode")
    if mode not in TEXTURE_QA_MODES:
        report.error("ENUM", f"{where}.texture_qa.mode is invalid: {mode}")
    attempt = texture.get("attempt_index")
    if not is_integer(attempt) or not 0 <= attempt <= 2:
        report.error("TEXTURE_QA", f"{where}.texture_qa.attempt_index must be an integer from 0 to 2.")
    scales = texture.get("scales_checked")
    if require_keys(scales, TEXTURE_QA_SCALES, f"{where}.texture_qa.scales_checked", report):
        for scale in TEXTURE_QA_SCALES:
            if not isinstance(scales.get(scale), bool):
                report.error("TYPE", f"{where}.texture_qa.scales_checked.{scale} must be boolean.")
    checks = texture.get("checks")
    if require_keys(checks, TEXTURE_QA_CHECKS, f"{where}.texture_qa.checks", report):
        for name in TEXTURE_QA_CHECKS:
            if checks.get(name) not in TEXTURE_QA_RESULTS:
                report.error("ENUM", f"{where}.texture_qa.checks.{name} is invalid: {checks.get(name)}")
    if texture.get("verdict") not in {"pending", "pass", "fail"}:
        report.error("ENUM", f"{where}.texture_qa.verdict is invalid: {texture.get('verdict')}")
    pairs = texture.get("cross_material_pairs")
    if not isinstance(pairs, list) or any(
        not isinstance(pair, dict)
        or not isinstance(pair.get("material_a"), str)
        or not isinstance(pair.get("material_b"), str)
        or pair.get("same_repeating_texture") not in {True, False}
        for pair in pairs
    ):
        report.error(
            "TEXTURE_QA",
            f"{where}.texture_qa.cross_material_pairs must list material_a/material_b/same_repeating_texture records.",
        )
    require_string_list(texture.get("hard_failures"), f"{where}.texture_qa.hard_failures", report)
    require_string_list(texture.get("notes"), f"{where}.texture_qa.notes", report)
    if texture.get("user_decision") not in AUTHENTICITY_USER_DECISIONS:
        report.error("ENUM", f"{where}.texture_qa.user_decision is invalid: {texture.get('user_decision')}")
    if texture.get("escalation") not in {"none", "retry", "model_blocked"}:
        report.error("ENUM", f"{where}.texture_qa.escalation is invalid: {texture.get('escalation')}")
    for field in ("checked_at", "user_decided_at"):
        require_string(texture.get(field), f"{where}.texture_qa.{field}", report, allow_empty=True)

    status = asset.get("status")
    if status == "planned":
        if mode != "pending" or attempt != 0 or texture.get("verdict") != "pending":
            report.error("TEXTURE_QA", f"Planned asset {asset.get('id')} must keep texture QA pending at attempt 0.")
        return
    if asset.get("type") not in AUTHENTIC_ASSET_TYPES:
        return
    expected_mode = asset.get("surface_policy")
    if mode != expected_mode:
        report.error("TEXTURE_QA", f"Asset {asset.get('id')} texture mode must match surface_policy={expected_mode}.")
    if not is_integer(attempt) or attempt < 1:
        report.error("TEXTURE_QA", f"Reviewed asset {asset.get('id')} requires attempt_index 1 or 2.")
    if not valid_timestamp(texture.get("checked_at")):
        report.error("TIMESTAMP", f"{where}.texture_qa.checked_at is required after inspection.")
    if isinstance(checks, dict) and any(checks.get(name) == "fail" for name in TEXTURE_QA_CHECKS):
        if texture.get("verdict") != "fail":
            report.error("TEXTURE_QA", f"Asset {asset.get('id')} has a failed texture check but no fail verdict.")
    if isinstance(pairs, list) and any(pair.get("same_repeating_texture") is True for pair in pairs if isinstance(pair, dict)):
        if texture.get("verdict") != "fail":
            report.error("TEXTURE_HARD_FAIL", f"Asset {asset.get('id')} repeats texture across unrelated materials.")
    if status in {"candidate", "approved", "superseded"}:
        if not texture_qa_passed(asset, require_user_approval=status in {"approved", "superseded"}):
            report.error("TEXTURE_GATE", f"Asset {asset.get('id')} status={status} has not passed four-scale texture QA.")
        if texture.get("escalation") != "none":
            report.error("TEXTURE_QA", f"Asset {asset.get('id')} status={status} must use escalation=none.")
    if status == "candidate" and texture.get("user_decision") != "pending":
        report.error("TEXTURE_QA", f"Candidate asset {asset.get('id')} must await user texture approval.")
    if status in {"approved", "superseded"}:
        if texture.get("user_decision") != "approved" or not valid_timestamp(texture.get("user_decided_at")):
            report.error("TEXTURE_GATE", f"Approved asset {asset.get('id')} requires explicit texture approval and timestamp.")
    if status == "model_blocked":
        if attempt != 2 or texture.get("verdict") != "fail" or texture.get("escalation") != "model_blocked":
            report.error("MODEL_BLOCKED", f"Asset {asset.get('id')} may be model_blocked only after attempt 2 fails texture QA.")
    if attempt == 2 and texture.get("verdict") == "fail" and status != "model_blocked":
        report.error("MODEL_BLOCKED", f"Asset {asset.get('id')} failed texture QA twice and must become model_blocked.")


def geometry_qa_passed(asset: dict[str, Any], *, require_user_approval: bool) -> bool:
    del require_user_approval
    geometry = asset.get("geometry_qa")
    if not isinstance(geometry, dict):
        return False
    if geometry.get("mode") == "not_applicable":
        return geometry.get("verdict") == "not_applicable" and not geometry.get("hard_failures")
    if geometry.get("verdict") != "pass" or geometry.get("hard_failures"):
        return False
    checks = geometry.get("checks")
    if not isinstance(checks, dict) or any(checks.get(name) != "pass" for name in GEOMETRY_QA_CHECKS):
        return False
    return True


def live_action_surface_passed(asset: dict[str, Any], *, require_user_approval: bool) -> bool:
    del require_user_approval
    return live_action_quality_passed(asset)


def validate_geometry_qa(asset: dict[str, Any], where: str, report: Report) -> None:
    geometry = asset.get("geometry_qa")
    required = (
        "mode",
        "reference_signature_id",
        "projection_class",
        "views_checked",
        "checks",
        "measurements_compared",
        "verdict",
        "hard_failures",
        "notes",
        "checked_at",
    )
    if not require_keys(geometry, required, f"{where}.geometry_qa", report):
        return
    mode = geometry.get("mode")
    if mode not in GEOMETRY_QA_MODES:
        report.error("ENUM", f"{where}.geometry_qa.mode is invalid: {mode}")
    require_string(geometry.get("reference_signature_id"), f"{where}.geometry_qa.reference_signature_id", report, allow_empty=True)
    if geometry.get("projection_class") not in {
        "pending", "neutral_front_or_back", "side_or_three_quarter", "perspective_narrative", "not_applicable"
    }:
        report.error("ENUM", f"{where}.geometry_qa.projection_class is invalid: {geometry.get('projection_class')}")
    require_string_list(geometry.get("views_checked"), f"{where}.geometry_qa.views_checked", report)
    checks = geometry.get("checks")
    if require_keys(checks, GEOMETRY_QA_CHECKS, f"{where}.geometry_qa.checks", report):
        for name in GEOMETRY_QA_CHECKS:
            if checks.get(name) not in GEOMETRY_QA_RESULTS:
                report.error("ENUM", f"{where}.geometry_qa.checks.{name} is invalid: {checks.get(name)}")
    measurements = geometry.get("measurements_compared")
    if not isinstance(measurements, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("field"), str)
        or not is_number(item.get("expected"))
        or not is_number(item.get("observed"))
        or not is_number(item.get("tolerance"))
        or item.get("pass") not in {True, False}
        for item in measurements
    ):
        report.error(
            "GEOMETRY_QA",
            f"{where}.geometry_qa.measurements_compared must list field/expected/observed/tolerance/pass records.",
        )
    if geometry.get("verdict") not in {"pending", "pass", "fail", "not_applicable"}:
        report.error("ENUM", f"{where}.geometry_qa.verdict is invalid: {geometry.get('verdict')}")
    require_string_list(geometry.get("hard_failures"), f"{where}.geometry_qa.hard_failures", report)
    require_string_list(geometry.get("notes"), f"{where}.geometry_qa.notes", report)
    if "user_decision" in geometry or "user_decided_at" in geometry:
        report.error("APPROVAL_SCOPE", f"{where}.geometry_qa must not contain user decisions; use manifests/reviews.json.")
    require_string(geometry.get("checked_at"), f"{where}.geometry_qa.checked_at", report, allow_empty=True)

    status = asset.get("status")
    human_relevant = asset.get("type") in {
        "character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_identity_view", "character_variant",
        "character_state", "pose_contact_anchor", "live_action_probe"
    } or bool(asset.get("identity_pack_id"))
    if status == "planned":
        if mode != "pending" or geometry.get("verdict") != "pending":
            report.error("GEOMETRY_QA", f"Planned asset {asset.get('id')} must keep geometry QA pending.")
        return
    if human_relevant and mode in {"pending", "not_applicable"}:
        report.error("GEOMETRY_GATE", f"Human-relevant asset {asset.get('id')} requires active geometry QA.")
    if not human_relevant and mode != "not_applicable":
        report.error("GEOMETRY_QA", f"Non-human asset {asset.get('id')} must use geometry_qa.mode=not_applicable.")
    if status in {"qualified", "approved", "superseded"} and not geometry_qa_passed(asset, require_user_approval=False):
        report.error("GEOMETRY_GATE", f"Asset {asset.get('id')} status={status} has not passed geometry QA.")
    if mode not in {"pending", "not_applicable"} and not valid_timestamp(geometry.get("checked_at")):
        report.error("TIMESTAMP", f"{where}.geometry_qa.checked_at is required after inspection.")
    if isinstance(measurements, list) and any(item.get("pass") is False for item in measurements if isinstance(item, dict)):
        if geometry.get("verdict") != "fail":
            report.error("PROPORTION_DRIFT", f"Asset {asset.get('id')} has a failed proportion measurement without a fail verdict.")


def validate_live_action_surface_qa(asset: dict[str, Any], where: str, report: Report) -> None:
    surface = asset.get("live_action_surface_qa")
    required = (
        "mode", "scales_checked", "checks", "verdict", "hard_failures", "notes",
        "checked_at", "user_decision", "user_decided_at",
    )
    if not require_keys(surface, required, f"{where}.live_action_surface_qa", report):
        return
    mode = surface.get("mode")
    if mode not in LIVE_ACTION_SURFACE_QA_MODES:
        report.error("ENUM", f"{where}.live_action_surface_qa.mode is invalid: {mode}")
    scales = surface.get("scales_checked")
    if require_keys(scales, TEXTURE_QA_SCALES, f"{where}.live_action_surface_qa.scales_checked", report):
        for scale in TEXTURE_QA_SCALES:
            if not isinstance(scales.get(scale), bool):
                report.error("TYPE", f"{where}.live_action_surface_qa.scales_checked.{scale} must be boolean.")
    checks = surface.get("checks")
    if require_keys(checks, LIVE_ACTION_SURFACE_CHECKS, f"{where}.live_action_surface_qa.checks", report):
        for name in LIVE_ACTION_SURFACE_CHECKS:
            if checks.get(name) not in LIVE_ACTION_SURFACE_RESULTS:
                report.error("ENUM", f"{where}.live_action_surface_qa.checks.{name} is invalid: {checks.get(name)}")
    if surface.get("verdict") not in {"pending", "pass", "fail", "not_applicable"}:
        report.error("ENUM", f"{where}.live_action_surface_qa.verdict is invalid: {surface.get('verdict')}")
    require_string_list(surface.get("hard_failures"), f"{where}.live_action_surface_qa.hard_failures", report)
    require_string_list(surface.get("notes"), f"{where}.live_action_surface_qa.notes", report)
    if surface.get("user_decision") not in AUTHENTICITY_USER_DECISIONS:
        report.error("ENUM", f"{where}.live_action_surface_qa.user_decision is invalid: {surface.get('user_decision')}")
    for field in ("checked_at", "user_decided_at"):
        require_string(surface.get(field), f"{where}.live_action_surface_qa.{field}", report, allow_empty=True)

    status = asset.get("status")
    if status == "planned":
        if mode != "pending" or surface.get("verdict") != "pending":
            report.error("LIVE_ACTION_SURFACE", f"Planned asset {asset.get('id')} must keep live-action surface QA pending.")
        return
    if asset.get("type") in AUTHENTIC_ASSET_TYPES and mode in {"pending", "not_applicable"}:
        report.error("LIVE_ACTION_SURFACE", f"Live-action asset {asset.get('id')} requires active surface QA.")
    if status in {"candidate", "approved", "superseded"} and asset.get("type") in AUTHENTIC_ASSET_TYPES:
        if not live_action_surface_passed(asset, require_user_approval=status in {"approved", "superseded"}):
            report.error("LIVE_ACTION_SURFACE", f"Asset {asset.get('id')} status={status} has not passed live-action surface QA.")
    if status == "candidate" and surface.get("user_decision") != "pending":
        report.error("LIVE_ACTION_SURFACE", f"Candidate asset {asset.get('id')} must await user surface approval.")
    if status in {"approved", "superseded"} and asset.get("type") in AUTHENTIC_ASSET_TYPES:
        if surface.get("user_decision") != "approved" or not valid_timestamp(surface.get("user_decided_at")):
            report.error("LIVE_ACTION_SURFACE", f"Approved asset {asset.get('id')} requires explicit live-action surface approval.")
    if mode not in {"pending", "not_applicable"} and not valid_timestamp(surface.get("checked_at")):
        report.error("TIMESTAMP", f"{where}.live_action_surface_qa.checked_at is required after inspection.")
    if surface.get("hard_failures") and surface.get("verdict") != "fail":
        report.error("LIVE_ACTION_SURFACE", f"Asset {asset.get('id')} has live-action hard failures without a fail verdict.")


def validate_live_action_quality_qa(asset: dict[str, Any], where: str, report: Report) -> None:
    quality = asset.get("live_action_quality_qa")
    required = (
        "mode", "scales_checked", "checks", "positive_evidence", "material_pairs",
        "skin_surface_state", "skin_state_cause", "skin_state_regions", "verdict",
        "dynamic_range_evidence", "hard_failures", "notes", "reviewer", "checked_at",
    )
    if not require_keys(quality, required, f"{where}.live_action_quality_qa", report):
        return
    if "user_decision" in quality or "user_decided_at" in quality:
        report.error("APPROVAL_SCOPE", f"{where}.live_action_quality_qa must not contain user decisions; use manifests/reviews.json.")
    mode = quality.get("mode")
    if mode not in QUALITY_QA_MODES:
        report.error("ENUM", f"{where}.live_action_quality_qa.mode is invalid: {mode}")
    verdict = quality.get("verdict")
    if verdict not in QUALITY_QA_RESULTS:
        report.error("ENUM", f"{where}.live_action_quality_qa.verdict is invalid: {verdict}")
    scales = quality.get("scales_checked")
    if require_keys(scales, TEXTURE_QA_SCALES, f"{where}.live_action_quality_qa.scales_checked", report):
        for scale in TEXTURE_QA_SCALES:
            if not isinstance(scales.get(scale), bool):
                report.error("TYPE", f"{where}.live_action_quality_qa.scales_checked.{scale} must be boolean.")
    checks = quality.get("checks")
    if require_keys(checks, LIVE_ACTION_QUALITY_CHECKS, f"{where}.live_action_quality_qa.checks", report):
        for check in LIVE_ACTION_QUALITY_CHECKS:
            if checks.get(check) not in QUALITY_QA_RESULTS:
                report.error("ENUM", f"{where}.live_action_quality_qa.checks.{check} is invalid: {checks.get(check)}")
    evidence = quality.get("positive_evidence")
    if not isinstance(evidence, dict):
        report.error("TYPE", f"{where}.live_action_quality_qa.positive_evidence must be an object.")
    dynamic_range = quality.get("dynamic_range_evidence")
    if require_keys(
        dynamic_range,
        DYNAMIC_RANGE_QA_FIELDS,
        f"{where}.live_action_quality_qa.dynamic_range_evidence",
        report,
    ):
        priority = dynamic_range.get("exposure_priority")
        if priority not in DYNAMIC_RANGE_PRIORITIES:
            report.error("DYNAMIC_RANGE", f"{where}.live_action_quality_qa has invalid exposure priority: {priority}")
        for field in ("middle_tone_anchor", "highlight_loss_or_rolloff", "shadow_loss_or_floor"):
            require_string(
                dynamic_range.get(field),
                f"{where}.live_action_quality_qa.dynamic_range_evidence.{field}",
                report,
                allow_empty=asset.get("status") == "planned",
            )
        if asset.get("status") in {"qualified", "approved", "superseded"} and dynamic_range.get("global_tone_mapping_detected") is not False:
            report.error("DYNAMIC_RANGE", f"{where} shows global HDR/local-tone-mapping behavior.")
    pairs = quality.get("material_pairs")
    if not isinstance(pairs, list) or any(
        not isinstance(pair, dict)
        or not isinstance(pair.get("material_a"), str)
        or not isinstance(pair.get("material_b"), str)
        or pair.get("same_repeating_texture") not in {True, False}
        for pair in pairs
    ):
        report.error("QUALITY_QA", f"{where}.live_action_quality_qa.material_pairs must list material_a/material_b/same_repeating_texture records.")
    skin_state = quality.get("skin_surface_state")
    if skin_state not in SKIN_WETNESS_STATES:
        report.error("ENUM", f"{where}.live_action_quality_qa.skin_surface_state is invalid: {skin_state}")
    require_string(quality.get("skin_state_cause"), f"{where}.live_action_quality_qa.skin_state_cause", report, allow_empty=True)
    require_string_list(quality.get("skin_state_regions"), f"{where}.live_action_quality_qa.skin_state_regions", report)
    require_string_list(quality.get("hard_failures"), f"{where}.live_action_quality_qa.hard_failures", report)
    require_string_list(quality.get("notes"), f"{where}.live_action_quality_qa.notes", report)
    require_string(quality.get("reviewer"), f"{where}.live_action_quality_qa.reviewer", report, allow_empty=True)
    require_string(quality.get("checked_at"), f"{where}.live_action_quality_qa.checked_at", report, allow_empty=True)

    status = asset.get("status")
    asset_type = asset.get("type")
    if status == "planned":
        if mode != "pending" or verdict != "pending":
            report.error("QUALITY_QA", f"Planned asset {asset.get('id')} must keep live-action quality QA pending.")
        return
    if asset_type not in AUTHENTIC_ASSET_TYPES:
        if mode != "not_applicable" or verdict != "not_applicable":
            report.error("QUALITY_QA", f"Non-photographic asset {asset.get('id')} must use not_applicable quality QA.")
        return
    expected_mode = "narrative_frame" if asset_type in PROFILED_ASSET_TYPES or asset_type in {"look_test", "live_action_probe"} else "authority_reference"
    if mode != expected_mode:
        report.error("QUALITY_QA", f"Asset {asset.get('id')} requires live_action_quality_qa.mode={expected_mode}.")
    if asset_type in HUMAN_RELEVANT_ASSET_TYPES or asset.get("identity_pack_id"):
        if skin_state == "not_applicable":
            report.error("SKIN_STATE", f"Human asset {asset.get('id')} requires an explicit skin_surface_state.")
    elif skin_state != "not_applicable":
        report.error("SKIN_STATE", f"Non-human asset {asset.get('id')} must use skin_surface_state=not_applicable.")
    if skin_state not in {"natural_dry", "normal", "not_applicable"}:
        if not quality.get("skin_state_cause") or not quality.get("skin_state_regions"):
            report.error("SKIN_STATE", f"Non-default skin state on {asset.get('id')} requires cause and bounded regions.")
    if status in {"qualified", "approved", "superseded"}:
        if not live_action_quality_passed(asset):
            report.error("QUALITY_GATE", f"Asset {asset.get('id')} status={status} has not passed the positive live-action quality gate.")
        if quality.get("reviewer") != "codex-visual" or not valid_timestamp(quality.get("checked_at")):
            report.error("QUALITY_GATE", f"Asset {asset.get('id')} requires codex-visual review and timestamp.")
    if isinstance(pairs, list) and any(pair.get("same_repeating_texture") is True for pair in pairs if isinstance(pair, dict)):
        if verdict != "fail":
            report.error("QUALITY_HARD_FAIL", f"Asset {asset.get('id')} repeats texture across unrelated materials.")
    if quality.get("hard_failures") and verdict != "fail":
        report.error("QUALITY_HARD_FAIL", f"Asset {asset.get('id')} has quality hard failures without a fail verdict.")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_generation_provenance(
    project_dir: Path,
    asset: dict[str, Any],
    where: str,
    report: Report,
) -> None:
    provenance = asset.get("generation_provenance")
    required = (
        "backend",
        "reproducibility_class",
        "pixel_reproducible",
        "operation",
        "prompt_sha256",
        "reference_order",
        "reference_inputs",
        "output",
        "software_agent",
    )
    if not require_keys(provenance, required, f"{where}.generation_provenance", report):
        return
    backend = provenance.get("backend")
    if backend not in GENERATION_BACKENDS:
        report.error("ENUM", f"{where}.generation_provenance.backend is invalid: {backend}")
    if provenance.get("reproducibility_class") not in REPRODUCIBILITY_CLASSES:
        report.error("ENUM", f"{where}.generation_provenance.reproducibility_class is invalid.")
    operation = provenance.get("operation")
    if operation not in ASSET_MODES:
        report.error("ENUM", f"{where}.generation_provenance.operation is invalid: {operation}")
    require_string(provenance.get("software_agent"), f"{where}.generation_provenance.software_agent", report, allow_empty=True)
    reference_order = provenance.get("reference_order")
    require_string_list(reference_order, f"{where}.generation_provenance.reference_order", report)
    reference_inputs = provenance.get("reference_inputs")
    if not isinstance(reference_inputs, list):
        report.error("TYPE", f"{where}.generation_provenance.reference_inputs must be an array.")
        reference_inputs = []
    input_ids: list[str] = []
    for index, item in enumerate(reference_inputs):
        item_where = f"{where}.generation_provenance.reference_inputs[{index}]"
        if not require_keys(item, ("asset_id", "relative_path", "sha256"), item_where, report):
            continue
        asset_id = item.get("asset_id")
        relative_path = item.get("relative_path")
        if require_string(asset_id, f"{item_where}.asset_id", report):
            input_ids.append(asset_id)
        path = check_relative_file(project_dir, relative_path, f"{item_where}.relative_path", report, required=True)
        digest = item.get("sha256")
        if not _valid_sha256(digest):
            report.error("PROVENANCE_HASH", f"{item_where}.sha256 must be a lowercase SHA-256 digest.")
        elif path is not None and _sha256_file(path) != digest:
            report.error("PROVENANCE_HASH", f"{item_where}.sha256 does not match {relative_path}.")
    if isinstance(reference_order, list) and reference_order != input_ids:
        report.error("PROVENANCE_ORDER", f"{where} reference_order must exactly match reference_inputs order.")
    if isinstance(reference_order, list) and reference_order != asset.get("reference_asset_ids"):
        report.error("PROVENANCE_ORDER", f"{where} provenance order must match asset.reference_asset_ids.")

    output = provenance.get("output")
    if require_keys(output, ("relative_path", "sha256", "width_px", "height_px", "color_mode", "mime_type"), f"{where}.generation_provenance.output", report):
        output_path = check_relative_file(
            project_dir, output.get("relative_path"), f"{where}.generation_provenance.output.relative_path", report,
            required=asset.get("status") not in {"planned", "model_blocked"},
        )
        digest = output.get("sha256")
        if asset.get("status") not in {"planned", "model_blocked"}:
            expected_output_path = (
                asset.get("approved_path") if asset.get("status") in {"approved", "superseded"} else asset.get("candidate_path")
            )
            if output.get("relative_path") != expected_output_path:
                report.error("PROVENANCE_OUTPUT", f"{where} provenance output must match the active candidate/approved path.")
            if not _valid_sha256(digest):
                report.error("PROVENANCE_HASH", f"{where}.generation_provenance.output.sha256 is invalid.")
            elif output_path is not None and _sha256_file(output_path) != digest:
                report.error("PROVENANCE_HASH", f"{where} output hash does not match the recorded file.")
            if not is_integer(output.get("width_px")) or output.get("width_px") <= 0:
                report.error("PROVENANCE_IMAGE", f"{where} output width_px must be positive.")
            if not is_integer(output.get("height_px")) or output.get("height_px") <= 0:
                report.error("PROVENANCE_IMAGE", f"{where} output height_px must be positive.")
            require_string(output.get("color_mode"), f"{where}.generation_provenance.output.color_mode", report)
            require_string(output.get("mime_type"), f"{where}.generation_provenance.output.mime_type", report)

    if asset.get("generator") == "builtin-imagegen" and asset.get("status") != "planned":
        if backend != "builtin-imagegen" or provenance.get("reproducibility_class") != "workflow_only":
            report.error("REPRODUCIBILITY", f"Generated asset {asset.get('id')} must record builtin-imagegen/workflow_only.")
        if provenance.get("pixel_reproducible") is not False:
            report.error("REPRODUCIBILITY", f"Generated asset {asset.get('id')} must record pixel_reproducible=false.")
        if operation != asset.get("mode"):
            report.error("PROVENANCE_OPERATION", f"Asset {asset.get('id')} provenance operation must match mode.")
        prompt_path_value = asset.get("prompt_path")
        prompt_path = check_relative_file(project_dir, prompt_path_value, f"{where}.prompt_path", report, required=True)
        prompt_digest = provenance.get("prompt_sha256")
        if not _valid_sha256(prompt_digest):
            report.error("PROVENANCE_HASH", f"{where}.generation_provenance.prompt_sha256 is invalid.")
        elif prompt_path is not None and _sha256_file(prompt_path) != prompt_digest:
            report.error("PROVENANCE_HASH", f"{where} prompt SHA-256 does not match {prompt_path_value}.")
        for reference_input in reference_inputs:
            if not isinstance(reference_input, dict):
                continue
            target = None
            target_id = reference_input.get("asset_id")
            if isinstance(target_id, str):
                # Assets are validated in a second pass; the path/hash still proves the exact ordered file here.
                target = target_id
            if target and not str(reference_input.get("relative_path", "")).startswith("assets/"):
                report.error("PROVENANCE_PATH", f"{where} reference input {target} must use a portable assets/ path.")
    elif asset.get("generator") == "provided":
        if backend != "provided" or provenance.get("reproducibility_class") != "source_exact":
            report.error("REPRODUCIBILITY", f"Provided asset {asset.get('id')} must record provided/source_exact provenance.")
    elif asset.get("generator") == "deterministic-crop" and asset.get("status") != "planned":
        if backend != "deterministic-crop" or provenance.get("reproducibility_class") != "source_exact":
            report.error("REPRODUCIBILITY", f"Identity crop {asset.get('id')} must record deterministic-crop/source_exact provenance.")
        if provenance.get("pixel_reproducible") is not True or operation != "crop":
            report.error("REPRODUCIBILITY", f"Identity crop {asset.get('id')} must be a pixel-reproducible crop operation.")
        crop_box = provenance.get("crop_box_px")
        if not isinstance(crop_box, list) or len(crop_box) != 4 or any(not is_integer(value) or value < 0 for value in crop_box):
            report.error("IDENTITY_CROP", f"Identity crop {asset.get('id')} requires a non-negative four-value crop_box_px.")


def validate_reference_provenance(asset: dict[str, Any], where: str, report: Report) -> None:
    provenance = asset.get("reference_provenance")
    required = ("kind", "source_note", "rights_confirmed", "identity_consent_confirmed")
    if not require_keys(provenance, required, f"{where}.reference_provenance", report):
        return
    kind = provenance.get("kind")
    if kind not in REFERENCE_PROVENANCE_KINDS:
        report.error("ENUM", f"{where}.reference_provenance.kind is invalid: {kind}")
    require_string(provenance.get("source_note"), f"{where}.reference_provenance.source_note", report, allow_empty=True)
    for field in ("rights_confirmed", "identity_consent_confirmed"):
        if not isinstance(provenance.get(field), bool):
            report.error("TYPE", f"{where}.reference_provenance.{field} must be boolean.")
    if kind in {"user_provided_photo", "mixed"} and provenance.get("rights_confirmed") is not True:
        report.error("REFERENCE_RIGHTS", f"{where} uses user-provided photography without confirmed usage rights.")
    if (
        kind in {"user_provided_photo", "mixed"}
        and asset.get("type") in {
            "character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_master", "character_variant", "character_state"
        }
        and provenance.get("identity_consent_confirmed") is not True
    ):
        report.error("IDENTITY_CONSENT", f"{where} uses an identifiable person without confirmed likeness consent.")
    if asset.get("generator") == "provided" and kind not in {"user_provided_photo", "mixed"}:
        report.error("REFERENCE_PROVENANCE", f"{where} provided assets require user_provided_photo or mixed provenance.")


def validate_authenticity_qa(asset: dict[str, Any], where: str, report: Report) -> None:
    auth = asset.get("authenticity_qa")
    required = (
        "mode",
        "attempt_index",
        "checks",
        "ai_smell_verdict",
        "hard_failures",
        "notes",
        "checked_at",
        "user_decision",
        "user_decided_at",
        "escalation",
    )
    if not require_keys(auth, required, f"{where}.authenticity_qa", report):
        return
    mode = auth.get("mode")
    if mode not in AUTHENTICITY_QA_MODES:
        report.error("ENUM", f"{where}.authenticity_qa.mode is invalid: {mode}")
    attempt = auth.get("attempt_index")
    if not is_integer(attempt) or not 0 <= attempt <= 2:
        report.error("AUTHENTICITY_QA", f"{where}.authenticity_qa.attempt_index must be an integer from 0 to 2.")
    checks = auth.get("checks")
    if require_keys(checks, AUTHENTICITY_CHECKS, f"{where}.authenticity_qa.checks", report):
        for name in AUTHENTICITY_CHECKS:
            if checks.get(name) not in AUTHENTICITY_RESULTS:
                report.error("ENUM", f"{where}.authenticity_qa.checks.{name} is invalid: {checks.get(name)}")
    verdict = auth.get("ai_smell_verdict")
    if verdict not in AUTHENTICITY_RESULTS:
        report.error("ENUM", f"{where}.authenticity_qa.ai_smell_verdict is invalid: {verdict}")
    require_string_list(auth.get("hard_failures"), f"{where}.authenticity_qa.hard_failures", report)
    require_string_list(auth.get("notes"), f"{where}.authenticity_qa.notes", report)
    user_decision = auth.get("user_decision")
    if user_decision not in AUTHENTICITY_USER_DECISIONS:
        report.error("ENUM", f"{where}.authenticity_qa.user_decision is invalid: {user_decision}")
    escalation = auth.get("escalation")
    if escalation not in AUTHENTICITY_ESCALATIONS:
        report.error("ENUM", f"{where}.authenticity_qa.escalation is invalid: {escalation}")
    for field in ("checked_at", "user_decided_at"):
        require_string(auth.get(field), f"{where}.authenticity_qa.{field}", report, allow_empty=True)

    status = asset.get("status")
    asset_type = asset.get("type")
    expected_mode = "neutral_reference" if asset_type in NEUTRAL_REFERENCE_ASSET_TYPES else "narrative_frame"
    if status == "planned":
        if mode != "pending" or attempt != 0 or verdict != "pending" or user_decision != "pending":
            report.error("AUTHENTICITY_QA", f"Planned asset {asset.get('id')} must keep authenticity QA pending at attempt 0.")
        return
    if asset_type not in AUTHENTIC_ASSET_TYPES:
        return
    if mode != expected_mode:
        report.error("AUTHENTICITY_QA", f"Asset {asset.get('id')} type={asset_type} requires authenticity_qa.mode={expected_mode}.")
    if not is_integer(attempt) or attempt < 1:
        report.error("AUTHENTICITY_QA", f"Reviewed asset {asset.get('id')} requires attempt_index 1 or 2.")
    if not valid_timestamp(auth.get("checked_at")):
        report.error("TIMESTAMP", f"{where}.authenticity_qa.checked_at is required after review.")
    if isinstance(checks, dict) and any(checks.get(name) == "fail" for name in AUTHENTICITY_CHECKS) and verdict != "fail":
        report.error("AUTHENTICITY_QA", f"Asset {asset.get('id')} has a failed authenticity check but no fail verdict.")
    if status in {"candidate", "approved", "superseded"}:
        if not authenticity_passed(asset, require_user_approval=status in {"approved", "superseded"}):
            report.error("AUTHENTICITY_GATE", f"Asset {asset.get('id')} status={status} has not passed the authenticity gate.")
        if escalation != "none":
            report.error("AUTHENTICITY_QA", f"Asset {asset.get('id')} status={status} must use escalation=none.")
    if status == "candidate" and user_decision != "pending":
        report.error("AUTHENTICITY_QA", f"Candidate asset {asset.get('id')} must wait for user_decision=pending.")
    if status in {"approved", "superseded"}:
        if user_decision != "approved" or not valid_timestamp(auth.get("user_decided_at")):
            report.error("AUTHENTICITY_GATE", f"Approved asset {asset.get('id')} requires explicit user approval and timestamp.")
    if status == "rejected" and user_decision == "approved":
        report.error("AUTHENTICITY_QA", f"Rejected asset {asset.get('id')} cannot have user_decision=approved.")
    if escalation == "real_reference_required":
        if asset_type not in {
            "character_face_anchor", "character_body_anchor", "character_master", "character_variant", "character_state", "location_master", "location_variant"
        }:
            report.error("AUTHENTICITY_QA", "real_reference_required is only valid for character or location anchors.")
        if status != "rejected" or attempt != 2 or verdict != "fail":
            report.error("AUTHENTICITY_QA", f"Asset {asset.get('id')} real-reference escalation requires rejected attempt 2 with fail verdict.")
    if asset_type in {"character_face_anchor", "character_body_anchor", "character_master", "location_master"} and attempt == 2 and verdict == "fail" and escalation != "real_reference_required":
        report.error("AUTHENTICITY_ESCALATION", f"Authoritative anchor {asset.get('id')} failed twice and must request a real reference.")


def validate_reference_coverage(asset: dict[str, Any], where: str, report: Report) -> None:
    asset_type = asset.get("type")
    status = asset.get("status")
    coverage = asset.get("reference_coverage")
    coverage_required = status in {"qualified", "approved", "superseded"} and asset_type in {
        "character_identity_inspector",
        "character_master",
        "location_master",
        "location_variant",
    }
    if coverage is None:
        if coverage_required:
            report.error(
                "REFERENCE_COVERAGE",
                f"Asset {asset.get('id')} requires structured multi-view/reference coverage metadata.",
            )
        return
    fields = (
        "policy",
        "required_views",
        "present_views",
        "same_subject_or_geography_pass",
        "background_policy",
        "notes",
    )
    if not require_keys(coverage, fields, f"{where}.reference_coverage", report):
        return
    policy = coverage.get("policy")
    if policy not in REFERENCE_COVERAGE_POLICIES:
        report.error("ENUM", f"{where}.reference_coverage.policy is invalid: {policy}")
    background_policy = coverage.get("background_policy")
    if background_policy not in REFERENCE_BACKGROUND_POLICIES:
        report.error("ENUM", f"{where}.reference_coverage.background_policy is invalid: {background_policy}")
    require_string_list(coverage.get("required_views"), f"{where}.reference_coverage.required_views", report)
    require_string_list(coverage.get("present_views"), f"{where}.reference_coverage.present_views", report)
    require_string_list(coverage.get("notes"), f"{where}.reference_coverage.notes", report)
    consistency_pass = coverage.get("same_subject_or_geography_pass")
    if not isinstance(consistency_pass, bool):
        report.error("TYPE", f"{where}.reference_coverage.same_subject_or_geography_pass must be boolean.")
    required_views = coverage.get("required_views") if isinstance(coverage.get("required_views"), list) else []
    present_views = coverage.get("present_views") if isinstance(coverage.get("present_views"), list) else []
    if len(required_views) != len(set(required_views)) or len(present_views) != len(set(present_views)):
        report.error("DUPLICATE_REFERENCE", f"Asset {asset.get('id')} repeats a reference coverage view.")
    missing_views = set(required_views) - set(present_views)
    if missing_views:
        report.error(
            "REFERENCE_COVERAGE",
            f"Asset {asset.get('id')} is missing declared views: {', '.join(sorted(missing_views))}.",
        )

    if status not in {"qualified", "approved", "superseded"}:
        return
    if asset_type == "character_identity_inspector":
        if policy != "identity_single_solve_inspector":
            report.error("IDENTITY_INSPECTOR", f"Identity inspector {asset.get('id')} must use identity_single_solve_inspector coverage.")
        if set(required_views) != set(IDENTITY_VIEW_ROLES) or set(present_views) != set(IDENTITY_VIEW_ROLES):
            report.error("IDENTITY_INSPECTOR", f"Identity inspector {asset.get('id')} must contain the seven official Higgsfield sheet roles once each.")
        if background_policy != "pure_white" or consistency_pass is not True:
            report.error("IDENTITY_INSPECTOR", f"Identity inspector {asset.get('id')} requires pure white and one-identity consistency across the full sheet.")
    elif asset_type == "character_master":
        if policy != "character_turnaround":
            report.error("CHARACTER_TURNAROUND", f"Character master {asset.get('id')} must use character_turnaround coverage.")
        missing_character_views = CHARACTER_TURNAROUND_VIEWS - set(present_views)
        if missing_character_views:
            report.error(
                "CHARACTER_TURNAROUND",
                f"Character master {asset.get('id')} lacks: {', '.join(sorted(missing_character_views))}.",
            )
        if background_policy != "pure_white":
            report.error("CHARACTER_TURNAROUND", f"Character master {asset.get('id')} requires a pure-white background.")
        if consistency_pass is not True:
            report.error("CHARACTER_TURNAROUND", f"Character master {asset.get('id')} must pass identity consistency across all views.")
    elif asset_type == "location_master":
        if policy not in {"single_view", "location_multiview"}:
            report.error("LOCATION_COVERAGE", f"Location master {asset.get('id')} uses invalid coverage policy {policy}.")
        if policy == "single_view" and "establishing_wide" not in present_views:
            report.error("LOCATION_COVERAGE", f"Single-view location master {asset.get('id')} requires establishing_wide.")
        if policy == "location_multiview" and LOCATION_MULTIVIEW_VIEWS - set(present_views):
            report.error(
                "LOCATION_COVERAGE",
                f"Location master {asset.get('id')} lacks required multi-view geography coverage.",
            )
        if consistency_pass is not True:
            report.error("LOCATION_COVERAGE", f"Location master {asset.get('id')} must pass geography consistency review.")
    elif asset_type == "location_variant":
        if policy not in {"single_view", "location_multiview"}:
            report.error("LOCATION_COVERAGE", f"Location variant {asset.get('id')} uses invalid coverage policy {policy}.")
        if policy == "single_view" and not (set(present_views) & (LOCATION_VIEW_ROLES - {""})):
            report.error("LOCATION_COVERAGE", f"Single-view location variant {asset.get('id')} requires a recognized scene-state view role.")
        if policy == "location_multiview":
            missing_location_views = LOCATION_MULTIVIEW_VIEWS - set(present_views)
            if missing_location_views:
                report.error(
                    "LOCATION_COVERAGE",
                    f"Location multi-view asset {asset.get('id')} lacks: {', '.join(sorted(missing_location_views))}.",
                )
        if consistency_pass is not True:
            report.error("LOCATION_COVERAGE", f"Location variant {asset.get('id')} must pass geography consistency review.")


def _positive_cue_occurs(text: str, cue: str) -> bool:
    folded = text.casefold()
    for match in re.finditer(rf"(?<![a-z0-9]){re.escape(cue.casefold())}(?![a-z0-9])", folded):
        prefix = folded[max(0, match.start() - 64):match.start()]
        clause_prefix = re.split(r"[.;\n]", prefix)[-1]
        if re.search(
            r"\b(?:no|without|avoid|forbid|forbidden|exclude|do not|never|reject)\b[^.;\n]{0,48}$",
            clause_prefix,
        ):
            continue
        return True
    return False


def validate_material_response_contract(asset: dict[str, Any], where: str, report: Report) -> None:
    contract = asset.get("material_response_contract")
    contract_where = f"{where}.material_response_contract"
    if not require_keys(contract, MATERIAL_RESPONSE_CONTRACT_FIELDS, contract_where, report):
        return

    for field in ("skin", "hair", "fabric", "hard_surfaces", "local_contrast_policy", "tone_mapping_policy", "material_roughness_separation", "performance_staging_policy"):
        require_string(contract.get(field), f"{contract_where}.{field}", report)
    for field in ("skin_key_source", "skin_key_source_size", "skin_key_direction", "skin_specular_behavior"):
        require_string(contract.get(field), f"{contract_where}.{field}", report, allow_empty=True)
    for field in ("skin_fill_sources", "color_contamination_sources"):
        require_string_list(contract.get(field), f"{contract_where}.{field}", report)

    skin_presence = contract.get("skin_presence")
    if skin_presence not in {"present", "absent"}:
        report.error("MATERIAL_RESPONSE", f"{contract_where}.skin_presence must be present or absent.")
    wetness = contract.get("skin_wetness_state")
    if wetness not in SKIN_WETNESS_STATES:
        report.error("MATERIAL_RESPONSE", f"{contract_where}.skin_wetness_state is invalid: {wetness}")

    human_bound = asset.get("type") in HUMAN_RELEVANT_ASSET_TYPES or bool(asset.get("identity_pack_id"))
    if human_bound and skin_presence != "present":
        report.error("SKIN_ILLUMINATION", f"Human-bearing asset {asset.get('id')} must use skin_presence=present.")
    if skin_presence == "present":
        for field in ("skin_key_source", "skin_key_source_size", "skin_key_direction", "skin_specular_behavior"):
            if not isinstance(contract.get(field), str) or not contract.get(field, "").strip():
                report.error("SKIN_ILLUMINATION", f"Asset {asset.get('id')} with visible skin requires {field}.")
        if wetness == "not_applicable":
            report.error("SKIN_ILLUMINATION", f"Asset {asset.get('id')} with visible skin requires an explicit wetness state.")
        if contract.get("performance_staging_policy") == "not_applicable":
            report.error("PERFORMANCE_STAGING", f"Asset {asset.get('id')} with visible people requires an observational/performance staging policy.")
    elif skin_presence == "absent":
        if wetness != "not_applicable":
            report.error("MATERIAL_RESPONSE", f"Asset {asset.get('id')} without visible skin must use skin_wetness_state=not_applicable.")

    contract_text = "\n".join(
        str(value) if not isinstance(value, list) else "\n".join(str(item) for item in value)
        for value in contract.values()
    )
    for cue in RISKY_RENDER_CUES:
        if _positive_cue_occurs(contract_text, cue):
            report.error(
                "MATERIAL_RESPONSE",
                f"Asset {asset.get('id')} material_response_contract positively uses the uncalibrated render cue `{cue}`.",
            )

    if skin_presence == "present" and wetness in {"natural_dry", "normal"}:
        for cue in ("wet skin", "sweaty skin", "perspiration sheen", "oil sheen", "oily skin"):
            if _positive_cue_occurs(contract_text, cue):
                report.error(
                    "SKIN_ILLUMINATION",
                    f"Asset {asset.get('id')} declares a natural non-wet skin state but positively requests `{cue}`.",
                )
    if wetness in {"perspiration", "rain_wet", "submerged", "cosmetic_sheen"} and not asset.get("localized_story_evidence"):
        report.error(
            "SKIN_ILLUMINATION",
            f"Asset {asset.get('id')} uses {wetness} without localized_story_evidence.",
        )


def asset_dependency_is_usable(source: dict[str, Any], target: dict[str, Any]) -> bool:
    if target.get("status") == "approved":
        return True
    return (
        source.get("status") == "qualified"
        and target.get("status") == "qualified"
        and isinstance(source.get("approval_gate_id"), str)
        and bool(source.get("approval_gate_id"))
        and source.get("approval_gate_id") == target.get("approval_gate_id")
    )


def validate_assets(
    project_dir: Path,
    data: dict[str, Any] | None,
    scene_ids: set[str],
    report: Report,
) -> dict[str, dict[str, Any]]:
    rows = validate_manifest_header(data, "assets", "manifests/assets.json", report)
    assets: dict[str, dict[str, Any]] = {}
    roles: dict[str, list[dict[str, Any]]] = defaultdict(list)
    required = (
        "id",
        "role",
        "type",
        "status",
        "revision",
        "generator",
        "mode",
        "derived_from",
        "replaces_asset_id",
        "reference_asset_ids",
        "scene_ids",
        "capture_profile_id",
        "comparison_set_id",
        "scene_state_id",
        "view_role",
        "view_side",
        "identity_view_role",
        "identity_background_policy",
        "spatial_map_id",
        "primary_anchor_asset_id",
        "constraints",
        "prompt_path",
        "candidate_path",
        "approved_path",
        "prompt_strategy_id",
        "calibration_family",
        "candidate_set_id",
        "quality_profile_id",
        "approval_gate_id",
        "identity_pack_id",
        "character_state_id",
        "location_world_id",
        "location_state_id",
        "root_reference_ids",
        "state_delta",
        "surface_policy",
        "medium_signature_id",
        "localized_story_evidence",
        "material_response_contract",
        "dynamic_range_plan",
        "pose_contact_anchor_ids",
        "reference_provenance",
        "qa",
        "photographic_qa",
        "geometry_qa",
        "live_action_quality_qa",
        "generation_provenance",
        "created_at",
    )

    for index, asset in enumerate(rows):
        where = f"manifests/assets.json.assets[{index}]"
        if not require_keys(asset, required, where, report):
            continue
        asset_id = asset.get("id")
        role = asset.get("role")
        if not require_string(asset_id, f"{where}.id", report):
            continue
        if not ID_RE.fullmatch(asset_id):
            report.error("INVALID_ID", f"Invalid asset id: {asset_id}")
        if asset_id in assets:
            report.error("DUPLICATE_ID", f"Duplicate asset id: {asset_id}")
        else:
            assets[asset_id] = asset
        if require_string(role, f"{where}.role", report):
            roles[role].append(asset)

        asset_type = asset.get("type")
        status = asset.get("status")
        generator = asset.get("generator")
        mode = asset.get("mode")
        if asset_type not in ASSET_TYPES:
            report.error("ENUM", f"{where}.type is invalid: {asset_type}")
        if status not in ASSET_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        if generator not in ASSET_GENERATORS:
            report.error("BOUNDARY", f"{where}.generator must be builtin-imagegen, provided, or deterministic-crop.")
        if mode not in ASSET_MODES:
            report.error("ENUM", f"{where}.mode is invalid: {mode}")
        revision = asset.get("revision")
        if not is_integer(revision) or revision < 1:
            report.error("TYPE", f"{where}.revision must be an integer >= 1.")
        elif not re.search(rf"--v0*{revision}$", asset_id):
            report.warning("VERSION_NAME", f"{asset_id} does not end with a version matching revision {revision}.")
        if not valid_timestamp(asset.get("created_at")):
            report.error("TIMESTAMP", f"{where}.created_at must be a valid ISO-8601 timestamp.")

        for field in (
            "derived_from",
            "replaces_asset_id",
            "capture_profile_id",
            "comparison_set_id",
            "scene_state_id",
            "view_role",
            "view_side",
            "identity_view_role",
            "identity_background_policy",
            "spatial_map_id",
            "primary_anchor_asset_id",
            "prompt_path",
            "candidate_path",
            "approved_path",
            "prompt_strategy_id",
            "calibration_family",
            "candidate_set_id",
            "quality_profile_id",
            "approval_gate_id",
            "identity_pack_id",
            "character_state_id",
            "location_world_id",
            "location_state_id",
            "surface_policy",
            "medium_signature_id",
        ):
            require_string(asset.get(field), f"{where}.{field}", report, allow_empty=True)
        for field in (
            "reference_asset_ids", "root_reference_ids", "scene_ids", "constraints",
            "localized_story_evidence", "pose_contact_anchor_ids",
        ):
            require_string_list(asset.get(field), f"{where}.{field}", report)
        if status not in {"planned", "model_blocked"} and not asset.get("approval_gate_id"):
            report.error("REVIEW_GATE", f"Asset {asset_id} requires approval_gate_id.")
        if status not in {"planned", "model_blocked"} and asset_type in AUTHENTIC_ASSET_TYPES and not asset.get("quality_profile_id"):
            report.error("QUALITY_PROFILE", f"Photographic asset {asset_id} requires quality_profile_id.")
        if generator == "builtin-imagegen" and status != "planned" and not asset.get("candidate_set_id"):
            report.error("CANDIDATE_SET", f"Generated asset {asset_id} requires candidate_set_id.")
        if not isinstance(asset.get("state_delta"), dict):
            report.error("TYPE", f"{where}.state_delta must be an object.")
        validate_material_response_contract(asset, where, report)
        if asset_type in AUTHENTIC_ASSET_TYPES:
            validate_dynamic_range_plan(asset.get("dynamic_range_plan"), f"{where}.dynamic_range_plan", report)
            dynamic_evidence = asset.get("live_action_quality_qa", {}).get("dynamic_range_evidence", {})
            if (
                isinstance(dynamic_evidence, dict)
                and isinstance(asset.get("dynamic_range_plan"), dict)
                and dynamic_evidence.get("exposure_priority") != asset["dynamic_range_plan"].get("exposure_priority")
            ):
                report.error(
                    "DYNAMIC_RANGE",
                    f"{where} dynamic-range QA exposure priority must match the asset capture plan.",
                )
        if asset.get("surface_policy") not in SURFACE_POLICIES:
            report.error("ENUM", f"{where}.surface_policy is invalid: {asset.get('surface_policy')}")
        if asset_type == "live_action_probe":
            if generator != "builtin-imagegen" or mode != "generate":
                report.error("LIVE_ACTION_PROBE_ASSET", f"Probe asset {asset_id} must be an independent built-in ImageGen generation.")
            if asset.get("surface_policy") != "clean_narrative":
                report.error("LIVE_ACTION_PROBE_ASSET", f"Probe asset {asset_id} must use surface_policy=clean_narrative.")
            if asset.get("derived_from") or len(asset.get("reference_asset_ids", [])) != 2:
                report.error(
                    "LIVE_ACTION_PROBE_REFERENCE",
                    f"Probe asset {asset_id} must directly reference exactly one unified identity Inspector and one location authority; no derived candidate chain.",
                )
            for field in (
                "probe_task",
                "probe_blocking",
                "probe_camera_condition",
                "ordinary_light_source",
            ):
                require_string(asset.get(field), f"{where}.{field}", report, allow_empty=status == "planned")

        identity_view_role = asset.get("identity_view_role")
        if identity_view_role not in {"", *IDENTITY_VIEW_ROLES}:
            report.error("ENUM", f"{where}.identity_view_role is invalid: {identity_view_role}")
        if asset_type == "character_identity_inspector":
            if identity_view_role:
                report.error("IDENTITY_INSPECTOR", f"Unified inspector {asset_id} must not masquerade as one crop role.")
            if asset.get("identity_background_policy") != "pure_white":
                report.error("IDENTITY_INSPECTOR", f"Unified inspector {asset_id} requires a pure-white background.")
            layout = asset.get("identity_inspector_layout")
            expected_slots = [*IDENTITY_VIEW_ROLES, "blank"]
            if not isinstance(layout, dict):
                report.error("IDENTITY_INSPECTOR", f"Unified inspector {asset_id} requires identity_inspector_layout metadata.")
            else:
                if layout.get("profile") != "higgsfield-character-reference-sheet-two-row-single-solve-v1.6":
                    report.error("IDENTITY_INSPECTOR", f"Unified inspector {asset_id} uses an unsupported layout profile.")
                if layout.get("grid") != [4, 2] or layout.get("slot_roles") != expected_slots:
                    report.error("IDENTITY_INSPECTOR", f"Unified inspector {asset_id} must use the official 4x2 seven-role order plus one blank cell.")
                if layout.get("single_identity_solve") is not True or layout.get("authoritative") is not True:
                    report.error("IDENTITY_INSPECTOR", f"Unified inspector {asset_id} must be authoritative and share one identity solve.")
        elif asset_type in {"character_face_anchor", "character_body_anchor", "character_identity_view"}:
            if identity_view_role not in IDENTITY_VIEW_ROLES:
                report.error("IDENTITY_VIEW", f"Identity crop {asset_id} requires one v1.6 identity_view_role.")
            if asset.get("identity_background_policy") != "pure_white":
                report.error("IDENTITY_VIEW", f"Identity crop {asset_id} requires a pure-white background.")
        elif identity_view_role:
            report.error("IDENTITY_VIEW", f"Only identity authority assets may set identity_view_role: {asset_id}.")
        elif asset.get("identity_background_policy"):
            report.error("IDENTITY_VIEW", f"Only identity authority assets may set identity_background_policy: {asset_id}.")

        if asset.get("view_role") not in LOCATION_VIEW_ROLES:
            report.error("ENUM", f"{where}.view_role is invalid: {asset.get('view_role')}")
        if asset.get("view_side") not in LOCATION_VIEW_SIDES:
            report.error("ENUM", f"{where}.view_side is invalid: {asset.get('view_side')}")
        if asset_type != "location_variant" and (asset.get("view_role") or asset.get("view_side")):
            report.error("SPATIAL_ASSET", f"Only location_variant scene-state views may set view_role/view_side: {asset_id}.")

        for scene_id in asset.get("scene_ids", []) if isinstance(asset.get("scene_ids"), list) else []:
            if scene_id not in scene_ids:
                report.error("ORPHAN_SCENE", f"Asset {asset_id} references missing scene {scene_id}.")

        validate_reference_provenance(asset, where, report)
        validate_geometry_qa(asset, where, report)
        validate_live_action_quality_qa(asset, where, report)
        validate_generation_provenance(project_dir, asset, where, report)
        validate_reference_coverage(asset, where, report)

        qa = asset.get("qa")
        if require_keys(qa, ("hard_failures", "soft_notes", "checked_at"), f"{where}.qa", report):
            require_string_list(qa.get("hard_failures"), f"{where}.qa.hard_failures", report)
            require_string_list(qa.get("soft_notes"), f"{where}.qa.soft_notes", report)
            checked_at = qa.get("checked_at")
            if status != "planned" and not valid_timestamp(checked_at):
                report.error("TIMESTAMP", f"{where}.qa.checked_at is required after generation or review.")
            if status == "approved" and qa.get("hard_failures"):
                report.error("APPROVAL", f"Approved asset {asset_id} still has hard failures.")

        photo_qa = asset.get("photographic_qa")
        photo_required = (
            "mode",
            "reconstruction_pass",
            "checks",
            "hard_failures",
            "notes",
            "checked_at",
        )
        if require_keys(photo_qa, photo_required, f"{where}.photographic_qa", report):
            photo_mode = photo_qa.get("mode")
            if photo_mode not in PHOTO_QA_MODES:
                report.error("ENUM", f"{where}.photographic_qa.mode is invalid: {photo_mode}")
            if not isinstance(photo_qa.get("reconstruction_pass"), bool):
                report.error("TYPE", f"{where}.photographic_qa.reconstruction_pass must be boolean.")
            checks = photo_qa.get("checks")
            if require_keys(checks, PHOTO_QA_CHECKS, f"{where}.photographic_qa.checks", report):
                for check_name in PHOTO_QA_CHECKS:
                    if checks.get(check_name) not in PHOTO_QA_RESULTS:
                        report.error(
                            "ENUM",
                            f"{where}.photographic_qa.checks.{check_name} is invalid: {checks.get(check_name)}",
                        )
            require_string_list(photo_qa.get("hard_failures"), f"{where}.photographic_qa.hard_failures", report)
            require_string_list(photo_qa.get("notes"), f"{where}.photographic_qa.notes", report)
            photo_checked_at = photo_qa.get("checked_at")
            if status != "planned" and not valid_timestamp(photo_checked_at):
                report.error("TIMESTAMP", f"{where}.photographic_qa.checked_at is required after generation or review.")
            if status == "planned" and photo_mode != "pending":
                report.warning("PHOTO_QA", f"Planned asset {asset_id} should use photographic_qa.mode=pending.")
            if status == "approved":
                if photo_mode == "pending" or photo_qa.get("reconstruction_pass") is not True:
                    report.error("PHOTO_QA", f"Approved asset {asset_id} has not passed reconstructable photography QA.")
                if isinstance(checks, dict) and any(checks.get(name) != "pass" for name in PHOTO_QA_CHECKS):
                    report.error("PHOTO_QA", f"Approved asset {asset_id} must pass all photographic QA checks.")
                if photo_qa.get("hard_failures"):
                    report.error("PHOTO_QA", f"Approved asset {asset_id} still has photographic hard failures.")

            expected_mode: str | None = None
            if asset_type in NARRATIVE_ASSET_TYPES or asset_type in {"look_test", "live_action_probe"}:
                expected_mode = "cinematic_frame"
            elif asset_type == "title_card":
                expected_mode = "optical_graphic"
            elif asset_type in {
                "style",
                "character_identity_inspector",
                "character_face_anchor",
                "character_body_anchor",
                "character_identity_view",
                "character_master",
                "character_variant",
                "character_state",
                "location_master",
                "location_variant",
                "prop",
                "prop_state",
                "vehicle",
                "animal",
                "pose_contact_anchor",
            }:
                expected_mode = "reference_photo"
            if status != "planned" and expected_mode and photo_mode != expected_mode:
                report.error(
                    "PHOTO_QA",
                    f"Asset {asset_id} type={asset_type} requires photographic_qa.mode={expected_mode}.",
                )

        if generator == "provided":
            if mode != "provided" or status not in {"qualified", "approved"}:
                report.error("BOUNDARY", f"Provided asset {asset_id} must use mode=provided and status qualified/approved.")
        elif generator == "deterministic-crop":
            if mode != "crop" or asset_type not in {"character_face_anchor", "character_body_anchor", "character_identity_view"}:
                report.error("IDENTITY_CROP", f"Deterministic crop {asset_id} must be a canonical identity-view asset with mode=crop.")
            if asset.get("prompt_path") or asset.get("candidate_set_id") or asset.get("prompt_strategy_id") or asset.get("calibration_family"):
                report.error("IDENTITY_CROP", f"Deterministic crop {asset_id} must not claim an ImageGen prompt, candidate set, strategy, or calibration family.")
        elif mode == "provided":
            report.error("BOUNDARY", f"ImageGen asset {asset_id} cannot use mode=provided.")

        generated = generator == "builtin-imagegen" and status != "planned"
        prompt_path = check_relative_file(
            project_dir,
            asset.get("prompt_path"),
            f"{where}.prompt_path",
            report,
            required=generated,
        )
        if prompt_path and not (
            portable_manifest_path(asset["prompt_path"]).startswith("prompts/images/")
            or is_compiled_prompt_path(asset.get("prompt_path"), "images")
        ):
            report.warning("PATH_CONVENTION", f"Asset prompt should live under prompts/images/: {asset['prompt_path']}")
        prompt_strategy = asset.get("prompt_strategy_id")
        calibration_family = asset.get("calibration_family")
        if generated and asset_type in AUTHENTIC_ASSET_TYPES:
            if prompt_strategy not in IMAGE_PROMPT_STRATEGIES:
                report.error("IMAGE_PROMPT_STRATEGY", f"Asset {asset_id} requires a recognized image2-live-action-evidence-v1.6 prompt_strategy_id.")
            expected_strategy = IMAGE_PROMPT_STRATEGY_BY_TYPE.get(str(asset_type))
            if expected_strategy and prompt_strategy != expected_strategy:
                report.error(
                    "IMAGE_PROMPT_STRATEGY",
                    f"Asset {asset_id} type={asset_type} requires prompt_strategy_id={expected_strategy}.",
                )
            if not isinstance(calibration_family, str) or not calibration_family.strip():
                report.error("CALIBRATION_FAMILY", f"Generated asset {asset_id} requires calibration_family.")
            elif calibration_family != "image2-live-action-evidence-v1.6":
                report.error("CALIBRATION_FAMILY", f"Generated asset {asset_id} must use calibration_family=image2-live-action-evidence-v1.6.")
        if prompt_path and generated and prompt_strategy in IMAGE_PROMPT_STRATEGIES:
            validate_image_prompt_sections(prompt_path, asset_id, str(prompt_strategy), asset, report)
        if asset_type == "look_test" and prompt_path and not (
            portable_manifest_path(asset["prompt_path"]).startswith("prompts/images/look-tests/")
            or is_compiled_prompt_path(asset.get("prompt_path"), "images")
        ):
            report.warning("PATH_CONVENTION", f"Look Test prompt should live under prompts/images/look-tests/: {asset['prompt_path']}")

        candidate_required = status in {"qualified", "rejected"}
        candidate_path = check_relative_file(
            project_dir,
            asset.get("candidate_path"),
            f"{where}.candidate_path",
            report,
            required=candidate_required,
        )
        if candidate_path and not portable_manifest_path(asset["candidate_path"]).startswith("assets/"):
            report.warning("PATH_CONVENTION", f"Candidate should live under assets/: {asset['candidate_path']}")

        approved_required = status in {"approved", "superseded"}
        approved_path = check_relative_file(
            project_dir,
            asset.get("approved_path"),
            f"{where}.approved_path",
            report,
            required=approved_required,
        )
        if approved_path and not portable_manifest_path(asset["approved_path"]).startswith("assets/"):
            report.warning("PATH_CONVENTION", f"Approved asset should live under assets/: {asset['approved_path']}")
        if status == "approved" and isinstance(asset.get("approved_path"), str) and "candidate" in asset["approved_path"].lower():
            report.warning("PATH_CONVENTION", f"Approved asset path still looks like a candidate: {asset['approved_path']}")

    for role, versions in roles.items():
        approved = [item for item in versions if item.get("status") == "approved"]
        candidates = [item for item in versions if item.get("status") == "qualified"]
        planned = [item for item in versions if item.get("status") == "planned"]
        if len(approved) > 1:
            report.error("DUPLICATE_ROLE", f"Role {role} has multiple approved authorities: {', '.join(x['id'] for x in approved)}")
        if len(candidates) > 1:
            report.error("DUPLICATE_ROLE", f"Role {role} has multiple active candidates: {', '.join(x['id'] for x in candidates)}")
        if len(planned) > 1 or (planned and (approved or candidates)):
            report.error("DUPLICATE_ROLE", f"Role {role} has stale or duplicate planned owners.")
        if approved and candidates and candidates[0].get("replaces_asset_id") != approved[0].get("id"):
            report.error(
                "REPLACEMENT",
                f"Qualified replacement {candidates[0].get('id')} must replace current authority {approved[0].get('id')} for role {role}.",
            )

    for asset_id, asset in assets.items():
        derived_from = asset.get("derived_from")
        reference_ids = asset.get("reference_asset_ids") if isinstance(asset.get("reference_asset_ids"), list) else []
        root_reference_ids = asset.get("root_reference_ids") if isinstance(asset.get("root_reference_ids"), list) else []
        replaces = asset.get("replaces_asset_id")
        if derived_from:
            parent = assets.get(derived_from)
            if parent is None:
                report.error("MISSING_REFERENCE", f"Asset {asset_id} derives from missing asset {derived_from}.")
            elif not asset_dependency_is_usable(asset, parent):
                report.error("UNAPPROVED_REFERENCE", f"Asset {asset_id} derives from an asset outside its approved or same-gate qualified dependency scope: {derived_from}.")
            elif parent.get("type") in AUTHENTIC_ASSET_TYPES and (
                not photographic_qa_passed(parent)
                or not authenticity_passed(parent, require_user_approval=True)
                or not texture_qa_passed(parent, require_user_approval=True)
                or not geometry_qa_passed(parent, require_user_approval=True)
                or not live_action_surface_passed(parent, require_user_approval=True)
            ):
                report.error("AUTHENTICITY_GATE", f"Asset {asset_id} derives from asset {derived_from} that has not passed all v1.6 QA gates.")
        if asset.get("type") in {"character_variant", "location_variant", "location_plate"} and not derived_from:
            report.error("MISSING_REFERENCE", f"Variant asset {asset_id} requires derived_from.")
        if derived_from and derived_from in assets:
            parent_type = assets[derived_from].get("type")
            if asset.get("type") == "character_variant" and parent_type not in {"character_master", "character_variant"}:
                report.error("REFERENCE_TYPE", f"Character variant {asset_id} derives from incompatible type {parent_type}.")
            if asset.get("type") == "location_variant" and parent_type not in {"location_master", "location_variant"}:
                report.error("REFERENCE_TYPE", f"Location variant {asset_id} derives from incompatible type {parent_type}.")
            if asset.get("type") == "location_plate" and parent_type not in {"location_master", "location_variant"}:
                report.error("REFERENCE_TYPE", f"Location plate {asset_id} derives from incompatible type {parent_type}.")
        state_asset = asset.get("type") in {"character_state", "location_variant", "prop_state"}
        if state_asset and not root_reference_ids:
            report.error("ROOT_REFERENCE", f"State asset {asset_id} requires direct root_reference_ids.")
        if asset.get("type") == "character_state" and derived_from:
            report.error("RECURSIVE_STATE", f"Character state {asset_id} must not derive from another image; regenerate from identity roots.")
        if asset.get("type") in {"character_face_anchor", "character_body_anchor", "character_identity_view"}:
            parent = assets.get(derived_from) if isinstance(derived_from, str) else None
            if asset.get("generator") != "deterministic-crop" or not parent or parent.get("type") != "character_identity_inspector":
                report.error("IDENTITY_CROP", f"Identity view {asset_id} must be a deterministic crop derived directly from one unified inspector.")
            if reference_ids != [derived_from] or root_reference_ids != [derived_from]:
                report.error("IDENTITY_CROP", f"Identity view {asset_id} must reference only its unified inspector authority.")
        if asset.get("type") == "prop_state" and derived_from:
            report.error("RECURSIVE_STATE", f"Prop state {asset_id} must not derive from another state; regenerate from the clean prop root.")
        if asset.get("type") == "location_variant" and derived_from and assets.get(derived_from, {}).get("type") != "location_master":
            report.error("RECURSIVE_STATE", f"Location state view {asset_id} must derive directly from a clean location master.")
        if state_asset and not asset.get("state_delta"):
            report.error("STATE_DELTA", f"State asset {asset_id} requires an explicit non-empty state_delta.")
        if asset.get("type") in {
            "character_identity_inspector", "character_face_anchor", "character_body_anchor", "character_identity_view", "character_master",
            "location_master", "prop", "vehicle", "animal"
        } and asset.get("status") not in {"planned", "model_blocked"} and asset.get("surface_policy") != "clean_authority":
            report.error("SURFACE_POLICY", f"Authority asset {asset_id} must use surface_policy=clean_authority.")
        if asset.get("type") in PROFILED_ASSET_TYPES and asset.get("status") not in {"planned", "model_blocked"}:
            if asset.get("surface_policy") not in {"clean_narrative", "calibrated_medium_signature"}:
                report.error(
                    "SURFACE_POLICY",
                    f"Narrative asset {asset_id} must use clean_narrative or calibrated_medium_signature.",
                )
        medium_id = asset.get("medium_signature_id")
        if asset.get("surface_policy") == "calibrated_medium_signature" and not medium_id:
            report.error("MEDIUM_SIGNATURE", f"Asset {asset_id} requires medium_signature_id.")
        if asset.get("surface_policy") != "calibrated_medium_signature" and medium_id:
            report.error("MEDIUM_SIGNATURE", f"Asset {asset_id} may set medium_signature_id only for calibrated_medium_signature.")
        if asset.get("surface_policy") == "clean_authority" and asset.get("localized_story_evidence"):
            report.error("SURFACE_POLICY", f"Clean authority asset {asset_id} cannot carry localized story evidence.")
        pose_anchor_ids = asset.get("pose_contact_anchor_ids") if isinstance(asset.get("pose_contact_anchor_ids"), list) else []
        for pose_anchor_id in pose_anchor_ids:
            target = assets.get(pose_anchor_id)
            if target is None or target.get("type") != "pose_contact_anchor":
                report.error("POSE_CONTACT_ANCHOR", f"Asset {asset_id} references invalid pose/contact anchor {pose_anchor_id}.")
            elif not asset_dependency_is_usable(asset, target):
                report.error("UNAPPROVED_REFERENCE", f"Asset {asset_id} references an unusable pose/contact anchor {pose_anchor_id}.")
            if pose_anchor_id not in reference_ids:
                report.error("POSE_CONTACT_ANCHOR", f"Asset {asset_id} pose/contact anchor {pose_anchor_id} must also be a direct reference.")
        if len(reference_ids) != len(set(reference_ids)):
            report.error("DUPLICATE_REFERENCE", f"Asset {asset_id} repeats a reference asset id.")
        for reference_id in reference_ids:
            target = assets.get(reference_id)
            if reference_id == asset_id:
                report.error("REFERENCE_CYCLE", f"Asset {asset_id} references itself.")
            elif target is None:
                report.error("MISSING_REFERENCE", f"Asset {asset_id} references missing asset {reference_id}.")
            elif not asset_dependency_is_usable(asset, target):
                report.error("UNAPPROVED_REFERENCE", f"Asset {asset_id} references an asset outside its approved or same-gate qualified scope: {reference_id}.")
            elif target.get("type") in AUTHENTIC_ASSET_TYPES and (
                not photographic_qa_passed(target)
                or not authenticity_passed(target, require_user_approval=True)
                or not texture_qa_passed(target, require_user_approval=True)
                or not geometry_qa_passed(target, require_user_approval=True)
                or not live_action_surface_passed(target, require_user_approval=True)
            ):
                report.error("AUTHENTICITY_GATE", f"Asset {asset_id} references asset {reference_id} that has not passed all v1.6 QA gates.")
        provenance = asset.get("generation_provenance") if isinstance(asset.get("generation_provenance"), dict) else {}
        provenance_inputs = provenance.get("reference_inputs") if isinstance(provenance.get("reference_inputs"), list) else []
        for item in provenance_inputs:
            if not isinstance(item, dict):
                continue
            target = assets.get(item.get("asset_id"))
            if target and item.get("relative_path") != target.get("approved_path"):
                report.error(
                    "PROVENANCE_PATH",
                    f"Asset {asset_id} reference {item.get('asset_id')} must record its approved authority path.",
                )
        if len(root_reference_ids) != len(set(root_reference_ids)):
            report.error("DUPLICATE_REFERENCE", f"Asset {asset_id} repeats a root reference asset id.")
        for root_id in root_reference_ids:
            target = assets.get(root_id)
            if target is None:
                report.error("MISSING_REFERENCE", f"Asset {asset_id} names missing root reference {root_id}.")
                continue
            if root_id not in reference_ids:
                report.error("ROOT_REFERENCE", f"Asset {asset_id} root reference {root_id} must also appear in reference_asset_ids.")
            if not asset_dependency_is_usable(asset, target):
                report.error("UNAPPROVED_REFERENCE", f"Asset {asset_id} uses a root outside its approved or same-gate qualified scope: {root_id}.")
            if target.get("type") in {"character_state", "character_variant", "location_variant", "location_plate", "prop_state", "look_test", "storyboard", "keyframe", "pose_contact_anchor"}:
                report.error("RECURSIVE_STATE", f"Asset {asset_id} uses non-root state/candidate asset {root_id} as a root reference.")
            if target.get("type") in AUTHENTIC_ASSET_TYPES and not texture_qa_passed(target, require_user_approval=True):
                report.error("TEXTURE_GATE", f"Asset {asset_id} root reference {root_id} has not passed texture QA.")
            if target.get("type") in AUTHENTIC_ASSET_TYPES and not live_action_surface_passed(target, require_user_approval=True):
                report.error("LIVE_ACTION_SURFACE", f"Asset {asset_id} root reference {root_id} has not passed live-action surface QA.")
            if target.get("type") in AUTHENTIC_ASSET_TYPES and not geometry_qa_passed(target, require_user_approval=True):
                report.error("GEOMETRY_GATE", f"Asset {asset_id} root reference {root_id} has not passed geometry QA.")
        if replaces:
            target = assets.get(replaces)
            if target is None:
                report.error("MISSING_REFERENCE", f"Asset {asset_id} replaces missing asset {replaces}.")
            elif target.get("role") != asset.get("role"):
                report.error("REPLACEMENT", f"Asset {asset_id} and replacement target {replaces} must share the same role.")
            elif asset.get("status") == "qualified" and target.get("status") != "approved":
                report.error("REPLACEMENT", f"Qualified asset {asset_id} must replace an approved asset.")
            elif asset.get("status") == "approved" and target.get("status") != "superseded":
                report.error("REPLACEMENT", f"Approved replacement {asset_id} requires target {replaces} to be superseded.")

    for asset_id in assets:
        seen: set[str] = set()
        current = asset_id
        while current in assets:
            parent = assets[current].get("derived_from")
            if not parent:
                break
            if parent in seen or parent == asset_id:
                report.error("REFERENCE_CYCLE", f"derived_from cycle detected at asset {asset_id}.")
                break
            seen.add(parent)
            current = parent

    return assets


def _validate_position(value: Any, where: str, report: Report) -> bool:
    if not require_keys(value, ("x", "y", "z"), where, report):
        return False
    valid = True
    for axis in ("x", "y", "z"):
        coordinate = value.get(axis)
        if not is_number(coordinate):
            report.error("SPATIAL_POSITION", f"{where}.{axis} must be numeric metres.")
            valid = False
        elif abs(float(coordinate) * 10 - round(float(coordinate) * 10)) > 1e-6:
            report.error("SPATIAL_PRECISION", f"{where}.{axis} must use approximately 0.1 m precision, not false centimetre precision.")
            valid = False
    return valid


def _asset_dependency_ids(asset_id: str, assets: dict[str, dict[str, Any]]) -> list[str]:
    """Return deterministic transitive source anchors without repeating the root."""
    ordered: list[str] = []
    seen = {asset_id}

    def visit(current_id: str) -> None:
        current = assets.get(current_id)
        if not current:
            return
        candidates: list[str] = []
        derived_from = current.get("derived_from")
        if isinstance(derived_from, str) and derived_from:
            candidates.append(derived_from)
        references = current.get("reference_asset_ids")
        if isinstance(references, list):
            candidates.extend(item for item in references if isinstance(item, str) and item)
        roots = current.get("root_reference_ids")
        if isinstance(roots, list):
            candidates.extend(item for item in roots if isinstance(item, str) and item)
        for candidate_id in candidates:
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            ordered.append(candidate_id)
            visit(candidate_id)

    visit(asset_id)
    return ordered


def _asset_dependency_contains(
    asset_id: str, target_id: str, assets: dict[str, dict[str, Any]]
) -> bool:
    return asset_id == target_id or target_id in _asset_dependency_ids(asset_id, assets)


def _validate_scene_state_view(
    asset_id: Any,
    *,
    expected_role: str,
    expected_side: str | None,
    map_id: str,
    scene_id: str,
    scene_state_id: str,
    location_master_id: str,
    anchor_id: str,
    assets: dict[str, dict[str, Any]],
    where: str,
    report: Report,
) -> dict[str, Any] | None:
    if not isinstance(asset_id, str) or not asset_id:
        report.error("SCENE_STATE_VIEW", f"{where} requires an asset id.")
        return None
    asset = assets.get(asset_id)
    if asset is None:
        report.error("MISSING_REFERENCE", f"{where} references missing scene-state view {asset_id}.")
        return None
    validate_approved_asset_reference(asset_id, where, assets, report, {"location_variant"})
    if asset.get("generator") != "builtin-imagegen" or asset.get("mode") != "edit" or asset.get("derived_from") != location_master_id:
        report.error(
            "SCENE_STATE_VIEW",
            f"Scene-state view {asset_id} must be an independent built-in ImageGen edit derived directly from location master {location_master_id}.",
        )
    if asset.get("scene_ids") != [scene_id]:
        report.error("SCENE_STATE_VIEW", f"Scene-state view {asset_id} must belong only to scene {scene_id}.")
    if asset.get("scene_state_id") != scene_state_id:
        report.error("SCENE_STATE_VIEW", f"Scene-state view {asset_id} must use scene_state_id={scene_state_id}.")
    if asset.get("spatial_map_id") != map_id:
        report.error("SCENE_STATE_VIEW", f"Scene-state view {asset_id} must use spatial_map_id={map_id}.")
    if asset.get("primary_anchor_asset_id") != anchor_id:
        report.error("SPATIAL_ANCHOR", f"Scene-state view {asset_id} must bind primary anchor {anchor_id}.")
    reference_ids = asset.get("reference_asset_ids") if isinstance(asset.get("reference_asset_ids"), list) else []
    if anchor_id not in reference_ids:
        report.error("SPATIAL_ANCHOR", f"Scene-state view {asset_id} must directly reference primary anchor {anchor_id}.")
    if asset.get("view_role") != expected_role:
        report.error("SCENE_STATE_VIEW", f"Scene-state view {asset_id} must use view_role={expected_role}.")
    if expected_side is not None and asset.get("view_side") != expected_side:
        report.error("SCENE_STATE_VIEW", f"Scene-state view {asset_id} must use view_side={expected_side}.")
    coverage = asset.get("reference_coverage") if isinstance(asset.get("reference_coverage"), dict) else {}
    present_views = coverage.get("present_views") if isinstance(coverage.get("present_views"), list) else []
    if coverage.get("policy") != "single_view" or present_views != [expected_role]:
        report.error(
            "SCENE_STATE_VIEW",
            f"Scene-state view {asset_id} must declare exactly one single_view coverage role: {expected_role}.",
        )
    approved_path = asset.get("approved_path")
    if isinstance(approved_path, str) and not approved_path.startswith("assets/locations/state-views/"):
        report.error("PATH_CONVENTION", f"Scene-state view {asset_id} must live under assets/locations/state-views/.")
    return asset


def validate_spatial(
    data: dict[str, Any] | None,
    scenes: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    rows = validate_manifest_header(data, "spatial_maps", "manifests/spatial.json", report)
    spatial_maps: dict[str, dict[str, Any]] = {}
    scene_to_map: dict[str, str] = {}
    state_ids: set[str] = set()
    required = (
        "id",
        "status",
        "scene_id",
        "scene_state_id",
        "location_master_asset_id",
        "establishing_view_asset_id",
        "side_three_quarter_view_asset_id",
        "additional_view_asset_ids",
        "primary_anchor",
        "coordinate_system",
        "landmarks",
        "marks",
        "movement_paths",
        "secondary_landmark_ids",
        "approval_gate_id",
        "spatial_qa",
    )
    for index, spatial_map in enumerate(rows):
        where = f"manifests/spatial.json.spatial_maps[{index}]"
        if not require_keys(spatial_map, required, where, report):
            continue
        map_id = spatial_map.get("id")
        scene_id = spatial_map.get("scene_id")
        state_id = spatial_map.get("scene_state_id")
        if not require_string(map_id, f"{where}.id", report):
            continue
        if not ID_RE.fullmatch(map_id):
            report.error("INVALID_ID", f"Invalid spatial map id: {map_id}")
        if map_id in spatial_maps:
            report.error("DUPLICATE_ID", f"Duplicate spatial map id: {map_id}")
        else:
            spatial_maps[map_id] = spatial_map
        if not require_string(scene_id, f"{where}.scene_id", report) or scene_id not in scenes:
            report.error("ORPHAN_SCENE", f"Spatial map {map_id} references missing scene {scene_id}.")
            continue
        if scene_id in scene_to_map:
            report.error("SPATIAL_MAP", f"Scene {scene_id} has more than one spatial map.")
        else:
            scene_to_map[scene_id] = map_id
        if not require_string(state_id, f"{where}.scene_state_id", report):
            continue
        if state_id in state_ids:
            report.error("DUPLICATE_ID", f"Duplicate scene_state_id: {state_id}")
        state_ids.add(state_id)
        status = spatial_map.get("status")
        if status not in SPATIAL_MAP_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(spatial_map.get("approval_gate_id"), f"{where}.approval_gate_id", report)

        scene = scenes[scene_id]
        if scene.get("spatial_map_id") != map_id or scene.get("scene_state_id") != state_id:
            report.error("SPATIAL_MAP", f"Scene {scene_id} must point back to spatial map {map_id} and state {state_id}.")

        location_master_id = spatial_map.get("location_master_asset_id")
        validate_approved_asset_reference(
            location_master_id, f"Spatial map {map_id} location master", assets, report, {"location_master"}
        )
        anchor = spatial_map.get("primary_anchor")
        anchor_id = ""
        if require_keys(
            anchor,
            ("asset_id", "selection_source", "selection_rationale", "stability", "dimensions_m", "orientation"),
            f"{where}.primary_anchor",
            report,
        ):
            anchor_id = anchor.get("asset_id") if isinstance(anchor.get("asset_id"), str) else ""
            require_string(anchor_id, f"{where}.primary_anchor.asset_id", report)
            if anchor.get("selection_source") not in ANCHOR_SELECTION_SOURCES:
                report.error("ENUM", f"{where}.primary_anchor.selection_source is invalid: {anchor.get('selection_source')}")
            if anchor.get("stability") not in ANCHOR_STABILITIES:
                report.error("ENUM", f"{where}.primary_anchor.stability is invalid: {anchor.get('stability')}")
            require_string(anchor.get("selection_rationale"), f"{where}.primary_anchor.selection_rationale", report)
            require_string(anchor.get("orientation"), f"{where}.primary_anchor.orientation", report)
            dimensions = anchor.get("dimensions_m")
            if require_keys(dimensions, ("width", "depth", "height"), f"{where}.primary_anchor.dimensions_m", report):
                for dimension in ("width", "depth", "height"):
                    value = dimensions.get(dimension)
                    if not is_number(value) or value <= 0:
                        report.error("SPATIAL_ANCHOR", f"{where}.primary_anchor.dimensions_m.{dimension} must be positive.")
                    elif abs(float(value) * 10 - round(float(value) * 10)) > 1e-6:
                        report.error(
                            "SPATIAL_PRECISION",
                            f"{where}.primary_anchor.dimensions_m.{dimension} must use approximately 0.1 m precision.",
                        )
            validate_approved_asset_reference(anchor_id, f"Spatial map {map_id} primary anchor", assets, report, {"prop"})
            anchor_asset = assets.get(anchor_id, {})
            coverage = anchor_asset.get("reference_coverage") if isinstance(anchor_asset.get("reference_coverage"), dict) else {}
            present = set(coverage.get("present_views", [])) if isinstance(coverage.get("present_views"), list) else set()
            if coverage.get("policy") != "object_multiview" or not OBJECT_ANCHOR_VIEWS.issubset(present):
                report.error(
                    "SPATIAL_ANCHOR",
                    f"Primary anchor {anchor_id} requires object_multiview coverage with front, side and three_quarter views.",
                )
            if scene.get("primary_anchor_asset_id") != anchor_id:
                report.error("SPATIAL_ANCHOR", f"Scene {scene_id} must bind exactly primary anchor {anchor_id}.")

        coordinate = spatial_map.get("coordinate_system")
        coordinate_fields = (
            "origin",
            "units",
            "precision_m",
            "x_positive_label",
            "y_positive_label",
            "z_positive_label",
        )
        if require_keys(coordinate, coordinate_fields, f"{where}.coordinate_system", report):
            if coordinate.get("origin") != "primary_anchor_ground_contact_center":
                report.error("SPATIAL_COORDINATES", f"{where}.coordinate_system.origin must be primary_anchor_ground_contact_center.")
            if coordinate.get("units") != "metres":
                report.error("SPATIAL_COORDINATES", f"{where}.coordinate_system.units must be metres.")
            if not is_number(coordinate.get("precision_m")) or abs(float(coordinate.get("precision_m", 0)) - 0.1) > 1e-6:
                report.error("SPATIAL_PRECISION", f"{where}.coordinate_system.precision_m must be 0.1.")
            require_nonempty_string_fields(
                coordinate,
                ("x_positive_label", "y_positive_label", "z_positive_label"),
                f"{where}.coordinate_system",
                report,
            )

        establishing_id = spatial_map.get("establishing_view_asset_id")
        three_quarter_id = spatial_map.get("side_three_quarter_view_asset_id")
        establishing = _validate_scene_state_view(
            establishing_id,
            expected_role="establishing_wide",
            expected_side="not_applicable",
            map_id=map_id,
            scene_id=scene_id,
            scene_state_id=state_id,
            location_master_id=str(location_master_id),
            anchor_id=anchor_id,
            assets=assets,
            where=f"Spatial map {map_id} establishing view",
            report=report,
        )
        three_quarter = _validate_scene_state_view(
            three_quarter_id,
            expected_role="side_three_quarter_wide",
            expected_side=(assets.get(three_quarter_id, {}).get("view_side") if isinstance(three_quarter_id, str) else ""),
            map_id=map_id,
            scene_id=scene_id,
            scene_state_id=state_id,
            location_master_id=str(location_master_id),
            anchor_id=anchor_id,
            assets=assets,
            where=f"Spatial map {map_id} side-three-quarter view",
            report=report,
        )
        if isinstance(three_quarter, dict) and three_quarter.get("view_side") not in {"left", "right"}:
            report.error("THREE_QUARTER_VIEW", f"Scene-state view {three_quarter_id} must declare left or right side.")

        additional_ids = spatial_map.get("additional_view_asset_ids")
        require_string_list(additional_ids, f"{where}.additional_view_asset_ids", report)
        if not isinstance(additional_ids, list):
            additional_ids = []
        if len(additional_ids) != len(set(additional_ids)):
            report.error("DUPLICATE_REFERENCE", f"Spatial map {map_id} repeats an additional view asset.")
        all_view_assets = [asset for asset in (establishing, three_quarter) if isinstance(asset, dict)]
        for additional_id in additional_ids:
            additional = assets.get(additional_id)
            role = additional.get("view_role") if isinstance(additional, dict) else ""
            if role not in LOCATION_MULTIVIEW_VIEWS:
                report.error("SCENE_STATE_VIEW", f"Additional view {additional_id} must use a full multi-axis coverage role.")
                continue
            side = "left" if role == "left_three_quarter_wide" else "right" if role == "right_three_quarter_wide" else "not_applicable"
            checked = _validate_scene_state_view(
                additional_id,
                expected_role=str(role),
                expected_side=side,
                map_id=map_id,
                scene_id=scene_id,
                scene_state_id=state_id,
                location_master_id=str(location_master_id),
                anchor_id=anchor_id,
                assets=assets,
                where=f"Spatial map {map_id} additional view",
                report=report,
            )
            if checked:
                all_view_assets.append(checked)
        view_ids = [str(asset.get("id")) for asset in all_view_assets]
        prompt_paths = [str(asset.get("prompt_path")) for asset in all_view_assets]
        approved_paths = [str(asset.get("approved_path")) for asset in all_view_assets]
        if len(view_ids) != len(set(view_ids)) or len(prompt_paths) != len(set(prompt_paths)) or len(approved_paths) != len(set(approved_paths)):
            report.error("SCENE_STATE_VIEW", f"Spatial map {map_id} requires independent view assets, prompt files and output files.")

        qa = spatial_map.get("spatial_qa")
        qa_fields = (
            "attempt_index",
            "escalation",
            "three_quarter_yaw_deg",
            "adjacent_planes_visible",
            "geography_consistency_pass",
            "anchor_presence_pass",
            "anchor_position_pass",
            "anchor_scale_pass",
            "anchor_orientation_pass",
            "camera_access_pass",
            "hard_failures",
            "notes",
            "checked_at",
        )
        if require_keys(qa, qa_fields, f"{where}.spatial_qa", report):
            attempt = qa.get("attempt_index")
            escalation = qa.get("escalation")
            if not is_integer(attempt) or not 1 <= attempt <= 2:
                report.error("SPATIAL_QA", f"Spatial map {map_id} attempt_index must be 1 or 2.")
            if escalation not in SPATIAL_ESCALATIONS:
                report.error("ENUM", f"{where}.spatial_qa.escalation is invalid: {escalation}")
            yaw = qa.get("three_quarter_yaw_deg")
            if not is_number(yaw) or not 30 <= abs(float(yaw)) <= 60:
                report.error("THREE_QUARTER_VIEW", f"Spatial map {map_id} requires a reviewed 30–60 degree side-three-quarter yaw.")
            for field in (
                "adjacent_planes_visible",
                "geography_consistency_pass",
                "anchor_presence_pass",
                "anchor_position_pass",
                "anchor_scale_pass",
                "anchor_orientation_pass",
                "camera_access_pass",
            ):
                if not isinstance(qa.get(field), bool):
                    report.error("TYPE", f"{where}.spatial_qa.{field} must be boolean.")
                elif status == "approved" and qa.get(field) is not True:
                    report.error("SPATIAL_QA", f"Approved spatial map {map_id} requires {field}=true.")
            require_string_list(qa.get("hard_failures"), f"{where}.spatial_qa.hard_failures", report)
            require_string_list(qa.get("notes"), f"{where}.spatial_qa.notes", report)
            if status == "approved" and qa.get("hard_failures"):
                report.error("SPATIAL_QA", f"Approved spatial map {map_id} still has hard failures.")
            if status == "approved" and escalation != "none":
                report.error("SPATIAL_QA", f"Approved spatial map {map_id} must use escalation=none.")
            failed_checks = [
                field
                for field in (
                    "adjacent_planes_visible",
                    "geography_consistency_pass",
                    "anchor_presence_pass",
                    "anchor_position_pass",
                    "anchor_scale_pass",
                    "anchor_orientation_pass",
                    "camera_access_pass",
                )
                if qa.get(field) is False
            ]
            if status == "real_reference_required":
                if attempt != 2 or escalation != "real_reference_required" or (not failed_checks and not qa.get("hard_failures")):
                    report.error(
                        "SPATIAL_ESCALATION",
                        f"Spatial map {map_id} real-reference escalation requires failed attempt 2 and escalation=real_reference_required.",
                    )
            elif attempt == 2 and (failed_checks or qa.get("hard_failures")) and escalation != "real_reference_required":
                report.error(
                    "SPATIAL_ESCALATION",
                    f"Spatial map {map_id} failed twice and must request a rights-cleared location reference or floor plan.",
                )
            if status == "approved" and not valid_timestamp(qa.get("checked_at")):
                report.error("TIMESTAMP", f"Approved spatial map {map_id} requires a spatial QA timestamp.")

        landmark_ids: set[str] = set()
        landmarks = spatial_map.get("landmarks")
        if not isinstance(landmarks, list):
            report.error("TYPE", f"{where}.landmarks must be an array.")
            landmarks = []
        for landmark_index, landmark in enumerate(landmarks):
            landmark_where = f"{where}.landmarks[{landmark_index}]"
            if not require_keys(landmark, ("id", "label", "position_m", "relation_to_anchor"), landmark_where, report):
                continue
            landmark_id = landmark.get("id")
            if not require_string(landmark_id, f"{landmark_where}.id", report):
                continue
            if landmark_id in landmark_ids:
                report.error("DUPLICATE_ID", f"Duplicate spatial landmark id: {landmark_id}")
            landmark_ids.add(landmark_id)
            require_string(landmark.get("label"), f"{landmark_where}.label", report)
            require_string(landmark.get("relation_to_anchor"), f"{landmark_where}.relation_to_anchor", report)
            _validate_position(landmark.get("position_m"), f"{landmark_where}.position_m", report)

        mark_ids: set[str] = set()
        marks = spatial_map.get("marks")
        if not isinstance(marks, list):
            report.error("TYPE", f"{where}.marks must be an array.")
            marks = []
        for mark_index, mark in enumerate(marks):
            mark_where = f"{where}.marks[{mark_index}]"
            if not require_keys(mark, ("id", "kind", "asset_id", "position_m", "facing", "relation_to_anchor"), mark_where, report):
                continue
            mark_id = mark.get("id")
            if not require_string(mark_id, f"{mark_where}.id", report):
                continue
            if mark_id in mark_ids:
                report.error("DUPLICATE_ID", f"Duplicate spatial mark id: {mark_id}")
            mark_ids.add(mark_id)
            if mark.get("kind") not in SPATIAL_MARK_KINDS:
                report.error("ENUM", f"{mark_where}.kind is invalid: {mark.get('kind')}")
            require_string(mark.get("asset_id"), f"{mark_where}.asset_id", report, allow_empty=True)
            if mark.get("asset_id") and mark.get("asset_id") not in assets:
                report.error("MISSING_REFERENCE", f"Spatial mark {mark_id} references missing asset {mark.get('asset_id')}.")
            require_string(mark.get("facing"), f"{mark_where}.facing", report)
            require_string(mark.get("relation_to_anchor"), f"{mark_where}.relation_to_anchor", report)
            _validate_position(mark.get("position_m"), f"{mark_where}.position_m", report)

        movement_ids: set[str] = set()
        movement_paths = spatial_map.get("movement_paths")
        if not isinstance(movement_paths, list):
            report.error("TYPE", f"{where}.movement_paths must be an array.")
            movement_paths = []
        for path_index, movement in enumerate(movement_paths):
            movement_where = f"{where}.movement_paths[{path_index}]"
            if not require_keys(
                movement,
                ("id", "subject_asset_id", "start_mark_id", "end_mark_id", "path_description"),
                movement_where,
                report,
            ):
                continue
            movement_id = movement.get("id")
            if not require_string(movement_id, f"{movement_where}.id", report):
                continue
            if movement_id in movement_ids:
                report.error("DUPLICATE_ID", f"Duplicate spatial movement path id: {movement_id}")
            movement_ids.add(movement_id)
            subject_id = movement.get("subject_asset_id")
            if not require_string(subject_id, f"{movement_where}.subject_asset_id", report) or subject_id not in assets:
                report.error("MISSING_REFERENCE", f"Movement path {movement_id} references missing subject {subject_id}.")
            for field in ("start_mark_id", "end_mark_id"):
                value = movement.get(field)
                if not require_string(value, f"{movement_where}.{field}", report) or value not in mark_ids:
                    report.error("SPATIAL_POSITION", f"Movement path {movement_id} references missing mark {value}.")
            require_string(movement.get("path_description"), f"{movement_where}.path_description", report)

        secondary_ids = spatial_map.get("secondary_landmark_ids")
        require_string_list(secondary_ids, f"{where}.secondary_landmark_ids", report)
        if isinstance(secondary_ids, list):
            if len(secondary_ids) != len(set(secondary_ids)):
                report.error("DUPLICATE_REFERENCE", f"Spatial map {map_id} repeats a secondary landmark.")
            for landmark_id in secondary_ids:
                if landmark_id not in landmark_ids:
                    report.error("MISSING_REFERENCE", f"Spatial map {map_id} references missing landmark {landmark_id}.")

    for scene_id, scene in scenes.items():
        expected_map_id = scene.get("spatial_map_id")
        spatial_map = spatial_maps.get(expected_map_id) if isinstance(expected_map_id, str) else None
        if spatial_map is None:
            report.error("SPATIAL_MAP", f"Scene {scene_id} requires exactly one spatial map {expected_map_id}.")
        elif spatial_map.get("scene_id") != scene_id:
            report.error("SPATIAL_MAP", f"Scene {scene_id} points to a spatial map owned by another scene.")
    return spatial_maps


def require_nonempty_string_fields(value: dict[str, Any], fields: tuple[str, ...], where: str, report: Report) -> None:
    for field in fields:
        require_string(value.get(field), f"{where}.{field}", report)


def _normalized_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def profile_strategy_dimensions(profile: dict[str, Any]) -> tuple[str, ...]:
    optics = profile.get("optics") if isinstance(profile.get("optics"), dict) else {}
    motion = profile.get("motion") if isinstance(profile.get("motion"), dict) else {}
    return (
        str(profile.get("cinematic_treatment_id", "")),
        str(profile.get("format_plan_id", "")),
        _normalized_json(profile.get("capture_circumstance")),
        _normalized_json(
            {
                key: optics.get(key)
                for key in (
                    "projection",
                    "focal_strategy",
                    "contrast",
                    "focus_falloff",
                    "distortion",
                    "breathing",
                    "bokeh",
                )
            }
        ),
        _normalized_json({"support": motion.get("support"), "inertia": motion.get("inertia")}),
        _normalized_json(profile.get("exposure")),
        _normalized_json(profile.get("lighting")),
        str(profile.get("medium_signature_id", "")),
    )


def validate_cinematography(
    project_dir: Path,
    data: dict[str, Any] | None,
    scenes: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    spatial_maps: dict[str, dict[str, Any]],
    report: Report,
) -> tuple[
    dict[str, dict[str, Any]],
    str,
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    profiles: dict[str, dict[str, Any]] = {}
    comparison_sets: dict[str, dict[str, Any]] = {}
    treatments: dict[str, dict[str, Any]] = {}
    format_plans: dict[str, dict[str, Any]] = {}
    medium_signatures: dict[str, dict[str, Any]] = {}
    if data is None:
        return profiles, "", comparison_sets, treatments, format_plans, medium_signatures
    required_top = (
        "schema_version", "policy", "base_profile_id", "base_treatment_id", "base_format_plan_id",
        "profiles", "cinematic_treatments", "format_plans", "medium_signatures", "comparison_sets",
    )
    if not require_keys(data, required_top, "manifests/cinematography.json", report):
        return profiles, "", comparison_sets, treatments, format_plans, medium_signatures
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/cinematography.json.schema_version must be {SCHEMA_VERSION}.")
    if data.get("policy") != "adaptive-live-action-v1.6":
        report.error("BOUNDARY", "manifests/cinematography.json.policy must be adaptive-live-action-v1.6.")
    base_profile_id = data.get("base_profile_id")
    base_treatment_id = data.get("base_treatment_id")
    base_format_plan_id = data.get("base_format_plan_id")
    require_string(base_profile_id, "manifests/cinematography.json.base_profile_id", report, allow_empty=True)
    require_string(base_treatment_id, "manifests/cinematography.json.base_treatment_id", report, allow_empty=True)
    require_string(base_format_plan_id, "manifests/cinematography.json.base_format_plan_id", report, allow_empty=True)
    profile_rows = data.get("profiles")
    treatment_rows = data.get("cinematic_treatments")
    format_rows = data.get("format_plans")
    medium_rows = data.get("medium_signatures")
    comparison_rows = data.get("comparison_sets")
    if not isinstance(profile_rows, list):
        report.error("TYPE", "manifests/cinematography.json.profiles must be an array.")
        profile_rows = []
    if not isinstance(comparison_rows, list):
        report.error("TYPE", "manifests/cinematography.json.comparison_sets must be an array.")
        comparison_rows = []
    if not isinstance(treatment_rows, list):
        report.error("TYPE", "manifests/cinematography.json.cinematic_treatments must be an array.")
        treatment_rows = []
    if not isinstance(format_rows, list):
        report.error("TYPE", "manifests/cinematography.json.format_plans must be an array.")
        format_rows = []
    if not isinstance(medium_rows, list):
        report.error("TYPE", "manifests/cinematography.json.medium_signatures must be an array.")
        medium_rows = []

    treatment_fields = (
        "id", "status", "scope", "scene_ids", "family", "thesis", "narrative_distance",
        "camera_witness", "composition_grammar", "optical_spatial_behavior", "motivated_light",
        "color_pipeline", "camera_mobility", "temporal_cadence", "environmental_medium",
        "polish_ceiling", "named_reference_policy", "observable_reference_translation",
        "return_rule", "approval_gate_id",
    )
    for index, treatment in enumerate(treatment_rows):
        where = f"manifests/cinematography.json.cinematic_treatments[{index}]"
        if not require_keys(treatment, treatment_fields, where, report):
            continue
        treatment_id = treatment.get("id")
        if not require_string(treatment_id, f"{where}.id", report):
            continue
        if treatment_id in treatments:
            report.error("DUPLICATE_ID", f"Duplicate cinematic treatment id: {treatment_id}")
        treatments[treatment_id] = treatment
        status = treatment.get("status")
        if status not in PROFILE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        if treatment.get("scope") not in PROFILE_SCOPES:
            report.error("ENUM", f"{where}.scope is invalid: {treatment.get('scope')}")
        if treatment.get("family") not in CINEMATIC_TREATMENT_FAMILIES:
            report.error("ENUM", f"{where}.family is invalid: {treatment.get('family')}")
        require_string(treatment.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        require_string_list(treatment.get("scene_ids"), f"{where}.scene_ids", report)
        for scene_id in treatment.get("scene_ids", []) if isinstance(treatment.get("scene_ids"), list) else []:
            if scene_id not in scenes:
                report.error("ORPHAN_SCENE", f"Treatment {treatment_id} references missing scene {scene_id}.")
        require_nonempty_string_fields(
            treatment,
            (
                "thesis", "narrative_distance", "camera_witness", "composition_grammar",
                "optical_spatial_behavior", "motivated_light", "color_pipeline", "camera_mobility",
                "temporal_cadence", "environmental_medium", "polish_ceiling", "return_rule",
            ),
            where,
            report,
        )
        if treatment.get("named_reference_policy") != "observable_translation_only":
            report.error("STYLE_REFERENCE_POLICY", f"Treatment {treatment_id} must use observable_translation_only.")
        require_string_list(
            treatment.get("observable_reference_translation"),
            f"{where}.observable_reference_translation",
            report,
        )
        if "user_approved_at" in treatment:
            report.error("APPROVAL_SCOPE", f"Treatment {treatment_id} must receive approval through manifests/reviews.json.")

    format_fields = (
        "id", "status", "scope", "sequence_ids", "narrative_reason", "capture_aperture",
        "working_frame", "delivery_aspect", "crop_extraction", "safe_areas", "squeeze_ratio",
        "desqueeze_delivery", "reframe_policy", "transition_design", "return_rule",
        "baked_black_bars", "approval_gate_id",
    )
    for index, format_plan in enumerate(format_rows):
        where = f"manifests/cinematography.json.format_plans[{index}]"
        if not require_keys(format_plan, format_fields, where, report):
            continue
        format_id = format_plan.get("id")
        if not require_string(format_id, f"{where}.id", report):
            continue
        if format_id in format_plans:
            report.error("DUPLICATE_ID", f"Duplicate format plan id: {format_id}")
        format_plans[format_id] = format_plan
        status = format_plan.get("status")
        if status not in FORMAT_PLAN_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        scope = format_plan.get("scope")
        if scope not in FORMAT_PLAN_SCOPES:
            report.error("ENUM", f"{where}.scope is invalid: {scope}")
        require_string(format_plan.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        require_string_list(format_plan.get("sequence_ids"), f"{where}.sequence_ids", report)
        if scope == "project" and format_plan.get("sequence_ids"):
            report.error("FORMAT_SCOPE", f"Project format plan {format_id} must not list sequence_ids.")
        if scope == "sequence" and not format_plan.get("sequence_ids"):
            report.error("FORMAT_SCOPE", f"Sequence format plan {format_id} requires sequence_ids.")
        for field in ("narrative_reason", "crop_extraction", "desqueeze_delivery", "reframe_policy", "transition_design", "return_rule"):
            require_string(format_plan.get(field), f"{where}.{field}", report)
        for field in ("capture_aperture", "working_frame", "delivery_aspect"):
            value = format_plan.get(field)
            if not require_string(value, f"{where}.{field}", report):
                continue
            if not ASPECT_RE.fullmatch(value):
                report.error("INVALID_ASPECT", f"{where}.{field} must look like 16:9.")
        safe_areas = format_plan.get("safe_areas")
        if require_keys(safe_areas, ("action_percent", "title_percent"), f"{where}.safe_areas", report):
            for field in ("action_percent", "title_percent"):
                value = safe_areas.get(field)
                if not is_number(value) or not 0 < float(value) <= 100:
                    report.error("FORMAT_PLAN", f"{where}.safe_areas.{field} must be in (0, 100].")
        squeeze = format_plan.get("squeeze_ratio")
        if not is_number(squeeze) or float(squeeze) < 1:
            report.error("FORMAT_PLAN", f"{where}.squeeze_ratio must be >= 1.")
        if format_plan.get("baked_black_bars") is not False:
            report.error("FORMAT_PLAN", f"Format plan {format_id} must set baked_black_bars=false.")
        if "user_approved_at" in format_plan:
            report.error("APPROVAL_SCOPE", f"Format plan {format_id} must receive approval through manifests/reviews.json.")

    medium_fields = (
        "id", "status", "asset_families", "story_use", "rationale", "prompt_terms",
        "protected_regions", "calibration_runs", "fallback_policy",
    )
    for index, medium in enumerate(medium_rows):
        where = f"manifests/cinematography.json.medium_signatures[{index}]"
        if not require_keys(medium, medium_fields, where, report):
            continue
        medium_id = medium.get("id")
        if not require_string(medium_id, f"{where}.id", report):
            continue
        if medium_id in medium_signatures:
            report.error("DUPLICATE_ID", f"Duplicate medium signature id: {medium_id}")
        medium_signatures[medium_id] = medium
        status = medium.get("status")
        if status not in MEDIUM_SIGNATURE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        for field in ("asset_families", "prompt_terms", "protected_regions"):
            require_string_list(medium.get(field), f"{where}.{field}", report)
        require_string(medium.get("story_use"), f"{where}.story_use", report)
        require_string(medium.get("rationale"), f"{where}.rationale", report)
        if medium.get("fallback_policy") != "clean_narrative_after_one_artifact_failure":
            report.error("MEDIUM_SIGNATURE", f"Medium signature {medium_id} requires the clean-narrative fallback policy.")
        runs = medium.get("calibration_runs")
        if not isinstance(runs, list):
            report.error("TYPE", f"{where}.calibration_runs must be an array.")
            runs = []
        run_ids: set[str] = set()
        for run_index, run in enumerate(runs):
            run_where = f"{where}.calibration_runs[{run_index}]"
            if not require_keys(run, ("id", "independent_generate", "texture_pass", "live_action_surface_pass", "checked_at"), run_where, report):
                continue
            require_string(run.get("id"), f"{run_where}.id", report)
            if run.get("id") in run_ids:
                report.error("MEDIUM_CALIBRATION", f"Medium signature {medium_id} repeats calibration run {run.get('id')}.")
            run_ids.add(str(run.get("id")))
            for field in ("independent_generate", "texture_pass", "live_action_surface_pass"):
                if not isinstance(run.get(field), bool):
                    report.error("TYPE", f"{run_where}.{field} must be boolean.")
            if not valid_timestamp(run.get("checked_at")):
                report.error("TIMESTAMP", f"{run_where}.checked_at must be a timestamp.")
        if status == "stable":
            if len(runs) != 2 or any(
                run.get("independent_generate") is not True
                or run.get("texture_pass") is not True
                or run.get("live_action_surface_pass") is not True
                for run in runs if isinstance(run, dict)
            ):
                report.error("MEDIUM_CALIBRATION", f"Stable medium signature {medium_id} requires exactly two independent passing runs.")

    profile_required = (
        "id",
        "status",
        "scope",
        "scene_ids",
        "story_rationale",
        "return_to_baseline",
        "cinematic_treatment_id",
        "format_plan_id",
        "medium_signature_id",
        "capture_circumstance",
        "capture",
        "optics",
        "exposure",
        "motion",
        "lighting",
        "pipeline",
        "texture",
        "look_test_asset_ids",
        "approved_look_test_id",
        "approval_gate_id",
    )
    for index, profile in enumerate(profile_rows):
        where = f"manifests/cinematography.json.profiles[{index}]"
        if not require_keys(profile, profile_required, where, report):
            continue
        profile_id = profile.get("id")
        if not require_string(profile_id, f"{where}.id", report):
            continue
        if not ID_RE.fullmatch(profile_id):
            report.error("INVALID_ID", f"Invalid capture Profile id: {profile_id}")
        if profile_id in profiles:
            report.error("DUPLICATE_ID", f"Duplicate capture Profile id: {profile_id}")
        else:
            profiles[profile_id] = profile
        status = profile.get("status")
        scope = profile.get("scope")
        if status not in PROFILE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        if scope not in PROFILE_SCOPES:
            report.error("ENUM", f"{where}.scope is invalid: {scope}")
        require_string(profile.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        require_nonempty_string_fields(profile, ("story_rationale", "return_to_baseline"), where, report)
        treatment_id = profile.get("cinematic_treatment_id")
        format_id = profile.get("format_plan_id")
        medium_id = profile.get("medium_signature_id")
        require_string(treatment_id, f"{where}.cinematic_treatment_id", report)
        require_string(format_id, f"{where}.format_plan_id", report)
        require_string(medium_id, f"{where}.medium_signature_id", report, allow_empty=True)
        treatment = treatments.get(treatment_id) if isinstance(treatment_id, str) else None
        if treatment is None:
            report.error("MISSING_REFERENCE", f"Profile {profile_id} references missing cinematic treatment {treatment_id}.")
        elif treatment.get("status") != status:
            report.error("TREATMENT_REFERENCE", f"Profile {profile_id} and treatment {treatment_id} must share status={status}.")
        format_plan = format_plans.get(format_id) if isinstance(format_id, str) else None
        if format_plan is None:
            report.error("MISSING_REFERENCE", f"Profile {profile_id} references missing format plan {format_id}.")
        elif format_plan.get("status") not in {"approved", "qualified"}:
            report.error("FORMAT_APPROVAL", f"Profile {profile_id} requires an approved format plan or a qualified one in the same foundation gate.")
        elif format_plan.get("status") == "qualified" and format_plan.get("approval_gate_id") != profile.get("approval_gate_id"):
            report.error("REVIEW_GATE", f"Qualified Profile {profile_id} and format plan {format_id} must share a foundation gate.")
        if medium_id:
            medium = medium_signatures.get(medium_id)
            if medium is None:
                report.error("MISSING_REFERENCE", f"Profile {profile_id} references missing medium signature {medium_id}.")
            elif medium.get("status") != "stable":
                report.error("MEDIUM_CALIBRATION", f"Profile {profile_id} may use only a stable medium signature.")
        require_string_list(profile.get("scene_ids"), f"{where}.scene_ids", report)
        profile_scene_ids = profile.get("scene_ids") if isinstance(profile.get("scene_ids"), list) else []
        if len(profile_scene_ids) != len(set(profile_scene_ids)):
            report.error("DUPLICATE_REFERENCE", f"Profile {profile_id} repeats a scene id.")
        for scene_id in profile_scene_ids:
            if scene_id not in scenes:
                report.error("ORPHAN_SCENE", f"Profile {profile_id} references missing scene {scene_id}.")
        if scope == "project" and profile_scene_ids:
            report.error("PROFILE_SCOPE", f"Project Profile {profile_id} must have an empty scene_ids array.")
        if scope == "scene_group" and len(profile_scene_ids) < 2:
            report.error("PROFILE_SCOPE", f"Scene-group Profile {profile_id} must cover at least two scenes.")
        if scope == "scene" and len(profile_scene_ids) != 1:
            report.error("PROFILE_SCOPE", f"Scene Profile {profile_id} must cover exactly one scene.")

        circumstance = profile.get("capture_circumstance")
        circumstance_fields = (
            "observer_role",
            "camera_access",
            "operator_constraint",
            "allowed_contingency",
            "off_frame_context",
        )
        if require_keys(circumstance, circumstance_fields, f"{where}.capture_circumstance", report):
            require_nonempty_string_fields(circumstance, circumstance_fields, f"{where}.capture_circumstance", report)

        capture = profile.get("capture")
        capture_required = ("medium", "format_class", "imaging_width_mm", "camera_reference", "behavior")
        if require_keys(capture, capture_required, f"{where}.capture", report):
            if capture.get("medium") not in CAPTURE_MEDIA:
                report.error("ENUM", f"{where}.capture.medium is invalid: {capture.get('medium')}")
            require_string(capture.get("format_class"), f"{where}.capture.format_class", report)
            width = capture.get("imaging_width_mm")
            if not is_number(width) or width <= 0:
                report.error("CAMERA", f"{where}.capture.imaging_width_mm must be positive.")
            require_string(capture.get("camera_reference"), f"{where}.capture.camera_reference", report, allow_empty=True)
            behavior = capture.get("behavior")
            behavior_fields = (
                "highlight_rolloff",
                "shadow_floor",
                "color_separation",
                "skin_response",
                "acutance",
            )
            if require_keys(behavior, behavior_fields, f"{where}.capture.behavior", report):
                require_nonempty_string_fields(behavior, behavior_fields, f"{where}.capture.behavior", report)

        optics = profile.get("optics")
        optics_required = (
            "projection",
            "lens_reference",
            "focal_strategy",
            "contrast",
            "focus_falloff",
            "flare",
            "distortion",
            "breathing",
            "bokeh",
            "desqueeze_ratio",
            "delivery_crop",
        )
        if require_keys(optics, optics_required, f"{where}.optics", report):
            projection = optics.get("projection")
            if projection not in OPTICAL_PROJECTIONS:
                report.error("ENUM", f"{where}.optics.projection is invalid: {projection}")
            require_string(optics.get("lens_reference"), f"{where}.optics.lens_reference", report, allow_empty=True)
            require_nonempty_string_fields(
                optics,
                ("focal_strategy", "contrast", "focus_falloff", "flare", "distortion", "breathing", "bokeh"),
                f"{where}.optics",
                report,
            )
            squeeze = optics.get("desqueeze_ratio")
            crop = optics.get("delivery_crop")
            if projection == "anamorphic":
                if not is_number(squeeze) or squeeze <= 1:
                    report.error("OPTICS", f"{where}.optics.desqueeze_ratio must be greater than 1 for anamorphic.")
                require_string(crop, f"{where}.optics.delivery_crop", report)
            elif projection == "spherical":
                if squeeze is not None:
                    report.error("OPTICS", f"{where}.optics.desqueeze_ratio must be null for spherical optics.")
                require_string(crop, f"{where}.optics.delivery_crop", report, allow_empty=True)
                if crop not in (None, ""):
                    report.error("OPTICS", f"{where}.optics.delivery_crop must be empty for spherical optics.")

        exposure = profile.get("exposure")
        exposure_fields = ("rating", "bias_stops", "highlight_priority", "shadow_policy")
        if require_keys(exposure, exposure_fields, f"{where}.exposure", report):
            require_nonempty_string_fields(exposure, ("rating", "highlight_priority", "shadow_policy"), f"{where}.exposure", report)
            if not is_number(exposure.get("bias_stops")):
                report.error("TYPE", f"{where}.exposure.bias_stops must be numeric.")

        motion = profile.get("motion")
        motion_fields = ("base_fps", "base_shutter_angle", "support", "inertia")
        if require_keys(motion, motion_fields, f"{where}.motion", report):
            if not is_number(motion.get("base_fps")) or motion.get("base_fps") <= 0:
                report.error("CAMERA", f"{where}.motion.base_fps must be positive.")
            if not is_number(motion.get("base_shutter_angle")) or not 1 <= motion.get("base_shutter_angle") <= 360:
                report.error("CAMERA", f"{where}.motion.base_shutter_angle must be between 1 and 360.")
            require_nonempty_string_fields(motion, ("support", "inertia"), f"{where}.motion", report)

        lighting = profile.get("lighting")
        lighting_fields = ("motivated_sources", "contrast_strategy", "fill_strategy", "practicals", "atmosphere")
        if require_keys(lighting, lighting_fields, f"{where}.lighting", report):
            require_string_list(lighting.get("motivated_sources"), f"{where}.lighting.motivated_sources", report)
            require_string_list(lighting.get("practicals"), f"{where}.lighting.practicals", report)
            require_nonempty_string_fields(
                lighting, ("contrast_strategy", "fill_strategy", "atmosphere"), f"{where}.lighting", report
            )
            if status != "planned" and isinstance(lighting.get("motivated_sources"), list) and not lighting.get("motivated_sources"):
                report.error("LIGHTING", f"Profile {profile_id} requires at least one motivated source after planning.")

        pipeline = profile.get("pipeline")
        pipeline_fields = ("white_balance", "transform_or_stock", "palette_response", "black_level", "highlight_color")
        if require_keys(pipeline, pipeline_fields, f"{where}.pipeline", report):
            require_nonempty_string_fields(pipeline, pipeline_fields, f"{where}.pipeline", report)

        texture = profile.get("texture")
        texture_fields = ("grain_or_noise", "halation", "gate_weave", "artifact_budget")
        if require_keys(texture, texture_fields, f"{where}.texture", report):
            require_nonempty_string_fields(texture, texture_fields, f"{where}.texture", report)

        require_string_list(profile.get("look_test_asset_ids"), f"{where}.look_test_asset_ids", report)
        look_ids = profile.get("look_test_asset_ids") if isinstance(profile.get("look_test_asset_ids"), list) else []
        if len(look_ids) != len(set(look_ids)):
            report.error("DUPLICATE_REFERENCE", f"Profile {profile_id} repeats a Look Test asset id.")
        approved_look_id = profile.get("approved_look_test_id")
        require_string(approved_look_id, f"{where}.approved_look_test_id", report, allow_empty=True)
        for look_id in look_ids:
            asset = assets.get(look_id)
            if asset is None:
                report.error("MISSING_REFERENCE", f"Profile {profile_id} references missing Look Test {look_id}.")
            elif asset.get("type") != "look_test":
                report.error("REFERENCE_TYPE", f"Profile {profile_id} references non-Look-Test asset {look_id}.")
            elif asset.get("capture_profile_id") != profile_id:
                report.error("PROFILE_REFERENCE", f"Look Test {look_id} must point back to Profile {profile_id}.")
        if status == "approved":
            if not look_ids or approved_look_id not in look_ids:
                report.error("PROFILE_APPROVAL", f"Approved Profile {profile_id} requires an approved Look Test in its list.")
            approved_asset = assets.get(approved_look_id) if isinstance(approved_look_id, str) else None
            if approved_asset is not None and approved_asset.get("status") != "approved":
                report.error("PROFILE_APPROVAL", f"Profile {profile_id} approved Look Test {approved_look_id} is not approved.")

    comparison_required = (
        "id",
        "status",
        "diagnostic_scene_id",
        "story_moment",
        "locked_format_plan_id",
        "locked_environmental_state_id",
        "locked_reference_asset_ids",
        "locked_blocking",
        "candidate_profile_ids",
        "candidate_asset_ids",
        "selected_profile_id",
        "selected_asset_id",
        "approval_gate_id",
    )
    for index, comparison in enumerate(comparison_rows):
        where = f"manifests/cinematography.json.comparison_sets[{index}]"
        if not require_keys(comparison, comparison_required, where, report):
            continue
        comparison_id = comparison.get("id")
        if not require_string(comparison_id, f"{where}.id", report):
            continue
        if not ID_RE.fullmatch(comparison_id):
            report.error("INVALID_ID", f"Invalid comparison set id: {comparison_id}")
        if comparison_id in comparison_sets:
            report.error("DUPLICATE_ID", f"Duplicate comparison set id: {comparison_id}")
        else:
            comparison_sets[comparison_id] = comparison
        status = comparison.get("status")
        if status not in COMPARISON_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(comparison.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        scene_id = comparison.get("diagnostic_scene_id")
        if not require_string(scene_id, f"{where}.diagnostic_scene_id", report) or scene_id not in scenes:
            report.error("ORPHAN_SCENE", f"Comparison set {comparison_id} references missing scene {scene_id}.")
        require_nonempty_string_fields(comparison, ("story_moment", "locked_blocking"), where, report)
        locked_format_id = comparison.get("locked_format_plan_id")
        locked_environment_id = comparison.get("locked_environmental_state_id")
        require_string(locked_format_id, f"{where}.locked_format_plan_id", report)
        require_string(locked_environment_id, f"{where}.locked_environmental_state_id", report)
        format_plan = format_plans.get(locked_format_id) if isinstance(locked_format_id, str) else None
        if format_plan is None or format_plan.get("status") != "approved":
            report.error("FORMAT_APPROVAL", f"Comparison set {comparison_id} requires an approved locked format plan.")
        if isinstance(scene_id, str) and scene_id in scenes:
            scene = scenes[scene_id]
            if scene.get("format_plan_id") != locked_format_id:
                report.error("LOOK_CONTROL", f"Comparison set {comparison_id} format plan must match diagnostic scene {scene_id}.")
            if scene.get("environmental_state_id") != locked_environment_id:
                report.error("LOOK_CONTROL", f"Comparison set {comparison_id} environmental state must match diagnostic scene {scene_id}.")
        for field in ("locked_reference_asset_ids", "candidate_profile_ids", "candidate_asset_ids"):
            require_string_list(comparison.get(field), f"{where}.{field}", report)
        locked_ids = comparison.get("locked_reference_asset_ids") if isinstance(comparison.get("locked_reference_asset_ids"), list) else []
        scene_spatial_map = None
        if isinstance(scene_id, str) and scene_id in scenes:
            scene_spatial_map = spatial_maps.get(scenes[scene_id].get("spatial_map_id"))
        if status != "planned":
            if not isinstance(scene_spatial_map, dict) or scene_spatial_map.get("status") != "approved":
                report.error("SPATIAL_GATE", f"Comparison set {comparison_id} requires an approved spatial map for scene {scene_id}.")
            else:
                primary_anchor = scene_spatial_map.get("primary_anchor")
                anchor_id = primary_anchor.get("asset_id") if isinstance(primary_anchor, dict) else ""
                required_spatial_refs = {
                    scene_spatial_map.get("location_master_asset_id"),
                    scene_spatial_map.get("establishing_view_asset_id"),
                    scene_spatial_map.get("side_three_quarter_view_asset_id"),
                    anchor_id,
                } - {None, ""}
                if not required_spatial_refs.issubset(set(locked_ids)):
                    report.error(
                        "SPATIAL_GATE",
                        f"Comparison set {comparison_id} must lock the location master, establishing view, side-three-quarter view and primary anchor.",
                    )
        for reference_id in locked_ids:
            validate_approved_asset_reference(reference_id, f"Comparison set {comparison_id} locked reference", assets, report)
        profile_ids = comparison.get("candidate_profile_ids") if isinstance(comparison.get("candidate_profile_ids"), list) else []
        asset_ids = comparison.get("candidate_asset_ids") if isinstance(comparison.get("candidate_asset_ids"), list) else []
        selected_profile_id = comparison.get("selected_profile_id")
        selected_asset_id = comparison.get("selected_asset_id")
        require_string(selected_profile_id, f"{where}.selected_profile_id", report, allow_empty=True)
        require_string(selected_asset_id, f"{where}.selected_asset_id", report, allow_empty=True)
        if status != "planned":
            if len(profile_ids) != 3 or len(set(profile_ids)) != 3:
                report.error("LOOK_COMPARISON", f"Comparison set {comparison_id} requires exactly three distinct Profiles.")
            if len(asset_ids) != 3 or len(set(asset_ids)) != 3:
                report.error("LOOK_COMPARISON", f"Comparison set {comparison_id} requires exactly three distinct Look Tests.")
        prompt_paths: list[str] = []
        image_paths: list[str] = []
        for position, profile_id in enumerate(profile_ids):
            profile = profiles.get(profile_id)
            if profile is None:
                report.error("MISSING_REFERENCE", f"Comparison set {comparison_id} references missing Profile {profile_id}.")
            if position < len(asset_ids):
                asset_id = asset_ids[position]
                asset = assets.get(asset_id)
                if asset is None:
                    report.error("MISSING_REFERENCE", f"Comparison set {comparison_id} references missing Look Test {asset_id}.")
                elif asset.get("type") != "look_test":
                    report.error("REFERENCE_TYPE", f"Comparison set {comparison_id} references non-Look-Test asset {asset_id}.")
                else:
                    if asset.get("mode") != "generate" or asset.get("derived_from"):
                        report.error(
                            "LOOK_INDEPENDENCE",
                            f"Look Test {asset_id} must be a fresh generate asset with empty derived_from.",
                        )
                    if asset.get("capture_profile_id") != profile_id:
                        report.error("PROFILE_REFERENCE", f"Look Test {asset_id} must use Profile {profile_id}.")
                    if asset.get("comparison_set_id") != comparison_id:
                        report.error("LOOK_COMPARISON", f"Look Test {asset_id} must point back to comparison set {comparison_id}.")
                    asset_reference_ids = (
                        asset.get("reference_asset_ids") if isinstance(asset.get("reference_asset_ids"), list) else []
                    )
                    if set(asset_reference_ids) != set(locked_ids):
                        report.error(
                            "LOOK_CONTROL",
                            f"Look Test {asset_id} references must exactly match comparison set {comparison_id} locked references.",
                        )
                    if set(asset_reference_ids) & set(asset_ids):
                        report.error(
                            "LOOK_INDEPENDENCE",
                            f"Look Test {asset_id} cannot use another comparison candidate as a reference.",
                        )
                    asset_scene_ids = asset.get("scene_ids") if isinstance(asset.get("scene_ids"), list) else []
                    if scene_id not in asset_scene_ids:
                        report.error(
                            "LOOK_CONTROL",
                            f"Look Test {asset_id} must include diagnostic scene {scene_id}.",
                        )
                    if isinstance(scene_spatial_map, dict):
                        expected_anchor = scene_spatial_map.get("primary_anchor", {}).get("asset_id")
                        if asset.get("spatial_map_id") != scene_spatial_map.get("id"):
                            report.error("SPATIAL_GATE", f"Look Test {asset_id} must inherit spatial map {scene_spatial_map.get('id')}.")
                        if asset.get("primary_anchor_asset_id") != expected_anchor:
                            report.error("SPATIAL_GATE", f"Look Test {asset_id} must bind primary anchor {expected_anchor}.")
                    if (
                        not photographic_qa_passed(asset)
                        or not authenticity_passed(asset, require_user_approval=False)
                        or not texture_qa_passed(asset, require_user_approval=False)
                        or not geometry_qa_passed(asset, require_user_approval=False)
                        or not live_action_surface_passed(asset, require_user_approval=False)
                    ):
                        report.error(
                            "LOOK_AUTHENTICITY",
                            f"Look Test {asset_id} must pass photographic, authenticity, texture, geometry, and live-action-surface QA before comparison.",
                        )
                    prompt_value = asset.get("prompt_path")
                    if isinstance(prompt_value, str) and prompt_value:
                        prompt_paths.append(prompt_value)
                        prompt_file = project_dir / prompt_value
                        if prompt_file.is_file():
                            try:
                                prompt_text = re.sub(r"\s+", " ", prompt_file.read_text(encoding="utf-8")).strip().casefold()
                                locked_text = re.sub(r"\s+", " ", str(comparison.get("locked_blocking"))).strip().casefold()
                                story_text = re.sub(r"\s+", " ", str(comparison.get("story_moment"))).strip().casefold()
                                if locked_text and locked_text not in prompt_text:
                                    report.error(
                                        "LOOK_CONTROL",
                                        f"Look Test {asset_id} prompt must contain the comparison set's exact locked_blocking text.",
                                    )
                                if story_text and story_text not in prompt_text:
                                    report.error(
                                        "LOOK_CONTROL",
                                        f"Look Test {asset_id} prompt must contain the comparison set's exact story_moment text.",
                                    )
                            except OSError as exc:
                                report.error("READ_ERROR", f"Cannot inspect controlled Look Test prompt {asset_id}: {exc}")
                    effective_image_path = asset.get("candidate_path") or asset.get("approved_path")
                    if isinstance(effective_image_path, str) and effective_image_path:
                        image_paths.append(effective_image_path)
        if status != "planned" and len(prompt_paths) == 3 and len(set(prompt_paths)) != 3:
            report.error("LOOK_INDEPENDENCE", f"Comparison set {comparison_id} requires three distinct prompt files.")
        if status != "planned" and len(image_paths) == 3 and len(set(image_paths)) != 3:
            report.error("LOOK_INDEPENDENCE", f"Comparison set {comparison_id} requires three distinct image files.")
        comparable_profiles = [profiles[profile_id] for profile_id in profile_ids if profile_id in profiles]
        if status != "planned" and len(comparable_profiles) == 3:
            dimensions = [profile_strategy_dimensions(profile) for profile in comparable_profiles]
            for left_index in range(3):
                for right_index in range(left_index + 1, 3):
                    difference_count = sum(
                        left != right
                        for left, right in zip(dimensions[left_index], dimensions[right_index])
                    )
                    if difference_count < 3:
                        report.error(
                            "LOOK_VARIATION_TOO_SHALLOW",
                            f"Comparison set {comparison_id} Profiles {profile_ids[left_index]} and "
                            f"{profile_ids[right_index]} differ in only {difference_count} treatment/capture dimensions; at least three are required.",
                        )
        if status == "qualified":
            if selected_profile_id or selected_asset_id:
                report.error("LOOK_COMPARISON", f"Qualified comparison set {comparison_id} cannot have a selection before its foundation gate.")
            for profile_id in profile_ids:
                if profile_id in profiles and profiles[profile_id].get("status") != "qualified":
                    report.error("LOOK_COMPARISON", f"Qualified comparison Profile {profile_id} must be qualified.")
            for asset_id in asset_ids:
                if asset_id in assets and assets[asset_id].get("status") != "qualified":
                    report.error("LOOK_COMPARISON", f"Qualified Look Test {asset_id} must be qualified.")
        elif status == "approved":
            if selected_profile_id not in profile_ids or selected_asset_id not in asset_ids:
                report.error("LOOK_COMPARISON", f"Approved comparison set {comparison_id} requires valid selected ids.")
            selection_positions_match = True
            if selected_profile_id in profile_ids and selected_asset_id in asset_ids:
                selection_positions_match = profile_ids.index(selected_profile_id) == asset_ids.index(selected_asset_id)
            if not selection_positions_match:
                report.error("LOOK_COMPARISON", f"Comparison set {comparison_id} selected Profile and asset positions must match.")
            for profile_id in profile_ids:
                expected = "approved" if profile_id == selected_profile_id else "rejected"
                if profile_id in profiles and profiles[profile_id].get("status") != expected:
                    report.error("LOOK_COMPARISON", f"Profile {profile_id} must be {expected} in approved comparison {comparison_id}.")
            for asset_id in asset_ids:
                expected = "approved" if asset_id == selected_asset_id else "rejected"
                if asset_id in assets and assets[asset_id].get("status") != expected:
                    report.error("LOOK_COMPARISON", f"Look Test {asset_id} must be {expected} in approved comparison {comparison_id}.")
        elif status == "rejected":
            if selected_profile_id or selected_asset_id:
                report.error("LOOK_COMPARISON", f"Rejected comparison set {comparison_id} cannot have a selection.")
            for profile_id in profile_ids:
                if profile_id in profiles and profiles[profile_id].get("status") != "rejected":
                    report.error("LOOK_COMPARISON", f"Rejected comparison Profile {profile_id} must be rejected.")
            for asset_id in asset_ids:
                if asset_id in assets and assets[asset_id].get("status") != "rejected":
                    report.error("LOOK_COMPARISON", f"Rejected Look Test {asset_id} must be rejected.")

    if isinstance(base_profile_id, str) and base_profile_id:
        base = profiles.get(base_profile_id)
        if base is None:
            report.error("MISSING_REFERENCE", f"base_profile_id references missing Profile {base_profile_id}.")
        else:
            if base.get("status") != "approved" or base.get("scope") != "project":
                report.error("PROFILE_APPROVAL", "base_profile_id must reference an approved project-scope Profile.")
            selected_by_approved_set = any(
                item.get("status") == "approved" and item.get("selected_profile_id") == base_profile_id
                for item in comparison_sets.values()
            )
            if not selected_by_approved_set:
                report.error("PROFILE_APPROVAL", "Base Profile must be selected by an approved three-candidate comparison set.")

    if isinstance(base_treatment_id, str) and base_treatment_id:
        treatment = treatments.get(base_treatment_id)
        if treatment is None or treatment.get("status") != "approved" or treatment.get("scope") != "project":
            report.error("TREATMENT_APPROVAL", "base_treatment_id must reference an approved project treatment.")
        base_profile = profiles.get(base_profile_id) if isinstance(base_profile_id, str) else None
        if isinstance(base_profile, dict) and base_profile.get("cinematic_treatment_id") != base_treatment_id:
            report.error("TREATMENT_REFERENCE", "Base Profile must reference base_treatment_id.")
    if isinstance(base_format_plan_id, str) and base_format_plan_id:
        format_plan = format_plans.get(base_format_plan_id)
        if format_plan is None or format_plan.get("status") != "approved" or format_plan.get("scope") != "project":
            report.error("FORMAT_APPROVAL", "base_format_plan_id must reference an approved project format plan.")
        base_profile = profiles.get(base_profile_id) if isinstance(base_profile_id, str) else None
        if isinstance(base_profile, dict) and base_profile.get("format_plan_id") != base_format_plan_id:
            report.error("FORMAT_REFERENCE", "Base Profile must reference base_format_plan_id.")

    return (
        profiles,
        base_profile_id if isinstance(base_profile_id, str) else "",
        comparison_sets,
        treatments,
        format_plans,
        medium_signatures,
    )


def validate_capture_dependencies(
    project: dict[str, Any] | None,
    scenes: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    base_profile_id: str,
    comparison_sets: dict[str, dict[str, Any]],
    spatial_maps: dict[str, dict[str, Any]],
    format_plans: dict[str, dict[str, Any]],
    medium_signatures: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, str]:
    effective_profiles: dict[str, str] = {}
    for scene_id, scene in scenes.items():
        override_id = scene.get("capture_profile_id")
        effective_id = override_id or base_profile_id
        if override_id:
            profile = profiles.get(override_id)
            if profile is None:
                report.error("MISSING_REFERENCE", f"Scene {scene_id} references missing capture Profile {override_id}.")
            else:
                if profile.get("status") != "approved":
                    report.error("UNAPPROVED_REFERENCE", f"Scene {scene_id} references non-approved Profile {override_id}.")
                if profile.get("scope") not in {"scene_group", "scene"} or scene_id not in profile.get("scene_ids", []):
                    report.error("PROFILE_SCOPE", f"Profile {override_id} is not an approved override for scene {scene_id}.")
        if effective_id:
            effective_profiles[scene_id] = effective_id
        format_id = scene.get("format_plan_id")
        format_plan = format_plans.get(format_id) if isinstance(format_id, str) else None
        if format_plan is None:
            report.error("MISSING_REFERENCE", f"Scene {scene_id} references missing format plan {format_id}.")
        elif format_plan.get("status") != "approved":
            report.error("FORMAT_APPROVAL", f"Scene {scene_id} requires an approved format plan {format_id}.")

    for asset_id, asset in assets.items():
        asset_type = asset.get("type")
        status = asset.get("status")
        profile_id = asset.get("capture_profile_id")
        comparison_id = asset.get("comparison_set_id")
        if asset_type in PROFILED_ASSET_TYPES and status != "planned" and not profile_id:
            report.error("MISSING_PROFILE", f"Asset {asset_id} type={asset_type} requires capture_profile_id.")
        if profile_id:
            profile = profiles.get(profile_id)
            if profile is None:
                report.error("MISSING_REFERENCE", f"Asset {asset_id} references missing Profile {profile_id}.")
            elif asset_type != "look_test" and profile.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"Narrative asset {asset_id} uses non-approved Profile {profile_id}.")
            elif asset_type == "look_test" and status in PROFILE_STATUSES and profile.get("status") != status:
                report.error("PROFILE_REFERENCE", f"Look Test {asset_id} status must match Profile {profile_id} status.")
            if isinstance(profile, dict):
                scene_format_ids = {
                    scenes[scene_id].get("format_plan_id")
                    for scene_id in asset.get("scene_ids", [])
                    if scene_id in scenes
                }
                if scene_format_ids and profile.get("format_plan_id") not in scene_format_ids:
                    report.error("FORMAT_REFERENCE", f"Asset {asset_id} Profile format does not match its scene format plan.")
                profile_medium_id = profile.get("medium_signature_id") or ""
                if asset.get("surface_policy") == "calibrated_medium_signature":
                    if asset.get("medium_signature_id") != profile_medium_id:
                        report.error("MEDIUM_SIGNATURE", f"Asset {asset_id} must inherit Profile medium signature {profile_medium_id}.")
                    medium = medium_signatures.get(profile_medium_id)
                    if medium is None or medium.get("status") != "stable":
                        report.error("MEDIUM_CALIBRATION", f"Asset {asset_id} uses an unavailable or unstable medium signature.")
                elif asset.get("medium_signature_id"):
                    report.error("MEDIUM_SIGNATURE", f"Asset {asset_id} may not carry a medium signature under {asset.get('surface_policy')}.")
        if asset_type == "look_test":
            if comparison_id and comparison_id not in comparison_sets:
                report.error("MISSING_REFERENCE", f"Look Test {asset_id} references missing comparison set {comparison_id}.")
        elif comparison_id:
            report.error("LOOK_COMPARISON", f"Only look_test assets may set comparison_set_id; found on {asset_id}.")
        if asset_type in NARRATIVE_ASSET_TYPES and status == "approved":
            if not base_profile_id:
                report.error("MISSING_PROFILE", f"Approved narrative asset {asset_id} requires an approved Base Profile.")
            for scene_id in asset.get("scene_ids", []) if isinstance(asset.get("scene_ids"), list) else []:
                effective_id = effective_profiles.get(scene_id)
                if effective_id and profile_id != effective_id:
                    report.error(
                        "PROFILE_CONTINUITY",
                        f"Asset {asset_id} uses Profile {profile_id}, but scene {scene_id} requires {effective_id}.",
                    )
        if asset_type in SPATIALIZED_ASSET_TYPES and status != "planned":
            asset_scene_ids = asset.get("scene_ids") if isinstance(asset.get("scene_ids"), list) else []
            if not asset_scene_ids:
                report.error("SPATIAL_GATE", f"Spatialized asset {asset_id} requires at least one scene_id.")
            for scene_id in asset_scene_ids:
                scene = scenes.get(scene_id)
                spatial_map = spatial_maps.get(scene.get("spatial_map_id")) if isinstance(scene, dict) else None
                if not isinstance(spatial_map, dict) or spatial_map.get("status") != "approved":
                    report.error("SPATIAL_GATE", f"Asset {asset_id} requires an approved spatial map for scene {scene_id}.")
                    continue
                anchor_id = spatial_map.get("primary_anchor", {}).get("asset_id")
                if asset.get("spatial_map_id") != spatial_map.get("id"):
                    report.error("SPATIAL_GATE", f"Asset {asset_id} must inherit spatial map {spatial_map.get('id')}.")
                if asset.get("scene_state_id") != spatial_map.get("scene_state_id"):
                    report.error("SPATIAL_GATE", f"Asset {asset_id} must inherit scene state {spatial_map.get('scene_state_id')}.")
                if asset.get("primary_anchor_asset_id") != anchor_id:
                    report.error("SPATIAL_GATE", f"Asset {asset_id} must bind primary anchor {anchor_id}.")
                required_dependencies = {
                    anchor_id,
                    spatial_map.get("side_three_quarter_view_asset_id"),
                } - {None, ""}
                missing_dependencies = {
                    dependency_id
                    for dependency_id in required_dependencies
                    if not _asset_dependency_contains(asset_id, str(dependency_id), assets)
                }
                if missing_dependencies:
                    report.error(
                        "SPATIAL_GATE",
                        f"Asset {asset_id} does not trace to required spatial dependencies: {', '.join(sorted(missing_dependencies))}.",
                    )
        if asset_type in {"storyboard", "keyframe"} and status == "approved":
            reference_ids = asset.get("reference_asset_ids") if isinstance(asset.get("reference_asset_ids"), list) else []
            if not any(assets.get(reference_id, {}).get("type") == "location_plate" for reference_id in reference_ids):
                report.warning(
                    "LOCATION_PLATE",
                    f"Approved {asset_type} {asset_id} has no approved location_plate reference; document a no-location exception in QA.",
                )

    return effective_profiles


def normalize_heading(line: str) -> str:
    value = line.strip().upper().lstrip("#").strip().rstrip(":")
    value = re.sub(r"\s*/\s*", "/", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _spatial_mark_index(spatial_map: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(mark.get("id")): mark
        for mark in spatial_map.get("marks", [])
        if isinstance(mark, dict) and isinstance(mark.get("id"), str)
    }


def _format_position(position: Any) -> str:
    if not isinstance(position, dict):
        return "(unknown)"
    values = []
    for axis in ("x", "y", "z"):
        value = position.get(axis)
        values.append(f"{float(value):.1f}" if is_number(value) else "?")
    return f"({', '.join(values)}) m"


def render_spatial_prompt_block(shot: dict[str, Any], spatial_map: dict[str, Any]) -> str:
    anchor = spatial_map.get("primary_anchor") if isinstance(spatial_map.get("primary_anchor"), dict) else {}
    anchor_id = str(anchor.get("asset_id") or "missing-anchor")
    coordinate = spatial_map.get("coordinate_system") if isinstance(spatial_map.get("coordinate_system"), dict) else {}
    mark_index = _spatial_mark_index(spatial_map)
    camera_mark_id = str(shot.get("camera_mark_id") or "")
    camera_mark = mark_index.get(camera_mark_id, {})
    projection = shot.get("anchor_projection") if isinstance(shot.get("anchor_projection"), dict) else {}
    distance = projection.get("distance_m")
    distance_text = f"{float(distance):.1f} m" if is_number(distance) else "unknown distance"
    lines = [
        f"Spatial map {spatial_map.get('id')}; scene state {spatial_map.get('scene_state_id')}.",
        f"Primary anchor {anchor_id}: origin at its ground-contact center (0.0, 0.0, 0.0) m; orientation {anchor.get('orientation', '')}.",
        f"Set-fixed axes: +X {coordinate.get('x_positive_label', '')}; +Y {coordinate.get('y_positive_label', '')}; +Z {coordinate.get('z_positive_label', '')}.",
        f"Camera {camera_mark_id}: {_format_position(camera_mark.get('position_m'))}; facing {camera_mark.get('facing', '')}; {camera_mark.get('relation_to_anchor', '')}; {distance_text} from {anchor_id}.",
    ]
    subject_mark_ids = shot.get("subject_mark_ids") if isinstance(shot.get("subject_mark_ids"), dict) else {}
    for asset_id in sorted(subject_mark_ids):
        mark_id = str(subject_mark_ids[asset_id])
        mark = mark_index.get(mark_id, {})
        lines.append(
            f"Subject {asset_id} at {mark_id}: {_format_position(mark.get('position_m'))}; facing {mark.get('facing', '')}; {mark.get('relation_to_anchor', '')}."
        )
    movement_index = {
        (
            movement.get("subject_asset_id"),
            movement.get("start_mark_id"),
            movement.get("end_mark_id"),
        ): movement
        for movement in spatial_map.get("movement_paths", [])
        if isinstance(movement, dict)
    }
    for beat in shot.get("action_beats", []) if isinstance(shot.get("action_beats"), list) else []:
        if not isinstance(beat, dict) or beat.get("changes_position") is not True:
            continue
        subject_id = beat.get("subject_asset_id")
        start_mark_id = beat.get("start_mark_id")
        end_mark_id = beat.get("end_mark_id")
        start_mark = mark_index.get(str(start_mark_id), {})
        end_mark = mark_index.get(str(end_mark_id), {})
        movement = movement_index.get((subject_id, start_mark_id, end_mark_id), {})
        lines.append(
            f"Movement {subject_id}: {start_mark_id} {_format_position(start_mark.get('position_m'))} to "
            f"{end_mark_id} {_format_position(end_mark.get('position_m'))}; {movement.get('path_description', '')}."
        )
    lines.append(
        f"Anchor projection: {projection.get('visibility', '')}; screen region {projection.get('screen_region', '')}; "
        f"camera-relative direction {projection.get('direction_from_camera', '')}; set-fixed direction "
        f"{projection.get('set_fixed_direction', '')}; {projection.get('set_fixed_relation', '')}; distance {distance_text}."
    )
    depth_order = shot.get("depth_order") if isinstance(shot.get("depth_order"), list) else []
    lines.append(f"Depth order, camera-near to far: {' -> '.join(str(item) for item in depth_order)}.")
    return "\n".join(lines)


def validate_image_prompt_sections(
    path: Path, asset_id: str, strategy: str, asset: dict[str, Any], report: Report
) -> None:
    try:
        text = path.read_text(encoding="utf-8")
        headings = {normalize_heading(line) for line in text.splitlines() if len(line) <= 120}
    except OSError as exc:
        report.error("READ_ERROR", f"Cannot inspect image prompt for {asset_id}: {exc}")
        return
    expected_headers = IMAGE_PROMPT_STRATEGIES.get(strategy)
    if expected_headers is None:
        report.error("IMAGE_PROMPT_STRATEGY", f"Asset {asset_id} uses unknown prompt strategy: {strategy}")
        return
    if not re.search(rf"(?im)^\s*prompt\s+strategy\s*:\s*{re.escape(strategy)}\s*$", text):
        report.error(
            "IMAGE_PROMPT_STRATEGY",
            f"Asset {asset_id} prompt must declare `Prompt strategy: {strategy}`.",
        )
    for header in expected_headers:
        if header not in headings:
            report.error("IMAGE_PROMPT_SECTION", f"Asset {asset_id} prompt is missing heading: {header}")
    active_heading = ""
    positive_lines: list[str] = []
    exclusion_lines: list[str] = []
    for line in text.splitlines():
        normalized = normalize_heading(line)
        if normalized in expected_headers:
            active_heading = normalized
            continue
        if re.match(r"(?i)^\s*prompt\s+strategy\s*:", line):
            continue
        if active_heading == "EXCLUSIONS":
            exclusion_lines.append(line)
        else:
            positive_lines.append(line)
    positive_text = "\n".join(positive_lines).casefold()
    exclusions = " ".join(exclusion_lines).casefold()
    if strategy == "image2-live-action-integration-probe-v1.6":
        for concept in ("photorealistic", "candid", "on-location photograph", "exposure priority", "clip", "lose detail", "no local hdr"):
            if concept not in positive_text:
                report.error("LIVE_ACTION_PROBE_PROMPT", f"Asset {asset_id} integration probe prompt omits `{concept}`.")
        forbidden_styling = (
            "cinematic", "film look", "film stock", "film grain", "anamorphic", "arri", "venice 2",
            "cooke", "kodak", "director", "hero light", "beauty light", "volumetric",
        )
        for cue in forbidden_styling:
            if cue in positive_text:
                report.error(
                    "LIVE_ACTION_PROBE_STYLING",
                    f"Asset {asset_id} integration probe may not use styling/equipment cue `{cue}` before realism is proven.",
                )
        for cue in (*RISKY_TEXTURE_CUES, *RISKY_RENDER_CUES):
            if _positive_cue_occurs(positive_text, cue):
                report.error("LIVE_ACTION_PROBE_STYLING", f"Asset {asset_id} positively uses disabled cue `{cue}`.")
        probe_exclusions = {
            "synthetic or game-like person": ("synthetic-rendered", "synthetic rendered", "game-like", "game like"),
            "oily/waxy/plastic skin": ("oily", "waxy", "plastic skin"),
            "cut-out or separately tone-mapped subject": ("cut-out", "cut out", "separate subject tone mapping"),
            "repeated artifact texture": ("repeated artifact texture", "repeating artifact texture"),
        }
        for label, alternatives in probe_exclusions.items():
            if not any(value in exclusions for value in alternatives):
                report.error("LIVE_ACTION_PROBE_PROMPT", f"Asset {asset_id} EXCLUSIONS must reject {label}.")
        total_words = len(re.findall(r"\b[A-Za-z][A-Za-z0-9'’-]*\b", text))
        exclusion_words = len(re.findall(r"\b[A-Za-z][A-Za-z0-9'’-]*\b", " ".join(exclusion_lines)))
        if not 120 <= total_words <= 260:
            report.error(
                "LIVE_ACTION_PROBE_LENGTH",
                f"Asset {asset_id} integration probe has about {total_words} English words; hard range is 120-260.",
            )
        if exclusion_words > 40:
            report.error(
                "LIVE_ACTION_PROBE_LENGTH",
                f"Asset {asset_id} integration-probe exclusions contain about {exclusion_words} words; maximum is 40.",
            )
        return
    for concept in (
        "finite scene-referred capture",
        "exposure priority",
        "allowed clipping",
        "allowed shadow loss",
        "no multi-exposure hdr merge",
    ):
        if concept not in positive_text:
            report.error("DYNAMIC_RANGE_PROMPT", f"Asset {asset_id} prompt omits `{concept}`.")
    calibrated_medium = (
        asset.get("surface_policy") == "calibrated_medium_signature"
        and isinstance(asset.get("medium_signature_id"), str)
        and bool(asset.get("medium_signature_id"))
    )
    for cue in RISKY_TEXTURE_CUES:
        if _positive_cue_occurs(positive_text, cue):
            if calibrated_medium:
                continue
            report.error(
                "UNCALIBRATED_TEXTURE_CUE",
                f"Asset {asset_id} positively uses disabled Image2 texture cue `{cue}` outside EXCLUSIONS.",
            )
    for cue in RISKY_RENDER_CUES:
        if _positive_cue_occurs(positive_text, cue):
            report.error(
                "UNCALIBRATED_RENDER_CUE",
                f"Asset {asset_id} positively uses the high-risk synthetic render cue `{cue}` outside EXCLUSIONS.",
            )
    exclusion_concepts = {
        "painterly or patch smear": ("painterly smear", "paint smear", "patch smear"),
        "repeating or cross-material artifact": (
            "repeating swirl", "repeated swirl", "repeating scale", "cross-material texture", "cross material texture", "texture copied across"
        ),
        "rendered outline, oversharpening, or local-contrast/HDR halo": (
            "oversharpen halo", "oversharpened halo", "sharpening halo", "rendered outline",
            "local-contrast halo", "local contrast halo", "hdr halo", "clarity halo",
        ),
    }
    has_human = (
        asset.get("type") in HUMAN_RELEVANT_ASSET_TYPES
        or bool(asset.get("identity_pack_id"))
        or bool(asset.get("character_state_id"))
    )
    if has_human:
        exclusion_concepts.update(
            {
                "wax/plastic/CG or animated rendering": (
                    "wax skin", "plastic skin", "cg render", "animated rendering", "animation look",
                ),
                "game-cinematic rendering or synthetic glossy skin": (
                    "game-cinematic rendering", "game cinematic rendering", "synthetic glossy skin",
                ),
            }
        )
    else:
        exclusion_concepts["illustration/animation/CG-PBR or game rendering"] = (
            "illustration", "animation", "cg/pbr render", "cg render", "game-environment finish", "game environment finish",
        )
    for label, alternatives in exclusion_concepts.items():
        if not any(value in exclusions for value in alternatives):
            report.error("IMAGE2_CLEAN_EXCLUSION", f"Asset {asset_id} EXCLUSIONS must explicitly reject {label}.")
    word_count = len(re.findall(r"\b[A-Za-z][A-Za-z0-9'’-]*\b", text))
    recommended_min, recommended_max = ((140, 260) if strategy == "image2-live-action-narrative-v1.6" else (80, 180))
    if word_count < recommended_min or word_count > recommended_max:
        report.warning(
            "IMAGE_PROMPT_CALIBRATION",
            f"Asset {asset_id} prompt has about {word_count} English words; calibrated range is {recommended_min}-{recommended_max} for {strategy}.",
        )
    if word_count > 350:
        report.warning(
            "IMAGE_PROMPT_LENGTH",
            f"Asset {asset_id} prompt contains about {word_count} English words; document why it exceeds the 350-word ceiling.",
        )


def validate_prompt_sections(
    path: Path,
    shot_id: str,
    motion_class: str,
    shot: dict[str, Any],
    spatial_map: dict[str, Any] | None,
    format_plan: dict[str, Any] | None,
    environmental_state: dict[str, Any] | None,
    special_lighting_events: list[dict[str, Any]],
    report: Report,
) -> None:
    try:
        text = path.read_text(encoding="utf-8")
        normalized_lines = [normalize_heading(line) for line in text.splitlines() if line.strip() and len(line) <= 100]
        headings = set(normalized_lines)
    except OSError as exc:
        report.error("READ_ERROR", f"Cannot inspect prompt for {shot_id}: {exc}")
        return
    for header in VIDEO_PROMPT_HEADERS:
        normalized_header = normalize_heading(header)
        if normalized_header not in headings:
            report.error("PROMPT_SECTION", f"Shot {shot_id} prompt is missing heading: {header}")
    expected_headings = [normalize_heading(value) for value in VIDEO_PROMPT_HEADERS]
    positions: list[int] = []
    for expected in expected_headings:
        matches = [index for index, value in enumerate(normalized_lines) if value == expected]
        if len(matches) != 1:
            report.error("HIGGSFIELD_PROMPT_CONTRACT", f"Shot {shot_id} must contain exactly one `{expected}` heading.")
        elif matches:
            positions.append(matches[0])
    if positions and positions != sorted(positions):
        report.error("HIGGSFIELD_PROMPT_CONTRACT", f"Shot {shot_id} headings are not in Higgsfield's official Seedance 2.5 order.")
    first_nonempty = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if normalize_heading(first_nonempty) != "GLOBAL STYLE":
        report.error("HIGGSFIELD_PROMPT_CONTRACT", f"Shot {shot_id} model prompt must begin with GLOBAL STYLE and contain no internal preamble.")
    if re.search(r"(?im)^\s*(?:prompt\s+strategy|qa|reviewer|hard\s+failures?)\s*[:\n]", text):
        report.error("HIGGSFIELD_PROMPT_CONTRACT", f"Shot {shot_id} leaks internal strategy or QA metadata into the model prompt.")
    normalized_text = re.sub(r"\s+", " ", text).casefold()
    dynamic_range = shot.get("dynamic_range_plan") if isinstance(shot.get("dynamic_range_plan"), dict) else {}
    for concept in ("finite scene-referred capture", "allowed clipping", "allowed shadow loss", "no multi-exposure hdr merge"):
        if concept not in normalized_text:
            report.error("DYNAMIC_RANGE_PROMPT", f"Shot {shot_id} LIGHTING contract omits `{concept}`.")
    for field in ("working_latitude_stops", "scene_contrast_stops_estimate"):
        value = dynamic_range.get(field)
        if is_number(value) and str(value).casefold() not in normalized_text:
            report.error("DYNAMIC_RANGE_PROMPT", f"Shot {shot_id} prompt omits {field}={value}.")
    priority = dynamic_range.get("exposure_priority")
    if isinstance(priority, str) and priority and priority.casefold() not in normalized_text:
        report.error("DYNAMIC_RANGE_PROMPT", f"Shot {shot_id} prompt omits exposure priority {priority}.")
    for cue in RISKY_RENDER_CUES:
        if _positive_cue_occurs(normalized_text, cue):
            report.error(
                "UNCALIBRATED_RENDER_CUE",
                f"Shot {shot_id} positively uses the high-risk synthetic render cue `{cue}`.",
            )
    # Exact IDs and QA remain in JSON.  The model prompt contains only visible
    # facts and @handles, matching the official reference-led contract.
    temporal = shot.get("temporal_capture") if isinstance(shot.get("temporal_capture"), dict) else {}
    for field in ("capture_fps", "delivery_fps", "shutter_angle"):
        value = temporal.get(field)
        if is_number(value) and str(value).casefold() not in normalized_text:
            report.error("TEMPORAL_PROMPT", f"Shot {shot_id} prompt omits temporal value {field}={value}.")
    exposure_time = temporal.get("exposure_time_s")
    if is_number(exposure_time):
        reciprocal = round(1.0 / float(exposure_time)) if float(exposure_time) > 0 else 0
        if f"1/{reciprocal}" not in normalized_text and f"{float(exposure_time):.6f}" not in normalized_text:
            report.error("TEMPORAL_PROMPT", f"Shot {shot_id} prompt omits computed exposure time.")
    camera_plan = shot.get("camera_move_plan") if isinstance(shot.get("camera_move_plan"), dict) else {}
    primitive = camera_plan.get("primitive")
    if isinstance(primitive, str) and primitive and primitive.replace("_", " ").casefold() not in normalized_text.replace("_", " "):
        report.error("CAMERA_PATH_PROMPT", f"Shot {shot_id} prompt omits camera primitive {primitive}.")
    for field in ("start_camera_mark_id", "end_camera_mark_id"):
        value = camera_plan.get(field)
        if isinstance(value, str) and value and value.casefold() not in normalized_text:
            report.error("CAMERA_PATH_PROMPT", f"Shot {shot_id} prompt omits {field}={value}.")
    blur = shot.get("motion_blur_plan") if isinstance(shot.get("motion_blur_plan"), dict) else {}
    for field in ("source", "amount", "direction"):
        value = blur.get(field)
        if isinstance(value, str) and value and value.casefold() not in normalized_text:
            report.error("MOTION_BLUR_PROMPT", f"Shot {shot_id} prompt omits motion-blur {field}={value}.")
    if "cinematic motion blur" in normalized_text and not all(
        isinstance(blur.get(field), str) and blur.get(field)
        for field in ("source", "amount", "direction")
    ):
        report.error("MOTION_BLUR_PROMPT", f"Shot {shot_id} uses generic cinematic motion blur without a physical plan.")
    if isinstance(format_plan, dict):
        delivery_aspect = format_plan.get("delivery_aspect")
        if isinstance(delivery_aspect, str) and delivery_aspect.casefold() not in normalized_text:
            report.error("FORMAT_PROMPT", f"Shot {shot_id} prompt omits delivery aspect {delivery_aspect}.")
        if format_plan.get("baked_black_bars") is False and not re.search(r"(?:no|without)\s+(?:baked\s+)?black\s+bars", normalized_text):
            report.error("FORMAT_PROMPT", f"Shot {shot_id} prompt must reject baked black bars.")
    if isinstance(environmental_state, dict):
        kind = environmental_state.get("kind")
        if isinstance(kind, str) and kind and kind.casefold() not in normalized_text:
            report.error("ENVIRONMENT_PROMPT", f"Shot {shot_id} prompt omits environment kind {kind}.")
        if kind != "clear":
            for field in ("intensity", "direction"):
                value = environmental_state.get(field)
                if isinstance(value, str) and value and value.casefold() not in normalized_text:
                    report.error("ENVIRONMENT_PROMPT", f"Shot {shot_id} prompt omits environment {field}: {value}.")
    for event in special_lighting_events:
        event_id = event.get("id")
        if isinstance(event_id, str) and event_id and event_id.casefold() not in normalized_text:
            report.error("SPECIAL_LIGHT_PROMPT", f"Shot {shot_id} prompt omits special-light event {event_id}.")
    geometry_locks = shot.get("body_geometry_locks") if isinstance(shot.get("body_geometry_locks"), dict) else {}
    for lock in geometry_locks.values():
        if not isinstance(lock, dict):
            report.error("BODY_GEOMETRY_PROMPT", f"Shot {shot_id} has an invalid body geometry lock.")
    cast_ids = shot.get("cast_asset_ids") if isinstance(shot.get("cast_asset_ids"), list) else []
    if len(cast_ids) >= 2:
        multi_person = (
            shot.get("multi_person_projection")
            if isinstance(shot.get("multi_person_projection"), dict)
            else {}
        )
        if "one shared camera projection" not in normalized_text:
            report.error(
                "MULTI_PERSON_PROJECTION_PROMPT",
                f"Shot {shot_id} prompt must state one shared camera projection for all people.",
            )
        if "do not independently scale" not in normalized_text:
            report.error(
                "MULTI_PERSON_PROJECTION_PROMPT",
                f"Shot {shot_id} prompt must forbid independent per-person scaling.",
            )
        subjects = multi_person.get("subjects") if isinstance(multi_person.get("subjects"), dict) else {}
        for root_id, subject in subjects.items():
            if not isinstance(subject, dict):
                continue
            distance = subject.get("camera_distance_m")
            if is_number(distance) and f"{distance} m" not in normalized_text:
                report.error(
                    "MULTI_PERSON_PROJECTION_PROMPT",
                    f"Shot {shot_id} prompt omits {root_id} camera distance {distance} m.",
                )
    if geometry_locks:
        skin_prompt_concepts = {
            "skin key source": ("skin key source", "skin light source"),
            "skin wetness state": ("skin wetness", "dry skin", "rain-wet skin", "water-wet skin", "localized perspiration"),
            "skin specular extent": ("skin specular", "specular extent", "specular range"),
            "local contrast or tone mapping": ("local contrast", "tone mapping"),
            "independent material roughness": ("material roughness", "roughness response"),
            "game-cinematic/synthetic-skin rejection": ("no game-cinematic", "no game cinematic", "reject game-cinematic", "synthetic glossy skin"),
        }
        for label, alternatives in skin_prompt_concepts.items():
            if not any(value in normalized_text for value in alternatives):
                report.error("SKIN_VIDEO_PROMPT", f"Shot {shot_id} prompt omits {label}.")
    if isinstance(spatial_map, dict):
        expected = re.sub(r"\s+", " ", render_spatial_prompt_block(shot, spatial_map)).strip().casefold()
        actual = re.sub(r"\s+", " ", text).strip().casefold()
        if expected not in actual:
            report.error(
                "SPATIAL_PROMPT",
                f"Shot {shot_id} LOCATION / SPATIAL MAP section must contain the deterministic facts rendered from manifests/spatial.json.",
            )


def validate_approved_asset_reference(
    reference_id: Any,
    where: str,
    assets: dict[str, dict[str, Any]],
    report: Report,
    allowed_types: set[str] | None = None,
) -> None:
    if reference_id in (None, ""):
        return
    if not isinstance(reference_id, str):
        report.error("TYPE", f"{where} must be an asset id string.")
        return
    asset = assets.get(reference_id)
    if asset is None:
        report.error("MISSING_REFERENCE", f"{where} references missing asset {reference_id}.")
        return
    if asset.get("status") != "approved":
        report.error("UNAPPROVED_REFERENCE", f"{where} references non-approved asset {reference_id}.")
    if allowed_types is not None and asset.get("type") not in allowed_types:
        report.error("REFERENCE_TYPE", f"{where} references {reference_id} with incompatible type {asset.get('type')}.")
    if asset.get("type") in AUTHENTIC_ASSET_TYPES and (
        not photographic_qa_passed(asset)
        or not authenticity_passed(asset, require_user_approval=True)
        or not texture_qa_passed(asset, require_user_approval=True)
        or not geometry_qa_passed(asset, require_user_approval=True)
        or not live_action_surface_passed(asset, require_user_approval=True)
    ):
        report.error(
            "AUTHENTICITY_GATE",
            f"{where} references asset {reference_id} that has not passed photographic, geometry, and unified live-action-quality gates.",
        )


def location_reference_has_multiview_coverage(
    asset_id: Any, assets: dict[str, dict[str, Any]]
) -> bool:
    if not isinstance(asset_id, str) or not asset_id:
        return False
    pending = [asset_id]
    seen: set[str] = set()
    while pending:
        current_id = pending.pop()
        if current_id in seen:
            continue
        seen.add(current_id)
        asset = assets.get(current_id)
        if not isinstance(asset, dict):
            continue
        coverage = asset.get("reference_coverage")
        if (
            asset.get("status") == "approved"
            and isinstance(coverage, dict)
            and coverage.get("policy") == "location_multiview"
            and coverage.get("same_subject_or_geography_pass") is True
            and LOCATION_MULTIVIEW_VIEWS.issubset(set(coverage.get("present_views", [])))
        ):
            return True
        derived_from = asset.get("derived_from")
        if isinstance(derived_from, str) and derived_from:
            pending.append(derived_from)
        reference_ids = asset.get("reference_asset_ids")
        if isinstance(reference_ids, list):
            pending.extend(reference_id for reference_id in reference_ids if isinstance(reference_id, str))
    return False


def _validate_approval_qa(
    qa: Any,
    where: str,
    status: str,
    check_names: tuple[str, ...],
    report: Report,
) -> bool:
    required = ("checks", "hard_failures", "notes", "checked_at", "reviewer")
    if not require_keys(qa, required, where, report):
        return False
    checks = qa.get("checks")
    if require_keys(checks, check_names, f"{where}.checks", report):
        for name in check_names:
            if not isinstance(checks.get(name), bool):
                report.error("TYPE", f"{where}.checks.{name} must be boolean.")
    require_string_list(qa.get("hard_failures"), f"{where}.hard_failures", report)
    require_string_list(qa.get("notes"), f"{where}.notes", report)
    if "user_decision" in qa or "user_decided_at" in qa:
        report.error("APPROVAL_SCOPE", f"{where} must not contain user decisions; use manifests/reviews.json.")
    require_string(qa.get("checked_at"), f"{where}.checked_at", report, allow_empty=True)
    if qa.get("reviewer") not in {"codex-visual", "codex-structural"}:
        report.error("ENUM", f"{where}.reviewer must be codex-visual or codex-structural.")
    passed = (
        isinstance(checks, dict)
        and all(checks.get(name) is True for name in check_names)
        and not qa.get("hard_failures")
        and valid_timestamp(qa.get("checked_at"))
    )
    if status == "approved":
        if not passed:
            report.error("APPROVAL", f"Approved record {where} has not passed its internal checks.")
    return passed


def _validate_role_physique(
    pack_id: str,
    brief: Any,
    fit_qa: Any,
    proportion_signature: Any,
    status: str,
    where: str,
    report: Report,
) -> None:
    """Validate role-specific body design without imposing one universal ideal."""
    fields = (
        "id", "classification", "source", "narrative_rationale", "age_presentation",
        "stature_and_frame", "shoulder_waist_hip_relation", "muscle_and_fat_distribution",
        "posture_and_gait", "wardrobe_silhouette", "must_have_traits",
        "candidate_rejection_criteria", "quantitative_targets", "visual_body_balance",
    )
    if not require_keys(brief, fields, f"{where}.role_physique_brief", report):
        return
    require_string(brief.get("id"), f"{where}.role_physique_brief.id", report)
    if brief.get("classification") not in PHYSIQUE_CLASSIFICATIONS:
        report.error("ENUM", f"{where}.role_physique_brief.classification is invalid: {brief.get('classification')}")
    if brief.get("source") not in PHYSIQUE_BRIEF_SOURCES:
        report.error("ENUM", f"{where}.role_physique_brief.source is invalid: {brief.get('source')}")
    for field in (
        "narrative_rationale", "age_presentation", "stature_and_frame",
        "shoulder_waist_hip_relation", "muscle_and_fat_distribution",
        "posture_and_gait", "wardrobe_silhouette",
    ):
        require_string(brief.get(field), f"{where}.role_physique_brief.{field}", report)
    require_string_list(brief.get("must_have_traits"), f"{where}.role_physique_brief.must_have_traits", report)
    require_string_list(
        brief.get("candidate_rejection_criteria"),
        f"{where}.role_physique_brief.candidate_rejection_criteria",
        report,
    )
    balance = brief.get("visual_body_balance")
    balance_where = f"{where}.role_physique_brief.visual_body_balance"
    balance_fields = (
        "target", "measurement_basis", "upper_body_share_range", "lower_body_share_range",
        "perspective_policy", "story_exception",
    )
    if require_keys(balance, balance_fields, balance_where, report):
        target = balance.get("target")
        if target not in VISUAL_BODY_BALANCE_TARGETS:
            report.error("ENUM", f"{balance_where}.target is invalid: {target}")
        require_string(balance.get("measurement_basis"), f"{balance_where}.measurement_basis", report)
        if balance.get("perspective_policy") != "natural_perspective_only":
            report.error(
                "PHYSIQUE_BALANCE",
                f"{balance_where}.perspective_policy must be natural_perspective_only; low-angle or wide-angle leg stretching is not an authority measurement.",
            )
        require_string(
            balance.get("story_exception"),
            f"{balance_where}.story_exception",
            report,
            allow_empty=target != "story_exception",
        )
        ranges: dict[str, tuple[float, float]] = {}
        for field in ("upper_body_share_range", "lower_body_share_range"):
            value = balance.get(field)
            if (
                not isinstance(value, list)
                or len(value) != 2
                or not all(is_number(item) for item in value)
                or not 0 < float(value[0]) <= float(value[1]) < 1
            ):
                report.error("PHYSIQUE_BALANCE", f"{balance_where}.{field} must be a two-number normalized range inside 0..1.")
                continue
            ranges[field] = (float(value[0]), float(value[1]))
        if len(ranges) == 2:
            upper_midpoint = sum(ranges["upper_body_share_range"]) / 2
            lower_midpoint = sum(ranges["lower_body_share_range"]) / 2
            if abs((upper_midpoint + lower_midpoint) - 1.0) > 0.08:
                report.error("PHYSIQUE_BALANCE", f"{balance_where} upper/lower visual ranges must describe one coherent standing silhouette.")
            lower_minimum, lower_maximum = ranges["lower_body_share_range"]
            if target == "balanced_four_six" and (lower_minimum < 0.54 or lower_maximum > 0.64):
                report.error("PHYSIQUE_BALANCE", f"{balance_where} balanced_four_six requires a lower-body visual share within 0.54..0.64.")
            if target == "elongated_three_seven" and (lower_minimum < 0.60 or lower_maximum > 0.70):
                report.error("PHYSIQUE_BALANCE", f"{balance_where} elongated_three_seven requires a lower-body visual share within 0.60..0.70.")
            if target in {"balanced_four_six", "elongated_three_seven"} and lower_maximum <= 0.54:
                report.error("PHYSIQUE_BALANCE", f"Identity pack {pack_id} has an unintended five-five visual balance.")
    targets = brief.get("quantitative_targets")
    if not isinstance(targets, list):
        report.error("TYPE", f"{where}.role_physique_brief.quantitative_targets must be an array.")
        targets = []
    seen_metrics: set[str] = set()
    signature_ratios = proportion_signature.get("ratios") if isinstance(proportion_signature, dict) and isinstance(proportion_signature.get("ratios"), dict) else {}
    for index, target in enumerate(targets):
        target_where = f"{where}.role_physique_brief.quantitative_targets[{index}]"
        if not require_keys(target, ("metric", "minimum", "maximum", "unit", "rationale"), target_where, report):
            continue
        metric = target.get("metric")
        if not require_string(metric, f"{target_where}.metric", report):
            continue
        if metric in seen_metrics:
            report.error("DUPLICATE_ID", f"Role physique brief {pack_id} repeats target metric {metric}.")
        seen_metrics.add(metric)
        if metric not in PROPORTION_RATIO_FIELDS:
            report.error("PHYSIQUE_TARGET", f"Unsupported role-physique metric: {metric}")
        minimum = target.get("minimum")
        maximum = target.get("maximum")
        if not is_number(minimum) or not is_number(maximum) or float(minimum) > float(maximum):
            report.error("PHYSIQUE_TARGET", f"{target_where} requires numeric minimum <= maximum.")
        if target.get("unit") not in PHYSIQUE_TARGET_UNITS:
            report.error("ENUM", f"{target_where}.unit is invalid: {target.get('unit')}")
        require_string(target.get("rationale"), f"{target_where}.rationale", report)
        observed = signature_ratios.get(metric)
        if metric in PROPORTION_RATIO_FIELDS and is_number(observed) and is_number(minimum) and is_number(maximum):
            if not float(minimum) <= float(observed) <= float(maximum):
                report.error(
                    "PHYSIQUE_MISMATCH",
                    f"Identity pack {pack_id} measured {metric}={observed} outside its role target [{minimum}, {maximum}].",
                )
    if brief.get("classification") in TARGET_DRIVEN_PHYSIQUE_CLASSIFICATIONS:
        if len(targets) < 2 or len(brief.get("candidate_rejection_criteria", [])) < 2:
            report.error(
                "PHYSIQUE_TARGET",
                f"Target-driven identity {pack_id} needs at least two measurable targets and two explicit candidate rejection criteria.",
            )

    qa_fields = ("checks", "verdict", "hard_failures", "notes", "checked_at", "reviewer")
    if not require_keys(fit_qa, qa_fields, f"{where}.physique_fit_qa", report):
        return
    checks = fit_qa.get("checks")
    if require_keys(checks, PHYSIQUE_FIT_CHECKS, f"{where}.physique_fit_qa.checks", report):
        for check in PHYSIQUE_FIT_CHECKS:
            if not isinstance(checks.get(check), bool):
                report.error("TYPE", f"{where}.physique_fit_qa.checks.{check} must be boolean.")
    if fit_qa.get("verdict") not in {"pending", "pass", "fail"}:
        report.error("ENUM", f"{where}.physique_fit_qa.verdict is invalid: {fit_qa.get('verdict')}")
    require_string_list(fit_qa.get("hard_failures"), f"{where}.physique_fit_qa.hard_failures", report)
    require_string_list(fit_qa.get("notes"), f"{where}.physique_fit_qa.notes", report)
    if fit_qa.get("reviewer") not in {"codex-visual", "codex-structural"}:
        report.error("ENUM", f"{where}.physique_fit_qa.reviewer is invalid.")
    passed = (
        isinstance(checks, dict)
        and all(checks.get(check) is True for check in PHYSIQUE_FIT_CHECKS)
        and fit_qa.get("verdict") == "pass"
        and not fit_qa.get("hard_failures")
        and valid_timestamp(fit_qa.get("checked_at"))
    )
    if status in {"qualified", "approved"} and not passed:
        report.error("PHYSIQUE_GATE", f"Identity pack {pack_id} has not passed its role-conditioned physique gate.")


def validate_identities(
    project_dir: Path,
    data: dict[str, Any] | None,
    assets: dict[str, dict[str, Any]],
    report: Report,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    packs: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}
    if data is None:
        return packs, states
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/identities.json.schema_version must be {SCHEMA_VERSION}.")
    pack_rows = data.get("identity_packs")
    state_rows = data.get("character_states", [])
    if not isinstance(pack_rows, list):
        report.error("TYPE", "manifests/identities.json.identity_packs must be an array.")
        pack_rows = []
    if not isinstance(state_rows, list):
        report.error("TYPE", "manifests/identities.json.character_states must be an array.")
        state_rows = []
    root_to_pack: dict[str, str] = {}

    for index, pack in enumerate(pack_rows):
        where = f"manifests/identities.json.identity_packs[{index}]"
        required = (
            "id", "status", "identity_kind", "identity_inspector_asset_id", "identity_view_asset_ids", "face_anchor_asset_id",
            "body_anchor_asset_id", "role_physique_brief", "physique_fit_qa",
            "proportion_signature", "skeletal_lock", "immutable_identity",
            "reference_board", "character_state_ids", "approval_gate_id", "qa",
        )
        if not require_keys(pack, required, where, report):
            continue
        pack_id = pack.get("id")
        if not require_string(pack_id, f"{where}.id", report):
            continue
        if pack_id in packs:
            report.error("DUPLICATE_ID", f"Duplicate identity pack id: {pack_id}")
        packs[pack_id] = pack
        status = pack.get("status")
        if status not in IDENTITY_PACK_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        if pack.get("identity_kind") not in IDENTITY_KINDS:
            report.error("ENUM", f"{where}.identity_kind is invalid: {pack.get('identity_kind')}")
        require_string(pack.get("approval_gate_id"), f"{where}.approval_gate_id", report)

        inspector_id = pack.get("identity_inspector_asset_id")
        require_string(inspector_id, f"{where}.identity_inspector_asset_id", report)
        inspector = assets.get(inspector_id) if isinstance(inspector_id, str) else None
        if not isinstance(inspector, dict) or inspector.get("type") != "character_identity_inspector":
            report.error("IDENTITY_INSPECTOR", f"Identity pack {pack_id} requires one unified character_identity_inspector authority.")
            inspector = {}
        else:
            if inspector_id in root_to_pack:
                report.error("IDENTITY_AUTHORITY", f"Identity inspector {inspector_id} belongs to more than one identity pack.")
            root_to_pack[str(inspector_id)] = str(pack_id)
            if inspector.get("identity_pack_id") != pack_id:
                report.error("IDENTITY_AUTHORITY", f"Identity inspector {inspector_id} must bind identity pack {pack_id}.")
            if inspector.get("generator") != "builtin-imagegen" or inspector.get("mode") != "generate" or inspector.get("derived_from"):
                report.error("IDENTITY_INSPECTOR", f"Identity inspector {inspector_id} must be one independent built-in ImageGen generation.")
            if inspector.get("root_reference_ids"):
                report.error("IDENTITY_INSPECTOR", f"Identity inspector {inspector_id} is the first generated identity authority and cannot name another generated identity root.")
            if status in {"qualified", "approved"}:
                allowed_statuses = {"qualified", "approved"} if status == "qualified" else {"approved"}
                if inspector.get("status") not in allowed_statuses:
                    report.error("IDENTITY_GATE", f"Identity pack {pack_id} status={status} requires an equally approved inspector authority.")
                if inspector.get("approval_gate_id") != pack.get("approval_gate_id"):
                    report.error("REVIEW_GATE", f"Identity inspector {inspector_id} and pack {pack_id} must share the Foundation gate.")
                if (
                    not texture_qa_passed(inspector, require_user_approval=False)
                    or not geometry_qa_passed(inspector, require_user_approval=False)
                    or not live_action_surface_passed(inspector, require_user_approval=False)
                ):
                    report.error("IDENTITY_GATE", f"Identity inspector {inspector_id} has not passed whole-board identity, geometry and clean live-action QA.")
            if inspector.get("status") == "model_blocked" and status != "model_blocked":
                report.error("IDENTITY_GATE", f"A failed single-solve inspector must stop identity pack {pack_id} as model_blocked.")

        view_map = pack.get("identity_view_asset_ids")
        if not isinstance(view_map, dict):
            report.error("IDENTITY_VIEW", f"{where}.identity_view_asset_ids must map the seven canonical roles to assets.")
            view_map = {}
        missing_roles = [role for role in IDENTITY_VIEW_ROLES if role not in view_map]
        extra_roles = sorted(set(view_map) - set(IDENTITY_VIEW_ROLES))
        if missing_roles or extra_roles:
            report.error(
                "IDENTITY_VIEW",
                f"Identity pack {pack_id} requires exactly seven canonical roles; missing={missing_roles}, extra={extra_roles}.",
            )
        ordered_roots = [view_map.get(role) for role in IDENTITY_VIEW_ROLES]
        valid_root_ids = [asset_id for asset_id in ordered_roots if isinstance(asset_id, str) and asset_id]
        if len(valid_root_ids) != 7 or len(set(valid_root_ids)) != 7:
            report.error("IDENTITY_VIEW", f"Identity pack {pack_id} requires seven distinct deterministic crop asset ids.")
        if pack.get("face_anchor_asset_id") != view_map.get("portrait_front"):
            report.error("IDENTITY_AUTHORITY", f"Identity pack {pack_id} face anchor must alias portrait_front.")
        if pack.get("body_anchor_asset_id") != view_map.get("full_front"):
            report.error("IDENTITY_AUTHORITY", f"Identity pack {pack_id} body anchor must alias full_front.")
        for role, asset_id in ((role, view_map.get(role)) for role in IDENTITY_VIEW_ROLES):
            require_string(asset_id, f"{where}.identity_view_asset_ids.{role}", report)
            allowed_type = (
                {"character_face_anchor"} if role == "portrait_front"
                else {"character_body_anchor"} if role == "full_front"
                else {"character_identity_view"}
            )
            if not isinstance(asset_id, str) or not asset_id:
                continue
            asset = assets.get(asset_id, {})
            if not asset or asset.get("type") not in allowed_type:
                report.error("IDENTITY_VIEW", f"Identity crop {asset_id} has the wrong type for {role}.")
                continue
            if asset.get("identity_pack_id") != pack_id or asset.get("identity_view_role") != role:
                report.error("IDENTITY_AUTHORITY", f"Identity crop {asset_id} must bind {pack_id}/{role}.")
            if asset.get("generator") != "deterministic-crop" or asset.get("mode") != "crop":
                report.error("IDENTITY_CROP", f"Identity crop {asset_id} must be produced by deterministic-crop, never a separate generation.")
            if asset.get("derived_from") != inspector_id or asset.get("root_reference_ids") != [inspector_id] or asset.get("reference_asset_ids") != [inspector_id]:
                report.error("IDENTITY_CROP", f"Identity crop {asset_id} must derive directly and only from unified inspector {inspector_id}.")
            if status in {"qualified", "approved"}:
                allowed_statuses = {"qualified", "approved"} if status == "qualified" else {"approved"}
                if asset.get("status") not in allowed_statuses:
                    report.error("IDENTITY_GATE", f"Identity pack {pack_id} status={status} requires completed crop {asset_id}.")
                if (
                    not texture_qa_passed(asset, require_user_approval=False)
                    or not geometry_qa_passed(asset, require_user_approval=False)
                    or not live_action_surface_passed(asset, require_user_approval=False)
                ):
                    report.error("IDENTITY_GATE", f"Identity crop {asset_id} does not inherit a passing inspector QA record.")

        signature = pack.get("proportion_signature")
        signature_fields = (
            "id", "normalization", "measurement_asset_ids", "projection_classes", "confidence",
            "ratios", "tolerances", "intentional_asymmetries", "expected_digit_topology",
        )
        if require_keys(signature, signature_fields, f"{where}.proportion_signature", report):
            require_string(signature.get("id"), f"{where}.proportion_signature.id", report)
            if signature.get("normalization") != "standing_height_1.0":
                report.error("PROPORTION_SIGNATURE", f"Identity pack {pack_id} must normalize proportions to standing_height_1.0.")
            measurement_ids = signature.get("measurement_asset_ids")
            require_string_list(measurement_ids, f"{where}.proportion_signature.measurement_asset_ids", report)
            expected_measurements = [view_map.get("full_front"), view_map.get("full_back")]
            if measurement_ids != expected_measurements:
                report.error("PROPORTION_SIGNATURE", f"Identity pack {pack_id} proportion measurements must use full_front then full_back.")
            projections = signature.get("projection_classes")
            if not isinstance(projections, dict) or any(
                projections.get(role) not in {"measurement", "silhouette_confirmation"}
                for role in IDENTITY_VIEW_ROLES
            ):
                report.error("PROPORTION_SIGNATURE", f"Identity pack {pack_id} requires a projection class for every view.")
            if is_number(signature.get("confidence")):
                if not 0 <= float(signature.get("confidence")) <= 1:
                    report.error("PROPORTION_SIGNATURE", f"Identity pack {pack_id} confidence must be between 0 and 1.")
            else:
                report.error("TYPE", f"{where}.proportion_signature.confidence must be numeric.")
            ratios = signature.get("ratios")
            tolerances = signature.get("tolerances")
            if require_keys(ratios, PROPORTION_RATIO_FIELDS, f"{where}.proportion_signature.ratios", report):
                for field in PROPORTION_RATIO_FIELDS:
                    if not is_number(ratios.get(field)) or float(ratios.get(field)) <= 0:
                        report.error("PROPORTION_SIGNATURE", f"{where}.proportion_signature.ratios.{field} must be positive.")
            if require_keys(tolerances, PROPORTION_RATIO_FIELDS, f"{where}.proportion_signature.tolerances", report):
                for field in PROPORTION_RATIO_FIELDS:
                    value = tolerances.get(field)
                    if not is_number(value) or not 0 <= float(value) <= 0.15:
                        report.error("PROPORTION_SIGNATURE", f"{where}.proportion_signature.tolerances.{field} must be between 0 and 0.15.")
            require_string_list(signature.get("intentional_asymmetries"), f"{where}.proportion_signature.intentional_asymmetries", report)
            digit_topology = signature.get("expected_digit_topology")
            if require_keys(digit_topology, ("left_hand", "right_hand", "left_foot", "right_foot"), f"{where}.proportion_signature.expected_digit_topology", report):
                for field in ("left_hand", "right_hand", "left_foot", "right_foot"):
                    if not is_integer(digit_topology.get(field)) or digit_topology.get(field) < 0:
                        report.error("PROPORTION_SIGNATURE", f"{where}.proportion_signature.expected_digit_topology.{field} must be a non-negative integer.")
            if "user_approved_at" in signature:
                report.error("APPROVAL_SCOPE", f"Identity pack {pack_id} proportion approval belongs in manifests/reviews.json.")

        _validate_role_physique(
            str(pack_id), pack.get("role_physique_brief"), pack.get("physique_fit_qa"),
            signature, str(status), where, report,
        )

        skeletal = pack.get("skeletal_lock")
        if require_keys(skeletal, ("locked", "soft_tissue_delta_allowed", "notes"), f"{where}.skeletal_lock", report):
            if skeletal.get("locked") is not True:
                report.error("PROPORTION_DRIFT", f"Identity pack {pack_id} skeletal_lock.locked must be true.")
            require_string_list(skeletal.get("soft_tissue_delta_allowed"), f"{where}.skeletal_lock.soft_tissue_delta_allowed", report)
            require_string_list(skeletal.get("notes"), f"{where}.skeletal_lock.notes", report)
        immutable = pack.get("immutable_identity")
        if require_keys(immutable, IMMUTABLE_IDENTITY_FIELDS, f"{where}.immutable_identity", report):
            for field in IMMUTABLE_IDENTITY_FIELDS:
                require_string(immutable.get(field), f"{where}.immutable_identity.{field}", report)
        board = pack.get("reference_board")
        if require_keys(
            board,
            ("status", "relative_path", "sha256", "source_sha256s", "layout_profile", "authoritative", "crop_map_path"),
            f"{where}.reference_board",
            report,
        ):
            if board.get("status") not in {"planned", "ready"}:
                report.error("ENUM", f"{where}.reference_board.status is invalid: {board.get('status')}")
            require_string(board.get("relative_path"), f"{where}.reference_board.relative_path", report, allow_empty=True)
            require_string(board.get("sha256"), f"{where}.reference_board.sha256", report, allow_empty=True)
            require_string(board.get("crop_map_path"), f"{where}.reference_board.crop_map_path", report, allow_empty=True)
            if not isinstance(board.get("source_sha256s"), dict):
                report.error("TYPE", f"{where}.reference_board.source_sha256s must be an object.")
            require_string(board.get("layout_profile"), f"{where}.reference_board.layout_profile", report)
            if board.get("authoritative") not in {True, False}:
                report.error("TYPE", f"{where}.reference_board.authoritative must be boolean.")
            if status in {"qualified", "approved"} and board.get("status") != "ready":
                report.error("IDENTITY_GATE", f"Identity pack {pack_id} cannot proceed until the unified board is ready and its seven crops exist.")
            if board.get("status") == "ready":
                board_path = check_relative_file(
                    project_dir,
                    board.get("relative_path"),
                    f"{where}.reference_board.relative_path",
                    report,
                    required=True,
                )
                digest = board.get("sha256")
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    report.error("REFERENCE_BOARD", f"{where}.reference_board.sha256 must be a lowercase SHA-256 digest.")
                elif board_path is not None and hashlib.sha256(board_path.read_bytes()).hexdigest() != digest:
                    report.error("REFERENCE_BOARD", f"Identity pack {pack_id} reference-board SHA-256 does not match its file.")
                inspector_output = inspector.get("generation_provenance", {}).get("output", {}) if isinstance(inspector, dict) else {}
                if board.get("relative_path") != inspector_output.get("relative_path") or digest != inspector_output.get("sha256"):
                    report.error("REFERENCE_BOARD", f"Identity pack {pack_id} board must be the exact unified inspector output, not a recomposed image.")
                source_hashes = board.get("source_sha256s")
                if not isinstance(source_hashes, dict) or set(source_hashes) != set(IDENTITY_VIEW_ROLES):
                    report.error("REFERENCE_BOARD", f"Identity pack {pack_id} board must record one source hash for each canonical view.")
                else:
                    for role, asset_id in ((role, view_map.get(role)) for role in IDENTITY_VIEW_ROLES):
                        source_asset = assets.get(asset_id, {}) if isinstance(asset_id, str) else {}
                        output = source_asset.get("generation_provenance", {}).get("output", {})
                        expected_hash = output.get("sha256") if isinstance(output, dict) else None
                        if source_hashes.get(role) != expected_hash:
                            report.error("REFERENCE_BOARD", f"Identity pack {pack_id} board source hash for {role} does not match the authority asset.")
                if board.get("layout_profile") != "higgsfield-character-reference-sheet-two-row-single-solve-v1.6":
                    report.error("REFERENCE_BOARD", f"Identity pack {pack_id} board uses an unsupported layout profile.")
                if board.get("authoritative") is not True:
                    report.error("REFERENCE_BOARD", f"Identity pack {pack_id} unified board must be authoritative.")
                check_relative_file(
                    project_dir,
                    board.get("crop_map_path"),
                    f"{where}.reference_board.crop_map_path",
                    report,
                    required=True,
                )
        require_string_list(pack.get("character_state_ids"), f"{where}.character_state_ids", report)
        _validate_approval_qa(
            pack.get("qa"), f"{where}.qa", str(status),
            ("face_identity", "single_solve_identity_board", "seven_deterministic_crops", "role_conditioned_physique", "proportion_signature", "joint_topology", "clean_texture", "live_action_surface"), report,
        )

    for index, state in enumerate(state_rows):
        where = f"manifests/identities.json.character_states[{index}]"
        required = (
            "id", "status", "identity_pack_id", "authority_asset_id", "state_delta", "soft_tissue_delta",
            "preserve_immutable", "preserve_proportion_signature", "preserve_role_physique",
            "first_visible_shot_id", "cause", "approval_gate_id", "qa",
        )
        if not require_keys(state, required, where, report):
            continue
        state_id = state.get("id")
        if not require_string(state_id, f"{where}.id", report):
            continue
        if state_id in states:
            report.error("DUPLICATE_ID", f"Duplicate character state id: {state_id}")
        states[state_id] = state
        status = state.get("status")
        if status not in LOCATION_STATE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(state.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        pack_id = state.get("identity_pack_id")
        pack = packs.get(pack_id) if isinstance(pack_id, str) else None
        if pack is None:
            report.error("MISSING_REFERENCE", f"Character state {state_id} references missing identity pack {pack_id}.")
        elif status == "approved" and pack.get("status") != "approved":
            report.error("UNAPPROVED_REFERENCE", f"Approved character state {state_id} requires approved identity pack {pack_id}.")
        authority_id = state.get("authority_asset_id")
        require_string(authority_id, f"{where}.authority_asset_id", report)
        validate_approved_asset_reference(authority_id, f"Character state {state_id} authority", assets, report, {"character_state"})
        authority = assets.get(authority_id, {}) if isinstance(authority_id, str) else {}
        if authority:
            if authority.get("character_state_id") != state_id or authority.get("identity_pack_id") != pack_id:
                report.error("STATE_BINDING", f"Character state asset {authority_id} does not bind {pack_id}/{state_id}.")
            if authority.get("derived_from"):
                report.error("RECURSIVE_STATE", f"Character state authority {authority_id} must be independently generated from roots.")
            expected_roots = [pack.get("identity_inspector_asset_id")] if isinstance(pack, dict) else []
            if authority.get("root_reference_ids") != expected_roots:
                report.error("ROOT_REFERENCE", f"Character state {state_id} must reference the unified identity inspector as its first and only identity root.")
            if authority.get("state_delta") != state.get("state_delta"):
                report.error("STATE_DELTA", f"Character state {state_id} asset delta conflicts with identities manifest.")
        if not isinstance(state.get("state_delta"), dict) or not state.get("state_delta"):
            report.error("STATE_DELTA", f"Character state {state_id} requires a non-empty state_delta.")
        soft_delta = state.get("soft_tissue_delta")
        if require_keys(
            soft_delta,
            ("kind", "extent", "cause", "first_visible_shot_id", "preserve_skeleton"),
            f"{where}.soft_tissue_delta",
            report,
        ):
            for field in ("kind", "extent", "cause", "first_visible_shot_id"):
                require_string(soft_delta.get(field), f"{where}.soft_tissue_delta.{field}", report, allow_empty=field == "first_visible_shot_id")
            if soft_delta.get("preserve_skeleton") is not True:
                report.error("PROPORTION_DRIFT", f"Character state {state_id} soft-tissue delta must preserve the skeleton.")
        if state.get("preserve_proportion_signature") is not True:
            report.error("PROPORTION_DRIFT", f"Character state {state_id} must preserve the approved proportion signature.")
        if state.get("preserve_role_physique") is not True:
            report.error("PHYSIQUE_DRIFT", f"Character state {state_id} must preserve the approved role-conditioned physique unless its declared soft-tissue delta explicitly changes it.")
        preserve = state.get("preserve_immutable")
        if not isinstance(preserve, dict):
            report.error("TYPE", f"{where}.preserve_immutable must be an object.")
        else:
            for field in IMMUTABLE_IDENTITY_FIELDS:
                if preserve.get(field) is not True:
                    report.error("IMMUTABLE_IDENTITY", f"Character state {state_id} must preserve {field}.")
            unauthorized = set(state.get("state_delta", {})) & (set(IMMUTABLE_IDENTITY_FIELDS) | {"role_physique_brief", "proportion_signature", "skeletal_lock"})
            if unauthorized:
                report.error("IMMUTABLE_IDENTITY", f"Character state {state_id} changes immutable fields: {', '.join(sorted(unauthorized))}.")
        require_string(state.get("first_visible_shot_id"), f"{where}.first_visible_shot_id", report, allow_empty=True)
        require_string(state.get("cause"), f"{where}.cause", report)
        _validate_approval_qa(
            state.get("qa"), f"{where}.qa", str(status),
            ("root_traceability", "immutable_identity", "role_conditioned_physique", "proportion_signature", "soft_tissue_delta", "anatomy", "clean_texture", "live_action_surface"), report,
        )

    for pack_id, pack in packs.items():
        declared = pack.get("character_state_ids") if isinstance(pack.get("character_state_ids"), list) else []
        actual = sorted(state_id for state_id, state in states.items() if state.get("identity_pack_id") == pack_id)
        if sorted(declared) != actual:
            report.error("STATE_BINDING", f"Identity pack {pack_id} character_state_ids do not match character state records.")
    authority_state_ids = {state.get("authority_asset_id"): state_id for state_id, state in states.items()}
    for asset_id, asset in assets.items():
        if asset.get("type") != "character_state" or asset.get("status") in {"planned", "model_blocked"}:
            continue
        state_id = asset.get("character_state_id")
        if state_id not in states or authority_state_ids.get(asset_id) != state_id:
            report.error("STATE_BINDING", f"Character-state asset {asset_id} is not the declared authority for {state_id}.")
    return packs, states


def validate_world_state(
    data: dict[str, Any] | None,
    assets: dict[str, dict[str, Any]],
    report: Report,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    worlds: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}
    prop_states: dict[str, dict[str, Any]] = {}
    environmental_states: dict[str, dict[str, Any]] = {}
    special_lighting_events: dict[str, dict[str, Any]] = {}
    if data is None:
        return worlds, states, prop_states, environmental_states, special_lighting_events
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/world-state.json.schema_version must be {SCHEMA_VERSION}.")
    dna = data.get("production_design_dna")
    dna_fields = (
        "period", "socioeconomic_context", "architecture_logic", "color_sources", "material_rules",
        "public_infrastructure", "signage_policy", "ageing_policy",
    )
    if require_keys(dna, dna_fields, "manifests/world-state.json.production_design_dna", report):
        for field in ("period", "socioeconomic_context", "architecture_logic", "signage_policy", "ageing_policy"):
            require_string(dna.get(field), f"production_design_dna.{field}", report, allow_empty=True)
        for field in ("color_sources", "material_rules", "public_infrastructure"):
            require_string_list(dna.get(field), f"production_design_dna.{field}", report)
    world_rows = data.get("location_worlds")
    state_rows = data.get("location_states")
    prop_rows = data.get("prop_states")
    environment_rows = data.get("environmental_states")
    special_light_rows = data.get("special_lighting_events")
    for value, label in (
        (world_rows, "location_worlds"),
        (state_rows, "location_states"),
        (prop_rows, "prop_states"),
        (environment_rows, "environmental_states"),
        (special_light_rows, "special_lighting_events"),
    ):
        if not isinstance(value, list):
            report.error("TYPE", f"manifests/world-state.json.{label} must be an array.")
    world_rows = world_rows if isinstance(world_rows, list) else []
    state_rows = state_rows if isinstance(state_rows, list) else []
    prop_rows = prop_rows if isinstance(prop_rows, list) else []
    environment_rows = environment_rows if isinstance(environment_rows, list) else []
    special_light_rows = special_light_rows if isinstance(special_light_rows, list) else []
    invariant_fields = (
        "topology", "openings", "fixed_facilities", "primary_anchor_asset_id", "scale_relations", "material_baseline"
    )
    for index, world in enumerate(world_rows):
        where = f"manifests/world-state.json.location_worlds[{index}]"
        if not require_keys(world, ("id", "status", "location_master_asset_id", "immutable_world", "location_state_ids", "approval_gate_id", "qa"), where, report):
            continue
        world_id = world.get("id")
        if not require_string(world_id, f"{where}.id", report):
            continue
        if world_id in worlds:
            report.error("DUPLICATE_ID", f"Duplicate location world id: {world_id}")
        worlds[world_id] = world
        status = world.get("status")
        if status not in LOCATION_WORLD_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(world.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        master_id = world.get("location_master_asset_id")
        require_string(master_id, f"{where}.location_master_asset_id", report)
        validate_approved_asset_reference(master_id, f"Location world {world_id} master", assets, report, {"location_master"})
        master = assets.get(master_id, {}) if isinstance(master_id, str) else {}
        if master and master.get("location_world_id") != world_id:
            report.error("WORLD_BINDING", f"Location master {master_id} must bind location_world_id={world_id}.")
        immutable = world.get("immutable_world")
        if require_keys(immutable, invariant_fields, f"{where}.immutable_world", report):
            for field in invariant_fields:
                if field == "primary_anchor_asset_id":
                    require_string(immutable.get(field), f"{where}.immutable_world.{field}", report)
                    validate_approved_asset_reference(immutable.get(field), f"Location world {world_id} anchor", assets, report, {"prop"})
                elif isinstance(immutable.get(field), list):
                    require_string_list(immutable.get(field), f"{where}.immutable_world.{field}", report)
                else:
                    require_string(immutable.get(field), f"{where}.immutable_world.{field}", report)
        require_string_list(world.get("location_state_ids"), f"{where}.location_state_ids", report)
        _validate_approval_qa(
            world.get("qa"), f"{where}.qa", str(status),
            ("topology", "openings", "fixed_facilities", "anchor_and_scale", "material_baseline", "clean_texture"), report,
        )

    for index, state in enumerate(state_rows):
        where = f"manifests/world-state.json.location_states[{index}]"
        required = (
            "id", "status", "location_world_id", "scene_ids", "authority_asset_ids", "state_delta",
            "environmental_state_id", "special_lighting_event_ids", "preserve_immutable",
            "first_visible_shot_id", "cause", "approval_gate_id", "qa",
        )
        if not require_keys(state, required, where, report):
            continue
        state_id = state.get("id")
        if not require_string(state_id, f"{where}.id", report):
            continue
        if state_id in states:
            report.error("DUPLICATE_ID", f"Duplicate location state id: {state_id}")
        states[state_id] = state
        status = state.get("status")
        if status not in LOCATION_STATE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(state.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        world_id = state.get("location_world_id")
        world = worlds.get(world_id) if isinstance(world_id, str) else None
        if world is None:
            report.error("MISSING_REFERENCE", f"Location state {state_id} references missing world {world_id}.")
        elif status == "approved" and world.get("status") != "approved":
            report.error("UNAPPROVED_REFERENCE", f"Approved location state {state_id} requires approved world {world_id}.")
        require_string_list(state.get("scene_ids"), f"{where}.scene_ids", report)
        require_string_list(state.get("authority_asset_ids"), f"{where}.authority_asset_ids", report)
        require_string(state.get("environmental_state_id"), f"{where}.environmental_state_id", report)
        require_string_list(state.get("special_lighting_event_ids"), f"{where}.special_lighting_event_ids", report)
        if status == "approved" and not state.get("authority_asset_ids"):
            report.error("STATE_BINDING", f"Approved location state {state_id} requires authority assets.")
        if not isinstance(state.get("state_delta"), dict) or not state.get("state_delta"):
            report.error("STATE_DELTA", f"Location state {state_id} requires a non-empty state_delta.")
        preserve = state.get("preserve_immutable")
        if not isinstance(preserve, dict):
            report.error("TYPE", f"{where}.preserve_immutable must be an object.")
        else:
            for field in invariant_fields:
                if preserve.get(field) is not True:
                    report.error("LOCATION_DRIFT", f"Location state {state_id} must preserve {field}.")
            unauthorized = set(state.get("state_delta", {})) & set(invariant_fields)
            if unauthorized:
                report.error("LOCATION_DRIFT", f"Location state {state_id} changes immutable world fields: {', '.join(sorted(unauthorized))}.")
        master_id = world.get("location_master_asset_id") if isinstance(world, dict) else ""
        for authority_id in state.get("authority_asset_ids", []) if isinstance(state.get("authority_asset_ids"), list) else []:
            validate_approved_asset_reference(authority_id, f"Location state {state_id} authority", assets, report, {"location_variant", "location_plate"})
            authority = assets.get(authority_id, {})
            if authority.get("location_world_id") != world_id or authority.get("location_state_id") != state_id:
                report.error("STATE_BINDING", f"Location-state asset {authority_id} does not bind {world_id}/{state_id}.")
            if authority.get("state_delta") != state.get("state_delta"):
                report.error("STATE_DELTA", f"Location-state asset {authority_id} delta conflicts with world-state manifest.")
            if authority.get("type") == "location_variant" and authority.get("derived_from") != master_id:
                report.error("RECURSIVE_STATE", f"Location-state view {authority_id} must derive directly from clean master {master_id}.")
            if authority.get("root_reference_ids") != [master_id]:
                report.error("ROOT_REFERENCE", f"Location-state asset {authority_id} must name only clean master {master_id} as root.")
        require_string(state.get("first_visible_shot_id"), f"{where}.first_visible_shot_id", report, allow_empty=True)
        require_string(state.get("cause"), f"{where}.cause", report)
        _validate_approval_qa(
            state.get("qa"), f"{where}.qa", str(status),
            ("root_traceability", "topology", "fixed_facilities", "anchor_and_scale", "delta_locality", "clean_texture"), report,
        )

    for index, state in enumerate(prop_rows):
        where = f"manifests/world-state.json.prop_states[{index}]"
        required = ("id", "status", "root_prop_asset_id", "authority_asset_id", "state_delta", "preserve_structure", "first_visible_shot_id", "cause", "approval_gate_id", "qa")
        if not require_keys(state, required, where, report):
            continue
        state_id = state.get("id")
        if not require_string(state_id, f"{where}.id", report):
            continue
        if state_id in prop_states:
            report.error("DUPLICATE_ID", f"Duplicate prop state id: {state_id}")
        prop_states[state_id] = state
        status = state.get("status")
        if status not in LOCATION_STATE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(state.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        root_id = state.get("root_prop_asset_id")
        authority_id = state.get("authority_asset_id")
        require_string(root_id, f"{where}.root_prop_asset_id", report)
        require_string(authority_id, f"{where}.authority_asset_id", report)
        validate_approved_asset_reference(root_id, f"Prop state {state_id} root", assets, report, {"prop", "vehicle", "animal"})
        validate_approved_asset_reference(authority_id, f"Prop state {state_id} authority", assets, report, {"prop_state"})
        authority = assets.get(authority_id, {}) if isinstance(authority_id, str) else {}
        if authority:
            if authority.get("root_reference_ids") != [root_id] or authority.get("derived_from"):
                report.error("RECURSIVE_STATE", f"Prop state {state_id} must be independently generated from clean prop root {root_id}.")
            if authority.get("state_delta") != state.get("state_delta"):
                report.error("STATE_DELTA", f"Prop state {state_id} asset delta conflicts with world-state manifest.")
        if not isinstance(state.get("state_delta"), dict) or not state.get("state_delta"):
            report.error("STATE_DELTA", f"Prop state {state_id} requires a non-empty state_delta.")
        if state.get("preserve_structure") is not True:
            report.error("PROP_DRIFT", f"Prop state {state_id} must preserve manufacturing structure and scale.")
        require_string(state.get("first_visible_shot_id"), f"{where}.first_visible_shot_id", report, allow_empty=True)
        require_string(state.get("cause"), f"{where}.cause", report)
        _validate_approval_qa(
            state.get("qa"), f"{where}.qa", str(status),
            ("root_traceability", "structure_and_scale", "delta_locality", "clean_texture"), report,
        )

    for index, environment in enumerate(environment_rows):
        where = f"manifests/world-state.json.environmental_states[{index}]"
        required = (
            "id", "status", "kind", "scene_ids", "source_cause", "intensity", "visibility_range_m",
            "particle_or_medium_scale", "direction", "wind", "accumulation", "material_interactions",
            "light_behavior", "focus_exposure_effect", "sound", "start_shot_id", "end_shot_id",
            "continuity_signature", "approval_gate_id", "qa",
        )
        if not require_keys(environment, required, where, report):
            continue
        environment_id = environment.get("id")
        if not require_string(environment_id, f"{where}.id", report):
            continue
        if environment_id in environmental_states:
            report.error("DUPLICATE_ID", f"Duplicate environmental state id: {environment_id}")
        environmental_states[environment_id] = environment
        status = environment.get("status")
        if status not in ENVIRONMENT_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(environment.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        if environment.get("kind") not in ENVIRONMENT_KINDS:
            report.error("ENUM", f"{where}.kind is invalid: {environment.get('kind')}")
        require_string_list(environment.get("scene_ids"), f"{where}.scene_ids", report)
        for field in (
            "source_cause", "intensity", "particle_or_medium_scale", "direction", "accumulation",
            "focus_exposure_effect", "continuity_signature",
        ):
            require_string(environment.get(field), f"{where}.{field}", report)
        visibility = environment.get("visibility_range_m")
        if not is_number(visibility) or visibility <= 0:
            report.error("ENVIRONMENT_PHYSICS", f"{where}.visibility_range_m must be positive.")
        wind = environment.get("wind")
        if require_keys(wind, ("direction", "speed_mps", "gust_mps"), f"{where}.wind", report):
            require_string(wind.get("direction"), f"{where}.wind.direction", report)
            if not is_number(wind.get("speed_mps")) or wind.get("speed_mps") < 0:
                report.error("ENVIRONMENT_PHYSICS", f"{where}.wind.speed_mps must be non-negative.")
            wind_speed = wind.get("speed_mps")
            gust_speed = wind.get("gust_mps")
            if not is_number(gust_speed) or (is_number(wind_speed) and gust_speed < wind_speed):
                report.error("ENVIRONMENT_PHYSICS", f"{where}.wind.gust_mps must be >= speed_mps.")
        require_string_list(environment.get("material_interactions"), f"{where}.material_interactions", report)
        light = environment.get("light_behavior")
        if require_keys(
            light,
            ("scattering_or_attenuation", "distance_behavior", "readability_source", "reflection_response"),
            f"{where}.light_behavior",
            report,
        ):
            for field in ("scattering_or_attenuation", "distance_behavior", "readability_source", "reflection_response"):
                require_string(light.get(field), f"{where}.light_behavior.{field}", report)
        require_string_list(environment.get("sound"), f"{where}.sound", report)
        require_string(environment.get("start_shot_id"), f"{where}.start_shot_id", report, allow_empty=True)
        require_string(environment.get("end_shot_id"), f"{where}.end_shot_id", report, allow_empty=True)
        _validate_approval_qa(environment.get("qa"), f"{where}.qa", str(status), ENVIRONMENT_QA_CHECKS, report)
        if status == "approved" and environment.get("kind") != "clear":
            if not environment.get("material_interactions"):
                report.error("ENVIRONMENT_PHYSICS", f"Environmental state {environment_id} requires material interactions.")
            if not environment.get("light_behavior", {}).get("distance_behavior"):
                report.error("ENVIRONMENT_PHYSICS", f"Environmental state {environment_id} requires distance-dependent light behavior.")

    for index, event in enumerate(special_light_rows):
        where = f"manifests/world-state.json.special_lighting_events[{index}]"
        required = (
            "id", "status", "scene_ids", "source", "cause", "position", "temporal_waveform",
            "duration_s", "exposure_response", "shadow_response", "reflection_response",
            "subject_environment_response", "white_balance_effect", "start_shot_id", "end_shot_id", "approval_gate_id", "qa",
        )
        if not require_keys(event, required, where, report):
            continue
        event_id = event.get("id")
        if not require_string(event_id, f"{where}.id", report):
            continue
        if event_id in special_lighting_events:
            report.error("DUPLICATE_ID", f"Duplicate special-light event id: {event_id}")
        special_lighting_events[event_id] = event
        status = event.get("status")
        if status not in ENVIRONMENT_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(event.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        require_string_list(event.get("scene_ids"), f"{where}.scene_ids", report)
        for field in (
            "source", "cause", "position", "temporal_waveform", "exposure_response", "shadow_response",
            "reflection_response", "subject_environment_response", "white_balance_effect",
        ):
            require_string(event.get(field), f"{where}.{field}", report)
        if not is_number(event.get("duration_s")) or event.get("duration_s") <= 0:
            report.error("SPECIAL_LIGHT", f"{where}.duration_s must be positive.")
        require_string(event.get("start_shot_id"), f"{where}.start_shot_id", report, allow_empty=True)
        require_string(event.get("end_shot_id"), f"{where}.end_shot_id", report, allow_empty=True)
        _validate_approval_qa(event.get("qa"), f"{where}.qa", str(status), SPECIAL_LIGHT_QA_CHECKS, report)

    for state_id, state in states.items():
        environment_id = state.get("environmental_state_id")
        environment = environmental_states.get(environment_id)
        if environment is None:
            report.error("MISSING_REFERENCE", f"Location state {state_id} references missing environmental state {environment_id}.")
        elif state.get("status") == "approved" and environment.get("status") != "approved":
            report.error("UNAPPROVED_REFERENCE", f"Approved location state {state_id} requires approved environmental state {environment_id}.")
        elif sorted(state.get("scene_ids", [])) != sorted(environment.get("scene_ids", [])):
            report.error("ENVIRONMENT_STATE", f"Location state {state_id} and environmental state {environment_id} must cover the same scenes.")
        for event_id in state.get("special_lighting_event_ids", []) if isinstance(state.get("special_lighting_event_ids"), list) else []:
            event = special_lighting_events.get(event_id)
            if event is None:
                report.error("MISSING_REFERENCE", f"Location state {state_id} references missing special-light event {event_id}.")
            elif state.get("status") == "approved" and event.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"Approved location state {state_id} requires approved special-light event {event_id}.")

    for world_id, world in worlds.items():
        declared = world.get("location_state_ids") if isinstance(world.get("location_state_ids"), list) else []
        actual = sorted(state_id for state_id, state in states.items() if state.get("location_world_id") == world_id)
        if sorted(declared) != actual:
            report.error("STATE_BINDING", f"Location world {world_id} location_state_ids do not match location state records.")
    location_authorities = {
        asset_id: state_id
        for state_id, state in states.items()
        for asset_id in state.get("authority_asset_ids", [])
        if isinstance(asset_id, str)
    }
    prop_authorities = {state.get("authority_asset_id"): state_id for state_id, state in prop_states.items()}
    for asset_id, asset in assets.items():
        if asset.get("status") in {"planned", "model_blocked"}:
            continue
        if asset.get("type") in {"location_variant", "location_plate"} and asset.get("location_state_id"):
            if location_authorities.get(asset_id) != asset.get("location_state_id"):
                report.error("STATE_BINDING", f"Location-state asset {asset_id} is not listed by state {asset.get('location_state_id')}.")
        if asset.get("type") == "prop_state":
            if asset_id not in prop_authorities:
                report.error("STATE_BINDING", f"Prop-state asset {asset_id} is not declared in world-state manifest.")
    return worlds, states, prop_states, environmental_states, special_lighting_events


def validate_camera_move_plan(
    plan: Any,
    *,
    shot_id: str,
    duration_s: float,
    camera_support: Any,
    spatial_map: dict[str, Any] | None,
    where: str,
    report: Report,
) -> None:
    fields = (
        "primitive", "support", "start_camera_mark_id", "end_camera_mark_id", "path_points_m",
        "translation_m", "rotation_deg", "duration_s", "speed_curve", "peak_speed_mps", "easing",
        "path_clearance", "horizon_lock", "axis_lock", "parallax_expectation",
        "subject_screen_occupancy", "occlusion_crossings", "lens_focus_change", "settle_hold_s",
        "operator_contingency", "surreal_vfx_exception",
    )
    if not require_keys(plan, fields, where, report):
        return
    primitive = plan.get("primitive")
    if primitive not in CAMERA_MOVE_PRIMITIVES:
        report.error("CAMERA_PATH", f"{where}.primitive is invalid: {primitive}")
    require_string(plan.get("support"), f"{where}.support", report)
    if plan.get("support") != camera_support:
        report.error("CAMERA_PATH", f"Shot {shot_id} camera_move_plan.support must match camera_support.")
    mark_index = _spatial_mark_index(spatial_map) if isinstance(spatial_map, dict) else {}
    start_mark_id = plan.get("start_camera_mark_id")
    end_mark_id = plan.get("end_camera_mark_id")
    for field, mark_id in (("start_camera_mark_id", start_mark_id), ("end_camera_mark_id", end_mark_id)):
        require_string(mark_id, f"{where}.{field}", report)
        mark = mark_index.get(mark_id) if isinstance(mark_id, str) else None
        if not isinstance(mark, dict) or mark.get("kind") != "camera":
            report.error("CAMERA_PATH", f"Shot {shot_id} {field}={mark_id} must reference a camera mark.")
    points = plan.get("path_points_m")
    if not isinstance(points, list) or not points:
        report.error("CAMERA_PATH", f"{where}.path_points_m must contain at least one set-fixed path point.")
        points = []
    for point_index, point in enumerate(points):
        _validate_position(point, f"{where}.path_points_m[{point_index}]", report)
    translation = plan.get("translation_m")
    if not is_number(translation) or translation < 0:
        report.error("CAMERA_PATH", f"{where}.translation_m must be non-negative.")
    rotation = plan.get("rotation_deg")
    if require_keys(rotation, ("yaw", "pitch", "roll"), f"{where}.rotation_deg", report):
        for axis in ("yaw", "pitch", "roll"):
            if not is_number(rotation.get(axis)):
                report.error("CAMERA_PATH", f"{where}.rotation_deg.{axis} must be numeric.")
    movement_duration = plan.get("duration_s")
    if not is_number(movement_duration) or movement_duration < 0 or movement_duration > duration_s + 0.001:
        report.error("CAMERA_PATH", f"{where}.duration_s must be between 0 and the shot duration.")
    if plan.get("speed_curve") not in CAMERA_SPEED_CURVES:
        report.error("CAMERA_PATH", f"{where}.speed_curve is invalid: {plan.get('speed_curve')}")
    if not is_number(plan.get("peak_speed_mps")) or plan.get("peak_speed_mps") < 0:
        report.error("CAMERA_PATH", f"{where}.peak_speed_mps must be non-negative.")
    for field in (
        "easing", "horizon_lock", "axis_lock", "parallax_expectation", "subject_screen_occupancy",
        "lens_focus_change", "operator_contingency",
    ):
        require_string(plan.get(field), f"{where}.{field}", report)
    require_string_list(plan.get("occlusion_crossings"), f"{where}.occlusion_crossings", report)
    if not is_number(plan.get("settle_hold_s")) or plan.get("settle_hold_s") < 0:
        report.error("CAMERA_PATH", f"{where}.settle_hold_s must be non-negative.")
    clearance = plan.get("path_clearance")
    if require_keys(clearance, ("status", "traversable_region", "notes"), f"{where}.path_clearance", report):
        if clearance.get("status") != "pass":
            report.error("CAMERA_PATH_CLEARANCE", f"Shot {shot_id} requires path_clearance.status=pass.")
        require_string(clearance.get("traversable_region"), f"{where}.path_clearance.traversable_region", report)
        require_string_list(clearance.get("notes"), f"{where}.path_clearance.notes", report)
    vfx = plan.get("surreal_vfx_exception")
    if require_keys(vfx, ("enabled", "rationale"), f"{where}.surreal_vfx_exception", report):
        if not isinstance(vfx.get("enabled"), bool):
            report.error("TYPE", f"{where}.surreal_vfx_exception.enabled must be boolean.")
        require_string(vfx.get("rationale"), f"{where}.surreal_vfx_exception.rationale", report, allow_empty=vfx.get("enabled") is not True)
    if primitive == "locked":
        numeric_rotations = rotation if isinstance(rotation, dict) else {}
        if start_mark_id != end_mark_id or (is_number(translation) and float(translation) != 0) or any(
            is_number(numeric_rotations.get(axis)) and abs(float(numeric_rotations.get(axis))) > 0.001
            for axis in ("yaw", "pitch", "roll")
        ):
            report.error("CAMERA_PATH", f"Locked shot {shot_id} must have one camera mark, zero translation and zero rotation.")
        if is_number(plan.get("peak_speed_mps")) and float(plan.get("peak_speed_mps")) != 0:
            report.error("CAMERA_PATH", f"Locked shot {shot_id} must have peak_speed_mps=0.")


def validate_temporal_capture(
    capture: Any,
    *,
    shot_id: str,
    duration_s: float,
    where: str,
    report: Report,
) -> None:
    fields = (
        "capture_fps", "delivery_fps", "playback_rate", "shutter_angle", "exposure_time_s",
        "speed_ramp", "rolling_shutter_allowance",
    )
    if not require_keys(capture, fields, where, report):
        return
    capture_fps = capture.get("capture_fps")
    delivery_fps = capture.get("delivery_fps")
    shutter_angle = capture.get("shutter_angle")
    exposure_time = capture.get("exposure_time_s")
    playback_rate = capture.get("playback_rate")
    for field, value in (("capture_fps", capture_fps), ("delivery_fps", delivery_fps), ("playback_rate", playback_rate)):
        if not is_number(value) or value <= 0:
            report.error("TEMPORAL_CAPTURE", f"{where}.{field} must be positive.")
    if not is_number(shutter_angle) or not 1 <= shutter_angle <= 360:
        report.error("TEMPORAL_CAPTURE", f"{where}.shutter_angle must be between 1 and 360.")
    if not is_number(exposure_time) or exposure_time <= 0:
        report.error("TEMPORAL_CAPTURE", f"{where}.exposure_time_s must be positive.")
    elif is_number(capture_fps) and capture_fps > 0 and is_number(shutter_angle):
        expected = float(shutter_angle) / (360.0 * float(capture_fps))
        if abs(float(exposure_time) - expected) > max(0.0001, expected * 0.01):
            report.error(
                "SHUTTER_EXPOSURE_MISMATCH",
                f"Shot {shot_id} exposure_time_s must equal shutter_angle/(360*capture_fps), expected {expected:.8f}.",
            )
    ramp = capture.get("speed_ramp")
    if not isinstance(ramp, list):
        report.error("TYPE", f"{where}.speed_ramp must be an array.")
        ramp = []
    last_time = -1.0
    for point_index, point in enumerate(ramp):
        point_where = f"{where}.speed_ramp[{point_index}]"
        if not require_keys(point, ("time_s", "playback_rate"), point_where, report):
            continue
        time_s = point.get("time_s")
        rate = point.get("playback_rate")
        if not is_number(time_s) or not 0 <= time_s <= duration_s:
            report.error("SPEED_RAMP", f"{point_where}.time_s must lie within the shot.")
        elif float(time_s) <= last_time:
            report.error("SPEED_RAMP", f"{point_where}.time_s must increase strictly.")
        else:
            last_time = float(time_s)
        if not is_number(rate) or rate <= 0:
            report.error("SPEED_RAMP", f"{point_where}.playback_rate must be positive.")
    if not ramp and is_number(capture_fps) and capture_fps > 0 and is_number(delivery_fps) and is_number(playback_rate):
        expected_rate = float(delivery_fps) / float(capture_fps)
        if abs(float(playback_rate) - expected_rate) > 0.01:
            report.error("PLAYBACK_RATE", f"Shot {shot_id} playback_rate must equal delivery_fps/capture_fps when no speed ramp is present.")
    rolling = capture.get("rolling_shutter_allowance")
    if require_keys(rolling, ("mode", "rationale"), f"{where}.rolling_shutter_allowance", report):
        if rolling.get("mode") not in {"none", "profile_justified"}:
            report.error("ENUM", f"{where}.rolling_shutter_allowance.mode is invalid: {rolling.get('mode')}")
        require_string(rolling.get("rationale"), f"{where}.rolling_shutter_allowance.rationale", report, allow_empty=rolling.get("mode") == "none")


def validate_motion_blur_plan(
    plan: Any,
    *,
    shot_id: str,
    camera_primitive: str,
    where: str,
    report: Report,
) -> None:
    fields = (
        "source", "direction", "regions", "amount", "static_reference_regions",
        "occlusion_edge_behavior", "reason", "frame_blending_allowed", "ghosting_allowed",
    )
    if not require_keys(plan, fields, where, report):
        return
    source = plan.get("source")
    amount = plan.get("amount")
    if source not in MOTION_BLUR_SOURCES:
        report.error("MOTION_BLUR", f"{where}.source is invalid: {source}")
    if amount not in MOTION_BLUR_AMOUNTS:
        report.error("MOTION_BLUR", f"{where}.amount is invalid: {amount}")
    require_string(plan.get("direction"), f"{where}.direction", report, allow_empty=source == "none")
    require_string_list(plan.get("regions"), f"{where}.regions", report)
    require_string_list(plan.get("static_reference_regions"), f"{where}.static_reference_regions", report)
    require_string(plan.get("occlusion_edge_behavior"), f"{where}.occlusion_edge_behavior", report)
    require_string(plan.get("reason"), f"{where}.reason", report)
    if plan.get("frame_blending_allowed") is not False:
        report.error("MOTION_BLUR", f"Shot {shot_id} must set frame_blending_allowed=false.")
    if plan.get("ghosting_allowed") is not False:
        report.error("MOTION_BLUR", f"Shot {shot_id} must set ghosting_allowed=false.")
    if (source == "none") != (amount == "none"):
        report.error("MOTION_BLUR", f"Shot {shot_id} source and amount must agree on whether blur is present.")
    if camera_primitive == "locked" and source in {"camera", "both"}:
        report.error("MOTION_BLUR", f"Locked shot {shot_id} cannot claim camera-induced motion blur.")
    if source != "none" and not plan.get("static_reference_regions"):
        report.error("MOTION_BLUR", f"Shot {shot_id} with blur requires at least one static reference region.")


def validate_multi_person_projection(
    plan: Any,
    *,
    shot_id: str,
    cast_ids: list[str],
    geometry_locks: dict[str, Any],
    production_ready: bool,
    where: str,
    report: Report,
) -> None:
    """Validate that every body in a shared frame obeys one camera projection."""
    if len(cast_ids) < 2:
        return
    if not production_ready and plan in (None, {}):
        return
    fields = (
        "policy",
        "projection",
        "camera_height_m",
        "camera_pitch_deg",
        "subjects",
        "projected_height_relations",
        "horizon_vanishing_lines",
        "ground_contact",
        "occlusion_order",
        "per_person_scale_transform",
        "verdict",
        "hard_failures",
    )
    if not require_keys(plan, fields, where, report):
        return
    supported_policies = {
        "approved-body-geometry-plus-single-camera-projection-v1.6.2",
        "approved-body-geometry-plus-single-camera-projection-v1.6.4",
    }
    if production_ready and plan.get("policy") not in supported_policies:
        report.error(
            "MULTI_PERSON_PROJECTION",
            f"Ready shot {shot_id} must use a supported single-camera multi-person projection policy.",
        )
    require_string(plan.get("projection"), f"{where}.projection", report)
    camera_height = plan.get("camera_height_m")
    if not is_number(camera_height) or camera_height <= 0:
        report.error("MULTI_PERSON_PROJECTION", f"{where}.camera_height_m must be positive.")
    camera_pitch = plan.get("camera_pitch_deg")
    if not is_number(camera_pitch) or not -90 <= camera_pitch <= 90:
        report.error("MULTI_PERSON_PROJECTION", f"{where}.camera_pitch_deg must be between -90 and 90.")

    subjects = plan.get("subjects")
    if not isinstance(subjects, dict):
        report.error("TYPE", f"{where}.subjects must map every cast root to projection facts.")
        subjects = {}
    if production_ready and set(subjects) != set(cast_ids):
        report.error(
            "MULTI_PERSON_PROJECTION",
            f"Ready shot {shot_id} requires one projection subject record for every and only cast root.",
        )
    for root_id, subject in subjects.items():
        subject_where = f"{where}.subjects.{root_id}"
        if root_id not in cast_ids:
            report.error("MULTI_PERSON_PROJECTION", f"{subject_where} is not a cast root in shot {shot_id}.")
        if not require_keys(
            subject,
            (
                "approved_height_m",
                "camera_distance_m",
                "ground_elevation_m",
                "frame_coverage",
                "visible_landmarks",
            ),
            subject_where,
            report,
        ):
            continue
        height = subject.get("approved_height_m")
        distance = subject.get("camera_distance_m")
        elevation = subject.get("ground_elevation_m")
        if not is_number(height) or height <= 0:
            report.error("MULTI_PERSON_PROJECTION", f"{subject_where}.approved_height_m must be positive.")
        else:
            geometry_lock = geometry_locks.get(root_id)
            locked_height = geometry_lock.get("relative_height_m") if isinstance(geometry_lock, dict) else None
            if is_number(locked_height) and abs(float(height) - float(locked_height)) > 0.02:
                report.error(
                    "MULTI_PERSON_PROJECTION",
                    f"{subject_where}.approved_height_m conflicts with the body's geometry lock.",
                )
        if not is_number(distance) or distance <= 0:
            report.error("MULTI_PERSON_PROJECTION", f"{subject_where}.camera_distance_m must be positive.")
        elif abs(float(distance) * 10 - round(float(distance) * 10)) > 1e-6:
            report.error(
                "SPATIAL_PRECISION",
                f"{subject_where}.camera_distance_m must use approximately 0.1 m precision.",
            )
        if not is_number(elevation):
            report.error("MULTI_PERSON_PROJECTION", f"{subject_where}.ground_elevation_m must be numeric.")
        if subject.get("frame_coverage") not in {"complete", "cropped", "occluded"}:
            report.error(
                "MULTI_PERSON_PROJECTION",
                f"{subject_where}.frame_coverage must be complete, cropped, or occluded.",
            )
        landmarks = subject.get("visible_landmarks")
        require_string_list(landmarks, f"{subject_where}.visible_landmarks", report)
        if production_ready and not landmarks:
            report.error("MULTI_PERSON_PROJECTION", f"{subject_where} requires visible body landmarks.")

    relations = plan.get("projected_height_relations")
    if not isinstance(relations, list):
        report.error("TYPE", f"{where}.projected_height_relations must be an array.")
        relations = []
    expected_relation_count = len(cast_ids) * (len(cast_ids) - 1) // 2
    if production_ready and len(relations) != expected_relation_count:
        report.error(
            "MULTI_PERSON_PROJECTION",
            f"Ready shot {shot_id} requires {expected_relation_count} pairwise projected-height relation(s).",
        )
    seen_pairs: set[tuple[str, str]] = set()
    for index, relation in enumerate(relations):
        relation_where = f"{where}.projected_height_relations[{index}]"
        if not require_keys(
            relation,
            (
                "numerator_asset_id",
                "denominator_asset_id",
                "expected_ratio",
                "observed_ratio",
                "tolerance_fraction",
                "cropped_landmark_method",
                "pass",
            ),
            relation_where,
            report,
        ):
            continue
        numerator = relation.get("numerator_asset_id")
        denominator = relation.get("denominator_asset_id")
        if numerator not in cast_ids or denominator not in cast_ids or numerator == denominator:
            report.error("MULTI_PERSON_PROJECTION", f"{relation_where} must compare two distinct cast roots.")
            continue
        pair = tuple(sorted((str(numerator), str(denominator))))
        if pair in seen_pairs:
            report.error("MULTI_PERSON_PROJECTION", f"{relation_where} duplicates cast pair {pair}.")
        seen_pairs.add(pair)
        numerator_subject = subjects.get(numerator, {}) if isinstance(subjects.get(numerator), dict) else {}
        denominator_subject = subjects.get(denominator, {}) if isinstance(subjects.get(denominator), dict) else {}
        numerator_height = numerator_subject.get("approved_height_m")
        denominator_height = denominator_subject.get("approved_height_m")
        numerator_distance = numerator_subject.get("camera_distance_m")
        denominator_distance = denominator_subject.get("camera_distance_m")
        expected = relation.get("expected_ratio")
        if all(
            is_number(value) and value > 0
            for value in (numerator_height, denominator_height, numerator_distance, denominator_distance)
        ):
            calculated = (float(numerator_height) / float(numerator_distance)) / (
                float(denominator_height) / float(denominator_distance)
            )
            if not is_number(expected) or expected <= 0 or abs(float(expected) - calculated) / calculated > 0.03:
                report.error(
                    "MULTI_PERSON_PROJECTION",
                    f"{relation_where}.expected_ratio must match approved height divided by camera distance (about {calculated:.3f}).",
                )
        elif not is_number(expected) or expected <= 0:
            report.error("MULTI_PERSON_PROJECTION", f"{relation_where}.expected_ratio must be positive.")
        tolerance = relation.get("tolerance_fraction")
        if not is_number(tolerance) or not 0 <= tolerance <= 0.5:
            report.error("MULTI_PERSON_PROJECTION", f"{relation_where}.tolerance_fraction must be between 0 and 0.5.")
            tolerance = 0.0
        observed = relation.get("observed_ratio")
        if observed is None:
            require_string(
                relation.get("cropped_landmark_method"),
                f"{relation_where}.cropped_landmark_method",
                report,
            )
        elif not is_number(observed) or observed <= 0:
            report.error("MULTI_PERSON_PROJECTION", f"{relation_where}.observed_ratio must be positive or null for a crop.")
        elif is_number(expected) and expected > 0 and is_number(tolerance):
            if abs(float(observed) - float(expected)) / float(expected) > float(tolerance):
                report.error(
                    "MULTI_PERSON_PROJECTION",
                    f"{relation_where}.observed_ratio falls outside its declared tolerance.",
                )
        if relation.get("pass") is not True:
            report.error("MULTI_PERSON_PROJECTION", f"{relation_where}.pass must be true for a Ready shot.")

    for field in ("horizon_vanishing_lines", "ground_contact", "occlusion_order"):
        require_string(plan.get(field), f"{where}.{field}", report)
    if plan.get("per_person_scale_transform") is not False:
        report.error("MULTI_PERSON_PROJECTION", f"Shot {shot_id} must set per_person_scale_transform=false.")
    if plan.get("verdict") != "pass" or plan.get("hard_failures"):
        report.error("MULTI_PERSON_PROJECTION", f"Ready shot {shot_id} has not passed multi-person projection QA.")
    require_string_list(plan.get("hard_failures"), f"{where}.hard_failures", report)


def validate_dramatic_coverage_plan(
    plan: Any,
    *,
    shot_id: str,
    cast_ids: list[str],
    production_ready: bool,
    where: str,
    report: Report,
) -> None:
    """Reject spatial diagrams and game-level blocking masquerading as dramatic coverage."""
    if len(cast_ids) < 2:
        return
    if not production_ready and plan in (None, {}):
        return
    fields = (
        "policy",
        "coverage_role",
        "shot_size",
        "observer_position",
        "foreground_subject_ids",
        "focus_subject_ids",
        "crop_landmarks",
        "eyeline_contract",
        "motivated_action_beat",
        "composition_asymmetry",
        "wide_two_shot_justification",
        "spatial_proof_only",
        "game_level_blocking_detected",
        "verdict",
        "hard_failures",
    )
    if not require_keys(plan, fields, where, report):
        return
    if production_ready and plan.get("policy") != "narrative-coverage-not-spatial-diagram-v1.6.4":
        report.error(
            "DRAMATIC_COVERAGE",
            f"Ready shot {shot_id} must use narrative-coverage-not-spatial-diagram-v1.6.4.",
        )
    roles = {
        "master",
        "over_shoulder",
        "dirty_single",
        "reverse",
        "reaction",
        "profile_two_shot",
        "pov",
        "insert",
        "wide_exception",
    }
    shot_sizes = {
        "extreme_wide",
        "wide",
        "medium_wide",
        "medium",
        "medium_close",
        "close",
        "over_shoulder",
        "dirty_single",
        "profile_two_shot",
        "pov",
        "insert",
    }
    if plan.get("coverage_role") not in roles:
        report.error("DRAMATIC_COVERAGE", f"{where}.coverage_role is invalid: {plan.get('coverage_role')}")
    if plan.get("shot_size") not in shot_sizes:
        report.error("DRAMATIC_COVERAGE", f"{where}.shot_size is invalid: {plan.get('shot_size')}")
    for field in (
        "observer_position",
        "eyeline_contract",
        "motivated_action_beat",
        "composition_asymmetry",
    ):
        require_string(plan.get(field), f"{where}.{field}", report)
    for field in ("foreground_subject_ids", "focus_subject_ids", "crop_landmarks", "hard_failures"):
        require_string_list(plan.get(field), f"{where}.{field}", report)
    foreground_ids = plan.get("foreground_subject_ids") if isinstance(plan.get("foreground_subject_ids"), list) else []
    focus_ids = plan.get("focus_subject_ids") if isinstance(plan.get("focus_subject_ids"), list) else []
    for field, values in (("foreground_subject_ids", foreground_ids), ("focus_subject_ids", focus_ids)):
        if len(values) != len(set(values)):
            report.error("DRAMATIC_COVERAGE", f"{where}.{field} contains duplicate cast roots.")
        unknown = sorted(set(values) - set(cast_ids))
        if unknown:
            report.error("DRAMATIC_COVERAGE", f"{where}.{field} contains non-cast roots: {', '.join(unknown)}.")
    if production_ready and not focus_ids:
        report.error("DRAMATIC_COVERAGE", f"Ready shot {shot_id} must name at least one focus subject.")
    wide_exception = plan.get("shot_size") in {"wide", "extreme_wide"} or plan.get("coverage_role") == "wide_exception"
    require_string(
        plan.get("wide_two_shot_justification"),
        f"{where}.wide_two_shot_justification",
        report,
        allow_empty=not wide_exception,
    )
    if plan.get("spatial_proof_only") is not False:
        report.error("DRAMATIC_COVERAGE", f"Shot {shot_id} cannot use a spatial proof image as final coverage.")
    if plan.get("game_level_blocking_detected") is not False:
        report.error("DRAMATIC_COVERAGE", f"Shot {shot_id} contains game-level or diagrammatic blocking.")
    if plan.get("verdict") != "pass" or plan.get("hard_failures"):
        report.error("DRAMATIC_COVERAGE", f"Ready shot {shot_id} has not passed dramatic coverage QA.")


def validate_subject_environment_integration(
    plan: Any,
    *,
    shot_id: str,
    has_human: bool,
    production_ready: bool,
    where: str,
    report: Report,
) -> None:
    """Require people and the photographed world to share one physical image event."""
    if not has_human:
        return
    if not production_ready and plan in (None, {}):
        return
    fields = (
        "policy",
        "shared_light_sources",
        "shared_atmosphere_state_id",
        "atmosphere_depth_behavior",
        "focus_and_occlusion",
        "contact_and_grounding",
        "material_response_match",
        "color_contamination_match",
        "edge_integration",
        "cutout_edges_detected",
        "separate_person_tone_mapping_detected",
        "background_only_atmosphere_detected",
        "verdict",
        "hard_failures",
    )
    if not require_keys(plan, fields, where, report):
        return
    if production_ready and plan.get("policy") != "shared-light-air-focus-occlusion-v1.6.4":
        report.error(
            "SUBJECT_ENVIRONMENT_INTEGRATION",
            f"Ready shot {shot_id} must use shared-light-air-focus-occlusion-v1.6.4.",
        )
    light_sources = plan.get("shared_light_sources")
    require_string_list(light_sources, f"{where}.shared_light_sources", report)
    if production_ready and not light_sources:
        report.error(
            "SUBJECT_ENVIRONMENT_INTEGRATION",
            f"Ready shot {shot_id} must identify at least one light source shared by subject and set.",
        )
    for field in (
        "shared_atmosphere_state_id",
        "atmosphere_depth_behavior",
        "focus_and_occlusion",
        "contact_and_grounding",
        "material_response_match",
        "color_contamination_match",
        "edge_integration",
    ):
        require_string(plan.get(field), f"{where}.{field}", report)
    for field in (
        "cutout_edges_detected",
        "separate_person_tone_mapping_detected",
        "background_only_atmosphere_detected",
    ):
        if plan.get(field) is not False:
            report.error(
                "SUBJECT_ENVIRONMENT_INTEGRATION",
                f"Shot {shot_id} must set {field}=false.",
            )
    require_string_list(plan.get("hard_failures"), f"{where}.hard_failures", report)
    if plan.get("verdict") != "pass" or plan.get("hard_failures"):
        report.error(
            "SUBJECT_ENVIRONMENT_INTEGRATION",
            f"Ready shot {shot_id} has not passed subject/environment integration QA.",
        )


def validate_shots(
    project_dir: Path,
    data: dict[str, Any] | None,
    scenes: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    spatial_maps: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    effective_profiles: dict[str, str],
    identity_packs: dict[str, dict[str, Any]],
    character_states: dict[str, dict[str, Any]],
    location_states: dict[str, dict[str, Any]],
    prop_states: dict[str, dict[str, Any]],
    format_plans: dict[str, dict[str, Any]],
    environmental_states: dict[str, dict[str, Any]],
    special_lighting_events: dict[str, dict[str, Any]],
    quality_profiles: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    rows = validate_manifest_header(data, "shots", "manifests/shots.json", report)
    shots: dict[str, dict[str, Any]] = {}
    used_orders: dict[tuple[str, int], str] = {}
    production_shots_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    required = (
        "id",
        "scene_id",
        "order",
        "story_beat",
        "duration_s",
        "motion_class",
        "capture_profile_id",
        "quality_profile_id",
        "shot_size",
        "focal_length_mm",
        "fov_deg",
        "t_stop",
        "focus_plan",
        "camera_height_cm",
        "camera_axis",
        "camera_support",
        "camera_move",
        "camera_move_plan",
        "temporal_capture",
        "motion_blur_plan",
        "exposure_notes",
        "dynamic_range_plan",
        "format_plan_id",
        "environmental_state_id",
        "special_lighting_event_ids",
        "body_geometry_locks",
        "pose_contact_anchor_ids",
        "material_interaction_plan",
        "spatial_map_id",
        "camera_mark_id",
        "subject_mark_ids",
        "anchor_projection",
        "depth_order",
        "action_beats",
        "cast_asset_ids",
        "character_state_bindings",
        "location_asset_id",
        "location_state_id",
        "prop_asset_ids",
        "prop_state_bindings",
        "sequence_cluster_id",
        "sequence_visual_anchor_asset_id",
        "start_keyframe_id",
        "end_keyframe_id",
        "video_prompt_path",
        "model_prompt_strategy_id",
        "audio",
        "locks",
        "status",
        "adapter_notes",
    )

    for index, shot in enumerate(rows):
        where = f"manifests/shots.json.shots[{index}]"
        if not require_keys(shot, required, where, report):
            continue
        shot_id = shot.get("id")
        scene_id = shot.get("scene_id")
        if not require_string(shot_id, f"{where}.id", report):
            continue
        if not ID_RE.fullmatch(shot_id):
            report.error("INVALID_ID", f"Invalid shot id: {shot_id}")
        if shot_id in shots:
            report.error("DUPLICATE_ID", f"Duplicate shot id: {shot_id}")
        else:
            shots[shot_id] = shot
        if not require_string(scene_id, f"{where}.scene_id", report) or scene_id not in scenes:
            report.error("ORPHAN_SHOT", f"Shot {shot_id} references missing scene {scene_id}.")
        order = shot.get("order")
        if not is_integer(order):
            report.error("TYPE", f"{where}.order must be an integer.")
        elif isinstance(scene_id, str):
            key = (scene_id, order)
            if key in used_orders:
                report.error("DUPLICATE_ORDER", f"Shots {used_orders[key]} and {shot_id} share order {order} in {scene_id}.")
            else:
                used_orders[key] = shot_id

        require_string(shot.get("story_beat"), f"{where}.story_beat", report)
        duration = shot.get("duration_s")
        if not is_number(duration) or duration <= 0:
            report.error("TYPE", f"{where}.duration_s must be a positive number.")
            duration = 0.0
        elif float(duration) > 30.0:
            report.error(
                "HIGGSFIELD_DURATION",
                f"Shot {shot_id} exceeds Seedance 2.5's published 30-second maximum.",
            )
        motion_class = shot.get("motion_class")
        if motion_class not in MOTION_CLASSES:
            report.error("ENUM", f"{where}.motion_class is invalid: {motion_class}")
        status = shot.get("status")
        if status not in SHOT_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        production_ready = status in PRODUCTION_SHOT_STATUSES
        quality_profile_id = shot.get("quality_profile_id")
        require_string(quality_profile_id, f"{where}.quality_profile_id", report, allow_empty=not production_ready)
        quality_profile = quality_profiles.get(quality_profile_id) if isinstance(quality_profile_id, str) else None
        if production_ready and quality_profile is None:
            report.error("QUALITY_PROFILE", f"Ready shot {shot_id} references missing quality Profile {quality_profile_id}.")
        elif production_ready and quality_profile.get("status") != "approved":
            report.error("QUALITY_PROFILE", f"Ready shot {shot_id} requires an approved quality Profile.")
        if production_ready:
            validate_dynamic_range_plan(
                shot.get("dynamic_range_plan"),
                f"{where}.dynamic_range_plan",
                report,
            )
        sequence_anchor_id = shot.get("sequence_visual_anchor_asset_id")
        require_string(sequence_anchor_id, f"{where}.sequence_visual_anchor_asset_id", report, allow_empty=not production_ready)
        if production_ready:
            validate_approved_asset_reference(
                sequence_anchor_id,
                f"Ready shot {shot_id} sequence visual anchor",
                assets,
                report,
                {"keyframe", "storyboard"},
            )
            sequence_anchor = assets.get(sequence_anchor_id, {})
            if sequence_anchor.get("quality_profile_id") != quality_profile_id:
                report.error("QUALITY_PROFILE", f"Shot {shot_id} sequence visual anchor uses a different quality Profile.")

        for field in (
            "capture_profile_id",
            "shot_size",
            "focus_plan",
            "camera_axis",
            "camera_support",
            "camera_move",
            "exposure_notes",
            "format_plan_id",
            "environmental_state_id",
            "spatial_map_id",
            "camera_mark_id",
            "location_asset_id",
            "location_state_id",
            "sequence_cluster_id",
            "start_keyframe_id",
            "end_keyframe_id",
            "video_prompt_path",
            "model_prompt_strategy_id",
        ):
            required_when_ready = field in {
                "capture_profile_id",
                "shot_size",
                "focus_plan",
                "camera_axis",
                "camera_support",
                "camera_move",
                "exposure_notes",
                "format_plan_id",
                "environmental_state_id",
                "spatial_map_id",
                "camera_mark_id",
                "location_asset_id",
                "location_state_id",
                "sequence_cluster_id",
                "video_prompt_path",
                "model_prompt_strategy_id",
            }
            require_string(
                shot.get(field),
                f"{where}.{field}",
                report,
                allow_empty=not production_ready or not required_when_ready,
            )
        if production_ready and shot.get("model_prompt_strategy_id") != "shot-model-v1.6":
            report.error(
                "VIDEO_PROMPT_STRATEGY",
                f"Ready shot {shot_id} must use model_prompt_strategy_id=shot-model-v1.6.",
            )
        if production_ready and isinstance(scene_id, str) and scene_id in scenes:
            production_shots_by_scene[scene_id].append(shot)
        profile_id = shot.get("capture_profile_id")
        if production_ready:
            profile = profiles.get(profile_id) if isinstance(profile_id, str) else None
            if profile is None:
                report.error("MISSING_PROFILE", f"Ready shot {shot_id} references missing Profile {profile_id}.")
            elif profile.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"Ready shot {shot_id} references non-approved Profile {profile_id}.")
            expected_profile = effective_profiles.get(scene_id) if isinstance(scene_id, str) else None
            if not expected_profile:
                report.error("MISSING_PROFILE", f"Ready shot {shot_id} has no effective Base or scene Profile.")
            elif profile_id != expected_profile:
                report.error(
                    "PROFILE_CONTINUITY",
                    f"Ready shot {shot_id} uses Profile {profile_id}; scene {scene_id} requires {expected_profile}.",
                )

        format_plan_id = shot.get("format_plan_id")
        environment_id = shot.get("environmental_state_id")
        special_event_ids = shot.get("special_lighting_event_ids")
        require_string_list(special_event_ids, f"{where}.special_lighting_event_ids", report)
        if not isinstance(special_event_ids, list):
            special_event_ids = []
        if len(special_event_ids) != len(set(special_event_ids)):
            report.error("DUPLICATE_REFERENCE", f"Shot {shot_id} repeats a special-light event id.")
        if production_ready:
            scene = scenes.get(scene_id, {}) if isinstance(scene_id, str) else {}
            format_plan = format_plans.get(format_plan_id) if isinstance(format_plan_id, str) else None
            if format_plan is None or format_plan.get("status") != "approved":
                report.error("FORMAT_APPROVAL", f"Ready shot {shot_id} requires approved format plan {format_plan_id}.")
            if scene.get("format_plan_id") != format_plan_id:
                report.error("FORMAT_REFERENCE", f"Ready shot {shot_id} format plan must match scene {scene_id}.")
            profile = profiles.get(profile_id) if isinstance(profile_id, str) else None
            if isinstance(profile, dict) and profile.get("format_plan_id") != format_plan_id:
                report.error("FORMAT_REFERENCE", f"Ready shot {shot_id} format plan must match Profile {profile_id}.")
            environment = environmental_states.get(environment_id) if isinstance(environment_id, str) else None
            if environment is None or environment.get("status") != "approved":
                report.error("ENVIRONMENT_STATE", f"Ready shot {shot_id} requires approved environmental state {environment_id}.")
            elif scene_id not in environment.get("scene_ids", []):
                report.error("ENVIRONMENT_STATE", f"Environmental state {environment_id} does not cover scene {scene_id}.")
            if scene.get("environmental_state_id") != environment_id:
                report.error("ENVIRONMENT_STATE", f"Ready shot {shot_id} environmental state must match scene {scene_id}.")
            for event_id in special_event_ids:
                event = special_lighting_events.get(event_id)
                if event is None or event.get("status") != "approved":
                    report.error("SPECIAL_LIGHT", f"Ready shot {shot_id} references unavailable special-light event {event_id}.")
                elif scene_id not in event.get("scene_ids", []):
                    report.error("SPECIAL_LIGHT", f"Special-light event {event_id} does not cover scene {scene_id}.")

        spatial_map_id = shot.get("spatial_map_id")
        spatial_map = spatial_maps.get(spatial_map_id) if isinstance(spatial_map_id, str) else None
        expected_map_id = scenes.get(scene_id, {}).get("spatial_map_id") if isinstance(scene_id, str) else None
        if production_ready:
            if spatial_map is None:
                report.error("SPATIAL_MAP", f"Ready shot {shot_id} references missing spatial map {spatial_map_id}.")
            elif spatial_map.get("status") != "approved":
                report.error("SPATIAL_QA", f"Ready shot {shot_id} references non-approved spatial map {spatial_map_id}.")
            elif spatial_map.get("scene_id") != scene_id or spatial_map_id != expected_map_id:
                report.error(
                    "SPATIAL_MAP",
                    f"Ready shot {shot_id} must inherit scene {scene_id} spatial map {expected_map_id}.",
                )

        mark_index = _spatial_mark_index(spatial_map) if isinstance(spatial_map, dict) else {}
        camera_mark_id = shot.get("camera_mark_id")
        camera_mark = mark_index.get(camera_mark_id) if isinstance(camera_mark_id, str) else None
        if production_ready:
            if not isinstance(camera_mark, dict) or camera_mark.get("kind") != "camera":
                report.error(
                    "CAMERA_MARK",
                    f"Ready shot {shot_id} camera_mark_id={camera_mark_id} must reference a camera mark in {spatial_map_id}.",
                )

        subject_mark_ids = shot.get("subject_mark_ids")
        if not isinstance(subject_mark_ids, dict):
            report.error("TYPE", f"{where}.subject_mark_ids must be an object mapping cast asset ids to spatial mark ids.")
            subject_mark_ids = {}
        for subject_id, mark_id in subject_mark_ids.items():
            if not isinstance(subject_id, str) or not isinstance(mark_id, str):
                report.error("TYPE", f"{where}.subject_mark_ids keys and values must be strings.")
                continue
            mark = mark_index.get(mark_id)
            if not isinstance(mark, dict) or mark.get("kind") != "character":
                report.error("SUBJECT_MARK", f"Shot {shot_id} subject {subject_id} references invalid character mark {mark_id}.")
            elif mark.get("asset_id") != subject_id:
                report.error(
                    "SUBJECT_MARK",
                    f"Shot {shot_id} mark {mark_id} is assigned to {mark.get('asset_id')}, not {subject_id}.",
                )

        projection = shot.get("anchor_projection")
        projection_fields = (
            "visibility",
            "screen_region",
            "direction_from_camera",
            "set_fixed_direction",
            "set_fixed_relation",
            "distance_m",
        )
        projection_valid = require_keys(projection, projection_fields, f"{where}.anchor_projection", report)
        if projection_valid:
            visibility = projection.get("visibility")
            if visibility not in ANCHOR_VISIBILITIES:
                report.error("ENUM", f"{where}.anchor_projection.visibility is invalid: {visibility}")
            require_string(projection.get("screen_region"), f"{where}.anchor_projection.screen_region", report, allow_empty=True)
            require_string(
                projection.get("direction_from_camera"),
                f"{where}.anchor_projection.direction_from_camera",
                report,
                allow_empty=True,
            )
            if projection.get("set_fixed_direction") not in SET_FIXED_DIRECTIONS:
                report.error(
                    "ENUM",
                    f"{where}.anchor_projection.set_fixed_direction is invalid: {projection.get('set_fixed_direction')}",
                )
            require_string(
                projection.get("set_fixed_relation"),
                f"{where}.anchor_projection.set_fixed_relation",
                report,
                allow_empty=not production_ready,
            )
            relation = str(projection.get("set_fixed_relation") or "").strip().casefold()
            if production_ready and relation and re.fullmatch(
                r"(?:(?:screen|frame|camera)[\s_-]*(?:left|right|center|foreground|background)|画面(?:左|右|中央|前景|后景))[^a-z0-9+\-]*",
                relation,
            ):
                report.error(
                    "SET_FIXED_RELATION",
                    f"Ready shot {shot_id} anchor relation cannot use only screen-relative language.",
                )
            distance_m = projection.get("distance_m")
            if not is_number(distance_m) or distance_m <= 0:
                report.error("SPATIAL_DISTANCE", f"{where}.anchor_projection.distance_m must be a positive number.")
            elif abs(float(distance_m) * 10 - round(float(distance_m) * 10)) > 1e-6:
                report.error(
                    "SPATIAL_PRECISION",
                    f"{where}.anchor_projection.distance_m must use approximately 0.1 m precision.",
                )
            if production_ready and visibility in {"visible", "partial"} and not projection.get("screen_region"):
                report.error(
                    "ANCHOR_PROJECTION",
                    f"Ready shot {shot_id} with a visible anchor must name its screen region.",
                )
            if production_ready and visibility == "offscreen" and not projection.get("direction_from_camera"):
                report.error(
                    "ANCHOR_PROJECTION",
                    f"Ready shot {shot_id} with an offscreen anchor must name its camera-relative offscreen direction.",
                )
            if production_ready and isinstance(camera_mark, dict) and is_number(distance_m):
                position = camera_mark.get("position_m")
                if isinstance(position, dict) and all(is_number(position.get(axis)) for axis in ("x", "y", "z")):
                    measured = math.sqrt(sum(float(position[axis]) ** 2 for axis in ("x", "y", "z")))
                    if abs(measured - float(distance_m)) > 0.5:
                        report.error(
                            "SPATIAL_DISTANCE",
                            f"Shot {shot_id} anchor distance {distance_m} m conflicts with camera mark distance {measured:.1f} m.",
                        )

        depth_order = shot.get("depth_order")
        require_string_list(depth_order, f"{where}.depth_order", report)
        if isinstance(depth_order, list):
            if len(depth_order) != len(set(depth_order)):
                report.error("DUPLICATE_REFERENCE", f"Shot {shot_id} repeats an item in depth_order.")
            anchor_id = ""
            if isinstance(spatial_map, dict) and isinstance(spatial_map.get("primary_anchor"), dict):
                anchor_id = str(spatial_map["primary_anchor"].get("asset_id", ""))
            if production_ready and (not depth_order or anchor_id not in depth_order):
                report.error(
                    "DEPTH_ORDER",
                    f"Ready shot {shot_id} depth_order must include primary anchor {anchor_id}, including when offscreen.",
                )
        fov = shot.get("fov_deg")
        focal_length = shot.get("focal_length_mm")
        t_stop = shot.get("t_stop")
        height = shot.get("camera_height_cm")
        camera_move_plan = shot.get("camera_move_plan")
        temporal_capture = shot.get("temporal_capture")
        motion_blur_plan = shot.get("motion_blur_plan")
        if production_ready:
            validate_camera_move_plan(
                camera_move_plan,
                shot_id=str(shot_id),
                duration_s=float(duration),
                camera_support=shot.get("camera_support"),
                spatial_map=spatial_map,
                where=f"{where}.camera_move_plan",
                report=report,
            )
            validate_temporal_capture(
                temporal_capture,
                shot_id=str(shot_id),
                duration_s=float(duration),
                where=f"{where}.temporal_capture",
                report=report,
            )
            primitive = camera_move_plan.get("primitive", "") if isinstance(camera_move_plan, dict) else ""
            validate_motion_blur_plan(
                motion_blur_plan,
                shot_id=str(shot_id),
                camera_primitive=str(primitive),
                where=f"{where}.motion_blur_plan",
                report=report,
            )
        if production_ready and (not is_number(fov) or not 1 <= fov < 180):
            report.error("CAMERA", f"{where}.fov_deg must be between 1 and 179 for a ready shot.")
        elif fov not in (None, "") and not is_number(fov):
            report.error("TYPE", f"{where}.fov_deg must be numeric or null before readiness.")
        if production_ready and (not is_number(focal_length) or focal_length <= 0):
            report.error("OPTICS", f"{where}.focal_length_mm must be positive for a ready shot.")
        elif focal_length not in (None, "") and not is_number(focal_length):
            report.error("TYPE", f"{where}.focal_length_mm must be numeric or null before readiness.")
        if production_ready and (not is_number(t_stop) or not 0.7 <= t_stop <= 64):
            report.error("OPTICS", f"{where}.t_stop must be between 0.7 and 64 for a ready shot.")
        elif t_stop not in (None, "") and not is_number(t_stop):
            report.error("TYPE", f"{where}.t_stop must be numeric or null before readiness.")
        if production_ready and (not is_number(height) or height <= 0):
            report.error("CAMERA", f"{where}.camera_height_cm must be positive for a ready shot.")
        elif height not in (None, "") and not is_number(height):
            report.error("TYPE", f"{where}.camera_height_cm must be numeric or null before readiness.")
        if production_ready and is_number(height) and isinstance(camera_mark, dict):
            mark_position = camera_mark.get("position_m")
            mark_height = mark_position.get("z") if isinstance(mark_position, dict) else None
            if is_number(mark_height) and abs(float(height) - float(mark_height) * 100) > 10:
                report.error(
                    "CAMERA_MARK",
                    f"Shot {shot_id} camera_height_cm={height} conflicts with camera mark Z={float(mark_height):.1f} m.",
                )

        if production_ready and is_number(fov) and is_number(focal_length) and isinstance(profile_id, str):
            profile = profiles.get(profile_id)
            if profile:
                width = profile.get("capture", {}).get("imaging_width_mm")
                optics = profile.get("optics", {})
                squeeze = optics.get("desqueeze_ratio") if optics.get("projection") == "anamorphic" else 1.0
                if is_number(width) and is_number(squeeze) and squeeze > 0:
                    expected_fov = math.degrees(2 * math.atan((float(width) * float(squeeze)) / (2 * float(focal_length))))
                    difference = abs(float(fov) - expected_fov)
                    if difference > 20:
                        report.error(
                            "FOV_MISMATCH",
                            f"Shot {shot_id} FOV {fov}° conflicts with Profile width/lens estimate {expected_fov:.1f}°.",
                        )
                    elif difference > 8:
                        report.warning(
                            "FOV_MISMATCH",
                            f"Shot {shot_id} FOV {fov}° differs from Profile width/lens estimate {expected_fov:.1f}°.",
                        )

        for field in ("cast_asset_ids", "prop_asset_ids", "locks"):
            require_string_list(shot.get(field), f"{where}.{field}", report)
        cast_ids = shot.get("cast_asset_ids") if isinstance(shot.get("cast_asset_ids"), list) else []
        prop_ids = shot.get("prop_asset_ids") if isinstance(shot.get("prop_asset_ids"), list) else []
        if production_ready and cast_ids and (
            not isinstance(quality_profile, dict) or not quality_profile.get("live_action_probe_id")
        ):
            report.error(
                "LIVE_ACTION_PROBE_GATE",
                f"Ready person-bearing shot {shot_id} requires an approved ordinary-light live-action integration probe through its quality Profile.",
            )
        if len(cast_ids) != len(set(cast_ids)) or len(prop_ids) != len(set(prop_ids)):
            report.error("DUPLICATE_REFERENCE", f"Shot {shot_id} repeats an asset reference.")
        if production_ready and set(subject_mark_ids) != set(cast_ids):
            report.error(
                "SUBJECT_MARK",
                f"Ready shot {shot_id} subject_mark_ids must map every and only cast asset id.",
            )
        if production_ready and isinstance(depth_order, list):
            for cast_id in cast_ids:
                if cast_id not in depth_order:
                    report.error("DEPTH_ORDER", f"Ready shot {shot_id} depth_order omits cast asset {cast_id}.")
        for asset_id in cast_ids:
            validate_approved_asset_reference(asset_id, f"Shot {shot_id} cast", assets, report, {"character_identity_inspector"})
        for asset_id in prop_ids:
            validate_approved_asset_reference(asset_id, f"Shot {shot_id} prop", assets, report, {"prop", "vehicle", "animal"})
        character_bindings = shot.get("character_state_bindings")
        if not isinstance(character_bindings, dict):
            report.error("TYPE", f"{where}.character_state_bindings must map cast root asset ids to character state ids.")
            character_bindings = {}
        prop_bindings = shot.get("prop_state_bindings")
        if not isinstance(prop_bindings, dict):
            report.error("TYPE", f"{where}.prop_state_bindings must map prop root asset ids to prop state ids.")
            prop_bindings = {}
        if production_ready and set(character_bindings) != set(cast_ids):
            report.error("STATE_BINDING", f"Ready shot {shot_id} must bind exactly one character state for every cast root.")
        if production_ready and set(prop_bindings) != set(prop_ids):
            report.error("STATE_BINDING", f"Ready shot {shot_id} must bind exactly one prop state for every prop root.")
        for root_id, state_id in character_bindings.items():
            if not isinstance(root_id, str) or not isinstance(state_id, str):
                report.error("TYPE", f"{where}.character_state_bindings keys and values must be strings.")
                continue
            state = character_states.get(state_id)
            if state is None:
                report.error("MISSING_REFERENCE", f"Shot {shot_id} references missing character state {state_id}.")
                continue
            if production_ready and state.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"Ready shot {shot_id} uses non-approved character state {state_id}.")
            pack_id = assets.get(root_id, {}).get("identity_pack_id")
            if not pack_id or state.get("identity_pack_id") != pack_id or pack_id not in identity_packs:
                report.error("STATE_BINDING", f"Shot {shot_id} character state {state_id} does not belong to cast root {root_id}.")

        geometry_locks = shot.get("body_geometry_locks")
        if not isinstance(geometry_locks, dict):
            report.error("TYPE", f"{where}.body_geometry_locks must map cast roots to geometry locks.")
            geometry_locks = {}
        if production_ready and set(geometry_locks) != set(cast_ids):
            report.error("BODY_GEOMETRY_LOCK", f"Ready shot {shot_id} requires exactly one body-geometry lock per cast root.")
        for root_id, lock in geometry_locks.items():
            lock_where = f"{where}.body_geometry_locks.{root_id}"
            if not require_keys(
                lock,
                ("proportion_signature_id", "role_physique_brief_id", "character_state_id", "pose_projection", "critical_hand_detail", "digit_visibility", "relative_height_m"),
                lock_where,
                report,
            ):
                continue
            pack_id = assets.get(root_id, {}).get("identity_pack_id")
            pack = identity_packs.get(pack_id) if isinstance(pack_id, str) else None
            signature = pack.get("proportion_signature") if isinstance(pack, dict) else {}
            if lock.get("proportion_signature_id") != signature.get("id"):
                report.error("BODY_GEOMETRY_LOCK", f"Shot {shot_id} cast {root_id} must bind its approved proportion signature.")
            physique = pack.get("role_physique_brief") if isinstance(pack, dict) else {}
            if lock.get("role_physique_brief_id") != physique.get("id"):
                report.error("PHYSIQUE_LOCK", f"Shot {shot_id} cast {root_id} must bind its approved role-conditioned physique brief.")
            if lock.get("character_state_id") != character_bindings.get(root_id):
                report.error("BODY_GEOMETRY_LOCK", f"Shot {shot_id} cast {root_id} geometry lock must match its character state.")
            require_string(lock.get("pose_projection"), f"{lock_where}.pose_projection", report)
            if not isinstance(lock.get("critical_hand_detail"), bool):
                report.error("TYPE", f"{lock_where}.critical_hand_detail must be boolean.")
            if lock.get("digit_visibility") not in {"not_resolvable", "partially_resolvable", "fully_resolvable"}:
                report.error("ENUM", f"{lock_where}.digit_visibility is invalid: {lock.get('digit_visibility')}")
            if not is_number(lock.get("relative_height_m")) or lock.get("relative_height_m") <= 0:
                report.error("BODY_GEOMETRY_LOCK", f"{lock_where}.relative_height_m must be positive.")

        validate_multi_person_projection(
            shot.get("multi_person_projection"),
            shot_id=str(shot_id),
            cast_ids=[str(value) for value in cast_ids],
            geometry_locks=geometry_locks,
            production_ready=production_ready,
            where=f"{where}.multi_person_projection",
            report=report,
        )
        validate_dramatic_coverage_plan(
            shot.get("dramatic_coverage_plan"),
            shot_id=str(shot_id),
            cast_ids=[str(value) for value in cast_ids],
            production_ready=production_ready,
            where=f"{where}.dramatic_coverage_plan",
            report=report,
        )
        validate_subject_environment_integration(
            shot.get("subject_environment_integration"),
            shot_id=str(shot_id),
            has_human=bool(cast_ids),
            production_ready=production_ready,
            where=f"{where}.subject_environment_integration",
            report=report,
        )

        pose_anchor_ids = shot.get("pose_contact_anchor_ids")
        require_string_list(pose_anchor_ids, f"{where}.pose_contact_anchor_ids", report)
        if not isinstance(pose_anchor_ids, list):
            pose_anchor_ids = []
        if len(pose_anchor_ids) != len(set(pose_anchor_ids)):
            report.error("DUPLICATE_REFERENCE", f"Shot {shot_id} repeats a pose/contact anchor.")
        for pose_anchor_id in pose_anchor_ids:
            validate_approved_asset_reference(
                pose_anchor_id,
                f"Shot {shot_id} pose/contact anchor",
                assets,
                report,
                {"pose_contact_anchor"},
            )
        if production_ready and cast_ids and motion_class in {"action", "effects", "vehicle", "creature"} and not pose_anchor_ids:
            report.error("POSE_CONTACT_ANCHOR", f"High-risk shot {shot_id} requires at least one approved pose/contact anchor.")

        material_plan = shot.get("material_interaction_plan")
        if require_keys(
            material_plan,
            ("required", "contacts", "gravity", "collision", "landing", "material_response"),
            f"{where}.material_interaction_plan",
            report,
        ):
            if not isinstance(material_plan.get("required"), bool):
                report.error("TYPE", f"{where}.material_interaction_plan.required must be boolean.")
            require_string_list(material_plan.get("contacts"), f"{where}.material_interaction_plan.contacts", report)
            for field in ("gravity", "collision", "landing", "material_response"):
                require_string(material_plan.get(field), f"{where}.material_interaction_plan.{field}", report)
            if motion_class in PHYSICS_MOTION_CLASSES and material_plan.get("required") is not True:
                report.error("PHYSICS", f"Shot {shot_id} motion_class={motion_class} requires material interaction physics.")
        for root_id, state_id in prop_bindings.items():
            if not isinstance(root_id, str) or not isinstance(state_id, str):
                report.error("TYPE", f"{where}.prop_state_bindings keys and values must be strings.")
                continue
            state = prop_states.get(state_id)
            if state is None:
                report.error("MISSING_REFERENCE", f"Shot {shot_id} references missing prop state {state_id}.")
            elif state.get("root_prop_asset_id") != root_id:
                report.error("STATE_BINDING", f"Shot {shot_id} prop state {state_id} does not belong to prop root {root_id}.")
            elif production_ready and state.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"Ready shot {shot_id} uses non-approved prop state {state_id}.")
        location_state_id = shot.get("location_state_id")
        location_state = location_states.get(location_state_id) if isinstance(location_state_id, str) else None
        if production_ready:
            if location_state is None:
                report.error("MISSING_REFERENCE", f"Ready shot {shot_id} references missing location state {location_state_id}.")
            elif location_state.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"Ready shot {shot_id} uses non-approved location state {location_state_id}.")
            elif scene_id not in location_state.get("scene_ids", []):
                report.error("STATE_BINDING", f"Ready shot {shot_id} scene {scene_id} is not assigned to location state {location_state_id}.")
            if isinstance(location_state, dict):
                if location_state.get("environmental_state_id") != environment_id:
                    report.error("ENVIRONMENT_STATE", f"Shot {shot_id} environmental state conflicts with location state {location_state_id}.")
                if sorted(location_state.get("special_lighting_event_ids", [])) != sorted(special_event_ids):
                    report.error("SPECIAL_LIGHT", f"Shot {shot_id} special-light events conflict with location state {location_state_id}.")
        validate_approved_asset_reference(
            shot.get("location_asset_id"),
            f"Shot {shot_id} location",
            assets,
            report,
            {"location_plate"} if production_ready else {"location_master", "location_variant", "location_plate"},
        )
        if production_ready and isinstance(spatial_map, dict):
            anchor_id = str(spatial_map.get("primary_anchor", {}).get("asset_id", ""))
            if anchor_id not in prop_ids:
                report.error(
                    "SPATIAL_ANCHOR",
                    f"Ready shot {shot_id} must bind primary anchor {anchor_id} in prop_asset_ids, even when it is offscreen.",
                )
            location_asset = assets.get(shot.get("location_asset_id"), {})
            if location_asset.get("location_state_id") != location_state_id:
                report.error("STATE_BINDING", f"Shot {shot_id} location plate does not match location_state_id={location_state_id}.")
            if location_asset.get("spatial_map_id") != spatial_map_id:
                report.error(
                    "SPATIAL_MAP",
                    f"Shot {shot_id} location plate must inherit spatial map {spatial_map_id}.",
                )
            if location_asset.get("primary_anchor_asset_id") != anchor_id:
                report.error(
                    "SPATIAL_ANCHOR",
                    f"Shot {shot_id} location plate must inherit primary anchor {anchor_id}.",
                )
        for field in ("start_keyframe_id", "end_keyframe_id"):
            validate_approved_asset_reference(
                shot.get(field),
                f"Shot {shot_id} {field}",
                assets,
                report,
                {"keyframe", "storyboard"},
            )

        beats = shot.get("action_beats")
        if not isinstance(beats, list):
            report.error("TYPE", f"{where}.action_beats must be an array.")
            beats = []
        if production_ready and not beats:
            report.error("ACTION_TIMING", f"Ready shot {shot_id} requires at least one action beat.")
        normalized_beats: list[tuple[float, float]] = []
        last_end = 0.0
        movement_paths = spatial_map.get("movement_paths", []) if isinstance(spatial_map, dict) else []
        for beat_index, beat in enumerate(beats):
            beat_where = f"{where}.action_beats[{beat_index}]"
            if not require_keys(
                beat,
                (
                    "start_s",
                    "end_s",
                    "action",
                    "changes_position",
                    "subject_asset_id",
                    "start_mark_id",
                    "end_mark_id",
                ),
                beat_where,
                report,
            ):
                continue
            start = beat.get("start_s")
            end = beat.get("end_s")
            if not is_number(start) or not is_number(end) or start < 0 or end <= start:
                report.error("ACTION_TIMING", f"{beat_where} requires 0 <= start_s < end_s.")
                continue
            require_string(beat.get("action"), f"{beat_where}.action", report)
            changes_position = beat.get("changes_position")
            if not isinstance(changes_position, bool):
                report.error("TYPE", f"{beat_where}.changes_position must be boolean.")
            subject_id = beat.get("subject_asset_id")
            start_mark_id = beat.get("start_mark_id")
            end_mark_id = beat.get("end_mark_id")
            require_string(subject_id, f"{beat_where}.subject_asset_id", report, allow_empty=changes_position is not True)
            require_string(start_mark_id, f"{beat_where}.start_mark_id", report, allow_empty=changes_position is not True)
            require_string(end_mark_id, f"{beat_where}.end_mark_id", report, allow_empty=changes_position is not True)
            if changes_position is True:
                if subject_id not in cast_ids:
                    report.error(
                        "MOVEMENT_PATH",
                        f"{beat_where}.subject_asset_id must be a cast asset in shot {shot_id}.",
                    )
                for label, mark_id in (("start", start_mark_id), ("end", end_mark_id)):
                    mark = mark_index.get(mark_id) if isinstance(mark_id, str) else None
                    if not isinstance(mark, dict) or mark.get("kind") != "character" or mark.get("asset_id") != subject_id:
                        report.error(
                            "MOVEMENT_PATH",
                            f"{beat_where} {label} mark {mark_id} must be a character mark for {subject_id}.",
                        )
                if start_mark_id == end_mark_id:
                    report.error("MOVEMENT_PATH", f"{beat_where} positional movement requires distinct start and end marks.")
                matching_paths = [
                    path
                    for path in movement_paths
                    if isinstance(path, dict)
                    and path.get("subject_asset_id") == subject_id
                    and path.get("start_mark_id") == start_mark_id
                    and path.get("end_mark_id") == end_mark_id
                ]
                if not matching_paths:
                    report.error(
                        "MOVEMENT_PATH",
                        f"{beat_where} has no matching movement path in spatial map {spatial_map_id}.",
                    )
            if start < last_end - 0.001:
                report.error("ACTION_TIMING", f"{beat_where} overlaps the previous beat.")
            if duration and end > duration + 0.001:
                report.error("ACTION_TIMING", f"{beat_where} ends after shot duration {duration}.")
            normalized_beats.append((float(start), float(end)))
            last_end = max(last_end, float(end))
        if production_ready and normalized_beats:
            if normalized_beats[0][0] > 0.001:
                report.error("ACTION_TIMING", f"Ready shot {shot_id} action does not start at 0.0s.")
            for previous, current in zip(normalized_beats, normalized_beats[1:]):
                if current[0] > previous[1] + 0.001:
                    report.error("ACTION_TIMING", f"Ready shot {shot_id} has an uncovered interval {previous[1]}–{current[0]}s.")
            if duration and normalized_beats[-1][1] < float(duration) - 0.001:
                report.error("ACTION_TIMING", f"Ready shot {shot_id} action ends before duration {duration}s.")
        contact_risk = any(
            isinstance(beat, dict)
            and re.search(
                r"(?i)\b(?:grasp|grip|hold|touch|contact|strike|hit|fall|land|embrace|hug|weapon|handshake)\b|握|抓|触|撞|跌|落地|拥抱|持械",
                str(beat.get("action", "")),
            )
            for beat in beats
        )
        if production_ready and cast_ids and contact_risk and not pose_anchor_ids:
            report.error("POSE_CONTACT_ANCHOR", f"Shot {shot_id} contains a high-risk contact action and requires a pose/contact anchor.")

        audio = shot.get("audio")
        if require_keys(audio, ("dialogue", "ambience", "foley", "music", "silence"), f"{where}.audio", report):
            for field in ("dialogue", "ambience", "foley", "music", "silence"):
                require_string_list(audio.get(field), f"{where}.audio.{field}", report)
        if not isinstance(shot.get("adapter_notes"), dict):
            report.error("TYPE", f"{where}.adapter_notes must be an object.")

        prompt_path = check_relative_file(
            project_dir,
            shot.get("video_prompt_path"),
            f"{where}.video_prompt_path",
            report,
            required=production_ready,
        )
        if prompt_path:
            if not (
                portable_manifest_path(shot["video_prompt_path"]).startswith("prompts/video/")
                or is_compiled_prompt_path(shot.get("video_prompt_path"), "video")
            ):
                report.warning("PATH_CONVENTION", f"Shot prompt should live under prompts/video/: {shot['video_prompt_path']}")
            if production_ready:
                validate_prompt_sections(
                    prompt_path,
                    shot_id,
                    str(motion_class),
                    shot,
                    spatial_map,
                    format_plans.get(format_plan_id) if isinstance(format_plan_id, str) else None,
                    environmental_states.get(environment_id) if isinstance(environment_id, str) else None,
                    [special_lighting_events[event_id] for event_id in special_event_ids if event_id in special_lighting_events],
                    report,
                )

    for scene_id, scene_shots in production_shots_by_scene.items():
        axes = {
            shot.get("camera_axis")
            for shot in scene_shots
            if isinstance(shot.get("camera_axis"), str) and shot.get("camera_axis")
        }
        if len(axes) <= 1:
            continue
        scene = scenes.get(scene_id, {})
        spatial_map = spatial_maps.get(scene.get("spatial_map_id"))
        if not isinstance(spatial_map, dict) or spatial_map.get("status") != "approved":
            report.error(
                "LOCATION_MULTIVIEW_REQUIRED",
                f"Scene {scene_id} uses {len(axes)} camera axes but has no approved spatial map.",
            )
            continue
        view_ids = [spatial_map.get("side_three_quarter_view_asset_id")]
        additional_ids = spatial_map.get("additional_view_asset_ids")
        if isinstance(additional_ids, list):
            view_ids.extend(additional_ids)
        roles = {
            assets.get(asset_id, {}).get("view_role")
            for asset_id in view_ids
            if isinstance(asset_id, str)
        }
        side_asset = assets.get(spatial_map.get("side_three_quarter_view_asset_id"), {})
        if side_asset.get("view_role") == "side_three_quarter_wide":
            if side_asset.get("view_side") == "left":
                roles.add("left_three_quarter_wide")
            elif side_asset.get("view_side") == "right":
                roles.add("right_three_quarter_wide")
        missing_roles = sorted(LOCATION_MULTIVIEW_VIEWS - roles)
        if missing_roles:
            report.error(
                "LOCATION_MULTIVIEW_REQUIRED",
                f"Scene {scene_id} uses {len(axes)} camera axes and lacks independent approved spatial views: "
                f"{', '.join(missing_roles)}.",
            )

    return shots


def _shot_state_signature(shot: dict[str, Any]) -> dict[str, Any]:
    character_bindings = shot.get("character_state_bindings") if isinstance(shot.get("character_state_bindings"), dict) else {}
    prop_bindings = shot.get("prop_state_bindings") if isinstance(shot.get("prop_state_bindings"), dict) else {}
    return {
        "location_state_id": shot.get("location_state_id", ""),
        "environmental_state_id": shot.get("environmental_state_id", ""),
        "special_lighting_event_ids": sorted(str(value) for value in (shot.get("special_lighting_event_ids") or [])),
        "character_state_ids": sorted(str(value) for value in character_bindings.values()),
        "prop_state_ids": sorted(str(value) for value in prop_bindings.values()),
        "capture_profile_id": shot.get("capture_profile_id", ""),
        "format_plan_id": shot.get("format_plan_id", ""),
        "temporal_capture_signature": {
            key: (shot.get("temporal_capture") or {}).get(key)
            for key in ("capture_fps", "delivery_fps", "playback_rate", "shutter_angle")
        } if isinstance(shot.get("temporal_capture"), dict) else {},
        "lighting_state": (shot.get("adapter_notes") or {}).get("lighting_state", "")
        if isinstance(shot.get("adapter_notes"), dict) else "",
    }


def _sequence_reference_asset_ids(
    cluster_shots: list[dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    character_states: dict[str, dict[str, Any]],
    location_states: dict[str, dict[str, Any]],
    prop_states: dict[str, dict[str, Any]],
    spatial_maps: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    identity_packs: dict[str, dict[str, Any]],
    sequence_visual_anchor_asset_id: str,
    bridge_frame_asset_id: str,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(asset_id: Any) -> None:
        if not isinstance(asset_id, str) or not asset_id or asset_id in seen or asset_id not in assets:
            return
        seen.add(asset_id)
        ordered.append(asset_id)

    # Authorities are deliberately grouped by responsibility. This order is part
    # of the portable sequence contract and must not depend on dict ordering.
    for shot in cluster_shots:
        for root_id in shot.get("cast_asset_ids", []):
            pack_id = assets.get(root_id, {}).get("identity_pack_id")
            pack = identity_packs.get(pack_id, {})
            add(pack.get("identity_inspector_asset_id"))

    for shot in cluster_shots:
        for root_id in shot.get("cast_asset_ids", []):
            state_id = (shot.get("character_state_bindings") or {}).get(root_id)
            state = character_states.get(state_id, {})
            add(state.get("authority_asset_id"))

    for shot in cluster_shots:
        for pose_anchor_id in shot.get("pose_contact_anchor_ids", []):
            add(pose_anchor_id)

    for shot in cluster_shots:
        location_state = location_states.get(shot.get("location_state_id"), {})
        for asset_id in location_state.get("authority_asset_ids", []):
            add(asset_id)
        add(shot.get("location_asset_id"))
        spatial_map = spatial_maps.get(shot.get("spatial_map_id"), {})
        add(spatial_map.get("side_three_quarter_view_asset_id"))
        primary_anchor = spatial_map.get("primary_anchor") if isinstance(spatial_map.get("primary_anchor"), dict) else {}
        add(primary_anchor.get("asset_id"))

    for shot in cluster_shots:
        for root_id in shot.get("prop_asset_ids", []):
            add(root_id)
            state_id = (shot.get("prop_state_bindings") or {}).get(root_id)
            add(prop_states.get(state_id, {}).get("authority_asset_id"))

    for shot in cluster_shots:
        add(profiles.get(shot.get("capture_profile_id"), {}).get("approved_look_test_id"))

    add(sequence_visual_anchor_asset_id)
    add(bridge_frame_asset_id)

    for shot in cluster_shots:
        add(shot.get("start_keyframe_id"))
        add(shot.get("end_keyframe_id"))
    # Preserve any clean roots or authorities reachable only through a selected
    # state/frame. They follow the explicit role stack and never replace it.
    for asset_id in list(ordered):
        for dependency_id in _asset_dependency_ids(asset_id, assets):
            add(dependency_id)
    return ordered


def _reference_stack_sha256(reference_ids: list[str], assets: dict[str, dict[str, Any]]) -> str:
    """Hash ordered authority ids and their recorded output bytes, not machine paths."""
    payload: list[dict[str, str]] = []
    for asset_id in reference_ids:
        asset = assets.get(asset_id, {})
        provenance = asset.get("generation_provenance") if isinstance(asset.get("generation_provenance"), dict) else {}
        output = provenance.get("output") if isinstance(provenance.get("output"), dict) else {}
        payload.append({"asset_id": asset_id, "sha256": str(output.get("sha256") or "")})
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_sequences(
    data: dict[str, Any] | None,
    shots: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    character_states: dict[str, dict[str, Any]],
    location_states: dict[str, dict[str, Any]],
    prop_states: dict[str, dict[str, Any]],
    spatial_maps: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    identity_packs: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    clusters: dict[str, dict[str, Any]] = {}
    if data is None:
        return clusters
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/sequences.json.schema_version must be {SCHEMA_VERSION}.")
    adapters = data.get("provider_adapters")
    if not isinstance(adapters, dict) or not isinstance(adapters.get("higgsfield"), dict):
        report.error("PROVIDER_ADAPTER", "manifests/sequences.json requires a local Higgsfield provider adapter.")
    else:
        adapter = adapters["higgsfield"]
        if adapter.get("knowledge_snapshot") != HIGGSFIELD_KNOWLEDGE_SNAPSHOT:
            report.error("PROVIDER_ADAPTER", f"Higgsfield adapter snapshot must be {HIGGSFIELD_KNOWLEDGE_SNAPSHOT}.")
        if adapter.get("reference_limits") != HIGGSFIELD_ADAPTER_LIMITS:
            report.error("PROVIDER_ADAPTER", "Higgsfield reference limits must match the versioned local adapter table.")
        if adapter.get("camera_move_segment_limits") != HIGGSFIELD_CAMERA_MOVE_LIMITS:
            report.error("PROVIDER_ADAPTER", "Higgsfield camera-move limits must match the versioned local adapter table.")
        if adapter.get("official_profile_id") != HIGGSFIELD_OFFICIAL_PROFILE_ID:
            report.error("PROVIDER_ADAPTER", f"Higgsfield official profile must be {HIGGSFIELD_OFFICIAL_PROFILE_ID}.")
        if adapter.get("official_source_urls") != list(HIGGSFIELD_OFFICIAL_SOURCE_URLS):
            report.error("PROVIDER_ADAPTER", "Higgsfield official source URLs must match the versioned adapter evidence.")
        if adapter.get("strict_conformance") is not True:
            report.error("PROVIDER_ADAPTER", "Higgsfield strict_conformance must be true.")
        if adapter.get("default_target_workflow") != "cinema-studio-4" or adapter.get("default_target_model") != "seedance-2.5":
            report.error("PROVIDER_ADAPTER", "Higgsfield strict default must be Cinema Studio 4 with Seedance 2.5.")
        if adapter.get("prompt_sections") != list(VIDEO_PROMPT_HEADERS):
            report.error("PROVIDER_ADAPTER", "Higgsfield prompt sections must match the official Seedance 2.5 contract.")
    rows = data.get("sequence_clusters")
    if not isinstance(rows, list):
        report.error("TYPE", "manifests/sequences.json.sequence_clusters must be an array.")
        rows = []
    shot_to_cluster: dict[str, str] = {}
    for index, cluster in enumerate(rows):
        where = f"manifests/sequences.json.sequence_clusters[{index}]"
        required = (
            "id", "status", "scene_ids", "shot_ids", "state_signature", "first_keyframe_id", "end_keyframe_id",
            "bridge_from_sequence_id", "bridge_frame_asset_id", "target_workflow", "target_model",
            "official_conformance_profile_id", "reference_limit",
            "boundary_reason", "quality_profile_id", "sequence_visual_anchor_asset_id",
            "reference_order", "reference_stack_sha256", "approval_gate_id", "qa",
        )
        if not require_keys(cluster, required, where, report):
            continue
        cluster_id = cluster.get("id")
        if not require_string(cluster_id, f"{where}.id", report):
            continue
        if cluster_id in clusters:
            report.error("DUPLICATE_ID", f"Duplicate sequence cluster id: {cluster_id}")
        clusters[cluster_id] = cluster
        status = cluster.get("status")
        if status not in SEQUENCE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(cluster.get("quality_profile_id"), f"{where}.quality_profile_id", report)
        require_string(cluster.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        require_string_list(cluster.get("scene_ids"), f"{where}.scene_ids", report)
        require_string_list(cluster.get("shot_ids"), f"{where}.shot_ids", report)
        require_string(cluster.get("boundary_reason"), f"{where}.boundary_reason", report)
        target_workflow = cluster.get("target_workflow")
        if target_workflow not in HIGGSFIELD_ADAPTER_LIMITS:
            report.error("PROVIDER_ADAPTER", f"{where}.target_workflow is invalid: {target_workflow}")
            expected_limit = None
        else:
            expected_limit = HIGGSFIELD_ADAPTER_LIMITS[target_workflow]
        if cluster.get("reference_limit") != expected_limit:
            report.error("PROVIDER_ADAPTER", f"{where}.reference_limit must be {expected_limit} for {target_workflow}.")
        if target_workflow not in HIGGSFIELD_STRICT_WORKFLOWS:
            report.error("HIGGSFIELD_OFFICIAL_CONFORMANCE", f"{where}.target_workflow must be a current strict workflow: {sorted(HIGGSFIELD_STRICT_WORKFLOWS)}.")
        if cluster.get("target_model") != "seedance-2.5":
            report.error("HIGGSFIELD_OFFICIAL_CONFORMANCE", f"{where}.target_model must be seedance-2.5 for the published strict prompt contract.")
        if cluster.get("official_conformance_profile_id") != HIGGSFIELD_OFFICIAL_PROFILE_ID:
            report.error("HIGGSFIELD_OFFICIAL_CONFORMANCE", f"{where} must bind official profile {HIGGSFIELD_OFFICIAL_PROFILE_ID}.")
        signature = cluster.get("state_signature")
        signature_fields = (
            "location_state_id", "environmental_state_id", "special_lighting_event_ids",
            "character_state_ids", "prop_state_ids", "capture_profile_id", "format_plan_id",
            "temporal_capture_signature", "lighting_state",
        )
        if require_keys(signature, signature_fields, f"{where}.state_signature", report):
            require_string(signature.get("location_state_id"), f"{where}.state_signature.location_state_id", report)
            require_string(signature.get("environmental_state_id"), f"{where}.state_signature.environmental_state_id", report)
            require_string_list(signature.get("special_lighting_event_ids"), f"{where}.state_signature.special_lighting_event_ids", report)
            require_string_list(signature.get("character_state_ids"), f"{where}.state_signature.character_state_ids", report)
            require_string_list(signature.get("prop_state_ids"), f"{where}.state_signature.prop_state_ids", report)
            require_string(signature.get("capture_profile_id"), f"{where}.state_signature.capture_profile_id", report)
            require_string(signature.get("format_plan_id"), f"{where}.state_signature.format_plan_id", report)
            temporal_signature = signature.get("temporal_capture_signature")
            if require_keys(
                temporal_signature,
                ("capture_fps", "delivery_fps", "playback_rate", "shutter_angle"),
                f"{where}.state_signature.temporal_capture_signature",
                report,
            ):
                for field in ("capture_fps", "delivery_fps", "playback_rate", "shutter_angle"):
                    if not is_number(temporal_signature.get(field)):
                        report.error("TYPE", f"{where}.state_signature.temporal_capture_signature.{field} must be numeric.")
            require_string(signature.get("lighting_state"), f"{where}.state_signature.lighting_state", report)
        cluster_shots: list[dict[str, Any]] = []
        for shot_id in cluster.get("shot_ids", []) if isinstance(cluster.get("shot_ids"), list) else []:
            shot = shots.get(shot_id)
            if shot is None:
                report.error("MISSING_REFERENCE", f"Sequence {cluster_id} references missing shot {shot_id}.")
                continue
            cluster_shots.append(shot)
            if shot_id in shot_to_cluster:
                report.error("SEQUENCE_CLUSTER", f"Shot {shot_id} belongs to more than one sequence cluster.")
            shot_to_cluster[shot_id] = cluster_id
            if shot.get("sequence_cluster_id") != cluster_id:
                report.error("SEQUENCE_CLUSTER", f"Shot {shot_id} does not point back to sequence {cluster_id}.")
            if signature != _shot_state_signature(shot):
                report.error("SEQUENCE_STATE_MISMATCH", f"Shot {shot_id} state signature differs from sequence {cluster_id}.")
            adapter_notes = shot.get("adapter_notes") if isinstance(shot.get("adapter_notes"), dict) else {}
            higgsfield_notes = adapter_notes.get("higgsfield") if isinstance(adapter_notes.get("higgsfield"), dict) else {}
            camera_segments = higgsfield_notes.get("camera_path_segments")
            segment_count = len(camera_segments) if isinstance(camera_segments, list) else 1
            segment_limit = HIGGSFIELD_CAMERA_MOVE_LIMITS.get(str(target_workflow))
            if segment_limit is not None and segment_count > segment_limit:
                report.error(
                    "CAMERA_PATH_LIMIT",
                    f"Shot {shot_id} maps to {segment_count} Higgsfield camera segments but {target_workflow} allows {segment_limit}.",
                )
        actual_scene_ids = []
        cluster_duration = sum(
            float(shot.get("duration_s"))
            for shot in cluster_shots
            if is_number(shot.get("duration_s"))
        )
        if cluster_duration > 30.0 + 1e-9:
            report.error(
                "HIGGSFIELD_DURATION",
                f"Sequence {cluster_id} totals {cluster_duration:g} seconds; one Seedance 2.5 generation may not exceed the published 30-second maximum.",
            )
        for shot in cluster_shots:
            scene_id = shot.get("scene_id")
            if isinstance(scene_id, str) and scene_id not in actual_scene_ids:
                actual_scene_ids.append(scene_id)
        if cluster.get("scene_ids") != actual_scene_ids:
            report.error("SEQUENCE_CLUSTER", f"Sequence {cluster_id} scene_ids must follow first appearance in shot_ids.")
        for field in ("first_keyframe_id", "end_keyframe_id"):
            validate_approved_asset_reference(cluster.get(field), f"Sequence {cluster_id} {field}", assets, report, {"keyframe", "storyboard"})
        if cluster_shots:
            if cluster.get("first_keyframe_id") != cluster_shots[0].get("start_keyframe_id"):
                report.error("SEQUENCE_KEYFRAME", f"Sequence {cluster_id} first keyframe must match its first shot.")
            if cluster.get("end_keyframe_id") != cluster_shots[-1].get("end_keyframe_id"):
                report.error("SEQUENCE_KEYFRAME", f"Sequence {cluster_id} end keyframe must match its last shot.")
        bridge_from = cluster.get("bridge_from_sequence_id")
        bridge_frame = cluster.get("bridge_frame_asset_id")
        require_string(bridge_from, f"{where}.bridge_from_sequence_id", report, allow_empty=True)
        require_string(bridge_frame, f"{where}.bridge_frame_asset_id", report, allow_empty=True)
        if bool(bridge_from) != bool(bridge_frame):
            report.error("SEQUENCE_BRIDGE", f"Sequence {cluster_id} must set both bridge source and bridge frame, or neither.")
        if bridge_frame:
            validate_approved_asset_reference(bridge_frame, f"Sequence {cluster_id} bridge frame", assets, report, {"keyframe", "storyboard"})
        visual_anchor_id = cluster.get("sequence_visual_anchor_asset_id")
        require_string(visual_anchor_id, f"{where}.sequence_visual_anchor_asset_id", report)
        visual_anchor = assets.get(visual_anchor_id) if isinstance(visual_anchor_id, str) else None
        if visual_anchor is None:
            report.error("MISSING_REFERENCE", f"Sequence {cluster_id} references missing sequence visual anchor {visual_anchor_id}.")
        else:
            if visual_anchor.get("type") not in {"keyframe", "storyboard"}:
                report.error("REFERENCE_TYPE", f"Sequence visual anchor {visual_anchor_id} must be a keyframe or storyboard asset.")
            if visual_anchor.get("approval_gate_id") != cluster.get("approval_gate_id"):
                report.error("REVIEW_GATE", f"Sequence {cluster_id} and visual anchor {visual_anchor_id} must share approval_gate_id.")
            if visual_anchor.get("quality_profile_id") != cluster.get("quality_profile_id"):
                report.error("QUALITY_PROFILE", f"Sequence {cluster_id} and visual anchor {visual_anchor_id} must share quality_profile_id.")
            if status in {"ready", "generated", "selected", "superseded"} and visual_anchor.get("status") != "approved":
                report.error("UNAPPROVED_REFERENCE", f"Production sequence {cluster_id} requires an approved sequence visual anchor.")
            elif status in {"blocked", "planned"} and visual_anchor.get("status") not in {"qualified", "approved"}:
                report.error("UNAPPROVED_REFERENCE", f"Sequence {cluster_id} visual anchor must be qualified or approved.")
            visual_reference_ids = visual_anchor.get("reference_asset_ids") if isinstance(visual_anchor.get("reference_asset_ids"), list) else []
            visual_root_ids = visual_anchor.get("root_reference_ids") if isinstance(visual_anchor.get("root_reference_ids"), list) else []
            anchor_refs = set(visual_reference_ids) | set(visual_root_ids)
            required_anchor_refs: set[str] = set()
            if isinstance(signature, dict):
                for state_id in signature.get("character_state_ids", []):
                    authority_id = character_states.get(state_id, {}).get("authority_asset_id")
                    if isinstance(authority_id, str) and authority_id:
                        required_anchor_refs.add(authority_id)
                location_state = location_states.get(signature.get("location_state_id"), {})
                required_anchor_refs.update(
                    asset_id for asset_id in location_state.get("authority_asset_ids", [])
                    if isinstance(asset_id, str) and asset_id
                )
            for shot in cluster_shots:
                spatial_map = spatial_maps.get(shot.get("spatial_map_id"), {})
                primary_anchor = spatial_map.get("primary_anchor") if isinstance(spatial_map.get("primary_anchor"), dict) else {}
                anchor_asset_id = primary_anchor.get("asset_id")
                if isinstance(anchor_asset_id, str) and anchor_asset_id:
                    required_anchor_refs.add(anchor_asset_id)
            missing_anchor_refs = sorted(required_anchor_refs - anchor_refs)
            if missing_anchor_refs:
                report.error(
                    "SEQUENCE_VISUAL_ANCHOR",
                    f"Sequence visual anchor {visual_anchor_id} omits current state or spatial authorities: {', '.join(missing_anchor_refs)}.",
                )
        reference_ids = _sequence_reference_asset_ids(
            cluster_shots, assets, character_states, location_states, prop_states, spatial_maps, profiles,
            identity_packs, str(visual_anchor_id or ""), str(bridge_frame or "")
        )
        reference_order = cluster.get("reference_order")
        require_string_list(reference_order, f"{where}.reference_order", report)
        if reference_order != reference_ids:
            report.error(
                "REFERENCE_ORDER",
                f"Sequence {cluster_id} reference_order must match the deterministic v1.6 authority stack; "
                f"expected {reference_ids}, recorded {reference_order}.",
            )
        reference_stack_sha256 = cluster.get("reference_stack_sha256")
        if not _valid_sha256(reference_stack_sha256):
            report.error("HASH", f"{where}.reference_stack_sha256 must be a lowercase SHA-256.")
        elif reference_stack_sha256 != _reference_stack_sha256(reference_ids, assets):
            report.error("REFERENCE_STACK_HASH", f"Sequence {cluster_id} reference_stack_sha256 does not match its ordered authorities.")
        if is_integer(expected_limit) and len(reference_ids) > expected_limit:
            report.error(
                "REFERENCE_LIMIT",
                f"Sequence {cluster_id} needs {len(reference_ids)} references but {target_workflow} allows {expected_limit}; split the sequence or select a larger adapter.",
            )
        _validate_approval_qa(
            cluster.get("qa"), f"{where}.qa", "approved" if status in {"ready", "generated", "selected"} else str(status),
            (
                "state_uniformity", "identity_consistency", "location_world_consistency",
                "environment_continuity", "format_and_temporal_uniformity", "first_end_keyframes", "reference_budget",
            ), report,
        )

    for cluster_id, cluster in clusters.items():
        bridge_from = cluster.get("bridge_from_sequence_id")
        if bridge_from:
            previous = clusters.get(bridge_from)
            if previous is None:
                report.error("MISSING_REFERENCE", f"Sequence {cluster_id} bridges from missing sequence {bridge_from}.")
            elif cluster.get("bridge_frame_asset_id") != previous.get("end_keyframe_id"):
                report.error("SEQUENCE_BRIDGE", f"Sequence {cluster_id} bridge frame must equal {bridge_from}'s approved end keyframe.")
    production_shot_ids = {
        shot_id for shot_id, shot in shots.items() if shot.get("status") in PRODUCTION_SHOT_STATUSES
    }
    if set(shot_to_cluster) != production_shot_ids:
        missing = sorted(production_shot_ids - set(shot_to_cluster))
        extra = sorted(set(shot_to_cluster) - production_shot_ids)
        if missing:
            report.error("SEQUENCE_CLUSTER", f"Production shots lack sequence clusters: {', '.join(missing)}.")
        if extra:
            report.error("SEQUENCE_CLUSTER", f"Non-production shots appear in sequence clusters: {', '.join(extra)}.")
    return clusters


def validate_continuity(
    data: dict[str, Any] | None,
    scenes: dict[str, dict[str, Any]],
    scene_orders: dict[str, int],
    assets: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    effective_profiles: dict[str, str],
    report: Report,
) -> None:
    if data is None:
        return
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/continuity.json.schema_version must be {SCHEMA_VERSION}.")
    tracks = data.get("tracks")
    transitions = data.get("transitions")
    if not isinstance(tracks, list):
        report.error("TYPE", "manifests/continuity.json.tracks must be an array.")
        tracks = []
    if not isinstance(transitions, list):
        report.error("TYPE", "manifests/continuity.json.transitions must be an array.")
        transitions = []

    tracks_by_id: dict[str, dict[str, Any]] = {}
    states_by_track: dict[str, dict[str, dict[str, Any]]] = {}
    ordered_states: dict[str, list[dict[str, Any]]] = {}

    for index, track in enumerate(tracks):
        where = f"manifests/continuity.json.tracks[{index}]"
        if not require_keys(track, ("id", "kind", "subject_asset_id", "states"), where, report):
            continue
        track_id = track.get("id")
        if not require_string(track_id, f"{where}.id", report):
            continue
        if track_id in tracks_by_id:
            report.error("DUPLICATE_ID", f"Duplicate continuity track id: {track_id}")
        else:
            tracks_by_id[track_id] = track
        if track.get("kind") not in CONTINUITY_KINDS:
            report.error("ENUM", f"{where}.kind is invalid: {track.get('kind')}")
        subject = track.get("subject_asset_id")
        require_string(subject, f"{where}.subject_asset_id", report, allow_empty=True)
        validate_approved_asset_reference(subject, f"Continuity track {track_id} subject", assets, report)
        states = track.get("states")
        if not isinstance(states, list) or not states:
            report.error("TYPE", f"{where}.states must be a non-empty array.")
            continue
        state_map: dict[str, dict[str, Any]] = {}
        previous_order: int | None = None
        valid_states: list[dict[str, Any]] = []
        for state_index, state in enumerate(states):
            state_where = f"{where}.states[{state_index}]"
            if not require_keys(state, ("id", "scene_id", "value", "notes"), state_where, report):
                continue
            state_id = state.get("id")
            scene_id = state.get("scene_id")
            if not require_string(state_id, f"{state_where}.id", report):
                continue
            if state_id in state_map:
                report.error("DUPLICATE_ID", f"Track {track_id} repeats state id {state_id}.")
            else:
                state_map[state_id] = state
            if not require_string(scene_id, f"{state_where}.scene_id", report) or scene_id not in scenes:
                report.error("ORPHAN_SCENE", f"Continuity state {state_id} references missing scene {scene_id}.")
            require_string(state.get("value"), f"{state_where}.value", report)
            require_string(state.get("notes"), f"{state_where}.notes", report, allow_empty=True)
            order = scene_orders.get(scene_id) if isinstance(scene_id, str) else None
            if order is not None and previous_order is not None and order < previous_order:
                report.error("STATE_ORDER", f"Track {track_id} states are not ordered by scene.")
            if order is not None:
                previous_order = order
            if track.get("kind") == "capture_profile" and isinstance(state.get("value"), str):
                profile_id = state.get("value")
                profile = profiles.get(profile_id)
                if profile is None:
                    report.error("MISSING_REFERENCE", f"Continuity state {state_id} references missing Profile {profile_id}.")
                elif profile.get("status") != "approved":
                    report.error("UNAPPROVED_REFERENCE", f"Continuity state {state_id} references non-approved Profile {profile_id}.")
                expected = effective_profiles.get(scene_id) if isinstance(scene_id, str) else None
                if expected and profile_id != expected:
                    report.error(
                        "PROFILE_CONTINUITY",
                        f"Continuity state {state_id} uses Profile {profile_id}; scene {scene_id} requires {expected}.",
                    )
            valid_states.append(state)
        states_by_track[track_id] = state_map
        ordered_states[track_id] = valid_states

    transition_pairs: set[tuple[str, str, str]] = set()
    for index, transition in enumerate(transitions):
        where = f"manifests/continuity.json.transitions[{index}]"
        if not require_keys(transition, ("track_id", "from_state", "to_state", "at_scene_id", "cause"), where, report):
            continue
        for field in ("track_id", "from_state", "to_state", "at_scene_id", "cause"):
            require_string(transition.get(field), f"{where}.{field}", report)
        track_id = transition.get("track_id")
        from_state = transition.get("from_state")
        to_state = transition.get("to_state")
        if track_id not in tracks_by_id:
            report.error("MISSING_REFERENCE", f"Transition references missing track {track_id}.")
            continue
        states = states_by_track.get(track_id, {})
        if from_state not in states or to_state not in states:
            report.error("MISSING_REFERENCE", f"Transition {track_id}:{from_state}->{to_state} references a missing state.")
            continue
        if from_state == to_state:
            report.error("STATE_TRANSITION", f"Transition {track_id} cannot point a state to itself.")
        pair = (track_id, from_state, to_state)
        if pair in transition_pairs:
            report.error("DUPLICATE_TRANSITION", f"Duplicate transition {track_id}:{from_state}->{to_state}.")
        transition_pairs.add(pair)
        state_sequence = [state.get("id") for state in ordered_states.get(track_id, [])]
        if state_sequence.index(from_state) >= state_sequence.index(to_state):
            report.error("STATE_TRANSITION", f"Transition {track_id}:{from_state}->{to_state} does not move forward.")
        target_scene = states[to_state].get("scene_id")
        if transition.get("at_scene_id") != target_scene:
            report.error("STATE_TRANSITION", f"Transition {track_id}:{from_state}->{to_state} must occur at target scene {target_scene}.")
        if transition.get("at_scene_id") not in scenes:
            report.error("ORPHAN_SCENE", f"Transition references missing scene {transition.get('at_scene_id')}.")
        if states[from_state].get("value") == states[to_state].get("value"):
            report.warning("REDUNDANT_TRANSITION", f"Transition {track_id}:{from_state}->{to_state} does not change value.")

    for track_id, states in ordered_states.items():
        for previous, current in zip(states, states[1:]):
            if previous.get("value") != current.get("value"):
                pair = (track_id, previous.get("id"), current.get("id"))
                if pair not in transition_pairs:
                    report.error(
                        "MISSING_TRANSITION",
                        f"Track {track_id} changes from {previous.get('id')} to {current.get('id')} without a transition.",
                    )


def validate_takes(
    project_dir: Path,
    data: dict[str, Any] | None,
    shots: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    takes: dict[str, dict[str, Any]] = {}
    rows = validate_manifest_header(data, "takes", "manifests/takes.json", report)
    required = (
        "id", "shot_id", "status", "source_path", "source_provider", "automatic_platform_call",
        "credits_consumed_by_skill", "temporal_qa", "created_at",
    )
    for index, take in enumerate(rows):
        where = f"manifests/takes.json.takes[{index}]"
        if not require_keys(take, required, where, report):
            continue
        take_id = take.get("id")
        if not require_string(take_id, f"{where}.id", report):
            continue
        if take_id in takes:
            report.error("DUPLICATE_ID", f"Duplicate take id: {take_id}")
        takes[take_id] = take
        shot_id = take.get("shot_id")
        if not require_string(shot_id, f"{where}.shot_id", report) or shot_id not in shots:
            report.error("MISSING_REFERENCE", f"Take {take_id} references missing shot {shot_id}.")
        if take.get("status") not in {"candidate", "approved", "rejected", "superseded"}:
            report.error("ENUM", f"{where}.status is invalid: {take.get('status')}")
        require_string(take.get("source_provider"), f"{where}.source_provider", report)
        if take.get("automatic_platform_call") is not False or take.get("credits_consumed_by_skill") is not False:
            report.error("BOUNDARY", f"Take {take_id} must record that the Skill made no platform call and consumed no credits.")
        check_relative_file(project_dir, take.get("source_path"), f"{where}.source_path", report, required=True)
        if not valid_timestamp(take.get("created_at")):
            report.error("TIMESTAMP", f"{where}.created_at must be a timestamp.")
        temporal = take.get("temporal_qa")
        temporal_fields = (
            "sample_points", "event_samples", "checks", "verdict", "hard_failures", "notes",
            "checked_at", "reviewer",
        )
        if not require_keys(temporal, temporal_fields, f"{where}.temporal_qa", report):
            continue
        sample_points = temporal.get("sample_points")
        if not isinstance(sample_points, dict) or set(sample_points) != {"start", "25_percent", "50_percent", "75_percent", "end"}:
            report.error("TEMPORAL_QA", f"Take {take_id} requires start/25/50/75/end sample points.")
        elif any(not is_number(value) or value < 0 for value in sample_points.values()):
            report.error("TEMPORAL_QA", f"Take {take_id} sample-point times must be non-negative numbers.")
        events = temporal.get("event_samples")
        if not isinstance(events, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("event"), str)
            or not is_number(item.get("time_s"))
            for item in events
        ):
            report.error("TEMPORAL_QA", f"Take {take_id} event_samples must list event/time_s records.")
        checks = temporal.get("checks")
        if require_keys(checks, TEMPORAL_QA_CHECKS, f"{where}.temporal_qa.checks", report):
            for name in TEMPORAL_QA_CHECKS:
                if checks.get(name) not in {"pass", "fail"}:
                    report.error("ENUM", f"{where}.temporal_qa.checks.{name} must be pass or fail.")
        if temporal.get("verdict") not in {"pass", "fail"}:
            report.error("ENUM", f"{where}.temporal_qa.verdict is invalid: {temporal.get('verdict')}")
        require_string_list(temporal.get("hard_failures"), f"{where}.temporal_qa.hard_failures", report)
        require_string_list(temporal.get("notes"), f"{where}.temporal_qa.notes", report)
        if not valid_timestamp(temporal.get("checked_at")):
            report.error("TIMESTAMP", f"{where}.temporal_qa.checked_at must be a timestamp.")
        if "user_decision" in temporal or "user_decided_at" in temporal:
            report.error("APPROVAL_SCOPE", f"{where}.temporal_qa must not contain user decisions; use a review gate if selection is required.")
        if temporal.get("reviewer") != "codex-visual":
            report.error("TEMPORAL_QA", f"{where}.temporal_qa.reviewer must be codex-visual.")
        if take.get("status") == "approved":
            if temporal.get("verdict") != "pass" or temporal.get("hard_failures"):
                report.error("TEMPORAL_GATE", f"Approved take {take_id} must pass temporal QA with no hard failures.")
            if not isinstance(checks, dict) or any(checks.get(name) != "pass" for name in TEMPORAL_QA_CHECKS):
                report.error("TEMPORAL_GATE", f"Approved take {take_id} must pass every temporal QA check.")
    return takes


def validate_dynamic_range_plan(plan: Any, where: str, report: Report) -> bool:
    fields = (
        "policy",
        "working_latitude_stops",
        "upper_latitude_stops",
        "lower_latitude_stops",
        "scene_contrast_stops_estimate",
        "exposure_priority",
        "middle_gray_anchor",
        "highlight_behavior",
        "shadow_behavior",
        "allowed_clipping",
        "allowed_shadow_loss",
        "local_tone_mapping",
        "multi_exposure_hdr",
        "narrative_reason",
    )
    if not require_keys(plan, fields, where, report):
        return False
    if plan.get("policy") not in DYNAMIC_RANGE_POLICIES:
        report.error("DYNAMIC_RANGE", f"{where}.policy must be finite_scene_referred.")
    numeric_fields = (
        "working_latitude_stops",
        "upper_latitude_stops",
        "lower_latitude_stops",
        "scene_contrast_stops_estimate",
    )
    for field in numeric_fields:
        value = plan.get(field)
        if not is_number(value) or not 0 < float(value) <= 30:
            report.error("DYNAMIC_RANGE", f"{where}.{field} must be a positive finite stop value no greater than 30.")
    working = plan.get("working_latitude_stops")
    upper = plan.get("upper_latitude_stops")
    lower = plan.get("lower_latitude_stops")
    if all(is_number(value) for value in (working, upper, lower)) and abs(float(working) - float(upper) - float(lower)) > 0.1:
        report.error("DYNAMIC_RANGE", f"{where} upper and lower latitude must sum to working latitude.")
    priority = plan.get("exposure_priority")
    if priority not in DYNAMIC_RANGE_PRIORITIES:
        report.error("DYNAMIC_RANGE", f"{where}.exposure_priority is invalid: {priority}")
    for field in ("middle_gray_anchor", "highlight_behavior", "shadow_behavior", "narrative_reason"):
        require_string(plan.get(field), f"{where}.{field}", report)
    require_string_list(plan.get("allowed_clipping"), f"{where}.allowed_clipping", report)
    require_string_list(plan.get("allowed_shadow_loss"), f"{where}.allowed_shadow_loss", report)
    if plan.get("local_tone_mapping") is not False:
        report.error("DYNAMIC_RANGE", f"{where}.local_tone_mapping must be false; do not make every tonal region equally legible.")
    if plan.get("multi_exposure_hdr") is not False:
        report.error("DYNAMIC_RANGE", f"{where}.multi_exposure_hdr must be false for one real photographed event.")
    scene_contrast = plan.get("scene_contrast_stops_estimate")
    if is_number(scene_contrast) and is_number(working) and float(scene_contrast) > float(working):
        clipping = plan.get("allowed_clipping") if isinstance(plan.get("allowed_clipping"), list) else []
        shadow_loss = plan.get("allowed_shadow_loss") if isinstance(plan.get("allowed_shadow_loss"), list) else []
        if not clipping and not shadow_loss:
            report.error(
                "DYNAMIC_RANGE_SACRIFICE",
                f"{where} scene contrast exceeds working latitude but declares no highlight clipping or shadow loss.",
            )
    return True


def validate_quality_manifest(
    data: dict[str, Any] | None,
    assets: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    if data is None:
        return profiles
    required = (
        "schema_version",
        "quality_floor_id",
        "quality_floors",
        "project_quality_profiles",
        "live_action_integration_probes",
        "calibration_families",
    )
    if not require_keys(data, required, "manifests/quality.json", report):
        return profiles
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/quality.json.schema_version must be {SCHEMA_VERSION}.")
    if data.get("quality_floor_id") != QUALITY_FLOOR_ID:
        report.error("QUALITY_FLOOR", f"quality_floor_id must be {QUALITY_FLOOR_ID}.")
    floors = data.get("quality_floors")
    if not isinstance(floors, list):
        report.error("TYPE", "manifests/quality.json.quality_floors must be an array.")
        floors = []
    floor_by_id: dict[str, dict[str, Any]] = {}
    behavior_fields = (
        "photographic_event", "skin_response", "material_separation", "tone_and_contrast", "dynamic_range",
        "focus_and_optics", "set_causality", "performance_and_composition",
    )
    for index, floor in enumerate(floors):
        where = f"manifests/quality.json.quality_floors[{index}]"
        if not require_keys(
            floor,
            ("id", "status", "evidence_role", "direct_generation_reference", "source_note", "observable_behaviors"),
            where,
            report,
        ):
            continue
        floor_id = floor.get("id")
        if not require_string(floor_id, f"{where}.id", report):
            continue
        if floor_id in floor_by_id:
            report.error("DUPLICATE_ID", f"Duplicate quality floor id: {floor_id}")
        floor_by_id[floor_id] = floor
        if floor.get("status") != "stable":
            report.error("QUALITY_FLOOR", f"Quality floor {floor_id} must remain stable.")
        if floor.get("evidence_role") != "calibration_only" or floor.get("direct_generation_reference") is not False:
            report.error("QUALITY_REFERENCE_LEAK", f"Quality floor {floor_id} is calibration evidence only and may not be a generation reference.")
        require_string(floor.get("source_note"), f"{where}.source_note", report)
        behaviors = floor.get("observable_behaviors")
        if require_keys(behaviors, behavior_fields, f"{where}.observable_behaviors", report):
            for field in behavior_fields:
                require_string(behaviors.get(field), f"{where}.observable_behaviors.{field}", report)
    if QUALITY_FLOOR_ID not in floor_by_id:
        report.error("QUALITY_FLOOR", f"Missing quality floor {QUALITY_FLOOR_ID}.")

    probe_rows = data.get("live_action_integration_probes")
    if not isinstance(probe_rows, list):
        report.error("TYPE", "manifests/quality.json.live_action_integration_probes must be an array.")
        probe_rows = []
    probes: dict[str, dict[str, Any]] = {}
    probe_fields = (
        "id", "status", "approval_gate_id", "quality_profile_id", "identity_inspector_asset_id",
        "location_asset_id", "probe_asset_id", "prompt_strategy_id", "reference_asset_ids",
        "attempt_batch_count", "max_attempt_batches", "retry_changed_variable", "ordinary_light_only",
        "special_environment_disabled", "scales_checked", "ai_visual_verdict", "failure_classes",
        "evidence", "reviewer", "checked_at",
    )
    for index, probe in enumerate(probe_rows):
        where = f"manifests/quality.json.live_action_integration_probes[{index}]"
        if not require_keys(probe, probe_fields, where, report):
            continue
        probe_id = probe.get("id")
        if not require_string(probe_id, f"{where}.id", report):
            continue
        if probe_id in probes:
            report.error("DUPLICATE_ID", f"Duplicate live-action integration probe id: {probe_id}")
        probes[probe_id] = probe
        status = probe.get("status")
        if status not in LIVE_ACTION_PROBE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        require_string(probe.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        require_string(probe.get("quality_profile_id"), f"{where}.quality_profile_id", report)
        for field in ("identity_inspector_asset_id", "location_asset_id", "probe_asset_id"):
            require_string(probe.get(field), f"{where}.{field}", report, allow_empty=status == "planned")
        if probe.get("prompt_strategy_id") != "image2-live-action-integration-probe-v1.6":
            report.error("LIVE_ACTION_PROBE", f"Probe {probe_id} must use image2-live-action-integration-probe-v1.6.")
        references = probe.get("reference_asset_ids")
        require_string_list(references, f"{where}.reference_asset_ids", report)
        expected_references = [probe.get("identity_inspector_asset_id"), probe.get("location_asset_id")]
        if status != "planned" and references != expected_references:
            report.error(
                "LIVE_ACTION_PROBE_REFERENCE",
                f"Probe {probe_id} must reference the unified identity Inspector first and approved location root second, with no inherited failed image.",
            )
        attempts = probe.get("attempt_batch_count")
        if not is_integer(attempts) or attempts < 0 or attempts > 2:
            report.error("LIVE_ACTION_PROBE_ATTEMPTS", f"{where}.attempt_batch_count must be 0, 1, or 2.")
        if probe.get("max_attempt_batches") != 2:
            report.error("LIVE_ACTION_PROBE_ATTEMPTS", f"Probe {probe_id} must allow at most two independent batches.")
        require_string(
            probe.get("retry_changed_variable"),
            f"{where}.retry_changed_variable",
            report,
            allow_empty=attempts in {0, 1},
        )
        if attempts == 2 and not str(probe.get("retry_changed_variable") or "").strip():
            report.error("LIVE_ACTION_PROBE_ATTEMPTS", f"Probe {probe_id} second batch must name its one changed variable.")
        if probe.get("ordinary_light_only") is not True or probe.get("special_environment_disabled") is not True:
            report.error(
                "LIVE_ACTION_PROBE_STYLING",
                f"Probe {probe_id} must use ordinary broad source light with special weather, effects, grade, and lens signatures disabled.",
            )
        scales = probe.get("scales_checked")
        require_string_list(scales, f"{where}.scales_checked", report)
        if status in {"approved", "failed", "backend_realism_blocked"} and scales != list(LIVE_ACTION_PROBE_SCALES):
            report.error("LIVE_ACTION_PROBE_SCALE", f"Probe {probe_id} must be reviewed at all four fixed scales in order.")
        verdict = probe.get("ai_visual_verdict")
        if verdict not in {"pending", "pass", "fail"}:
            report.error("ENUM", f"{where}.ai_visual_verdict is invalid: {verdict}")
        failures = probe.get("failure_classes")
        require_string_list(failures, f"{where}.failure_classes", report)
        if isinstance(failures, list):
            unknown = [value for value in failures if value not in LIVE_ACTION_PROBE_FAILURE_CLASSES]
            if unknown:
                report.error("LIVE_ACTION_PROBE_FAILURE", f"Probe {probe_id} contains unknown failure classes: {unknown}")
        evidence = probe.get("evidence")
        if require_keys(evidence, LIVE_ACTION_PROBE_EVIDENCE_FIELDS, f"{where}.evidence", report):
            for field in LIVE_ACTION_PROBE_EVIDENCE_FIELDS:
                require_string(
                    evidence.get(field),
                    f"{where}.evidence.{field}",
                    report,
                    allow_empty=status in {"planned", "qualified"},
                )
        require_string(probe.get("reviewer"), f"{where}.reviewer", report, allow_empty=status in {"planned", "qualified"})
        require_string(probe.get("checked_at"), f"{where}.checked_at", report, allow_empty=status in {"planned", "qualified"})
        if status in {"approved", "failed", "backend_realism_blocked"} and not valid_timestamp(probe.get("checked_at")):
            report.error("TIMESTAMP", f"Probe {probe_id} requires a review timestamp.")

        identity_asset = assets.get(probe.get("identity_inspector_asset_id"))
        location_asset = assets.get(probe.get("location_asset_id"))
        probe_asset = assets.get(probe.get("probe_asset_id"))
        if status != "planned":
            if not identity_asset or identity_asset.get("type") != "character_identity_inspector" or identity_asset.get("status") != "approved":
                report.error("LIVE_ACTION_PROBE_REFERENCE", f"Probe {probe_id} requires an approved unified identity Inspector.")
            if not location_asset or location_asset.get("type") not in {"location_master", "location_variant"} or location_asset.get("status") != "approved":
                report.error("LIVE_ACTION_PROBE_REFERENCE", f"Probe {probe_id} requires an approved location authority.")
            if not probe_asset or probe_asset.get("type") != "live_action_probe":
                report.error("LIVE_ACTION_PROBE_ASSET", f"Probe {probe_id} references no live_action_probe asset.")
            elif (
                probe_asset.get("prompt_strategy_id") != probe.get("prompt_strategy_id")
                or probe_asset.get("reference_asset_ids") != references
                or probe_asset.get("surface_policy") != "clean_narrative"
            ):
                report.error("LIVE_ACTION_PROBE_ASSET", f"Probe asset {probe.get('probe_asset_id')} does not preserve the clean two-root diagnostic contract.")
        if status == "approved":
            if attempts not in {1, 2} or verdict != "pass" or failures:
                report.error("LIVE_ACTION_PROBE_GATE", f"Approved probe {probe_id} must pass with no hard failure class within two batches.")
            if not probe_asset or probe_asset.get("status") != "approved":
                report.error("LIVE_ACTION_PROBE_GATE", f"Approved probe {probe_id} requires an approved probe image asset.")
            elif not (
                live_action_quality_passed(probe_asset)
                and texture_qa_passed(probe_asset, require_user_approval=False)
                and photographic_qa_passed(probe_asset)
            ):
                report.error("LIVE_ACTION_PROBE_GATE", f"Approved probe asset {probe.get('probe_asset_id')} has not passed all visual evidence gates.")
        if status == "backend_realism_blocked":
            if attempts != 2 or verdict != "fail" or not failures:
                report.error("LIVE_ACTION_PROBE_BLOCK", f"Blocked probe {probe_id} requires two failed batches and explicit failure classes.")
            if probe_asset and probe_asset.get("status") != "model_blocked":
                report.error("LIVE_ACTION_PROBE_BLOCK", f"Blocked probe asset {probe.get('probe_asset_id')} must be model_blocked.")

    rows = data.get("project_quality_profiles")
    if not isinstance(rows, list):
        report.error("TYPE", "manifests/quality.json.project_quality_profiles must be an array.")
        rows = []
    profile_fields = (
        "id", "status", "quality_floor_id", "scope", "scene_ids", "sequence_ids", "approval_gate_id",
        "treatment_family", "environment_module_ids", "capture_circumstance",
        "illumination_contract", "skin_response_contract", "material_response_contract",
        "tone_contrast_contract", "dynamic_range_contract", "focus_optics_contract", "set_causality_contract",
        "performance_composition_contract", "polish_ceiling", "anchor_asset_ids",
        "calibration_family_ids", "live_action_probe_id",
    )
    for index, profile in enumerate(rows):
        where = f"manifests/quality.json.project_quality_profiles[{index}]"
        if not require_keys(profile, profile_fields, where, report):
            continue
        profile_id = profile.get("id")
        if not require_string(profile_id, f"{where}.id", report):
            continue
        if profile_id in profiles:
            report.error("DUPLICATE_ID", f"Duplicate quality profile id: {profile_id}")
        profiles[profile_id] = profile
        if profile.get("status") not in QUALITY_PROFILE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {profile.get('status')}")
        if profile.get("quality_floor_id") != QUALITY_FLOOR_ID:
            report.error("QUALITY_FLOOR", f"Quality profile {profile_id} must inherit {QUALITY_FLOOR_ID}.")
        if profile.get("scope") not in {"project", "sequence"}:
            report.error("ENUM", f"{where}.scope must be project or sequence.")
        require_string(profile.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        for field in ("scene_ids", "sequence_ids", "environment_module_ids", "anchor_asset_ids", "calibration_family_ids"):
            require_string_list(profile.get(field), f"{where}.{field}", report)
        if any(module not in ENVIRONMENT_MODULES for module in profile.get("environment_module_ids", []) if isinstance(module, str)):
            report.error("ENVIRONMENT_MODULE", f"Quality profile {profile_id} contains an unknown environment module.")
        for field in (
            "capture_circumstance", "illumination_contract", "skin_response_contract",
            "material_response_contract", "tone_contrast_contract", "focus_optics_contract",
            "set_causality_contract", "performance_composition_contract", "polish_ceiling",
        ):
            require_string(profile.get(field), f"{where}.{field}", report)
        validate_dynamic_range_plan(profile.get("dynamic_range_contract"), f"{where}.dynamic_range_contract", report)
        for asset_id in profile.get("anchor_asset_ids", []) if isinstance(profile.get("anchor_asset_ids"), list) else []:
            if asset_id not in assets:
                report.error("MISSING_REFERENCE", f"Quality profile {profile_id} references missing anchor {asset_id}.")
        probe_id = profile.get("live_action_probe_id")
        require_string(probe_id, f"{where}.live_action_probe_id", report, allow_empty=True)
        if probe_id:
            probe = probes.get(probe_id)
            if probe is None:
                report.error("LIVE_ACTION_PROBE", f"Quality profile {profile_id} references missing probe {probe_id}.")
            elif probe.get("quality_profile_id") != profile_id:
                report.error("LIVE_ACTION_PROBE", f"Probe {probe_id} and quality profile {profile_id} must point to each other.")

    calibrations = data.get("calibration_families")
    if not isinstance(calibrations, list):
        report.error("TYPE", "manifests/quality.json.calibration_families must be an array.")
        calibrations = []
    calibration_ids: set[str] = set()
    for index, family in enumerate(calibrations):
        where = f"manifests/quality.json.calibration_families[{index}]"
        if not require_keys(
            family,
            ("id", "kind", "name", "status", "evidence_runs", "pass_count", "total_count", "clean_fallback"),
            where,
            report,
        ):
            continue
        family_id = family.get("id")
        if not require_string(family_id, f"{where}.id", report):
            continue
        if family_id in calibration_ids:
            report.error("DUPLICATE_ID", f"Duplicate calibration family id: {family_id}")
        calibration_ids.add(family_id)
        kind = family.get("kind")
        name = family.get("name")
        if kind not in {"treatment", "environment"}:
            report.error("ENUM", f"{where}.kind must be treatment or environment.")
        if kind == "treatment" and name not in CINEMATIC_TREATMENT_FAMILIES - {"custom"}:
            report.error("CALIBRATION_FAMILY", f"Unknown treatment calibration name: {name}")
        if kind == "environment" and name not in ENVIRONMENT_MODULES:
            report.error("CALIBRATION_FAMILY", f"Unknown environment calibration name: {name}")
        if family.get("status") not in QUALITY_CALIBRATION_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {family.get('status')}")
        if family.get("clean_fallback") != "clean_digital_capture":
            report.error("CALIBRATION_FAMILY", f"Calibration family {family_id} must fall back to clean_digital_capture.")
        runs = family.get("evidence_runs")
        if not isinstance(runs, list):
            report.error("TYPE", f"{where}.evidence_runs must be an array.")
            runs = []
        for run_index, run in enumerate(runs):
            run_where = f"{where}.evidence_runs[{run_index}]"
            if not require_keys(run, ("round", "candidate_count", "pass_count", "selected_candidate_id"), run_where, report):
                continue
            if run.get("candidate_count") != 3 or not is_integer(run.get("pass_count")) or not 0 <= run.get("pass_count") <= 3:
                report.error("CALIBRATION_RUN", f"{run_where} requires three candidates and a pass_count from 0 to 3.")
        if family.get("status") == "stable":
            minimum = 5 if name == "naturalistic_dialogue" else 4
            if len(runs) != 2 or family.get("total_count") != 6 or not is_integer(family.get("pass_count")) or family.get("pass_count") < minimum:
                report.error("CALIBRATION_RELEASE", f"Stable family {family_id} requires two three-candidate runs and at least {minimum}/6 passes.")
            if any(run.get("pass_count", 0) < 2 for run in runs if isinstance(run, dict)):
                report.error("CALIBRATION_RELEASE", f"Stable family {family_id} requires at least 2/3 passes in each round.")

    for asset_id, asset in assets.items():
        if asset.get("status") == "planned" or asset.get("type") not in AUTHENTIC_ASSET_TYPES:
            continue
        profile_id = asset.get("quality_profile_id")
        profile = profiles.get(profile_id)
        if profile is None:
            report.error("QUALITY_PROFILE", f"Asset {asset_id} references missing quality profile {profile_id}.")
        elif asset.get("status") == "approved" and profile.get("status") != "approved":
            report.error("QUALITY_PROFILE", f"Approved asset {asset_id} requires an approved quality profile.")
        if (
            asset.get("status") == "approved"
            and (
                asset.get("type") == "live_action_probe"
                or (
                    asset.get("type") in {"look_test", "storyboard", "keyframe", "key_art"}
                    and (asset.get("identity_pack_id") or asset.get("character_state_id"))
                )
            )
        ):
            probe_id = profile.get("live_action_probe_id") if isinstance(profile, dict) else ""
            probe = probes.get(probe_id) if isinstance(probe_id, str) else None
            if not probe or probe.get("status") != "approved":
                report.error(
                    "LIVE_ACTION_PROBE_GATE",
                    f"Approved person-bearing narrative asset {asset_id} requires an approved ordinary-light live-action integration probe.",
                )
    return profiles


def validate_candidate_manifest(
    project_dir: Path,
    data: dict[str, Any] | None,
    assets: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    sets: dict[str, dict[str, Any]] = {}
    if data is None:
        return sets
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/candidates.json.schema_version must be {SCHEMA_VERSION}.")
    policy = data.get("policy")
    expected_policy = {
        "identity_inspector_initial_count": 1,
        "identity_inspector_max_batches": 1,
        "critical_initial_count": 3,
        "derivative_initial_count": 2,
        "retry_count": 2,
        "max_batches": 2,
        "failed_candidates_visible_by_default": False,
    }
    if policy != expected_policy:
        report.error("CANDIDATE_POLICY", "manifests/candidates.json.policy must match the v1.6 quality-first policy.")
    rows = data.get("candidate_sets")
    if not isinstance(rows, list):
        report.error("TYPE", "manifests/candidates.json.candidate_sets must be an array.")
        rows = []
    all_variant_ids: set[str] = set()
    for index, candidate_set in enumerate(rows):
        where = f"manifests/candidates.json.candidate_sets[{index}]"
        required = (
            "id", "target_asset_id", "tier", "status", "operation", "approval_gate_id",
            "prompt_path", "reference_asset_ids", "batches", "selected_candidate_id",
            "selection_reason", "reviewer", "reviewed_at",
        )
        if not require_keys(candidate_set, required, where, report):
            continue
        set_id = candidate_set.get("id")
        if not require_string(set_id, f"{where}.id", report):
            continue
        if set_id in sets:
            report.error("DUPLICATE_ID", f"Duplicate candidate set id: {set_id}")
        sets[set_id] = candidate_set
        target_id = candidate_set.get("target_asset_id")
        target = assets.get(target_id)
        if target is None:
            report.error("MISSING_REFERENCE", f"Candidate set {set_id} references missing target asset {target_id}.")
        elif target.get("candidate_set_id") != set_id:
            report.error("CANDIDATE_SET", f"Target asset {target_id} does not point back to candidate set {set_id}.")
        tier = candidate_set.get("tier")
        if tier == "identity_single_solve":
            if not target or target.get("type") != "character_identity_inspector":
                report.error("IDENTITY_INSPECTOR", f"Candidate set {set_id} with identity_single_solve tier must target one unified identity inspector.")
            if candidate_set.get("operation") != "generate" or candidate_set.get("reference_asset_ids"):
                report.error("IDENTITY_INSPECTOR", f"Identity inspector candidate set {set_id} must be one text-led generate with no prior generated identity references.")
        elif target and target.get("type") == "character_identity_inspector":
            report.error("IDENTITY_INSPECTOR", f"Unified identity inspector {target_id} must use candidate tier identity_single_solve.")
        if candidate_set.get("tier") not in CANDIDATE_TIERS:
            report.error("ENUM", f"{where}.tier is invalid: {candidate_set.get('tier')}")
        if candidate_set.get("status") not in CANDIDATE_SET_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {candidate_set.get('status')}")
        if candidate_set.get("operation") not in CANDIDATE_OPERATIONS:
            report.error("ENUM", f"{where}.operation is invalid: {candidate_set.get('operation')}")
        require_string(candidate_set.get("approval_gate_id"), f"{where}.approval_gate_id", report)
        if target and candidate_set.get("approval_gate_id") != target.get("approval_gate_id"):
            report.error("REVIEW_GATE", f"Candidate set {set_id} and target {target_id} must share approval_gate_id.")
        require_string_list(candidate_set.get("reference_asset_ids"), f"{where}.reference_asset_ids", report)
        if target and candidate_set.get("reference_asset_ids") != target.get("reference_asset_ids"):
            report.error("CANDIDATE_REFERENCE", f"Candidate set {set_id} reference order must match target asset {target_id}.")
        check_relative_file(project_dir, candidate_set.get("prompt_path"), f"{where}.prompt_path", report, required=candidate_set.get("status") != "planned")
        batches = candidate_set.get("batches")
        maximum_batches = 1 if candidate_set.get("tier") == "identity_single_solve" else 2
        if not isinstance(batches, list) or len(batches) > maximum_batches:
            report.error("CANDIDATE_BATCH", f"Candidate set {set_id} may contain at most {maximum_batches} batch(es).")
            if candidate_set.get("tier") == "identity_single_solve":
                report.error(
                    "IDENTITY_SINGLE_SOLVE",
                    f"Identity inspector {target_id} permits exactly one generation batch; a failed board must stop this identity.",
                )
            batches = []
        variants: list[dict[str, Any]] = []
        for batch_position, batch in enumerate(batches, start=1):
            batch_where = f"{where}.batches[{batch_position - 1}]"
            if not require_keys(batch, ("index", "reason", "changed_variable", "candidates"), batch_where, report):
                continue
            if batch.get("index") != batch_position:
                report.error("CANDIDATE_BATCH", f"{batch_where}.index must be {batch_position}.")
            require_string(batch.get("reason"), f"{batch_where}.reason", report)
            require_string(batch.get("changed_variable"), f"{batch_where}.changed_variable", report, allow_empty=batch_position == 1)
            candidates = batch.get("candidates")
            expected_count = (
                1 if candidate_set.get("tier") == "identity_single_solve"
                else (3 if candidate_set.get("tier") == "critical" else 2) if batch_position == 1
                else 2
            )
            if not isinstance(candidates, list) or len(candidates) != expected_count:
                report.error("CANDIDATE_COUNT", f"{batch_where} requires exactly {expected_count} independent candidates.")
                candidates = []
            for variant_index, variant in enumerate(candidates):
                variant_where = f"{batch_where}.candidates[{variant_index}]"
                fields = (
                    "id", "status", "path", "sha256", "operation", "derived_from_candidate_id",
                    "prompt_sha256", "reference_order", "quality_verdict", "hard_failures",
                    "diagnostic_regions", "reviewed_at",
                )
                if not require_keys(variant, fields, variant_where, report):
                    continue
                variant_id = variant.get("id")
                if not require_string(variant_id, f"{variant_where}.id", report):
                    continue
                if variant_id in all_variant_ids or variant_id in assets:
                    report.error("DUPLICATE_ID", f"Candidate variant id must be unique and absent from assets.json: {variant_id}")
                all_variant_ids.add(variant_id)
                if variant.get("status") not in CANDIDATE_VARIANT_STATUSES:
                    report.error("ENUM", f"{variant_where}.status is invalid: {variant.get('status')}")
                if variant.get("operation") != "generate" or variant.get("derived_from_candidate_id"):
                    report.error("CANDIDATE_INDEPENDENCE", f"Candidate {variant_id} must be an independent generate, never an edit or another candidate's derivative.")
                require_string_list(variant.get("reference_order"), f"{variant_where}.reference_order", report)
                if variant.get("reference_order") != candidate_set.get("reference_asset_ids"):
                    report.error("CANDIDATE_REFERENCE", f"Candidate {variant_id} reference order differs from its set.")
                if variant.get("quality_verdict") not in {"pass", "fail"}:
                    report.error("ENUM", f"{variant_where}.quality_verdict must be pass or fail.")
                require_string_list(variant.get("hard_failures"), f"{variant_where}.hard_failures", report)
                diagnostic_regions = variant.get("diagnostic_regions")
                diagnostic_kinds = ("face", "hands", "materials", "highlights", "shadows")
                if require_keys(diagnostic_regions, diagnostic_kinds, f"{variant_where}.diagnostic_regions", report):
                    for diagnostic_kind in diagnostic_kinds:
                        regions = diagnostic_regions.get(diagnostic_kind)
                        if not isinstance(regions, list):
                            report.error("TYPE", f"{variant_where}.diagnostic_regions.{diagnostic_kind} must be an array.")
                            continue
                        for region_index, region in enumerate(regions):
                            region_where = f"{variant_where}.diagnostic_regions.{diagnostic_kind}[{region_index}]"
                            if not require_keys(region, ("label", "x", "y", "width", "height"), region_where, report):
                                continue
                            require_string(region.get("label"), f"{region_where}.label", report)
                            for field in ("x", "y", "width", "height"):
                                value = region.get(field)
                                if not is_number(value) or not 0 <= float(value) <= 1:
                                    report.error("DIAGNOSTIC_REGION", f"{region_where}.{field} must be normalized from 0 to 1.")
                            if all(is_number(region.get(field)) for field in ("x", "y", "width", "height")):
                                if float(region["width"]) <= 0 or float(region["height"]) <= 0 or float(region["x"]) + float(region["width"]) > 1.000001 or float(region["y"]) + float(region["height"]) > 1.000001:
                                    report.error("DIAGNOSTIC_REGION", f"{region_where} must be a positive box inside the source image.")
                    if variant.get("status") in {"passed", "selected"}:
                        for diagnostic_kind in ("materials", "highlights", "shadows"):
                            if not diagnostic_regions.get(diagnostic_kind):
                                report.error("DIAGNOSTIC_REGION", f"Passing candidate {variant_id} requires at least one {diagnostic_kind} region.")
                path = check_relative_file(project_dir, variant.get("path"), f"{variant_where}.path", report, required=True)
                if not _valid_sha256(variant.get("sha256")):
                    report.error("HASH", f"{variant_where}.sha256 must be a lowercase SHA-256.")
                elif path and _sha256_file(path) != variant.get("sha256"):
                    report.error("HASH", f"Candidate {variant_id} file hash does not match its record.")
                if not _valid_sha256(variant.get("prompt_sha256")):
                    report.error("HASH", f"{variant_where}.prompt_sha256 must be a lowercase SHA-256.")
                if variant.get("status") in {"passed", "selected"} and (variant.get("quality_verdict") != "pass" or variant.get("hard_failures")):
                    report.error("CANDIDATE_QUALITY", f"Passing candidate {variant_id} has a failed quality record.")
                if variant.get("status") in {"failed", "discarded"} and variant.get("quality_verdict") != "fail":
                    report.error("CANDIDATE_QUALITY", f"Failed candidate {variant_id} must have quality_verdict=fail.")
                if not valid_timestamp(variant.get("reviewed_at")):
                    report.error("TIMESTAMP", f"{variant_where}.reviewed_at must be a timestamp.")
                variants.append(variant)
        if len(batches) == 2:
            first = batches[0].get("candidates") if isinstance(batches[0], dict) else []
            if not isinstance(first, list) or any(item.get("quality_verdict") == "pass" for item in first if isinstance(item, dict)):
                report.error("CANDIDATE_RETRY", f"Candidate set {set_id} may retry only when every first-batch candidate failed.")
            if not isinstance(batches[1], dict) or not str(batches[1].get("changed_variable", "")).strip():
                report.error("CANDIDATE_RETRY", f"Candidate set {set_id} retry batch requires one named changed_variable.")
        selected_id = candidate_set.get("selected_candidate_id")
        selected = [variant for variant in variants if variant.get("status") == "selected"]
        if candidate_set.get("status") == "selected":
            if len(selected) != 1 or selected[0].get("id") != selected_id:
                report.error("CANDIDATE_SELECTION", f"Candidate set {set_id} requires exactly one passing selected candidate.")
            if candidate_set.get("reviewer") != "codex-visual" or not valid_timestamp(candidate_set.get("reviewed_at")):
                report.error("CANDIDATE_SELECTION", f"Selected candidate set {set_id} requires Codex visual review and timestamp.")
            require_string(candidate_set.get("selection_reason"), f"{where}.selection_reason", report)
            if target and target.get("status") not in {"qualified", "approved", "rejected", "superseded"}:
                report.error("CANDIDATE_SELECTION", f"Selected set {set_id} targets incompatible asset status {target.get('status')}.")
            if selected and target:
                active_path = target.get("approved_path") if target.get("status") in {"approved", "superseded"} else target.get("candidate_path")
                active_file = check_relative_file(project_dir, active_path, f"asset {target_id} active path", report, required=True)
                if active_file and _sha256_file(active_file) != selected[0].get("sha256"):
                    report.error("CANDIDATE_SELECTION", f"Target asset {target_id} bytes do not match selected candidate {selected_id}.")
        if candidate_set.get("status") == "model_blocked":
            required_batches = 1 if candidate_set.get("tier") == "identity_single_solve" else 2
            if len(batches) != required_batches or any(variant.get("quality_verdict") == "pass" for variant in variants):
                report.error(
                    "MODEL_BLOCKED",
                    f"Candidate set {set_id} may be model_blocked only after {required_batches} all-fail batch(es).",
                )
            if target and target.get("status") != "model_blocked":
                report.error("MODEL_BLOCKED", f"Target asset {target_id} must also be model_blocked.")

    for asset_id, asset in assets.items():
        if asset.get("generator") != "builtin-imagegen" or asset.get("status") == "planned":
            continue
        set_id = asset.get("candidate_set_id")
        if set_id not in sets:
            report.error("CANDIDATE_SET", f"Generated asset {asset_id} references missing candidate set {set_id}.")
    return sets


def validate_review_manifest(
    project_dir: Path,
    data: dict[str, Any] | None,
    assets: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    treatments: dict[str, dict[str, Any]],
    format_plans: dict[str, dict[str, Any]],
    comparison_sets: dict[str, dict[str, Any]],
    sequences: dict[str, dict[str, Any]],
    candidate_sets: dict[str, dict[str, Any]],
    quality_profiles: dict[str, dict[str, Any]],
    report: Report,
) -> dict[str, dict[str, Any]]:
    gates: dict[str, dict[str, Any]] = {}
    if data is None:
        return gates
    if data.get("schema_version") != SCHEMA_VERSION:
        report.error("SCHEMA_VERSION", f"manifests/reviews.json.schema_version must be {SCHEMA_VERSION}.")
    rows = data.get("review_gates")
    if not isinstance(rows, list):
        report.error("TYPE", "manifests/reviews.json.review_gates must be an array.")
        rows = []
    scoped_assets: dict[str, str] = {}
    foundation_ids: list[str] = []
    for index, gate in enumerate(rows):
        where = f"manifests/reviews.json.review_gates[{index}]"
        fields = (
            "id", "type", "status", "sequence_cluster_id", "asset_ids", "profile_ids",
            "quality_profile_ids", "treatment_ids", "format_plan_ids", "comparison_set_ids", "candidate_set_ids",
            "review_board_path", "diagnostic_board_paths", "decision", "decision_notes", "decided_at", "selections",
            "affected_ids", "created_at",
        )
        if not require_keys(gate, fields, where, report):
            continue
        gate_id = gate.get("id")
        if not require_string(gate_id, f"{where}.id", report):
            continue
        if gate_id in gates:
            report.error("DUPLICATE_ID", f"Duplicate review gate id: {gate_id}")
        gates[gate_id] = gate
        gate_type = gate.get("type")
        status = gate.get("status")
        if gate_type not in REVIEW_GATE_TYPES:
            report.error("ENUM", f"{where}.type is invalid: {gate_type}")
        if status not in REVIEW_GATE_STATUSES:
            report.error("ENUM", f"{where}.status is invalid: {status}")
        if gate_type == "foundation":
            foundation_ids.append(gate_id)
            if gate.get("sequence_cluster_id"):
                report.error("REVIEW_GATE", f"Foundation gate {gate_id} must not bind a sequence.")
        elif gate_type == "sequence":
            sequence_id = gate.get("sequence_cluster_id")
            if sequence_id not in sequences:
                report.error("MISSING_REFERENCE", f"Sequence gate {gate_id} references missing sequence {sequence_id}.")
            elif sequences[sequence_id].get("approval_gate_id") != gate_id:
                report.error("REVIEW_GATE", f"Sequence {sequence_id} does not point back to gate {gate_id}.")
        for field in (
            "asset_ids", "profile_ids", "quality_profile_ids", "treatment_ids", "format_plan_ids", "comparison_set_ids",
            "candidate_set_ids", "decision_notes", "affected_ids",
        ):
            require_string_list(gate.get(field), f"{where}.{field}", report)
        for asset_id in gate.get("asset_ids", []) if isinstance(gate.get("asset_ids"), list) else []:
            if asset_id not in assets:
                report.error("MISSING_REFERENCE", f"Review gate {gate_id} references missing asset {asset_id}.")
                continue
            if asset_id in scoped_assets:
                report.error("REVIEW_GATE", f"Asset {asset_id} belongs to more than one review gate.")
            scoped_assets[asset_id] = gate_id
            if assets[asset_id].get("approval_gate_id") != gate_id:
                report.error("REVIEW_GATE", f"Asset {asset_id} does not point back to review gate {gate_id}.")
        for profile_id in gate.get("profile_ids", []) if isinstance(gate.get("profile_ids"), list) else []:
            profile = profiles.get(profile_id)
            if profile is None:
                report.error("MISSING_REFERENCE", f"Review gate {gate_id} references missing capture Profile {profile_id}.")
            elif profile.get("approval_gate_id") != gate_id:
                report.error("REVIEW_GATE", f"Capture Profile {profile_id} does not point back to review gate {gate_id}.")
        for profile_id in gate.get("quality_profile_ids", []) if isinstance(gate.get("quality_profile_ids"), list) else []:
            profile = quality_profiles.get(profile_id)
            if profile is None:
                report.error("MISSING_REFERENCE", f"Review gate {gate_id} references missing quality Profile {profile_id}.")
            elif profile.get("approval_gate_id") != gate_id:
                report.error("REVIEW_GATE", f"Quality Profile {profile_id} does not point back to review gate {gate_id}.")
        for treatment_id in gate.get("treatment_ids", []) if isinstance(gate.get("treatment_ids"), list) else []:
            treatment = treatments.get(treatment_id)
            if treatment is None:
                report.error("MISSING_REFERENCE", f"Review gate {gate_id} references missing Treatment {treatment_id}.")
            elif treatment.get("approval_gate_id") != gate_id:
                report.error("REVIEW_GATE", f"Treatment {treatment_id} does not point back to review gate {gate_id}.")
        for format_id in gate.get("format_plan_ids", []) if isinstance(gate.get("format_plan_ids"), list) else []:
            format_plan = format_plans.get(format_id)
            if format_plan is None:
                report.error("MISSING_REFERENCE", f"Review gate {gate_id} references missing format plan {format_id}.")
            elif format_plan.get("approval_gate_id") != gate_id:
                report.error("REVIEW_GATE", f"Format plan {format_id} does not point back to review gate {gate_id}.")
        for comparison_id in gate.get("comparison_set_ids", []) if isinstance(gate.get("comparison_set_ids"), list) else []:
            comparison = comparison_sets.get(comparison_id)
            if comparison is None:
                report.error("MISSING_REFERENCE", f"Review gate {gate_id} references missing Look comparison {comparison_id}.")
            elif comparison.get("approval_gate_id") != gate_id:
                report.error("REVIEW_GATE", f"Look comparison {comparison_id} does not point back to review gate {gate_id}.")
        for set_id in gate.get("candidate_set_ids", []) if isinstance(gate.get("candidate_set_ids"), list) else []:
            if set_id not in candidate_sets:
                report.error("MISSING_REFERENCE", f"Review gate {gate_id} references missing candidate set {set_id}.")
        board_required = status in {"ready_for_review", "approved", "changes_requested"}
        check_relative_file(project_dir, gate.get("review_board_path"), f"{where}.review_board_path", report, required=board_required)
        diagnostic_paths = gate.get("diagnostic_board_paths")
        diagnostic_kinds = ("face", "hands", "materials", "highlights", "shadows")
        if require_keys(diagnostic_paths, diagnostic_kinds, f"{where}.diagnostic_board_paths", report):
            for kind in diagnostic_kinds:
                path_value = diagnostic_paths.get(kind)
                require_string(path_value, f"{where}.diagnostic_board_paths.{kind}", report, allow_empty=not board_required)
                if path_value:
                    check_relative_file(project_dir, path_value, f"{where}.diagnostic_board_paths.{kind}", report, required=True)
        decision = gate.get("decision")
        if decision not in REVIEW_DECISIONS:
            report.error("ENUM", f"{where}.decision is invalid: {decision}")
        require_string(gate.get("decided_at"), f"{where}.decided_at", report, allow_empty=True)
        if not valid_timestamp(gate.get("created_at")):
            report.error("TIMESTAMP", f"{where}.created_at must be a timestamp.")
        selections = gate.get("selections")
        if not isinstance(selections, dict):
            report.error("TYPE", f"{where}.selections must be an object.")
            selections = {}
        if status == "approved":
            if decision != "approved" or not valid_timestamp(gate.get("decided_at")):
                report.error("REVIEW_GATE", f"Approved gate {gate_id} requires one timestamped user decision.")
        elif status == "changes_requested":
            if decision != "changes_requested" or not valid_timestamp(gate.get("decided_at")) or not gate.get("decision_notes"):
                report.error("REVIEW_GATE", f"Changes-requested gate {gate_id} requires timestamped notes.")
        elif decision != "pending":
            report.error("REVIEW_GATE", f"Gate {gate_id} status={status} must keep decision=pending.")
        for comparison_id, profile_id in selections.items():
            comparison = comparison_sets.get(comparison_id)
            if not isinstance(comparison, dict) or profile_id not in comparison.get("candidate_profile_ids", []):
                report.error("LOOK_BLIND_DECISION", f"Gate {gate_id} contains invalid Look selection {comparison_id}={profile_id}.")
            elif status == "approved" and comparison.get("selected_profile_id") != profile_id:
                report.error("LOOK_BLIND_DECISION", f"Gate {gate_id} selection does not match approved comparison {comparison_id}.")

    if assets and len(foundation_ids) != 1:
        report.error("REVIEW_GATE", "A populated v1.6 project requires exactly one foundation gate.")
    for asset_id, asset in assets.items():
        if asset.get("status") in {"planned", "model_blocked"}:
            continue
        gate_id = asset.get("approval_gate_id")
        gate = gates.get(gate_id)
        if gate is None:
            report.error("REVIEW_GATE", f"Asset {asset_id} references missing review gate {gate_id}.")
            continue
        if asset.get("status") in {"approved", "superseded"} and gate.get("status") != "approved":
            report.error("REVIEW_GATE", f"Approved asset {asset_id} requires an approved gate.")
        if asset.get("status") == "qualified" and gate.get("status") == "approved":
            report.error("REVIEW_GATE", f"Qualified asset {asset_id} must be promoted or rejected when gate {gate_id} is approved.")
    for profile_id, profile in quality_profiles.items():
        if profile.get("status") in {"planned", "blocked"}:
            continue
        gate_id = profile.get("approval_gate_id")
        gate = gates.get(gate_id)
        if gate is None:
            report.error("REVIEW_GATE", f"Quality Profile {profile_id} references missing review gate {gate_id}.")
            continue
        if profile_id not in gate.get("quality_profile_ids", []):
            report.error("REVIEW_GATE", f"Quality Profile {profile_id} is absent from gate {gate_id} scope.")
        if profile.get("status") in {"approved", "superseded"} and gate.get("status") != "approved":
            report.error("REVIEW_GATE", f"Approved quality Profile {profile_id} requires an approved gate.")
    return gates


def validate_project(project_dir: Path, as_json: bool) -> int:
    if not project_dir.is_dir():
        message = f"Project directory does not exist: {project_dir}"
        if as_json:
            print(json.dumps({"valid": False, "errors": [{"code": "NO_PROJECT", "message": message}], "warnings": []}, indent=2))
        else:
            print(f"ERROR: {message}", file=sys.stderr)
        return 2

    project_dir = project_dir.resolve()
    report = Report()
    project = load_json(project_dir / "project.json", "project.json", report)
    if project is not None and project.get("schema_version") in LEGACY_SCHEMA_VERSIONS:
        legacy_version = project.get("schema_version")
        report.error(
            "LEGACY_SCHEMA",
            f"Project uses schema {legacy_version}; cinematic-ai-director v1.6 will not migrate or modify v1.0-v1.5 projects.",
        )
        result = {
            "valid": False,
            "project": str(project_dir),
            "errors": report.errors,
            "warnings": report.warnings,
        }
        if as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"INVALID: {project_dir}")
            print(f"Errors: {len(report.errors)}  Warnings: {len(report.warnings)}")
            for item in report.errors:
                print(f"[ERROR {item['code']}] {item['message']}")
        return 1

    validate_layout(project_dir, report)
    scenes, scene_orders = validate_project_metadata(project, report)
    assets_data = load_json(project_dir / "manifests/assets.json", "assets manifest", report)
    cinematography_data = load_json(
        project_dir / "manifests/cinematography.json", "cinematography manifest", report
    )
    spatial_data = load_json(project_dir / "manifests/spatial.json", "spatial manifest", report)
    shots_data = load_json(project_dir / "manifests/shots.json", "shots manifest", report)
    continuity_data = load_json(project_dir / "manifests/continuity.json", "continuity manifest", report)
    identities_data = load_json(project_dir / "manifests/identities.json", "identities manifest", report)
    world_state_data = load_json(project_dir / "manifests/world-state.json", "world-state manifest", report)
    sequences_data = load_json(project_dir / "manifests/sequences.json", "sequences manifest", report)
    takes_data = load_json(project_dir / "manifests/takes.json", "takes manifest", report)
    quality_data = load_json(project_dir / "manifests/quality.json", "quality manifest", report)
    candidates_data = load_json(project_dir / "manifests/candidates.json", "candidates manifest", report)
    reviews_data = load_json(project_dir / "manifests/reviews.json", "reviews manifest", report)
    assets = validate_assets(project_dir, assets_data, set(scenes), report)
    quality_profiles = validate_quality_manifest(quality_data, assets, report)
    candidate_sets = validate_candidate_manifest(project_dir, candidates_data, assets, report)
    identity_packs, character_states = validate_identities(project_dir, identities_data, assets, report)
    (
        location_worlds,
        location_states,
        prop_states,
        environmental_states,
        special_lighting_events,
    ) = validate_world_state(world_state_data, assets, report)
    spatial_maps = validate_spatial(spatial_data, scenes, assets, report)
    (
        profiles,
        base_profile_id,
        comparison_sets,
        treatments,
        format_plans,
        medium_signatures,
    ) = validate_cinematography(
        project_dir, cinematography_data, scenes, assets, spatial_maps, report
    )
    effective_profiles = validate_capture_dependencies(
        project,
        scenes,
        assets,
        profiles,
        base_profile_id,
        comparison_sets,
        spatial_maps,
        format_plans,
        medium_signatures,
        report,
    )
    shots = validate_shots(
        project_dir,
        shots_data,
        scenes,
        assets,
        spatial_maps,
        profiles,
        effective_profiles,
        identity_packs,
        character_states,
        location_states,
        prop_states,
        format_plans,
        environmental_states,
        special_lighting_events,
        quality_profiles,
        report,
    )
    sequences = validate_sequences(
        sequences_data,
        shots,
        assets,
        character_states,
        location_states,
        prop_states,
        spatial_maps,
        profiles,
        identity_packs,
        report,
    )
    validate_review_manifest(
        project_dir,
        reviews_data,
        assets,
        profiles,
        treatments,
        format_plans,
        comparison_sets,
        sequences,
        candidate_sets,
        quality_profiles,
        report,
    )
    validate_takes(project_dir, takes_data, shots, report)
    validate_continuity(
        continuity_data, scenes, scene_orders, assets, profiles, effective_profiles, report
    )

    result = {
        "valid": not report.errors,
        "project": str(project_dir),
        "errors": report.errors,
        "warnings": report.warnings,
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "VALID" if result["valid"] else "INVALID"
        print(f"{status}: {project_dir}")
        print(f"Errors: {len(report.errors)}  Warnings: {len(report.warnings)}")
        for item in report.errors:
            print(f"[ERROR {item['code']}] {item['message']}")
        for item in report.warnings:
            print(f"[WARNING {item['code']}] {item['message']}")
    return 0 if result["valid"] else 1


__all__ = [name for name in globals() if not name.startswith("__")]
