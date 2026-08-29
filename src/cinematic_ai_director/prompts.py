"""Deterministic ImageGen and shot prompt compilation."""

from __future__ import annotations

from .boards import *
from .core import *


def _prompt_block(heading: str, body: str) -> str:
    compact = re.sub(r"\s+", " ", body).strip()
    return f"{heading}\n{compact}\n"


def _dynamic_range_text(plan: Any) -> str:
    if not isinstance(plan, dict):
        raise ValueError("a finite dynamic-range plan is required")
    return (
        f"Finite scene-referred capture: working latitude {plan.get('working_latitude_stops')} stops "
        f"({plan.get('upper_latitude_stops')} above and {plan.get('lower_latitude_stops')} below middle gray) "
        f"against estimated scene contrast {plan.get('scene_contrast_stops_estimate')} stops. "
        f"Exposure priority: {plan.get('exposure_priority')}; middle-tone anchor: {plan.get('middle_gray_anchor')}. "
        f"Highlights: {plan.get('highlight_behavior')} Allowed clipping: "
        f"{'; '.join(str(value) for value in plan.get('allowed_clipping', [])) or 'none'}. "
        f"Shadows: {plan.get('shadow_behavior')} Allowed shadow loss: "
        f"{'; '.join(str(value) for value in plan.get('allowed_shadow_loss', [])) or 'none'}. "
        "Never expose or locally tone-map every bright and dark region into equal clarity; no multi-exposure HDR merge."
    )


def _compile_live_action_probe_prompt(
    asset: dict[str, Any], quality_profile: dict[str, Any]
) -> str:
    """Compile the deliberately small, ordinary-light realism diagnostic.

    This prompt is intentionally not a miniature production bible.  It asks the
    backend to solve one person, one real place, one simple contact, and one
    exposure decision before cinematic styling is allowed to hide defects.
    """
    plan = asset.get("dynamic_range_plan")
    if not isinstance(plan, dict):
        raise ValueError("a finite dynamic-range plan is required")
    task = str(asset.get("probe_task") or "performs one ordinary, readable task")
    blocking = str(asset.get("probe_blocking") or "the torso, face, working hand, contact object, and surrounding room share one frame")
    camera = str(asset.get("probe_camera_condition") or "a reachable eye-level medium camera at a natural working distance")
    light = str(asset.get("ordinary_light_source") or quality_profile.get("illumination_contract") or "one broad existing window source")
    clipping = "; ".join(str(value) for value in plan.get("allowed_clipping", [])) or "small source cores only"
    shadow_loss = "; ".join(str(value) for value in plan.get("allowed_shadow_loss", [])) or "the deepest unlit recesses"
    blocks = [
        f"Prompt strategy: {IMAGE_PROMPT_STRATEGY_BY_TYPE['live_action_probe']}",
        "",
        _prompt_block(
            "PHOTOGRAPHIC EVENT",
            f"A photorealistic candid on-location photograph records the approved adult as they {task}, an ordinary event rather than a poster.",
        ),
        _prompt_block(
            "APPROVED IDENTITY WORLD AND STATE",
            "This is a bounded image edit. The first attached image is the immutable approved empty-location plate and edit target; the second is the unified identity Inspector. Insert that adult. Preserve the plate's camera, crop, projection, architecture, table dimensions and supports, windows, doors, fixtures, anchor, materials, and every other non-subject detail.",
        ),
        _prompt_block(
            "PHYSICAL CAMERA AND BLOCKING",
            f"Keep the plate camera exactly; {camera} only describes it. {blocking}. Change pixels only inside the person, contact, and necessary cast-shadow regions. Share projection, ground plane, contact, occlusion, focus falloff, and edge behavior. Do not redesign the set.",
        ),
        _prompt_block(
            "SOURCE LIGHT AND MATERIAL RESPONSE",
            f"{light}. The same source and room bounce reach face, clothing, contact object, and set. Natural-dry skin stays matte-diffuse with weak source-shaped reflection; skin, hair, fabric, paint, glass, wood, and metal remain separate.",
        ),
        _prompt_block(
            "FOCUS EXPOSURE AND CONTINGENCY",
            f"Focus favors eyes and contact without equal sharpness everywhere. Exposure priority: {plan.get('exposure_priority')}. Let {clipping} clip and {shadow_loss} lose detail. Keep normal middle tones and finite latitude; no local HDR equalization.",
        ),
        _prompt_block(
            "EXCLUSIONS",
            "No synthetic-rendered or game-like person; no oily, waxy, or plastic skin; no cut-out subject edges, separate subject tone mapping, or repeated artifact texture; no scene geometry, fixture, camera, crop, or background-detail drift.",
        ),
    ]
    return "\n".join(blocks).strip() + "\n"


