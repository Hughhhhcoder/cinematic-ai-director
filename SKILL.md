---
name: cinematic-ai-director
description: Build, continue, audit, or export multi-shot live-action AI film, commercial, and music-video packages with one single-solve identity inspection board per person, role-conditioned physique, evidence-based clean ImageGen assets, finite scene-referred dynamic range, backstage candidate selection, foundation-and-sequence approvals, locked world states, spatially anchored sets, adaptive cinematography, physical weather and light, executable camera and motion-blur plans, and strict versioned Higgsfield production packages. Use for recurring photographed people, locations, props, blocking, cinematography, exposure, movement, and continuity; do not use for animation, illustration, CG, game art, or casual one-off images.
---

# Cinematic AI Director

Turn a live-action script into an auditable, low-interruption v1.6 production package that a human can execute in Higgsfield:

`reality and casting analysis → role-conditioned physique brief → one single-solve identity inspector → seven deterministic inspection crops → character/location/prop states → finite dynamic-range and quality profile → backstage candidate selection → foundation gate → sequence visual anchors → sequence gates → strict Higgsfield export or returned-take audit`

Match the user's language and fall back to English. Write generation prompts in English unless the user asks otherwise. Defaults are 16:9 and 24 fps/180°. Create projects under `<cwd>/ai-film/<slug>` unless the user chooses another root.

## Route the request

- New live-action script: read [pipeline.md](references/pipeline.md), [quality-evidence.md](references/quality-evidence.md), [role-physique.md](references/role-physique.md), [human-geometry.md](references/human-geometry.md), [candidate-selection.md](references/candidate-selection.md), [world-sequences.md](references/world-sequences.md), [spatial-system.md](references/spatial-system.md), [cinematic-grammar.md](references/cinematic-grammar.md), [atmosphere-weather.md](references/atmosphere-weather.md), [camera-motion-temporal.md](references/camera-motion-temporal.md), and [project-schema.md](references/project-schema.md).
- Existing project: first run `python3 scripts/film_project.py validate <project-dir>`. For schema v1.0–v1.5, report `LEGACY_SCHEMA`; never migrate or write automatically.
- Static assets: read [static-assets.md](references/static-assets.md), [quality-evidence.md](references/quality-evidence.md), [role-physique.md](references/role-physique.md), [image2-clean.md](references/image2-clean.md), and [candidate-selection.md](references/candidate-selection.md).
- Cinematography, format, weather, special light, or camera movement: read [cinematography.md](references/cinematography.md), [cinematic-grammar.md](references/cinematic-grammar.md), [atmosphere-weather.md](references/atmosphere-weather.md), and [camera-motion-temporal.md](references/camera-motion-temporal.md).
- Photoboards, keyframes, and shot packages: read [video-prompting.md](references/video-prompting.md), [spatial-system.md](references/spatial-system.md), [world-sequences.md](references/world-sequences.md), and [continuity-qa.md](references/continuity-qa.md).
- Higgsfield export or returned-take audit: read [higgsfield-export.md](references/higgsfield-export.md), validate first, then export. Register returned videos in `takes.json` and perform temporal QA.
- Research or recalibration: read [research-basis.md](references/research-basis.md) and [imagegen-calibration.md](references/imagegen-calibration.md). Load the large [higgsfield-public-index.md](references/higgsfield-public-index.md) only when public-source coverage must be checked.

Do not activate this skill for animation, illustration, anime, CG/PBR promotional renders, game art, or pure concept art. In a mixed-media project, handle only the photographed live-action portion.

## Non-negotiable boundaries

