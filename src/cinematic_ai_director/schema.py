#!/usr/bin/env python3
"""Initialize, validate, review, and export cinematic-ai-director project packages.

The script is intentionally offline and uses only the Python standard library.
"""

from __future__ import annotations

# These standard-library names form the deliberately dependency-free shared
# runtime namespace consumed by the compatibility modules through schema's
# public star export.  Keep the bundle explicit even when a name is not used in
# this file itself.
import argparse  # noqa: F401
import csv  # noqa: F401
import hashlib  # noqa: F401
import json  # noqa: F401
import math  # noqa: F401
import re  # noqa: F401
import shutil  # noqa: F401
import struct  # noqa: F401
import subprocess  # noqa: F401
import sys  # noqa: F401
import tempfile  # noqa: F401
import zlib  # noqa: F401
from collections import defaultdict  # noqa: F401
from datetime import datetime, timezone  # noqa: F401
from pathlib import Path  # noqa: F401
from typing import Any  # noqa: F401

SCHEMA_VERSION = "1.6"
LEGACY_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
ASPECT_RE = re.compile(r"^[1-9][0-9]*:[1-9][0-9]*$")

REQUIRED_DIRS = (
    "assets/style",
    "assets/characters",
    "assets/characters/identity-inspectors",
    "assets/characters/identity-packs",
    "assets/characters/identity-views",
    "assets/characters/pose-anchors",
    "assets/characters/states",
    "assets/reference-boards",
    "assets/look-tests",
    "assets/candidates",
    "assets/quality-evidence",
    "assets/quality-evidence/live-action-probes",
    "assets/review-boards",
    "assets/locations",
    "assets/locations/state-views",
    "assets/locations/plates",
    "assets/props",
    "assets/storyboards",
    "assets/keyframes",
    "assets/key-art",
    "manifests",
    "prompts/images",
    "prompts/images/look-tests",
    "prompts/images/identity-packs",
    "prompts/images/identity-inspectors",
    "prompts/images/identity-views",
    "prompts/images/pose-anchors",
    "prompts/images/states",
    "prompts/video",
    "prompts/compiled",
    "qa",
)
REQUIRED_FILES = (
    "project.json",
    "creative-bible.md",
    "edit-plan.md",
    "manifests/assets.json",
    "manifests/cinematography.json",
    "manifests/spatial.json",
    "manifests/shots.json",
    "manifests/continuity.json",
    "manifests/identities.json",
    "manifests/world-state.json",
    "manifests/sequences.json",
    "manifests/takes.json",
    "manifests/quality.json",
    "manifests/candidates.json",
    "manifests/reviews.json",
    "qa/asset-review.md",
    "qa/cinematography-review.md",
    "qa/spatial-review.md",
    "qa/shot-review.md",
    "qa/cross-scene-review.md",
    "qa/proportion-review.md",
    "qa/quality-review.md",
    "qa/live-action-integration-review.md",
    "qa/environment-review.md",
    "qa/temporal-review.md",
)

ASSET_TYPES = {
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
    "location_plate",
    "look_test",
    "prop",
    "prop_state",
    "vehicle",
    "animal",
    "pose_contact_anchor",
    "live_action_probe",
    "reference_board",
    "storyboard",
    "keyframe",
    "key_art",
    "title_card",
    "other",
}
ASSET_STATUSES = {"planned", "qualified", "approved", "rejected", "superseded", "model_blocked"}
ASSET_GENERATORS = {"builtin-imagegen", "provided", "deterministic-crop"}
ASSET_MODES = {"generate", "edit", "provided", "crop"}

SHOT_STATUSES = {"planned", "blocked", "ready", "generated", "selected", "rejected", "superseded"}
PRODUCTION_SHOT_STATUSES = {"ready", "generated", "selected"}
MOTION_CLASSES = {"static", "dialogue", "performance", "action", "effects", "vehicle", "creature"}
PHYSICS_MOTION_CLASSES = {"action", "effects", "vehicle", "creature"}

CONTINUITY_KINDS = {
    "character_identity",
    "character_state",
    "wardrobe",
    "injury",
    "prop_state",
    "prop_position",
    "spatial_anchor_state",
    "spatial_anchor_position",
    "location_time",
    "location_weather",
    "location_wb",
    "capture_profile",
    "proportion_signature",
    "environmental_state",
    "special_lighting_event",
    "format_plan",
    "temporal_capture",
    "motion_blur",
    "palette",
    "motif",
    "gesture",
    "story_payoff",
}