def _compile_image_prompt(
    asset: dict[str, Any],
    quality_profile: dict[str, Any],
    identity_pack: dict[str, Any] | None,
    comparison: dict[str, Any] | None,
) -> str:
    asset_type = str(asset.get("type") or "")
    identity_inspector_types = {"character_identity_inspector"}
    identity_neutral_types = identity_inspector_types | {"character_face_anchor", "character_body_anchor", "character_identity_view"}
    character_state_types = {"character_variant", "character_state"}
    human_reference_types = identity_neutral_types | character_state_types
    location_reference_types = {"location_master", "location_variant"}
    object_reference_types = {"prop", "prop_state", "vehicle", "animal"}
    strategy = str(asset.get("prompt_strategy_id") or IMAGE_PROMPT_STRATEGY_BY_TYPE.get(str(asset.get("type")), ""))
    if strategy not in IMAGE_PROMPT_STRATEGIES:
        raise ValueError(f"asset {asset.get('id')} has no supported v1.6 image prompt strategy")
    if asset_type == "live_action_probe":
        return _compile_live_action_probe_prompt(asset, quality_profile)
    role = str(asset.get("role") or asset.get("id"))
    state_delta = asset.get("state_delta") if isinstance(asset.get("state_delta"), dict) else {}
    physique = identity_pack.get("role_physique_brief") if isinstance(identity_pack, dict) and isinstance(identity_pack.get("role_physique_brief"), dict) else {}
    has_human = bool(identity_pack) or asset_type in HUMAN_RELEVANT_ASSET_TYPES or bool(asset.get("character_state_id"))
    physique_text = ""
    if physique:
        targets = physique.get("quantitative_targets") if isinstance(physique.get("quantitative_targets"), list) else []
        target_text = ", ".join(
            f"{item.get('metric')} {item.get('minimum')}-{item.get('maximum')}"
            for item in targets if isinstance(item, dict)
        )
        traits = ", ".join(str(value) for value in physique.get("must_have_traits", []) if isinstance(value, str))
        physique_text = (
            f" Physique {physique.get('id')} ({physique.get('classification')}): "
            f"{('targets ' + target_text) if target_text else physique.get('stature_and_frame')}; "
            f"traits {traits or physique.get('shoulder_waist_hip_relation')}; wardrobe must preserve them; no generic body."
        )
        if asset_type == "character_face_anchor":
            physique_text = ""
    material_contract = asset.get("material_response_contract") if isinstance(asset.get("material_response_contract"), dict) else {}
    skin_state = material_contract.get("skin_wetness_state", "not_applicable")
    if has_human:
        authority_scope = "Identity, state and body remain unchanged."
        if asset_type in identity_neutral_types:
            skin_state = "natural_dry"
            skin_contract = "Natural dry skin keeps continuous hue and value transitions under neutral reference light."
        elif asset_type in character_state_types:
            skin_contract = str(material_contract.get("skin") or "The declared state keeps continuous, source-shaped skin response.")
        else:
            skin_contract = str(quality_profile.get("skin_response_contract", ""))
        profile_material_contract = str(quality_profile.get("material_response_contract", "")).strip()
        material_scope = (
            "Skin, hair and garment fabric retain independent source-shaped reflection, edge and roughness behavior."
            if asset_type in human_reference_types
            else profile_material_contract or "Skin, hair, garment fabric and set/object materials keep independent source-shaped response."
        )
        surface_response = (
            f"Skin {skin_state}: {skin_contract} {material_scope}"
        )
        exclusions = (
            "Reject painterly smear/patch smear; wax skin/plastic skin, CG render/animation look/game-cinematic rendering or synthetic glossy skin; "
            "repeating swirl, topographic contour, maze, fingerprint or cellular face texture/cross-material texture; "
            "rendered outline/oversharpen halo/HDR halo; no oil film."
        )
    elif asset_type == "animal":
        authority_scope = "No human; preserve only approved animal anatomy/state."
        surface_response = (
            "Fur, feather, hide, eye, ground and any declared object surface "
            "retain physically distinct source-shaped reflection, strand behavior and roughness."
        )
        exclusions = (
            "Reject painterly smear/patch smear; animation, CG creature render, plastic anatomy or synthetic gloss; repeating fur clumps/cross-material texture; "
            "rendered outline/sharpening halo/HDR halo or invented rim light."
        )
    else:
        authority_scope = "No person is present; do not invent one. Preserve approved world/object/state."
        hard_surface_contract = str(material_contract.get("hard_surfaces") or "construction-specific material response")
        if asset_type in {"prop", "prop_state", "vehicle"}:
            surface_response = (
                f"{hard_surface_contract}. Every declared manufactured material keeps its own edge, reflection, wear-free baseline "
                "and roughness response; do not turn the object into a CG product render."
            )
        else:
            surface_response = (
                f"{hard_surface_contract}. Set materials appear only where approved and keep distinct reflection, edge and roughness; fabric weave stays material-specific."
            )
        exclusions = (
            "Reject painterly smear/patch smear; illustration/animation/CG-PBR render/game-environment finish; repeating swirl/cross-material texture; "
            "rendered outline/oversharpen halo/HDR halo or invented rim light."
        )
    scene_facts = ", ".join(str(value) for value in asset.get("scene_ids", []) if isinstance(value, str)) or "foundation reference"
    controlled_story = str(comparison.get("story_moment")) if isinstance(comparison, dict) else ""
    controlled_blocking = str(comparison.get("locked_blocking")) if isinstance(comparison, dict) else ""
    if asset_type in identity_inspector_types:
        inspector_layout = asset.get("identity_inspector_layout") if isinstance(asset.get("identity_inspector_layout"), dict) else {}
        layout_profile = inspector_layout.get("profile")
        primary_profile_side = str(inspector_layout.get("primary_profile_side") or "left")
        authority_references = (
            "Resolve one fictional adult identity once across the entire sheet. Every panel is simultaneous evidence of that same face, "
            "hairline, ears, skin tone, body, height impression, garment and shoes; no panel may reinterpret the person."
        )
        authority_scope = "This unified sheet is the first identity authority; later crops are inspection/upload derivatives only."
        if layout_profile == LEGACY_IDENTITY_LAYOUT_PROFILE:
            panel_count = 7
            event_body = (
                f"One neutral casting session records {role} as a single four-column, two-row pure-white technical reference sheet. "
                "Top row, left to right: full-body front, full-body left profile, full-body right profile, full-body back. "
                "Bottom row, left to right: face close-up front, face close-up left profile, face close-up right profile, one empty white cell. "
                "Use four equal-width columns and one continuous unambiguous pure-white horizontal gutter near canvas center; allow the full-body row enough height to preserve complete hair and footwear, and let no person, garment or shadow cross any cell boundary. "
                "No captions, labels, drawn borders, props or environment."
            )
        else:
            panel_count = 6
            event_body = (
                f"One neutral casting session records {role} as one large high-resolution three-column, two-row pure-white technical reference sheet. "
                f"Top row, left to right: complete full-body front, complete full-body {primary_profile_side} profile, complete full-body back. "
                "Bottom row, left to right: large face close-up front, large face close-up left profile, large face close-up right profile. "
                "The upper row occupies roughly sixty-two percent of the usable height so hair and footwear remain complete; the lower row gives each face enough scale to inspect eyes, hairline, ears, skin transitions and jaw geometry. "
                "Use three equal-width columns and one continuous unambiguous pure-white horizontal gutter; no person, garment or shadow crosses a cell boundary. "
                "No captions, labels, borders, props, scenery or empty cell. Native detail must be present at generation, not simulated by enlargement."
            )
        light_body = (
            f"One broad neutral soft source and restrained fill are identical across all {panel_count} panels, with normal white balance and no rim light. "
            "Natural-dry skin is matte-diffuse with only weak continuous source-shaped reflection; skin, hair, eyes, teeth, garment and shoes remain materially distinct. "
            "No beauty retouching, cosmetic sheen, story color or mood treatment."
        )
        focus_body = (
            "Level camera and long working distance; normal perspective, complete feet in every full-body panel, consistent scale/alignment, readable facial planes and middle tones. "
            "The approved role physique and natural four-six or justified three-seven visual balance must be visible without low angle, wide-angle stretching or a false raised waistline."
        )
    elif asset_type in {"character_face_anchor", "character_body_anchor", "character_identity_view"}:
        raise ValueError(
            f"asset {asset.get('id')} is a deterministic inspector crop and must not be sent to ImageGen"
        )
    elif asset_type in character_state_types:
        authority_references = "Use the unified identity-inspector authority first, then the declared current-state authority in manifest order; change only the state delta."
        event_body = (
            f"A neutral continuity camera records {role} for {scene_facts}, showing only the persistent state delta, not a dramatic still."
        )
        light_body = "Neutral continuity light makes the state and material boundaries inspectable. " + surface_response
        focus_body = (
            "Natural perspective and enough depth to compare identity, body, wardrobe and localized state; no mood grade, retouching or distortion."
        )
    elif asset_type in location_reference_types:
        authority_references = "Use the attached location master then fixed spatial-anchor reference in manifest order; preserve one physical place."
        event_body = (
            f"An unoccupied location-scout camera records {role} for {scene_facts}, proving reachable geography, construction, scale, adjacent planes and anchor."
        )
        light_body = (
            f"Only current-state daylight, weather and installed practicals; keep direction readable, without beauty light. {surface_response}"
        )
        focus_body = (
            "Natural scout perspective and readable near-to-far topology; protect practicals/middle tones; no shallow-depth or mood-grade shortcut."
        )
    elif asset_type in object_reference_types:
        authority_references = "Use the attached approved object root/current state in manifest order; preserve one manufacture and scale."
        event_body = (
            f"A neutral reference camera records {role} for {scene_facts}, showing manufacture, dimensions, contact base and current state, not a stylized render."
        )
        light_body = "Broad neutral reference light with readable direction; no dramatic rim or mood grade. " + surface_response
        focus_body = (
            "Natural perspective and enough depth for structure, scale, edges, joints and materials; protect reflections without HDR polish."
        )
    elif asset_type == "pose_contact_anchor":
        authority_references = "Use each unified identity-inspector authority first, then current state and object roots in manifest order; preserve each responsibility."
        event_body = (
            f"A rehearsal camera records {role} for {scene_facts}; start pose, weight transfer, contact and end pose remain inspectable."
        )
        light_body = "Clean rehearsal light reveals anatomy, hands, contacts and deformation without mood styling. " + surface_response
        focus_body = (
            "Natural perspective keeps every critical joint/contact plane readable; geometry outranks beauty, shallow depth or drama."
        )
    else:
        authority_references = "Attached references keep manifest order and declared roles."
        authority_scope = "Identity/state/body locked."
        event_body = (
            f"Scene {scene_facts}: {controlled_story} {quality_profile.get('capture_circumstance', '')}"
        )
        light_body = f"{quality_profile.get('illumination_contract', '')} {surface_response}"
        focus_body = (
            f"{quality_profile.get('tone_contrast_contract', '')} {quality_profile.get('focus_optics_contract', '')} "
            f"{quality_profile.get('performance_composition_contract', '')} Polish: {quality_profile.get('polish_ceiling', '')}."
        )
    focus_body = f"{focus_body} {_dynamic_range_text(asset.get('dynamic_range_plan'))}"
    blocking_physics = (
        "Keep weight, contact and topology."
        if has_human
        else "Keep grounded contact, topology and scale."
    )
    if asset_type == "character_identity_inspector":
        grid_text = "4-by-2" if layout_profile == LEGACY_IDENTITY_LAYOUT_PROFILE else "3-by-2"
        physical_camera_body = (
            f"One locked technical capture geometry for the entire {grid_text} sheet. Full-body panels use the same level height, long distance, neutral A-pose, scale and foot line; "
            "portrait panels use the same level face camera and crop. The role order is fixed, but do not sacrifice full-body anatomy merely to force mathematically equal row heights; preserve a clean detectable white row gutter. "
            "No panel-specific beauty angle, expression, focal-length shift or body redesign."
        )
    elif asset_type == "character_face_anchor":
        physical_camera_body = (
            "Eye-level portrait reference at natural working distance; face, hairline, ears, chin and upper shoulders remain readable without wide-angle distortion."
        )
    elif asset_type in identity_neutral_types:
        physical_camera_body = (
            "Eye-level reference position, long working distance and pure-white ground; full body and both feet remain visible. " + blocking_physics
        )
    else:
        physical_camera_body = (
            f"Map {asset.get('spatial_map_id') or 'foundation-neutral'}; reachable view {asset.get('view_role') or 'script-derived'}. {controlled_blocking} "
            f"Anchor {asset.get('primary_anchor_asset_id') or 'not applicable'} grounded/scaled. {blocking_physics}"
        )
    state_clause = f"State: {json.dumps(state_delta, ensure_ascii=False, sort_keys=True)}. " if state_delta else ""
    blocks = [
        f"Prompt strategy: {strategy}",
        "",
        _prompt_block(
            "PHOTOGRAPHIC EVENT",
            event_body,
        ),
        _prompt_block(
            "APPROVED IDENTITY WORLD AND STATE",
            f"{authority_references} {state_clause}{authority_scope}{physique_text}",
        ),
        _prompt_block(
            "PHYSICAL CAMERA AND BLOCKING",
            physical_camera_body,
        ),
        _prompt_block(
            "SOURCE LIGHT AND MATERIAL RESPONSE",
            light_body,
        ),
        _prompt_block(
            "FOCUS EXPOSURE AND CONTINGENCY",
            focus_body,
        ),
        _prompt_block(
            "EXCLUSIONS",
            exclusions,
        ),
    ]
    prompt = "\n".join(blocks).strip() + "\n"
    positive_prompt = "\n".join(blocks[:-1])
    for cue in RISKY_RENDER_CUES:
        if _positive_cue_occurs(re.sub(r"\s+", " ", positive_prompt).casefold(), cue):
            raise ValueError(f"compiled image prompt for {asset.get('id')} positively uses risky cue: {cue}")
    return prompt