1. Use only Codex built-in ImageGen for still assets, with one independent call per candidate. Do not call external image APIs, Higgsfield, Runway, third-party generators, or credit-consuming services.
2. Never install or run texture cleaners. Noise reduction, blur, downsampling, sharpening, or compression cannot rehabilitate a failed authority asset.
3. Video work ends at production facts, prompts, offline Higgsfield packages, and audits of videos returned by the user. Never sign in, upload, click Generate, or spend credits.
4. Keep `pixel_reproducible:false`. Reproduce workflow, prompt compilation, reference order, hashes, state locks, approvals, validation, and export—not random pixels or imaginary seeds.
5. Do not use scraped people as identity roots. A real-person reference must be user-provided with confirmed rights and identity consent.
6. Failed, rejected, superseded, state-derived, or candidate assets cannot become roots. Keep failed candidates out of authoritative manifests and routine user review.
7. Store user decisions only in review gates. QA stores Codex's pixel and structural evidence, not duplicate approvals.
8. A user-supplied quality reference is calibration-only unless the user explicitly authorizes content reuse; do not leak its person, home, light, or composition into unrelated projects.
9. Treat Higgsfield compatibility as a dated official conformance contract. Export only Cinema Studio 4 / Seedance 2.5 packages matching `cinema-studio-4-seedance-2.5-official-2026-08-27`; if the live UI differs, stop and update the adapter. Never claim stochastic pixels or platform generations are guaranteed.
10. Treat every still and shot as one finite, scene-referred exposure. Never ask a model to make the brightest source, face, set and deepest shadow equally detailed. Declare the middle-tone anchor, exposure priority, working latitude, expected highlight roll-off/clipping and expected shadow floor/loss; forbid unrecorded local tone mapping and multi-exposure HDR fusion.

## v1.6 production contract

- Derive the reality, casting, role-physique, production-design, state, and project-quality briefs before generating assets.
- Use `clean_authority` for roots and `clean_narrative` for story images. Enable a medium signature only after two independent passing calibration rounds.
- Give each recurring person one complete pure-white 4×2 identity inspector generated in one ImageGen call so every angle shares one identity solve. Use Higgsfield's official two-row roles: top row full front, full left profile, full right profile, full back; bottom row portrait front, portrait left profile, portrait right profile, then one empty white cell. No labels, borders, props, scenery, mood light, or panel-specific reinterpretation.
- Inspect the complete board before any crop, state, frame, or sequence generation. If any panel changes identity, body, wardrobe, scale, anatomy, skin response, lighting, or surface quality, mark the inspector and identity pack `model_blocked` after that one failed board; do not retry the same identity or contaminate downstream work.
- After a board passes, use `build-reference-board` to make seven deterministic, non-resampled PNG crops. The unified board remains the first and only identity authority; crops are inspection/UI upload aids and may never become roots or independent identity solves.
- Define physique by role, age, profession, training history, health, period, narrative function, wardrobe silhouette, and stated casting intent. Target-driven bodies require measurable ranges and rejection criteria; never fall back to a generic short-legged or boxy body.
- For fictional adult leads, default to a naturally measured `balanced_four_six` visual leg/body target; use an `elongated_three_seven` impression only when casting or story supports it. Reject any unintended `5:5` silhouette at identity, wardrobe-state, and narrative-frame gates. Prove the target with a level camera and normal perspective—never low-angle or wide-lens stretching.
- Establish each location as a world plus state views. Require an empty establishing wide and an independently generated side three-quarter wide sharing one fixed primary anchor and an approximately 0.1 m set coordinate system.
- Derive an original treatment, approved format, environmental physics, motivated special light, reachable camera path, temporal capture, and motion-blur plan. Translate named references into observable behavior rather than sending names to a model.
- Before generating any photographed asset, estimate scene contrast and approve the project's finite `dynamic_range_contract`, then record that asset's own `dynamic_range_plan`. Neutral references use a controlled low-contrast plan; empty locations cannot inherit human/skin exposure wording; narrative frames state what must remain readable and what is allowed to clip or fall below the texture floor.
- The identity inspector is a deliberate exception to the candidate pool: exactly one call and one board, with no retry for that same identity. Generate three candidates for other critical roots, each Look, sequence anchors, and hero frames; generate two for states, location angles, Photoboards, and ordinary keyframes. Never edit one candidate into another.
- Inspect thumbnail, fit, 100%, and 200%. A selected candidate must pass live-action quality, geometry, photographic, and when relevant spatial/environment QA with positive photographic evidence.
- Except for the single-attempt identity inspector, if the first batch entirely fails, change one highest-priority variable and independently generate two retries. If both fail, mark `model_blocked` and request a lawful real reference.
- Interrupt the user only for one Foundation gate plus one gate per sequence, except for legal-reference gaps, two failed batches, or a genuine story-direction conflict.
- Keep exact root order and SHA-256 inside a sequence. A bridge frame supplements identity/location roots; it never replaces them.
- A Ready shot must bind the exact quality/capture profile, finite `dynamic_range_plan`, treatment, format, identity/physique/proportion, character/location/prop/environment states, spatial map, camera path, temporal capture, motion blur, keyframes, physics, and audio.
- Derive blur from frame rate, shutter, camera path, and subject speed. Block frame blending, double contours, ghost limbs, jelly warping, texture crawl, oil-glint flicker, and direction contradictions.
- Export only after all target shots are Ready, their gates are approved, validation has zero errors, and the strict dated Higgsfield Profile supports reference roles/count, 9:16–21:9 format, at-most-30-second generation, prompt order, and camera mapping. Mismatch means block, never silent downgrade.

