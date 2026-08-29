# Changelog

All notable public changes are documented here. The project follows [Semantic Versioning](https://semver.org/).

## [1.6.6] — 2026-08-29

### Added

- Added an adaptive commercial/TVC reasoning contract covering the business brief, two materially different creative routes, competitor-swap rejection, per-shot function/removal tests, fashion look and material proof, full sound direction, and destination-specific delivery matrices.
- Added a mathematical editorial-rhythm contract: BPM/beat intervals, exact shot frames, commissioned runtime, action peaks, speed palettes, shutter/exposure, internal rhythmic events, and explicit fast-music/uniform-slow-motion mismatch blocking.
- Added strict native-detail QA that verifies real file dimensions, subject pixel coverage, focus/edge resolution, resampling/compression, and dimension-only enlargement before an asset can proceed.
- Added an explicit `topographic_contour_or_maze_skin_texture` failure class after native 100%/200% v1.6.6 Inspector tests showed that negative prompt wording alone does not reliably remove low-contrast repeated face texture.
- Added focused regression tests for the 3×2 identity layout, identity prompt contract, commercial initialization, route/rhythm/speed/delivery gates, fashion proof, and native-resolution failures.

### Changed

- New identities now use one large high-resolution 3×2 white Inspector generated in one call: full-body front/primary-profile/back above large face front/left-profile/right-profile. Six upload/inspection images are exact crops; the unified board remains the first authority. The earlier 4×2 form remains a read/export compatibility adapter for existing v1.6 projects.
- Commercial and MV projects are no longer treated as narrative films with a logo appended. Picture prompts receive only supported, visible creative/rhythm facts while complete business, edit, sound, and delivery evidence remains in deterministic sidecars.
- Kept all failed v1.6.6 identity-board generations out of the repository and public gallery; a clean thumbnail cannot overrule native-scale skin artifacts or insufficient full-body pixel coverage.
- Removed the superseded v1.6.5 public images, prompts, and board-builder from the current release tree after renewed geometry, material, and person–world review. Git history remains the audit trail; v1.6.6 publishes only an anonymized withheld-by-quality-gate record until a complete new chain passes.
- Schema remains `1.6`; the new policies are additive and timestamped so existing v1.6 projects remain readable without rewriting previously approved assets.

## [1.6.5] — 2026-08-28

### Added

- Added `image2-live-action-locked-insertion-probe-v1.6`: the approved empty location is now the immutable first image/edit target, while the unified identity Inspector is the second image and supplies identity only.
- Added `locked_scene_qa` with bounded person/contact/cast-shadow edit regions, at least six normalized furniture/architecture/fixture landmarks, aspect-ratio tolerance, and edit-region-excluded pixel correspondence thresholds.
- Added hard failures for table/counter dimension, front-edge, support, door/window, fixture, spatial-anchor, camera, crop, vanishing-relation, background-detail, and global relighting drift.
- Added regression tests proving that probe candidates may independently edit the same authority plate but may never regenerate the room or derive from another candidate.

### Changed

- Replaced the public empty location and person-in-location frame with a clean 2.39:1 coastal survey room and an independently edited ordinary-light person insertion. The fixed workbench, both end supports, windows, door, chart cabinet, red anchor and harbor remain corresponding outside the bounded subject regions.
- Removed the superseded v1.6.4 scene, integration image, prompts, and publication derivatives from the current release tree.
- Kept the project schema at `1.6`; v1.0–v1.5 remain legacy and are not migrated automatically.

## [1.6.4] — 2026-08-28

### Added

- Added a mandatory ordinary-light `live_action_probe` between approved identity/location roots and every person-bearing narrative asset. Passing roots separately is no longer accepted as proof that a person can inhabit the world photographically.
- Added `image2-live-action-integration-probe-v1.6`, a concise 120–260-word prompt strategy with exactly two authority references, finite-exposure trade-offs, natural-dry skin response, and no style/equipment vocabulary before realism is proven.
- Added project-level probe records, profile binding, candidate-pool isolation, four-scale integration QA, and the terminal `backend_realism_blocked` state after two failed batches.
- Added a dedicated person–world integration review covering one exposure system, source-light direction, focus/occlusion, ground/contact geometry, edge behavior, material response, dynamic-range sacrifice, oily/waxy skin, synthetic rendering, and repeated texture.

### Changed

- Removed every superseded Arctic and Western public image, crop, prompt, derivative, and documentation reference from the release tree.
- Rebuilt the public proof as one auditable chain: a single-call 4×2 identity Inspector, one empty 2.39:1 overcast tide-station authority, and one ordinary-light person/world probe selected from three independent generations.
- Tightened Ready-shot and Higgsfield-export validation so no human narrative asset can bypass the approved integration probe through metadata, style treatment, special weather, or downstream approval.

## [1.6.2] — 2026-08-28

### Added

- Added a hard multi-person projection contract: every shared frame now preserves each approved Inspector body, records one camera projection, subject distances, expected/observed scale, crop-aware landmarks, horizon/vanishing lines, occlusion, and ground/elevation logic.
- Added two single-call shared-solve Western identity Inspectors, a native 2.39:1 observational frontier-street authority, and a native 2.39:1 two-person confrontation evidence frame.
- Added machine-readable projection QA proving that no person was separately scaled for composition.

### Changed

- Rebuilt the public hero, social preview, gallery, WebP derivatives, identity crop manifests, hashes, prompts, and release archives around the seven approved evidence assets.
- Tightened the live-action gate against effects-driven Western posters, game-cinematic rendering, artificial dust/haze, pseudo-HDR, inconsistent foreground/background anatomy, floating feet, and crop/blur used to hide proportion errors.
- Kept all rejected aircraft and stylized Western candidates outside the repository, manifests, documentation, and release artifacts.

## [1.6.1] — 2026-08-28

### Changed

- Replaced the first public showcase with a new shared-solve white Arctic survey-pilot identity Inspector and a physically grounded search-and-rescue hangar sequence.
- Upgraded both location examples to native 2.39:1 theatrical widescreen delivery without baked black bars.
- Tightened publication evidence for natural-dry skin, role-matched long-legged body balance, material separation, finite highlight clipping, real shadow loss, and reference-stack provenance.
- Made identity cropping gutter-aware: the runtime now detects and records an unambiguous central white row gutter before exact, non-resampled crops, preventing full-body anatomy from being cut when ImageGen shifts the row split.
- Rebuilt the deterministic hero, social preview, WebP derivatives, identity crops, evidence manifest, and release archive; the superseded showcase remains recoverable only through Git history.

## [1.6.0] — 2026-08-27

First public release.

### Added

- Evidence-based live-action quality profiles and four-scale visual QA.
- Role-conditioned physique briefs, measurable body targets, one shared-solve 4×2 identity Inspector with seven exact crops, and state-safe soft-tissue deltas.
- Finite scene-referred dynamic-range contracts for every photographed asset and Ready shot, including explicit exposure priority, highlight/shadow sacrifice, QA evidence, prompt compilation, and portable Higgsfield `dynamic-range.json` files.
- Backstage independent candidate pools with Foundation and sequence-level approvals.
- Location worlds, independent side-three-quarter views, primary spatial anchors, set-fixed coordinates, and cross-scene state locks.
- Adaptive cinematography treatments, physical weather and motivated special-light events.
- Reconstructable camera paths, temporal capture, exposure-time validation, and directional motion-blur plans.
- Deterministic ImageGen and video prompt compilation plus portable offline Higgsfield packages.
- Modular Python 3.10+ CLI, cross-platform installer, deterministic release builder, bilingual documentation, and GitHub Pages.
- Compact public evidence set: one shared-solve identity Inspector, one empty spatial scene, and one clean person-in-scene frame with exact prompts, hashes, deterministic crops, and dynamic-range QA.

### Compatibility

- Project schema remains `1.6`.
- Schema v1.0–v1.5 is detected as `LEGACY_SCHEMA` and is never migrated automatically.
- Random image pixels are not reproducible; workflow facts, prompts, reference order, approvals, hashes, validation, and exports are reproducible.