def _format_camera_path(plan: Any) -> str:
    if not isinstance(plan, dict):
        return "No executable camera path recorded."
    path_points = plan.get("path_points_m") if isinstance(plan.get("path_points_m"), list) else []
    start = path_points[0] if path_points and isinstance(path_points[0], dict) else {}
    end = path_points[-1] if path_points and isinstance(path_points[-1], dict) else {}
    return (
        f"{plan.get('primitive')} on {plan.get('support')} from {plan.get('start_camera_mark_id')} to {plan.get('end_camera_mark_id')}; "
        f"start {json.dumps(start, ensure_ascii=False, sort_keys=True)}, end {json.dumps(end, ensure_ascii=False, sort_keys=True)}, "
        f"distance {plan.get('translation_m')} m, rotation {json.dumps(plan.get('rotation_deg'), ensure_ascii=False, sort_keys=True)} degrees, "
        f"duration {plan.get('duration_s')} s, curve {plan.get('speed_curve')}, settle {plan.get('settle_hold_s')} s."
    )


def _format_multi_person_projection(plan: Any) -> str:
    if not isinstance(plan, dict) or plan.get("verdict") != "pass":
        return ""
    subjects = plan.get("subjects") if isinstance(plan.get("subjects"), dict) else {}
    subject_text = "; ".join(
        (
            f"{asset_id}: approved standing height {subject.get('approved_height_m')} m, "
            f"camera distance {subject.get('camera_distance_m')} m, ground elevation "
            f"{subject.get('ground_elevation_m')} m, {subject.get('frame_coverage')}, visible landmarks "
            f"{', '.join(subject.get('visible_landmarks', []))}"
        )
        for asset_id, subject in sorted(subjects.items())
        if isinstance(subject, dict)
    )
    relation_text = "; ".join(
        (
            f"{relation.get('numerator_asset_id')} relative to {relation.get('denominator_asset_id')}: "
            f"expected projected-height ratio {relation.get('expected_ratio')} with tolerance "
            f"{relation.get('tolerance_fraction')}; "
            + (
                f"observed ratio {relation.get('observed_ratio')}"
                if relation.get("observed_ratio") is not None
                else f"cropped-body check {relation.get('cropped_landmark_method')}"
            )
        )
        for relation in plan.get("projected_height_relations", [])
        if isinstance(relation, dict)
    )
    return (
        f"Use one shared camera projection: {plan.get('projection')} at {plan.get('camera_height_m')} m, "
        f"pitch {plan.get('camera_pitch_deg')} degrees. {subject_text}. {relation_text}. "
        f"Horizon and vanishing lines: {plan.get('horizon_vanishing_lines')}. "
        f"Ground contact: {plan.get('ground_contact')}. Occlusion order: {plan.get('occlusion_order')}. "
        "Do not independently scale, stretch, shrink, or reproject any person."
    )