## Live-action quality gate

- Require a plausible photographic event, motivated highlight topology, continuous skin tone, independent roughness for skin/hair/fabric/wall/wood/metal, natural focus falloff, causal production design, and task-led performance.
- Require finite exposure evidence: one declared middle-tone anchor and exposure priority, plausible source-core roll-off or clipping, a real shadow floor with some detail allowed to disappear, and `global_tone_mapping_detected:false`. Uniformly legible windows, bulbs, faces and black recesses are an infinite-HDR hard failure.
- Allowed skin states are `natural_dry`, `normal`, `perspiration`, `rain_wet`, `submerged`, and `cosmetic_sheen`. Non-default states require cause, bounded regions, and duration. Uniform oil film, isolated beauty glints, wax/plastic skin, and unmotivated colored edges always fail.
- Disable visible grain, halation, chromatic aberration, dirty-lens effects, global bloom, clarity/HDR sculpting, and artificial age texture by default.
- Treat painterly patches, animation, CG/PBR or game-cinematic surfaces, clumped hair, prosthetic eyes, melted fabric, rendered outlines, repeating swirl/scale/cellular artifacts, cross-material dirt, and unmotivated light as hard failures.
- Do not use `weathered`, `worn`, `gritty`, `pores`, `film grain`, `8K`, `ultra-detailed`, `premium cinematic`, `hero lighting`, `dramatic rim light`, `game cinematic`, or `trailer still` as shortcuts unless a scoped two-round calibration proves a stable benefit.
- Compile prompts deterministically from structured facts. Version outputs and refuse overwrite.

## Commands

```bash
python3 scripts/film_project.py init --root <root> --title <title> --slug <slug>
python3 scripts/film_project.py validate <project-dir>
python3 scripts/film_project.py compile-prompts <project-dir> --gate <gate-id>
python3 scripts/film_project.py build-reference-board <project-dir> --identity-pack <pack-id>
python3 scripts/film_project.py build-review-board <project-dir> --gate <gate-id>
python3 scripts/film_project.py record-review <project-dir> --gate <gate-id> --decision approved --selection <comparison-id>=<profile-id>
python3 scripts/film_project.py record-review <project-dir> --gate <gate-id> --decision changes_requested --affected <id> --note <reason>
python3 scripts/film_project.py export-higgsfield <project-dir> --output <portable-dir>
```

## Completion

Call a stage complete only when failed candidates are isolated; Foundation and all relevant sequence gates are decided; identity, role physique, proportions, states, spatial/format/camera/temporal facts are traceable; quality, geometry, photographic, spatial, and continuity QA pass; validation reports zero errors; the Higgsfield package verifies offline; and no external generation was executed. Report absolute project/export paths, gate decisions, approved/blocked items, candidate pass rate, sequence/shot counts, validation, `pixel_reproducible:false`, and the platform actions that were intentionally not performed.
