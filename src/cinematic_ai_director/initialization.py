"""Project initialization for schema v1.6."""

from __future__ import annotations

from .schema import *


def init_project(args: argparse.Namespace) -> int:
    if not SLUG_RE.fullmatch(args.slug):
        print("ERROR: --slug must contain lowercase letters, digits, and single hyphens only.", file=sys.stderr)
        return 2
    if not args.title.strip():
        print("ERROR: --title must not be empty.", file=sys.stderr)
        return 2
    if not ASPECT_RE.fullmatch(args.aspect):
        print("ERROR: --aspect must look like 16:9.", file=sys.stderr)
        return 2

    root = Path(args.root).expanduser().resolve() if args.root else (Path.cwd() / "ai-film").resolve()
    target = root / args.slug
    if target.exists():
        print(f"ERROR: target already exists; refusing to overwrite: {target}", file=sys.stderr)
        return 2

    root.mkdir(parents=True, exist_ok=True)
    temp_path = Path(tempfile.mkdtemp(prefix=f".{args.slug}-", dir=root))
    now = utc_now()
    production_kind = str(getattr(args, "project_kind", "narrative-film")).replace("-", "_")
    if production_kind not in PRODUCTION_KINDS:
        print(f"ERROR: unsupported --project-kind: {production_kind}", file=sys.stderr)
        return 2

    try:
        for relative in REQUIRED_DIRS:
            (temp_path / relative).mkdir(parents=True, exist_ok=True)
        for relative in ("assets/products", "prompts/images/products"):
            (temp_path / relative).mkdir(parents=True, exist_ok=True)

        project = {
            "schema_version": SCHEMA_VERSION,
            "id": args.slug,
            "title": args.title.strip(),
            "slug": args.slug,
            "aspect_ratio": args.aspect,
            "interaction_language": args.language,
            "prompt_language": args.prompt_language,
            "production_mode": "live-action",
            "production_kind": production_kind,
            "capture_policy": "adaptive-live-action-v1.6",
            "dynamic_range_policy": {
                "mode": "finite_scene_referred",
                "infinite_hdr_forbidden": True,
                "multi_exposure_merge_forbidden": True,
                "rule": "Every photographed frame declares what exposure protects and what highlight or shadow information may be lost.",
            },
            "static_generator": "builtin-imagegen",
            "video_generation": "package-only",
            "approval_mode": "foundation-and-sequence-gates",
            "image_prompt_strategy": "image2-live-action-evidence-v1.6",
            "video_prompt_strategy": "shot-model-v1.6",
            "higgsfield_conformance": {
                "official_profile_id": HIGGSFIELD_OFFICIAL_PROFILE_ID,
                "knowledge_snapshot": HIGGSFIELD_KNOWLEDGE_SNAPSHOT,
                "target_workflow": "cinema-studio-4",
                "target_model": "seedance-2.5",
                "strict": True,
                "version_policy": "snapshot-must-match-or-block",
                "source_urls": list(HIGGSFIELD_OFFICIAL_SOURCE_URLS),
                "method_profile_id": HIGGSFIELD_METHOD_PROFILE_ID,
                "official_skills_version": HIGGSFIELD_SKILLS_SNAPSHOT_VERSION,
                "integration_mode": "methods-only-offline",
                "execution_boundary": dict(HIGGSFIELD_METHOD_EXECUTION_BOUNDARY),
            },
            "candidate_policy": {
                "identity_inspector_initial_count": 1,
                "identity_inspector_max_batches": 1,
                "critical_initial_count": 3,
                "derivative_initial_count": 2,
                "retry_count": 2,
                "max_batches": 2,
                "reviewer": "codex-visual",
                "expose_failed_candidates": False,
            },
            "identity_layout_policy": {
                "default_profile": IDENTITY_LAYOUT_PROFILE,
                "legacy_profiles_readable": [LEGACY_IDENTITY_LAYOUT_PROFILE],
                "single_identity_solve": True,
                "deterministic_crops_only": True,
            },
            "resolution_policy": {
                "mode": "strict_native_detail_v1.6.6",
                "effective_at": now,
                "minimum_identity_board_px": [1536, 1024],
                "minimum_identity_cell_width_px": 512,
                "minimum_full_body_subject_height_px": 560,
                "minimum_portrait_face_height_px": 300,
                "minimum_authority_long_edge_px": 1536,
                "minimum_narrative_long_edge_px": 1920,
                "minimum_narrative_short_edge_px": 1080,
                "no_dimension_only_upscale": True,
                "native_generation_or_source_required": True,
                "inspection_scales": ["thumbnail", "fit", "100_percent", "200_percent"],
            },
            "motion_baseline": {
                "capture_fps": 24,
                "delivery_fps": 24,
                "shutter_angle": 180,
                "exposure_time_s": 180 / (360 * 24),
            },
            "reproducibility": {
                "backend": "builtin-imagegen",
                "reproducibility_class": "workflow_only",
                "pixel_reproducible": False,
            },
            "created_at": now,
            "updated_at": now,
            "scenes": [],
        }
        write_json(temp_path / "project.json", project)
        write_json(temp_path / "manifests/assets.json", {"schema_version": SCHEMA_VERSION, "assets": []})
        write_json(
            temp_path / "manifests/cinematography.json",
            {
                "schema_version": SCHEMA_VERSION,
                "policy": "adaptive-live-action-v1.6",
                "base_profile_id": "",
                "base_treatment_id": "",
                "base_format_plan_id": "",
                "profiles": [],
                "cinematic_treatments": [],
                "format_plans": [],
                "medium_signatures": [],
                "comparison_sets": [],
            },
        )
        write_json(temp_path / "manifests/shots.json", {"schema_version": SCHEMA_VERSION, "shots": []})
        write_json(temp_path / "manifests/spatial.json", {"schema_version": SCHEMA_VERSION, "spatial_maps": []})
        write_json(
            temp_path / "manifests/continuity.json",
            {"schema_version": SCHEMA_VERSION, "tracks": [], "transitions": []},
        )
        write_json(
            temp_path / "manifests/identities.json",
            {"schema_version": SCHEMA_VERSION, "identity_packs": [], "character_states": []},
        )
        write_json(
            temp_path / "manifests/world-state.json",
            {
                "schema_version": SCHEMA_VERSION,
                "production_design_dna": {
                    "period": "",
                    "socioeconomic_context": "",
                    "architecture_logic": "",
                    "color_sources": [],
                    "material_rules": [],
                    "public_infrastructure": [],
                    "signage_policy": "",
                    "ageing_policy": "clean_authority; localized defects only when story-declared",
                },
                "location_worlds": [],
                "location_states": [],
                "prop_states": [],
                "environmental_states": [],
                "special_lighting_events": [],
            },
        )
        write_json(
            temp_path / "manifests/sequences.json",
            {
                "schema_version": SCHEMA_VERSION,
                "provider_adapters": {
                    "higgsfield": {
                        "knowledge_snapshot": HIGGSFIELD_KNOWLEDGE_SNAPSHOT,
                        "official_profile_id": HIGGSFIELD_OFFICIAL_PROFILE_ID,
                        "official_source_urls": list(HIGGSFIELD_OFFICIAL_SOURCE_URLS),
                        "strict_conformance": True,
                        "default_target_workflow": "cinema-studio-4",
                        "default_target_model": "seedance-2.5",
                        "prompt_sections": list(VIDEO_PROMPT_HEADERS),
                        "reference_limits": HIGGSFIELD_ADAPTER_LIMITS,
                        "camera_move_segment_limits": HIGGSFIELD_CAMERA_MOVE_LIMITS,
                        "method_profile_id": HIGGSFIELD_METHOD_PROFILE_ID,
                        "official_skills_version": HIGGSFIELD_SKILLS_SNAPSHOT_VERSION,
                        "integration_mode": "methods-only-offline",
                    }
                },
                "sequence_clusters": [],
            },
        )
        write_json(temp_path / "manifests/takes.json", {"schema_version": SCHEMA_VERSION, "takes": []})
        write_json(
            temp_path / "manifests/quality.json",
            {
                "schema_version": SCHEMA_VERSION,
                "quality_floor_id": QUALITY_FLOOR_ID,
                "quality_floors": [
                    {
                        "id": QUALITY_FLOOR_ID,
                        "status": "stable",
                        "evidence_role": "calibration_only",
                        "direct_generation_reference": False,
                        "source_note": "User-supplied clean observational photograph translated into portable observable behavior; source pixels are not sent to ImageGen.",
                        "observable_behaviors": {
                            "photographic_event": "A physically present camera observes ordinary behavior from a reachable human position.",
                            "skin_response": "Continuous natural hue and value transitions; highlights remain source-shaped and never form a uniform oil film.",
                            "material_separation": "Skin, hair, fabric, painted surfaces, wood, glass and metal keep independent reflection and edge behavior.",
                            "tone_and_contrast": "Restrained local contrast, protected middle tones and gradual highlight roll-off without HDR carving.",
                            "dynamic_range": "Finite capture latitude forces a declared exposure priority; source cores or deep shadows may lose detail instead of every tonal region being equally legible.",
                            "focus_and_optics": "Natural perspective and motivated focus falloff rather than universally shallow depth of field.",
                            "set_causality": "Construction, utilities, use traces and dressing have a practical cause; random dirt is not realism.",
                            "performance_and_composition": "Task-led or conversational behavior with plausible unused space and mild occlusion, not a publicity pose.",
                        },
                    }
                ],
                "project_quality_profiles": [],
                "live_action_integration_probes": [],
                "calibration_families": [],
            },
        )
        write_json(
            temp_path / "manifests/candidates.json",
            {
                "schema_version": SCHEMA_VERSION,
                "policy": {
                    "identity_inspector_initial_count": 1,
                    "identity_inspector_max_batches": 1,
                    "critical_initial_count": 3,
                    "derivative_initial_count": 2,
                    "retry_count": 2,
                    "max_batches": 2,
                    "failed_candidates_visible_by_default": False,
                },
                "candidate_sets": [],
            },
        )
        write_json(
            temp_path / "manifests/reviews.json",
            {"schema_version": SCHEMA_VERSION, "review_gates": []},
        )
        write_json(
            temp_path / "manifests/higgsfield-methods.json",
            {
                "schema_version": SCHEMA_VERSION,
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
                    "adopted": [
                        "Intent-first routing before prompt writing",
                        "Explicit reference responsibilities and deterministic reference order",
                        "Identity source quality, diversity, consent, and rights checks",
                        "Product truth locking before lifestyle, campaign, or video derivatives",
                        "Short model-facing instructions with production QA retained in manifests",
                    ],
                    "translated": [
                        "Live model-schema discovery becomes an operator preflight in the offline package",
                        "Soul training-photo guidance becomes a local readiness record without training",
                        "Product Photoshoot modes become local intent briefs without backend prompt emulation",
                        "Image, video, and audio generation defaults become advisory capability routes only",
                    ],
                    "provider_only_not_emulated": [
                        "Soul model training and reusable reference-id creation",
                        "Product Photoshoot backend prompt enhancement",
                        "Model execution, uploads, job polling, account access, and credit consumption",
                    ],
                },
                "generation_routes": [],
                "soul_readiness_records": [],
                "product_authorities": [],
                "product_photoshoot_briefs": [],
            },
        )
        commercial_mode = (
            "commercial_tvc" if production_kind == "commercial_tvc"
            else "commercial_mv_hybrid" if production_kind == "music_video"
            else "not_applicable"
        )
        write_json(
            temp_path / "manifests/commercial.json",
            {
                "schema_version": SCHEMA_VERSION,
                "mode": commercial_mode,
                "status": "planned",
                "commercial_brief": {
                    "category": "other",
                    "objective": "",
                    "audience": "",
                    "placement": "",
                    "runtime_s": 0,
                    "single_proposition": "",
                    "reasons_to_believe": [],
                    "mandatory_elements": [],
                    "brand_codes": [],
                    "prohibited_generic_codes": [],
                    "success_measure": "",
                },
                "creative_routes": [],
                "selected_route_id": "",
                "brand_assets": [],
                "wardrobe_looks": [],
                "rhythm_plan": {
                    "music": {
                        "usage": "score",
                        "bpm": 0,
                        "meter": "",
                        "downbeat_s": 0,
                        "energy_curve": [],
                    },
                    "tempo_motion_relationship": "free",
                    "relationship_reason": "",
                    "edit_strategy": "",
                    "speed_palette": [],
                    "shot_rhythm": [],
                },
                "audio_plan": {
                    "dialogue_vo": [],
                    "music": [],
                    "ambience": [],
                    "foley": [],
                    "transition_accents": [],
                    "brand_mnemonic": [],
                    "mix_hierarchy": [],
                },
                "deliverables": [],
                "qa": {
                    "checks": {name: False for name in COMMERCIAL_QA_CHECKS},
                    "hard_failures": [],
                    "notes": [],
                    "checked_at": "",
                    "reviewer": "codex-structural",
                },
            },
        )
        (temp_path / "creative-bible.md").write_text(
            creative_bible_template(args.title.strip(), args.aspect), encoding="utf-8"
        )
        (temp_path / "edit-plan.md").write_text(edit_plan_template(args.title.strip()), encoding="utf-8")
        (temp_path / "qa/asset-review.md").write_text(asset_review_template(args.title.strip()), encoding="utf-8")
        (temp_path / "qa/cinematography-review.md").write_text(
            cinematography_review_template(args.title.strip()), encoding="utf-8"
        )
        (temp_path / "qa/spatial-review.md").write_text(
            spatial_review_template(args.title.strip()), encoding="utf-8"
        )
        (temp_path / "qa/shot-review.md").write_text(shot_review_template(args.title.strip()), encoding="utf-8")
        (temp_path / "qa/cross-scene-review.md").write_text(
            cross_scene_review_template(args.title.strip()), encoding="utf-8"
        )
        (temp_path / "qa/proportion-review.md").write_text(
            proportion_review_template(args.title.strip()), encoding="utf-8"
        )
        (temp_path / "qa/quality-review.md").write_text(
            quality_review_template(args.title.strip()), encoding="utf-8"
        )
        (temp_path / "qa/live-action-integration-review.md").write_text(
            "# Live-action Integration Review\n\n"
            "No person-bearing narrative asset may proceed until one ordinary-light integration probe "
            "passes at thumbnail, fit, 100%, and 200%. A second failed batch blocks the backend for this "
            "identity/location pair and requires lawful real-photo references or package-only work.\n",
            encoding="utf-8",
        )
        (temp_path / "qa/environment-review.md").write_text(
            environment_review_template(args.title.strip()), encoding="utf-8"
        )
        (temp_path / "qa/temporal-review.md").write_text(
            temporal_review_template(args.title.strip()), encoding="utf-8"
        )
        (temp_path / "qa/commercial-review.md").write_text(
            f"# {args.title.strip()} — Commercial / TVC Review\n\n"
            "Use only when manifests/commercial.json mode is commercial_tvc or commercial_mv_hybrid. "
            "Review business specificity, creative alternatives, product/wardrobe proof, beat-to-action timing, "
            "capture-speed logic, complete sound design, exact runtime and destination-specific delivery.\n",
            encoding="utf-8",
        )
        (temp_path / "qa/higgsfield-methods-review.md").write_text(
            f"# {args.title.strip()} — Higgsfield Methods Review\n\n"
            "This review adopts planning and quality practices from the official higgsfield-generate, "
            "higgsfield-soul-id, and higgsfield-product-photoshoot skills. It must never record a CLI install, "
            "login, upload, Soul training job, generation job, polling action, or credit spend. Verify task intent, "
            "reference responsibilities, real-person consent, product truth, prompt ownership, and the current "
            "platform schema before a human later uses the offline package.\n",
            encoding="utf-8",
        )
        temp_path.replace(target)
    except Exception as exc:  # pragma: no cover - defensive cleanup
        if temp_path.exists():
            shutil.rmtree(temp_path)
        print(f"ERROR: project initialization failed: {exc}", file=sys.stderr)
        return 2

    print(f"Created cinematic AI film project: {target}")
    return 0


__all__ = [name for name in globals() if not name.startswith("__")]