def _format_dramatic_coverage(plan: Any) -> str:
    if not isinstance(plan, dict) or plan.get("verdict") != "pass":
        return ""
    foreground = ", ".join(plan.get("foreground_subject_ids", [])) or "no foreground cast root"
    focus = ", ".join(plan.get("focus_subject_ids", [])) or "the recorded story subject"
    crops = ", ".join(plan.get("crop_landmarks", [])) or "no body crop"
    return (
        f"Coverage role {plan.get('coverage_role')} at {plan.get('shot_size')} from {plan.get('observer_position')}. "
        f"Foreground {foreground}; focus {focus}; crop only at {crops}. "
        f"Eyeline contract: {plan.get('eyeline_contract')}. Action beat: {plan.get('motivated_action_beat')}. "
        f"Composition: {plan.get('composition_asymmetry')}. This is dramatic coverage, not a symmetric spatial diagram."
    )


def _format_subject_environment_integration(plan: Any) -> str:
    if not isinstance(plan, dict) or plan.get("verdict") != "pass":
        return ""
    sources = ", ".join(plan.get("shared_light_sources", []))
    return (
        f"Subject and set share these physical light sources: {sources}. "
        f"Atmosphere {plan.get('shared_atmosphere_state_id')}: {plan.get('atmosphere_depth_behavior')}. "
        f"Focus and occlusion: {plan.get('focus_and_occlusion')}. Contact: {plan.get('contact_and_grounding')}. "
        f"Materials: {plan.get('material_response_match')}. Color contamination: {plan.get('color_contamination_match')}. "
        f"Edges: {plan.get('edge_integration')}. Do not isolate, relight, sharpen, tone-map, or paste a person over the world."
    )