# Higgsfield's current Seedance 2.5 guide publishes this exact prompt order.
# Internal QA and reconstruction facts remain in JSON; the model-facing prompt
# uses only these supported, visible sections.
VIDEO_PROMPT_HEADERS = (
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

IMAGE_PROMPT_SECTIONS = (
    "PHOTOGRAPHIC EVENT",
    "APPROVED IDENTITY WORLD AND STATE",
    "PHYSICAL CAMERA AND BLOCKING",
    "SOURCE LIGHT AND MATERIAL RESPONSE",
    "FOCUS EXPOSURE AND CONTINGENCY",
    "EXCLUSIONS",
)
IMAGE_PROMPT_STRATEGIES = {
    f"image2-live-action-{family}-v1.6": IMAGE_PROMPT_SECTIONS
    for family in (
        "identity-inspector", "character-face", "character-body", "identity-view", "character-state",
        "location", "object", "pose-contact", "integration-probe", "locked-insertion-probe", "narrative",
    )
}
IMAGE_PROMPT_STRATEGIES["image2-live-action-identity-inspector-v1.6.6"] = IMAGE_PROMPT_SECTIONS
IMAGE_PROMPT_STRATEGY_BY_TYPE = {
    "character_identity_inspector": "image2-live-action-identity-inspector-v1.6.6",
    "character_face_anchor": "image2-live-action-character-face-v1.6",
    "character_body_anchor": "image2-live-action-character-body-v1.6",
    "character_identity_view": "image2-live-action-identity-view-v1.6",
    "character_variant": "image2-live-action-character-state-v1.6",
    "character_state": "image2-live-action-character-state-v1.6",
    "location_master": "image2-live-action-location-v1.6",
    "location_variant": "image2-live-action-location-v1.6",
    "location_plate": "image2-live-action-narrative-v1.6",
    "prop": "image2-live-action-object-v1.6",
    "prop_state": "image2-live-action-object-v1.6",
    "vehicle": "image2-live-action-object-v1.6",
    "animal": "image2-live-action-object-v1.6",
    "pose_contact_anchor": "image2-live-action-pose-contact-v1.6",
    "live_action_probe": "image2-live-action-locked-insertion-probe-v1.6",
    "look_test": "image2-live-action-narrative-v1.6",
    "storyboard": "image2-live-action-narrative-v1.6",
    "keyframe": "image2-live-action-narrative-v1.6",
    "key_art": "image2-live-action-narrative-v1.6",
}

PROFILE_STATUSES = {"planned", "qualified", "approved", "rejected", "superseded"}
PROFILE_SCOPES = {"project", "scene_group", "scene"}
CINEMATIC_TREATMENT_FAMILIES = {
    "naturalistic_dialogue",
    "nocturnal_crime",
    "grounded_horror",
    "period_reconstruction",
    "epic_environment",
    "kinetic_action",
    "intimate_romance",
    "precision_commercial",
    "performance_mv",
    "archive_surveillance",
    "custom",
}
FORMAT_PLAN_STATUSES = {"planned", "qualified", "approved", "rejected", "superseded"}
FORMAT_PLAN_SCOPES = {"project", "sequence"}
CAPTURE_MEDIA = {"digital", "35mm", "16mm", "super8"}
OPTICAL_PROJECTIONS = {"spherical", "anamorphic"}
COMPARISON_STATUSES = {"planned", "qualified", "approved", "rejected", "superseded"}
PHOTO_QA_MODES = {"pending", "reference_photo", "cinematic_frame", "optical_graphic"}
PHOTO_QA_RESULTS = {"pending", "pass", "fail"}
PHOTO_QA_CHECKS = (
    "capture_plausibility",
    "optical_coherence",
    "exposure_lighting",
    "material_skin",
    "texture_locality",
    "profile_continuity",
)
AUTHENTICITY_QA_MODES = {"pending", "neutral_reference", "narrative_frame"}
AUTHENTICITY_RESULTS = {"pending", "pass", "fail"}
AUTHENTICITY_CHECKS = (
    "casting_specificity",
    "human_surface",
    "set_causality",
    "lighting_causality",
    "composition_contingency",
    "material_contact",
    "artifact_absence",
    "brief_fit",
)
AUTHENTICITY_USER_DECISIONS = {"pending", "approved", "rejected"}
AUTHENTICITY_ESCALATIONS = {"none", "retry", "real_reference_required"}
TEXTURE_QA_MODES = {"pending", "clean_authority", "clean_narrative", "calibrated_medium_signature", "not_applicable"}
TEXTURE_QA_RESULTS = {"pending", "pass", "fail", "not_applicable"}
TEXTURE_QA_CHECKS = (
    "painterly_smear_or_low_frequency_blur",
    "repeating_swirl_scale_fingerprint_or_cellular_pattern",
    "cross_material_texture_leakage",
    "skin_hair_and_fabric_scale",
    "oversharpen_halos_specks_and_dirty_shadows",
    "localized_defect_bounds",
    "resampling_compression_and_color_mode",
)
TEXTURE_QA_SCALES = ("thumbnail", "fit", "100_percent", "200_percent")
SURFACE_POLICIES = {"clean_authority", "clean_narrative", "calibrated_medium_signature", "not_applicable"}
GENERATION_BACKENDS = {"builtin-imagegen", "provided", "deterministic-crop"}
REPRODUCIBILITY_CLASSES = {"workflow_only", "source_exact"}
RISKY_TEXTURE_CUES = (
    "weathered",
    "worn",
    "gritty",
    "tactile texture",
    "patina",
    "fingerprints",
    "pores",
    "film grain",
    "microtexture",
    "ultra-detailed",
    "8k",
)
RISKY_RENDER_CUES = (
    "teal-and-orange",
    "teal and orange",
    "beautiful rim light",
    "dramatic rim light",
    "cinematic rim light",
    "hero lighting",
    "heroic composition",
    "heroic pose",
    "poster pose",
    "promo pose",
    "key art pose",
    "perfect composition",
    "premium cinematic",
    "cinematic skin",
    "glossy skin",
    "skin glow",
    "beauty lighting",
    "cinematic contrast",
    "crunchy contrast",
    "clarity boost",
    "hdr look",
    "hdr lighting",
    "volumetric haze",
    "epic lighting",
    "game cinematic",
    "game-cinematic",
    "trailer still",
    "award-winning cinematography",
)
LIVE_ACTION_PROBE_STATUSES = {
    "planned",
    "qualified",
    "approved",
    "failed",
    "backend_realism_blocked",
}
LIVE_ACTION_PROBE_FAILURE_CLASSES = {
    "synthetic_person_rendering",
    "oily_waxy_or_plastic_skin",
    "person_world_cutout",
    "separate_subject_tone_mapping",
    "shared_light_failure",
    "shared_focus_or_occlusion_failure",
    "repeating_artifact_texture",
    "topographic_contour_or_maze_skin_texture",
    "body_geometry_or_contact_failure",
    "finite_dynamic_range_failure",
    "scene_geometry_or_fixture_drift",
    "unbounded_background_edit",
}
LIVE_ACTION_PROBE_SCALES = ("thumbnail", "fit", "100_percent", "200_percent")
LIVE_ACTION_PROBE_EVIDENCE_FIELDS = (
    "face_and_skin_readable",
    "task_contact_readable",
    "shared_light",
    "shared_focus_and_occlusion",
    "finite_dynamic_range",
    "skin_material_separation",
    "locked_scene_correspondence",
)
LOCKED_SCENE_QA_CHECKS = (
    "camera_projection_and_crop",
    "table_counter_geometry",
    "fixed_architecture",
    "fixture_count_and_placement",
    "anchor_position_scale_orientation",
    "background_material_identity",
    "no_unrelated_relighting_or_tone_mapping",
    "person_contact_region_only",
)
IDENTITY_PACK_STATUSES = {"planned", "qualified", "approved", "blocked", "model_blocked"}
IDENTITY_KINDS = {"fictional", "real_person"}
LEGACY_IDENTITY_LAYOUT_PROFILE = "higgsfield-character-reference-sheet-two-row-single-solve-v1.6"
IDENTITY_LAYOUT_PROFILE = "high-resolution-six-view-single-solve-3x2-v1.6.6"
LEGACY_IDENTITY_VIEW_ROLES = (
    "full_front",
    "full_left_profile",
    "full_right_profile",
    "full_back",
    "portrait_front",
    "portrait_left_profile",
    "portrait_right_profile",
)
IDENTITY_VIEW_ROLES = (
    "full_front",
    "full_primary_profile",
    "full_back",
    "portrait_front",
    "portrait_left_profile",
    "portrait_right_profile",
)
IDENTITY_LAYOUTS = {
    IDENTITY_LAYOUT_PROFILE: {
        "grid": [3, 2],
        "roles": IDENTITY_VIEW_ROLES,
        "slot_roles": [*IDENTITY_VIEW_ROLES],
        "blank_slot": None,
        "minimum_canvas_px": [1536, 1024],
        "minimum_cell_width_px": 512,
    },
    LEGACY_IDENTITY_LAYOUT_PROFILE: {
        "grid": [4, 2],
        "roles": LEGACY_IDENTITY_VIEW_ROLES,
        "slot_roles": [*LEGACY_IDENTITY_VIEW_ROLES, "blank"],
        "blank_slot": {"row": 2, "column": 4},
        "minimum_canvas_px": [1536, 1024],
        "minimum_cell_width_px": 384,
    },
}
ALL_IDENTITY_VIEW_ROLES = set(IDENTITY_VIEW_ROLES) | set(LEGACY_IDENTITY_VIEW_ROLES)


def identity_layout_spec(profile: Any) -> dict[str, Any] | None:
    """Return the immutable layout contract for a supported identity board.

    v1.6.6 changes the default authoring layout to a larger 3x2 six-view board,
    while retaining the earlier 4x2 seven-view layout as a read/validate/export
    adapter.  Existing v1.6 projects therefore stay valid without migration.
    """
    if not isinstance(profile, str):
        return None
    value = IDENTITY_LAYOUTS.get(profile)
    return dict(value) if isinstance(value, dict) else None


def identity_roles_for_layout(profile: Any) -> tuple[str, ...]:
    spec = identity_layout_spec(profile)
    roles = spec.get("roles") if isinstance(spec, dict) else None
    return tuple(str(role) for role in roles) if isinstance(roles, list | tuple) else ()
PROPORTION_RATIO_FIELDS = (
    "head_to_body",
    "shoulder_width",
    "hip_width",
    "torso_length",
    "upper_arm_length",
    "forearm_length",
    "thigh_length",
    "shin_length",
    "arm_span",
    "hand_length",
    "foot_length",
)
PHYSIQUE_CLASSIFICATIONS = {
    "observed_specific", "narrative_fit", "aspirational_lean", "aspirational_athletic",
    "aspirational_muscular", "dancer_performer", "fashion_model",
    "strength_power", "endurance_trained", "deconditioned_story_specific",
    "soft_tissue_transition", "custom",
}
TARGET_DRIVEN_PHYSIQUE_CLASSIFICATIONS = {
    "aspirational_lean", "aspirational_athletic", "aspirational_muscular",
    "dancer_performer", "fashion_model", "strength_power", "endurance_trained",
}
PHYSIQUE_BRIEF_SOURCES = {"script", "user_direction", "mixed"}
PHYSIQUE_TARGET_UNITS = {"standing_height_1.0"}
VISUAL_BODY_BALANCE_TARGETS = {
    "observed_specific",
    "balanced_four_six",
    "elongated_three_seven",
    "story_exception",
}
PHYSIQUE_FIT_CHECKS = (
    "narrative_and_casting_fit",
    "quantitative_target_fit",
    "visual_leg_body_balance_fit",
    "silhouette_and_volume_fit",
    "posture_and_gait_fit",
    "wardrobe_silhouette_fit",
    "no_unrequested_body_template",
)
GEOMETRY_QA_MODES = {"pending", "identity_authority", "state_reference", "narrative_frame", "not_applicable"}
GEOMETRY_QA_RESULTS = {"pending", "pass", "fail", "not_applicable"}
GEOMETRY_QA_CHECKS = (
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
LIVE_ACTION_SURFACE_QA_MODES = {"pending", "authority_reference", "narrative_frame", "not_applicable"}
LIVE_ACTION_SURFACE_RESULTS = {"pending", "pass", "fail", "not_applicable"}
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
QUALITY_FLOOR_ID = "clean-observational-live-action-v001"
QUALITY_QA_MODES = {"pending", "authority_reference", "narrative_frame", "not_applicable"}
QUALITY_QA_RESULTS = {"pending", "pass", "fail", "not_applicable"}
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
DYNAMIC_RANGE_POLICIES = {"finite_scene_referred"}
DYNAMIC_RANGE_PRIORITIES = {
    "protect_skin",
    "protect_highlights",
    "protect_shadows",
    "protect_skin_and_practicals",
    "balanced_middle_tones",
}
DYNAMIC_RANGE_QA_FIELDS = (
    "exposure_priority",
    "middle_tone_anchor",
    "highlight_loss_or_rolloff",
    "shadow_loss_or_floor",
    "global_tone_mapping_detected",
)
QUALITY_PROFILE_STATUSES = {"planned", "qualified", "approved", "superseded", "blocked"}
QUALITY_CALIBRATION_STATUSES = {"untested", "conditional", "stable", "blocked"}
QUALITY_EVIDENCE_ROLES = {"calibration_only", "project_generated_anchor"}
ENVIRONMENT_MODULES = {
    "rain_wet", "snow_cold", "fog_smoke", "dust_sand", "storm_lightning",
    "fire_embers_emergency", "underwater", "heat_haze",
}
CANDIDATE_SET_STATUSES = {"planned", "generating", "reviewed", "selected", "model_blocked"}
CANDIDATE_VARIANT_STATUSES = {"planned", "generated", "passed", "failed", "selected", "discarded"}
CANDIDATE_TIERS = {"identity_single_solve", "critical", "derivative"}
CANDIDATE_OPERATIONS = {"generate", "edit", "provided"}
REVIEW_GATE_TYPES = {"foundation", "sequence"}
REVIEW_GATE_STATUSES = {"building", "ready_for_review", "approved", "changes_requested", "superseded"}
REVIEW_DECISIONS = {"pending", "approved", "changes_requested"}
MATERIAL_RESPONSE_CONTRACT_FIELDS = (
    "skin",
    "hair",
    "fabric",
    "hard_surfaces",
    "skin_presence",
    "skin_key_source",
    "skin_key_source_size",
    "skin_key_direction",
    "skin_fill_sources",
    "skin_specular_behavior",
    "skin_wetness_state",
    "local_contrast_policy",
    "tone_mapping_policy",
    "material_roughness_separation",
    "color_contamination_sources",
    "performance_staging_policy",
)
SKIN_WETNESS_STATES = {
    "natural_dry", "normal", "perspiration", "rain_wet", "submerged",
    "cosmetic_sheen", "not_applicable",
}
MEDIUM_SIGNATURE_STATUSES = {"disabled", "calibrating", "stable", "rejected"}
ENVIRONMENT_STATUSES = {"planned", "qualified", "approved", "superseded", "blocked"}
ENVIRONMENT_KINDS = {
    "clear", "rain", "snow", "fog", "mist", "smoke", "dust", "storm",
    "fire_embers", "underwater", "heat_shimmer",
}
ENVIRONMENT_QA_CHECKS = (
    "physical_source",
    "visibility_and_depth",
    "advection_and_direction",
    "accumulation_and_material_interaction",
    "light_scattering_or_attenuation",
    "exposure_focus_effect",
    "temporal_bounds",
    "sound_and_continuity",
)
SPECIAL_LIGHT_QA_CHECKS = (
    "motivated_source",
    "temporal_waveform",
    "exposure_response",
    "shadow_propagation",
    "reflection_propagation",
    "subject_and_environment_response",
)
CAMERA_MOVE_PRIMITIVES = {
    "locked", "pan", "tilt", "roll", "dolly_in", "dolly_out", "truck", "pedestal",
    "jib_crane", "orbit", "handheld_follow", "gimbal_follow", "vehicle_mount", "drone",
}
CAMERA_SPEED_CURVES = {"constant", "ease_in", "ease_out", "ease_in_out", "hand_operated", "custom"}
MOTION_BLUR_SOURCES = {"none", "camera", "subject", "both", "atmosphere"}
MOTION_BLUR_AMOUNTS = {"none", "low", "moderate", "high"}
TEMPORAL_QA_CHECKS = (
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
PRODUCTION_KINDS = {"narrative_film", "commercial_tvc", "music_video"}
COMMERCIAL_MANIFEST_MODES = {"not_applicable", "commercial_tvc", "commercial_mv_hybrid"}
COMMERCIAL_STATUSES = {"planned", "qualified", "approved", "blocked"}
COMMERCIAL_ROUTE_STATUSES = {"proposed", "selected", "approved", "rejected"}
COMMERCIAL_RHYTHM_STRATEGIES = {"synchronous", "half_time", "counterpoint", "dialogue_led", "free"}
COMMERCIAL_SPEED_REGIMES = {"real_time", "overcranked_slow", "undercranked_fast", "variable_speed", "locked_stillness"}
COMMERCIAL_ENERGY_LEVELS = {"restrained", "low", "medium", "high", "burst"}
COMMERCIAL_CATEGORIES = {"fashion", "product", "service", "brand", "performance", "retail", "other"}
COMMERCIAL_MUSIC_USAGE = {"score", "source", "none"}
COMMERCIAL_DELIVERABLE_KINDS = {"master", "proxy", "cutdown", "social", "endboard", "other"}
COMMERCIAL_SHOT_FUNCTIONS = {
    "hook", "brand_world", "product_reveal", "wardrobe_reveal", "feature_proof", "material_detail",
    "comparison", "performance", "transition", "escalation", "payoff", "endboard", "cta", "other",
}
COMMERCIAL_QA_CHECKS = (
    "brief_specificity",
    "brand_specific_concept",
    "product_or_wardrobe_proof",
    "shot_function_and_removal_test",
    "music_action_edit_coherence",
    "speed_sampling_and_motion_blur",
    "performance_energy_and_variety",
    "sound_design_and_mix_hierarchy",
    "endboard_copy_and_cta",
    "delivery_matrix_conformance",
)
TAKE_COMMERCIAL_QA_CHECKS = (
    "beat_action_alignment",
    "speed_and_motion_blur",
    "product_or_wardrobe_readability",
    "performance_energy",
    "identity_state_and_material_continuity",
    "audio_sync_and_transition_accents",
)
RESOLUTION_QA_CHECKS = (
    "native_pixel_dimensions",
    "subject_or_detail_pixel_coverage",
    "focus_and_edge_resolution",
    "compression_and_resampling",
    "no_dimension_only_upscale",
)
IMMUTABLE_IDENTITY_FIELDS = (
    "facial_bone_proportions",
    "feature_spacing",
    "body_build_and_height_ratio",
    "skin_tone_range",
    "hairline",
    "fixed_marks",
    "handedness",
)
LOCATION_WORLD_STATUSES = {"planned", "qualified", "approved", "blocked", "model_blocked"}
LOCATION_STATE_STATUSES = {"planned", "qualified", "approved", "superseded", "blocked", "model_blocked"}
SEQUENCE_STATUSES = {"planned", "blocked", "ready", "generated", "selected", "superseded"}
HIGGSFIELD_ADAPTER_LIMITS = {
    "popcorn": 4,
    "cinema-studio-3": 9,
    "seedance-2.5": 50,
    "cinema-studio-4": 50,
}
HIGGSFIELD_STRICT_WORKFLOWS = {"cinema-studio-4"}
# Public documentation does not expose one universal multi-move ceiling for all
# interfaces. The offline package therefore emits one executable move per shot;
# multi-shot sequences are represented as explicit Shot blocks instead of an
# invented UI capability.
HIGGSFIELD_CAMERA_MOVE_LIMITS = {
    "popcorn": 1,
    "cinema-studio-3": 1,
    "seedance-2.5": 1,
    "cinema-studio-4": 1,
}
REFERENCE_PROVENANCE_KINDS = {"text_only", "generated_anchor", "user_provided_photo", "mixed"}
REFERENCE_COVERAGE_POLICIES = {
    "single_view",
    "identity_single_solve_inspector",
    "character_turnaround",
    "location_multiview",
    "object_multiview",
}
CHARACTER_TURNAROUND_VIEWS = {
    "full_front",
    "full_left_profile",
    "full_right_profile",
    "full_back",
    "portrait_front",
    "portrait_left_profile",
    "portrait_right_profile",
}
LOCATION_MULTIVIEW_VIEWS = {
    "front_wide",
    "left_three_quarter_wide",
    "right_three_quarter_wide",
    "reverse_wide",
}
LOCATION_VIEW_ROLES = {
    "",
    "establishing_wide",
    "side_three_quarter_wide",
    *LOCATION_MULTIVIEW_VIEWS,
}
LOCATION_VIEW_SIDES = {"", "left", "right", "not_applicable"}
OBJECT_ANCHOR_VIEWS = {"front", "side", "three_quarter"}
SPATIAL_MAP_STATUSES = {"planned", "qualified", "approved", "blocked", "real_reference_required"}
SPATIAL_ESCALATIONS = {"none", "retry", "real_reference_required"}
SPATIAL_MARK_KINDS = {"camera", "character", "prop", "landmark", "action"}
ANCHOR_STABILITIES = {"fixed", "state_locked"}
ANCHOR_SELECTION_SOURCES = {"script_prop", "fixed_set_dressing"}
ANCHOR_VISIBILITIES = {"visible", "partial", "offscreen"}
SET_FIXED_DIRECTIONS = {"origin", "+X", "-X", "+Y", "-Y"}
REFERENCE_BACKGROUND_POLICIES = {"pure_white", "neutral_light", "on_location_neutral", "not_applicable"}
HIGGSFIELD_PACKAGE_VERSION = "1.6"
HIGGSFIELD_KNOWLEDGE_SNAPSHOT = "2026-08-27"
HIGGSFIELD_OFFICIAL_PROFILE_ID = "cinema-studio-4-seedance-2.5-official-2026-08-27"
HIGGSFIELD_OFFICIAL_SOURCE_URLS = (
    "https://higgsfield.ai/blog/seedance-2-5-prompting-guide",
    "https://higgsfield.ai/blog/ai-short-film-youtube-guide",
    "https://higgsfield.ai/blog/realistic-ai-human-movement",
    "https://higgsfield.ai/blog/cinema-studio-4-0",
)
HIGGSFIELD_PRODUCTION_STATUSES = {"ready", "generated", "selected"}
HIGGSFIELD_REFERENCE_CATEGORIES = {
    "character_identity_inspector": "characters",
    "character_master": "characters",
    "character_variant": "characters",
    "character_face_anchor": "characters",
    "character_body_anchor": "characters",
    "character_identity_view": "characters",
    "character_state": "characters",
    "location_master": "locations",
    "location_variant": "locations",
    "location_plate": "locations",
    "prop": "props",
    "prop_state": "props",
    "vehicle": "props",
    "animal": "props",
    "pose_contact_anchor": "frames",
    "reference_board": "characters",
    "style": "looks",
    "look_test": "looks",
    "storyboard": "frames",
    "keyframe": "frames",
    "key_art": "key-art",
    "title_card": "key-art",
    "other": "other",
}
AUTHENTIC_ASSET_TYPES = ASSET_TYPES - {"title_card", "other", "reference_board"}
NEUTRAL_REFERENCE_ASSET_TYPES = {
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
}
HUMAN_RELEVANT_ASSET_TYPES = {
    "character_identity_inspector",
    "character_face_anchor",
    "character_body_anchor",
    "character_identity_view",
    "character_master",
    "character_variant",
    "character_state",
    "pose_contact_anchor",
    "live_action_probe",
}
PROFILED_ASSET_TYPES = {"look_test", "location_plate", "storyboard", "keyframe", "key_art"}
NARRATIVE_ASSET_TYPES = {"location_plate", "storyboard", "keyframe", "key_art"}
SPATIALIZED_ASSET_TYPES = PROFILED_ASSET_TYPES


class Report:
    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def error(self, code: str, message: str) -> None:
        self.errors.append({"code": code, "message": message})

    def warning(self, code: str, message: str) -> None:
        self.warnings.append({"code": code, "message": message})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def creative_bible_template(title: str, aspect: str) -> str:
    return f"""# {title} — Creative Bible

Status: draft

## Story contract

- Premise: 未设定
- Audience promise: 未设定
- Target runtime: 未设定
- Aspect ratio: {aspect}
- Dialogue language: 未设定

## Reality brief

- Casting truth: 未设定
- Location truth: 未设定
- Production causality: 未设定
- Camera witness and access: 未设定
- Polish ceiling: 未设定
- AI priors to reject: 未设定

## Live-action production design

- Period, architecture, wardrobe, and props: 未设定
- Palette and prohibited colors: 未设定
- Materials, utilities, and causal surface rules: 未设定
- Clean authority rule: root identity, location, and object assets carry no decorative grain, dirt, patina, fingerprint, pore enhancement, or generic wear
- Localized story evidence: every persistent defect must name material, exact region, extent, cause, and first visible shot

## Identity geometry and state contract

- Identity-pack authority: one high-resolution white-background 3×2 identity inspector generated in one ImageGen call and validated as a whole before any downstream work
- Board roles: top row full-body front / one story-relevant full-body profile / full-body back; bottom row face close-up front / face close-up left profile / face close-up right profile
- Inspection/upload views: six deterministic, non-resampled crops from that authority board; record the one unambiguous central white row gutter and its actual split instead of blindly assuming equal row heights; crops never become separate identity solves
- Native-detail floor: board at least 1536×1024, each column at least 512 px, full-body figures and portrait faces large enough for geometry and surface inspection; resizing dimensions never counts as recovered detail
- Proportion signature: identity-specific head/body, shoulder/hip, torso/limb, arm-span, hand/foot and intentional-asymmetry ratios
- Immutable identity fields: skeletal proportions, feature spacing, skin range, hairline, fixed marks, handedness and expected digit topology
- Persistent state fields: wardrobe, hair state, age stage, injury, wetness, dirt, makeup, story props
- Soft-tissue delta: age, weight, pregnancy, swelling or muscle change requires a cause and first visible shot; skeletal proportions stay locked
- Transient performance fields: emotion, gaze, action and breath remain shot-level
- State derivation rule: every state references the unified inspector directly; state-to-state edits and crop-as-root references are forbidden

## Production-design DNA and world state

- Period and socioeconomic conditions: 未设定
- Architectural and infrastructure logic: 未设定
- Color sources and signage rules: 未设定
- Material baselines and allowed ageing: 未设定
- Location-world invariants and state-change causes: 未设定

## Spatial production contract

- Scene-state boundaries: 未设定
- Primary spatial anchor selection per scene: 未设定
- Set-fixed +X/+Y directions and named boundaries: 未设定
- Required establishing and side three-quarter evidence: 未设定
- Camera, character, landmark, and movement marks: 未设定

## Cinematography thesis

- Audience distance and subjectivity: 未设定
- Spatial and movement strategy: 未设定
- Highlight, shadow, skin, and material strategy: 未设定
- Motivated-light principle: 未设定
- Color and texture rationale: 未设定

## Cinematic treatment and format gate

- Observable treatment axes: narrative distance, camera witness, composition, optical space, motivated light, color pipeline, support/inertia, cadence, environmental medium and polish ceiling
- Named reference translation: names may stay in the internal brief, but only observable original behavior enters model prompts
- Capture aperture / working frame / delivery frame: 未设定
- Crop, safe areas, squeeze/desqueeze and reframe policy: 未设定
- Format approval status and sequence overrides: 未批准

## Environment and temporal capture

- Weather/atmosphere source, density, direction, visibility and material interaction: 未设定
- Special-light event source, timing, exposure, shadow and reflection propagation: 未设定
- Camera path, support, speed curve and clearance: 未设定
- Capture fps / delivery fps / shutter angle / exposure time: 24 / 24 / 180° / about 1/48 s unless story-justified
- Motion-blur source, direction, extent and static reference regions: 未设定

## Baseline capture profile — unapproved until Look Test selection

- Medium and active format: 未设定
- Observable capture behavior: 未设定
- Lens and focus behavior: 未设定
- Exposure strategy: 未设定
- Motion baseline: 24fps / 180° unless story-justified
- Lighting organization: 未设定
- Image pipeline and artifact budget: 未设定
- Permitted scene-group/scene deviations and return rule: none approved

## Character and performance grammar

- Recurring identities: 未设定
- Wardrobe/state rules: 未设定
- Body, gaze, face, breath, and dialogue timing: 未设定

## Sound grammar

- Dialogue: 未设定
- Ambience and foley: 未设定
- Music and silence: 未设定

## Commercial / TVC creative system (when applicable)

- Business objective, audience, placement and single proposition: 未设定
- Product/wardrobe reasons to believe and non-negotiable brand codes: 未设定
- At least two materially distinct creative routes and competitor-swap test: 未设定
- Shot-function and removal test: 未设定
- Music BPM/meter/downbeat, motion-energy relationship and edit grammar: 未设定
- Capture-speed palette, playback rate, action peaks and motion-blur logic: 未设定
- Dialogue/VO, music, ambience, Foley, transition accents and mnemonic hierarchy: 未设定
- Exact duration/frame count, master/proxy distinction, aspect/crop and audio delivery matrix: 未设定

## Motifs, payoffs, and hard locks

- Recurring motifs: 未设定
- Narrative payoffs: 未设定
- Must remain true: 未设定
- Must never appear: text, unrelated logos, trademarks, watermarks, and any project-specific exclusions not yet listed
"""


def edit_plan_template(title: str) -> str:
    return f"""# {title} — Edit Plan

Status: draft

## Assembly

| Order | Shot ID | Intended in/out | Cut motivation | Audio bridge | Alternate | Risk |
|---:|---|---|---|---|---|---|

## Scene-level sound

- Dialogue: 未设定
- Ambience: 未设定
- Foley: 未设定
- Music: 未设定
- Required silence: 未设定

## Open decisions

- None recorded.
"""


def asset_review_template(title: str) -> str:
    return f"""# {title} — Asset Review

Record each authority asset's role, selected candidate set, prompt/reference hashes, internal QA verdict, approval gate and final authority path. Raw failed candidates belong only in `manifests/candidates.json`; user decisions belong only in `manifests/reviews.json`.
"""


def authenticity_review_template(title: str) -> str:
    return f"""# {title} — Authenticity Review

For every generated or provided live-action asset, record reference provenance, attempt index, casting specificity, human surfaces, set causality, lighting causality, composition contingency, material/contact behavior, AI artifacts, brief fit, the explicit AI-smell verdict, user decision, and any real-reference escalation. Technical camera plausibility alone is not sufficient.
"""


def shot_review_template(title: str) -> str:
    return f"""# {title} — Shot Review

Record effective capture Profile, reconstructable camera/lens/focus/exposure/light/pipeline, reference correctness, first-frame continuity, action timing, physics, performance, audio, end-state continuity, prompt readiness, and provider-adapter limitations for each shot.
"""


def cinematography_review_template(title: str) -> str:
    return f"""# {title} — Cinematography Review

For each Profile and Look Test comparison set, record the story rationale, physical cause, observable result, capture circumstance, locked story facts/references/blocking, three independently generated candidate previews, photographic and authenticity QA, blind labels, explicit user selection, rejected alternatives, and decision time. Do not lock pixel-level composition. Generated images simulate physical capture and do not carry claimed real-camera metadata.
"""


def spatial_review_template(title: str) -> str:
    return f"""# {title} — Spatial Review

For each scene state, record the approved location master, independently generated establishing and side-three-quarter views, primary anchor object, anchor dimensions/orientation, fixed coordinate axes, named landmarks, camera/character/action marks, cross-view geography, and the spatial QA verdict. The side-three-quarter view must be 30–60 degrees off the authoritative frontal axis, show adjacent planes and depth, and keep the anchor's position, scale, grounding, and orientation unchanged.
"""


def texture_review_template(title: str) -> str:
    return f"""# {title} — Texture Review

For every production candidate, record inspection at thumbnail, fit-to-window, 100%, and 200%. Check painterly smear/low-frequency blur; repeating swirl, scale, fingerprint, or cellular texture; cross-material leakage; plastic skin, fused hair, and incorrect textile scale; oversharpened halos, random bright specks, and dirty shadows; localized defect boundaries; and any resampling, compression, or color-mode change. Repeated texture across two unrelated materials, or any such texture on a face or authority asset, is a hard failure.
"""


def cross_scene_review_template(title: str) -> str:
    return f"""# {title} — Cross-scene Review

Compare every recurring identity, persistent character state, prop state, location world, and location state across sequence clusters. Record immutable-field matches, permitted deltas only, location topology/openings/fixed facilities/anchor/scale/material preservation, sequence-boundary causes, first/end keyframe continuity, bridge-frame use, and explicit user approval. A bridge frame supplements but never replaces root authorities.
"""


def proportion_review_template(title: str) -> str:
    return f"""# {title} — Human Geometry Review

For each recurring identity, record one authoritative high-resolution single-solve white-background 3×2 inspector, its six deterministic inspection/upload crops, identity-specific normalized proportion signature, source and projection class, confidence/tolerances, skeletal locks, intentional asymmetries, expected digit topology, native-detail QA, and Foundation-gate approval. Reject the whole board if any panel changes identity, anatomy, wardrobe, scale, lighting, surface quality, or useful resolution; do not generate downstream crops or states. Existing v1.6 4×2 boards remain readable through the legacy adapter. For every state or narrative frame, check silhouette/volume, joints, segment lengths, hands/feet/digits, shoulder-pelvis alignment, weight bearing, foreshortening, occlusion, garment separation, and multi-person relative scale. Do not treat perspective shortening as anatomical drift.
"""


def live_action_surface_review_template(title: str) -> str:
    return f"""# {title} — Live-action Surface Review

For every visible person, first record the skin key source, its apparent size and direction, fill sources, wetness state, expected specular extent, local-contrast policy, tone-mapping policy, color contamination sources, and performance-staging policy. Then reject painterly or patch smear, wax/plastic/CG skin, small glossy highlights unrelated to a source, skin tones carved by clarity/HDR processing, artificial eyes, fused hair, melted textiles, render outlines, sharpening halos, copied textures, impossible contact shadows, collapsed material roughness, game-cinematic rendering, and publicity-pose staging. Authority assets carry no artificial medium signature. Narrative medium character is allowed only through a stable two-run calibration and must fall back to clean imaging after one artifact failure.
"""


def quality_review_template(title: str) -> str:
    return f"""# {title} — Live-action Quality Review

Use `clean-observational-live-action-v001` as a behavior floor, never as a production image reference. For every selected candidate record four-scale inspection, photographic-event plausibility, skin highlight topology and tone continuity, eye/hair/edge behavior, material response and roughness separation, detail integrity, artifact absence, lighting/contact/set causality, observed performance and the script-specific polish ceiling. Evidence must explain what visibly passes, not merely list absent defects. Uniform oil film, plastic skin, painterly smear, repeated cross-material texture, game/CG rendering, unmotivated light and publicity-pose staging are hard failures.
"""


def environment_review_template(title: str) -> str:
    return f"""# {title} — Environment Review

For every environmental state and special-light event, record source/cause, intensity, visibility, direction, wind/advection, accumulation, surface/wardrobe/hair interaction, distance-dependent scattering or attenuation, exposure/focus effect, temporal bounds, sound and continuity. Fog, rain, snow, smoke, dust, fire, underwater effects and heat shimmer must alter the photographed world physically rather than appear as a decorative overlay.
"""


def temporal_review_template(title: str) -> str:
    return f"""# {title} — Temporal Review

Record capture and delivery frame rates, shutter angle, computed exposure time, playback mapping, camera path, speed/easing, focus behavior and expected motion-blur source/direction/extent. For returned takes inspect start, 25%, 50%, 75%, end, plus contact, lighting and cut events for identity/body/background consistency, texture crawl, flicker, morphing, ghost limbs, weather continuity, camera-path conformance, focus, rolling-shutter artifacts and blur direction.
"""


__all__ = [name for name in globals() if not name.startswith("__")]
