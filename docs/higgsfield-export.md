# Portable Higgsfield export

## What the package contains

```text
exports/higgsfield/
├── manifest.json
├── official-conformance.json
├── reference-map.json
├── method-routing.json
├── soul-id-prep.json
├── product-photoshoot-prep.json
├── audio-work-orders.json
├── upload-order.csv
├── shot-list.csv
├── references/
├── sequences/<sequence-id>/
│   ├── state-lock.json
│   ├── quality-profile.json
│   ├── sequence-anchor.json
│   ├── spatial-map.json
│   ├── format-plan.json
│   ├── camera-path.json
│   ├── environment-state.json
│   ├── dynamic-range.json
│   ├── temporal-lock.json
│   ├── settings.json
│   └── prompt.txt
├── shots/<scene>/<shot>/
├── production/
├── checksums.sha256
└── verify_package.py
```

`@handles` place the unified high-resolution 3×2 identity Inspector first, then the current character state; six exact crops are secondary only when the current UI needs separate views. Existing v1.6 projects may retain the versioned 4×2 adapter. Pose/contact evidence, location shot and three-quarter views, spatial anchor, root/current props, approved Look, start/end frames, and supplementary bridges keep distinct responsibilities.

## Export gate

Foundation and every target sequence must be approved. At least one shot must be Ready, generated, or selected. Inspector/physique/proportion, states, quality/capture profile, treatment, format, sequence anchor, space, path, time, blur, frames, and QA must be complete.

v1.6 strict export is locked to `cinema-studio-4-seedance-2.5-official-2026-08-27`. The package validator enforces the official prompt order, deliberate reference responsibilities, numbered Shot/`Hard cut` boundaries, at most 50 references, at most 30 seconds, 9:16–21:9, and the published native 1080p/audio contract. A current-interface mismatch blocks export until the adapter is updated.

`dynamic-range.json` preserves each shot's finite latitude, scene-contrast estimate, exposure priority, middle-gray anchor, highlight rolloff/clipping, shadow floor/loss, and prohibition on local tone mapping or multi-exposure HDR. The model-visible version is placed inside the official `LIGHTING` section; the exporter never invents a separate prompt heading that Higgsfield did not document.

The v1.7 methods layer is independently fixed to `higgsfield-official-skills-0.12.0-offline-methods-2026-08-31`. It contributes intent routing, reference responsibilities, lawful Soul photo readiness, product truth/mode briefs, prompt economy, and audio work orders. It does not call the platform, and all model names remain advisory until a human checks the current schema. The product file contains only product truth plus a short intent; it never fabricates the provider backend's enhanced prompt.

```bash
python3 scripts/film_project.py validate <project> --json
python3 scripts/film_project.py export-higgsfield <project>
python3 <project>/exports/higgsfield/verify_package.py
```

## Manual execution

1. Verify the root package and sequence.
2. Confirm the sequence state, format, path, atmosphere, and temporal facts.
3. Bind approved files in ranked reference-map order, with each identity Inspector before its current state and optional crops.
4. Confirm camera/subject marks, body and contact facts, quality profile, anchor projection, and the declared highlight/shadow exposure sacrifice.
5. Paste the compiled prompt and map only supported settings into the current UI.
6. Generate one calibration take, download it, and return it for start/25%/50%/75%/end plus event-frame audit.

The exporter never logs in, uploads, calls a platform, or consumes credits. Strict conformance guarantees the versioned package contract, not stochastic third-party pixels. Official sources: [Seedance 2.5](https://higgsfield.ai/blog/seedance-2-5-prompting-guide), [short-film reference workflow](https://higgsfield.ai/blog/ai-short-film-youtube-guide), [realistic movement workflow](https://higgsfield.ai/blog/realistic-ai-human-movement), and [Cinema Studio 4](https://higgsfield.ai/blog/cinema-studio-4-0).