def _compile_video_prompt(
    shot: dict[str, Any],
    spatial_map: dict[str, Any],
    format_plan: dict[str, Any],
    quality_profile: dict[str, Any],
    environmental_state: dict[str, Any],
    special_events: list[dict[str, Any]],
    commercial_direction: dict[str, Any] | None = None,
) -> str:
    references = list(shot.get("cast_asset_ids", [])) + list(shot.get("character_state_bindings", {}).values())
    references += [shot.get("location_asset_id"), shot.get("location_state_id")]
    references += list(shot.get("prop_asset_ids", [])) + list(shot.get("prop_state_bindings", {}).values())
    references += [shot.get("sequence_visual_anchor_asset_id")]
    references = [str(value) for value in references if isinstance(value, str) and value]
    geometry_locks = shot.get("body_geometry_locks") if isinstance(shot.get("body_geometry_locks"), dict) else {}
    has_human = bool(geometry_locks) or bool(shot.get("cast_asset_ids"))
    geometry_text = "; ".join(
        f"{root}: proportion {lock.get('proportion_signature_id')}, role physique {lock.get('role_physique_brief_id')}, state {lock.get('character_state_id')}, projection {lock.get('pose_projection')}"
        for root, lock in geometry_locks.items() if isinstance(lock, dict)
    )
    multi_person_projection_text = _format_multi_person_projection(
        shot.get("multi_person_projection")
    )
    dramatic_coverage_text = _format_dramatic_coverage(shot.get("dramatic_coverage_plan"))
    subject_environment_text = _format_subject_environment_integration(
        shot.get("subject_environment_integration")
    )
    temporal = shot.get("temporal_capture") if isinstance(shot.get("temporal_capture"), dict) else {}
    blur = shot.get("motion_blur_plan") if isinstance(shot.get("motion_blur_plan"), dict) else {}
    material = shot.get("material_interaction_plan") if isinstance(shot.get("material_interaction_plan"), dict) else {}
    dynamic_range = _dynamic_range_text(shot.get("dynamic_range_plan"))
    environment_text = (
        f"{shot.get('environmental_state_id')}: {environmental_state.get('kind')}, intensity {environmental_state.get('intensity')}, "
        f"direction {environmental_state.get('direction')}; physical source {environmental_state.get('source')}. "
        f"Special events: {', '.join(str(event.get('id')) for event in special_events) or 'none'}."
    )
    if has_human:
        light_material_response = (
            f"{quality_profile.get('illumination_contract', '')} Skin key source remains source-shaped; skin wetness follows the declared state, "
            "skin specular extent stays local and causal, local contrast remains restrained, and every material roughness response stays independent. "
            f"{quality_profile.get('skin_response_contract', '')} {quality_profile.get('material_response_contract', '')}"
        )
        temporal_surface_locks = (
            "Preserve identity, role-conditioned physique, proportions, states, topology, source light and material separation through every frame. "
            "No game-cinematic rendering, synthetic glossy skin, uniform oil film, painterly smear, texture crawl, copied cross-material dirt, "
            "oil-glint flicker, warped contact, morphing or sharpening halo."
        )
    else:
        light_material_response = (
            f"{quality_profile.get('illumination_contract', '')} Skin response is not applicable and no person may be invented. "
            f"Every declared set and object material retains independent source-shaped reflection and roughness. {quality_profile.get('material_response_contract', '')}"
        )
        temporal_surface_locks = (
            "Preserve object geometry, set topology, state, source light and material separation through every frame. No invented person, "
            "animation or CG/PBR finish, painterly smear, texture crawl, copied cross-material dirt, morphing or sharpening halo."
        )
    format_text = (
        f"Capture {format_plan.get('capture_aperture')}; working frame {format_plan.get('working_frame')}; "
        f"delivery {format_plan.get('delivery_aspect')}; crop {format_plan.get('crop_extraction')}; no baked black bars."
    )
    reference_text = ", ".join(references) or "no character reference"
    physics_text = json.dumps(material, ensure_ascii=False, sort_keys=True)
    if shot.get("motion_class") not in PHYSICS_MOTION_CLASSES:
        physics_text = (
            "Preserve ordinary gravity, weight bearing, cloth and hair inertia, grounded contacts, and the declared environmental response; "
            "do not invent extra people, props, smoke, liquid or effects."
        )
    commercial_direction = commercial_direction if isinstance(commercial_direction, dict) else {}
    route = commercial_direction.get("route") if isinstance(commercial_direction.get("route"), dict) else {}
    rhythm = commercial_direction.get("shot_rhythm") if isinstance(commercial_direction.get("shot_rhythm"), dict) else {}
    speed = commercial_direction.get("speed") if isinstance(commercial_direction.get("speed"), dict) else {}
    music = commercial_direction.get("music") if isinstance(commercial_direction.get("music"), dict) else {}
    commercial_style = ""
    commercial_scene = ""
    commercial_action = ""
    commercial_camera = ""
    commercial_audio = ""
    if commercial_direction:
        commercial_style = (
            f" Commercial route: {route.get('visual_logic', '')}. Product/wardrobe proof: {route.get('product_or_wardrobe_proof', '')}."
        )
        commercial_scene = (
            f" Commercial shot function: {rhythm.get('function', '')}; energy {rhythm.get('energy', '')}; "
            f"cut relation {rhythm.get('cut_relation', '')}."
        )
        commercial_action = (
            f" The primary action peak occurs at {rhythm.get('action_peak_s')} seconds; internal rhythmic events: "
            f"{'; '.join(str(value) for value in rhythm.get('internal_rhythmic_events', [])) or 'none'}."
        )
        commercial_camera = (
            f" Commercial speed regime {speed.get('regime', '')}: {speed.get('intended_motion', '')}; blur logic {speed.get('blur_logic', '')}."
        )
        commercial_audio = (
            f" Music {music.get('bpm')} BPM in {music.get('meter')}, using the declared tempo-motion relationship; "
            f"preserve shot-specific Foley, ambience and transition accents from the production audio plan."
        )
    blocks: list[str] = []
    bodies = {
        "GLOBAL STYLE": (
            f"Original live-action {quality_profile.get('polish_ceiling', 'clean photographed')}; {format_text} "
            f"Capture {temporal.get('capture_fps')} fps at {temporal.get('shutter_angle')} degree shutter, exposure time {temporal.get('exposure_time_s')} seconds, "
            f"playback {temporal.get('playback_rate')}, and deliver {temporal.get('delivery_fps')} fps. "
            "Real photographed people and physical sets; restrained source-shaped contrast and clean digital surfaces. "
            "No animation, illustration, CG/PBR or game-render finish; no synthetic glossy skin, uniform oil film, painterly smear, "
            "topographic contour, maze, fingerprint, cellular or repeating cross-material texture, "
            "unmotivated rim light, sharpening halo, frame blending, ghost limbs, texture crawl or jelly warping."
            f"{commercial_style}"
        ),
        "SCENE": f"{shot.get('story_beat')} {environment_text} {dramatic_coverage_text}{commercial_scene}",
        "CHARACTERS": (
            f"Bind these exact approved references by handle: {reference_text}. {geometry_text or 'No person is present; do not invent one.'}. "
            f"{multi_person_projection_text} {temporal_surface_locks}"
        ),
        "LOCATION": render_spatial_prompt_block(shot, spatial_map),
        "FIRST FRAME AND BLOCKING": (
            f"Begin at the exact camera and subject marks declared in LOCATION. {geometry_text}. "
            f"{dramatic_coverage_text} {multi_person_projection_text} Preserve set-fixed facing, foreground/midground/background order, relative height, "
            "weight bearing, garment/body separation, contact points and occlusion order."
        ),
        "Shot 1": (
            f"One continuous {shot.get('duration_s')}-second shot. Execute in order: "
            + "; ".join(str(value) for value in shot.get("action_beats", []))
            + f". Performance is task-led and physically continuous, never a publicity pose. End at the recorded final pose and camera mark; no unplanned cut.{commercial_action}"
        ),
        "OPTICS": (
            f"{shot.get('focal_length_mm')} mm at T{shot.get('t_stop')}; {shot.get('focus_plan')}; {shot.get('exposure_notes')}. "
            "Keep natural perspective, causal focus falloff, source-shaped highlights and readable middle tones."
        ),
        "CAMERA": (
            f"{_format_camera_path(shot.get('camera_move_plan'))} Motion blur is caused by {blur.get('source')}, direction {blur.get('direction')}, "
            f"amount {blur.get('amount')}; keep {', '.join(blur.get('static_reference_regions', []))} stable where physically expected.{commercial_camera}"
        ),
        "PHYSICS": physics_text,
        "LIGHTING": (
            f"{light_material_response} {subject_environment_text} "
            f"{quality_profile.get('tone_contrast_contract', '')} {dynamic_range}"
        ),
        "AUDIO": f"{shot.get('audio')} {commercial_audio}".strip(),
    }
    for heading in VIDEO_PROMPT_HEADERS:
        blocks.append(_prompt_block(heading, bodies[heading]))
    return "\n".join(blocks).strip() + "\n"


def _commercial_direction_for_shot(data: Any, shot_id: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("mode") == "not_applicable":
        return {}
    routes = {
        item.get("id"): item for item in data.get("creative_routes", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    rhythm_plan = data.get("rhythm_plan") if isinstance(data.get("rhythm_plan"), dict) else {}
    rhythm_rows = {
        item.get("shot_id"): item for item in rhythm_plan.get("shot_rhythm", [])
        if isinstance(item, dict) and isinstance(item.get("shot_id"), str)
    }
    speed_rows = {
        item.get("id"): item for item in rhythm_plan.get("speed_palette", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    row = rhythm_rows.get(shot_id)
    if not isinstance(row, dict):
        return {}
    return {
        "mode": data.get("mode"),
        "route": routes.get(data.get("selected_route_id"), {}),
        "shot_rhythm": row,
        "speed": speed_rows.get(row.get("speed_palette_id"), {}),
        "music": rhythm_plan.get("music", {}),
        "audio_plan": data.get("audio_plan", {}),
    }


def compile_prompts(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.is_dir():
        print(f"ERROR: project directory does not exist: {project_dir}", file=sys.stderr)
        return 2
    try:
        _require_schema_16(project_dir)
        assets_manifest = _read_json_strict(project_dir / "manifests/assets.json")
        candidates_manifest = _read_json_strict(project_dir / "manifests/candidates.json")
        reviews_manifest = _read_json_strict(project_dir / "manifests/reviews.json")
        quality_manifest = _read_json_strict(project_dir / "manifests/quality.json")
        cinema_manifest = _read_json_strict(project_dir / "manifests/cinematography.json")
        identities_manifest = _read_json_strict(project_dir / "manifests/identities.json")
        shots_manifest = _read_json_strict(project_dir / "manifests/shots.json")
        spatial_manifest = _read_json_strict(project_dir / "manifests/spatial.json")
        world_manifest = _read_json_strict(project_dir / "manifests/world-state.json")
        commercial_path = project_dir / "manifests/commercial.json"
        commercial_manifest = _read_json_strict(commercial_path) if commercial_path.is_file() else None
        gate = _find_record(reviews_manifest.get("review_gates"), args.gate, "review gate")
        output_root = Path("prompts/compiled") / f"{args.gate}--v001"
        if (project_dir / output_root).exists():
            raise ValueError(f"compiled prompt gate {args.gate} v001 already exists; old prompt versions are never overwritten")
        assets = {item.get("id"): item for item in assets_manifest.get("assets", []) if isinstance(item, dict)}
        candidate_sets = {item.get("id"): item for item in candidates_manifest.get("candidate_sets", []) if isinstance(item, dict)}
        quality_profiles = {item.get("id"): item for item in quality_manifest.get("project_quality_profiles", []) if isinstance(item, dict)}
        identities = {item.get("id"): item for item in identities_manifest.get("identity_packs", []) if isinstance(item, dict)}
        comparisons = {item.get("id"): item for item in cinema_manifest.get("comparison_sets", []) if isinstance(item, dict)}
        format_plans = {item.get("id"): item for item in cinema_manifest.get("format_plans", []) if isinstance(item, dict)}
        spatial_maps = {item.get("id"): item for item in spatial_manifest.get("spatial_maps", []) if isinstance(item, dict)}
        environmental_states = {item.get("id"): item for item in world_manifest.get("environmental_states", []) if isinstance(item, dict)}
        special_events = {item.get("id"): item for item in world_manifest.get("special_lighting_events", []) if isinstance(item, dict)}
        compiled_index: list[dict[str, Any]] = []
        pending_writes: list[tuple[Path, str]] = []
        for asset_id in gate.get("asset_ids", []):
            asset = assets.get(asset_id)
            if not isinstance(asset, dict) or asset.get("generator") != "builtin-imagegen":
                continue
            quality_profile = quality_profiles.get(asset.get("quality_profile_id"))
            if not isinstance(quality_profile, dict):
                raise ValueError(f"asset {asset_id} has no project quality Profile")
            identity_pack = identities.get(asset.get("identity_pack_id"))
            comparison = comparisons.get(asset.get("comparison_set_id"))
            content = _compile_image_prompt(asset, quality_profile, identity_pack, comparison)
            prompt_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            relative = output_root / "images" / f"{asset_id}.txt"
            pending_writes.append((relative, content))
            asset["prompt_path"] = relative.as_posix()
            provenance = asset.get("generation_provenance")
            if isinstance(provenance, dict):
                provenance["prompt_sha256"] = prompt_digest
            candidate_set = candidate_sets.get(asset.get("candidate_set_id"))
            if isinstance(candidate_set, dict):
                candidate_set["prompt_path"] = relative.as_posix()
                for variant in _candidate_variants(candidate_set):
                    variant["prompt_sha256"] = prompt_digest
            compiled_index.append({"kind": "image", "id": asset_id, "path": relative.as_posix(), "sha256": prompt_digest})

        sequence_id = gate.get("sequence_cluster_id")
        for shot in shots_manifest.get("shots", []):
            if not isinstance(shot, dict) or not sequence_id or shot.get("sequence_cluster_id") != sequence_id:
                continue
            spatial_map = spatial_maps.get(shot.get("spatial_map_id"))
            format_plan = format_plans.get(shot.get("format_plan_id"))
            quality_profile = quality_profiles.get(shot.get("quality_profile_id"))
            environment = environmental_states.get(shot.get("environmental_state_id"), {})
            events = [special_events[event_id] for event_id in shot.get("special_lighting_event_ids", []) if event_id in special_events]
            if not isinstance(spatial_map, dict) or not isinstance(format_plan, dict) or not isinstance(quality_profile, dict):
                raise ValueError(f"shot {shot.get('id')} lacks spatial map, format plan or quality Profile")
            commercial_direction = _commercial_direction_for_shot(commercial_manifest, shot.get("id"))
            content = _compile_video_prompt(
                shot, spatial_map, format_plan, quality_profile, environment, events, commercial_direction
            )
            relative = output_root / "video" / f"{shot.get('id')}.txt"
            pending_writes.append((relative, content))
            shot["video_prompt_path"] = relative.as_posix()
            shot["model_prompt_strategy_id"] = "shot-model-v1.6"
            compiled_index.append({"kind": "video", "id": shot.get("id"), "path": relative.as_posix(), "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()})
        if not pending_writes:
            raise ValueError(f"review gate {args.gate} contains no compilable image assets or sequence shots")
        for relative, content in pending_writes:
            path = project_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            portable_write_text(path, content)
        portable_write_json(
            project_dir / output_root / "index.json",
            {"schema_version": SCHEMA_VERSION, "gate_id": args.gate, "compiler": "deterministic-structured-facts-v1.6", "files": compiled_index},
        )
        write_json(project_dir / "manifests/assets.json", assets_manifest)
        write_json(project_dir / "manifests/candidates.json", candidates_manifest)
        write_json(project_dir / "manifests/shots.json", shots_manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: compile-prompts failed: {exc}", file=sys.stderr)
        return 2
    print(f"Compiled {len(compiled_index)} deterministic prompts under {project_dir / output_root}.")
    return 0


__all__ = [name for name in globals() if not name.startswith("__")]
