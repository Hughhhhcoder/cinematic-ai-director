# Compact v1.6 evidence gallery

This release intentionally shows only three approved artifacts: one complete identity authority, one empty location, and one live-action narrative frame that combines them. All people are fictional adults and the location is original. The gallery excludes the user's calibration photograph, earlier benchmarks, failed candidates, and third-party project media.

The WebP files below are publication derivatives only. The retained PNGs remain the visual evidence; exact prompts, source-generation IDs, SHA-256 values, deterministic crop records, QA observations, and finite-dynamic-range reviews live in [`showcase/evidence.json`](https://github.com/Hughhhhcoder/cinematic-ai-director/blob/main/showcase/evidence.json).

<div class="cad-grid">
  <div class="cad-card"><img src="assets/showcase/identity-black-woman-v001.webp" alt="One white 4 by 2 identity inspection board showing seven consistent views of the same fictional Black woman and one blank cell"><strong>01 · One shared identity solve</strong><br>One ImageGen call creates the full Inspector. The whole board passes first; seven upload/check views are then cropped exactly without resampling or redraw.</div>
  <div class="cad-card"><img src="assets/showcase/scene-observational-kitchen-v001.webp" alt="An empty modest apartment kitchen photographed from a reachable side-three-quarter position with a cobalt kettle as spatial anchor"><strong>02 · Empty spatial authority</strong><br>Reachable camera, adjacent planes, ordinary construction, distinct clean materials, and a fixed cobalt-kettle anchor.</div>
  <div class="cad-card"><img src="assets/showcase/narrative-black-woman-kitchen-v001.webp" alt="The same fictional woman naturally listening at the approved kitchen table under soft window light"><strong>03 · Person in the approved world</strong><br>The Inspector remains first identity authority; the kitchen remains world authority. Matte source-led skin, task-led performance, coherent scale, and the same spatial anchor survive the narrative frame.</div>
</div>

## What was checked

Each retained original was inspected at thumbnail, fit, 100%, and 200% scales for live-action photographic evidence, geometry where applicable, source-light causality, oily or plastic skin, painterly smear, repeated AI texture, cross-material contamination, sharpening halos, and animation/CG/PBR appearance.

Dynamic range is also evaluated as a finite capture decision. The release records a working latitude, estimated scene contrast, exposure priority, middle-tone anchor, highlight transition, shadow floor, and allowed loss. This does **not** claim a real camera, EXIF, measured sensor latitude, or pixel reproducibility. It demonstrates the v1.6 rule that every photographed asset must decide what exposure protects; local tone mapping or exposure fusion may not make every tonal region equally explicit.

## Identity authority

The Inspector is the first and only identity input. Its fixed cells are:

`full_front · full_left_profile · full_right_profile · full_back`  
`portrait_front · portrait_left_profile · portrait_right_profile · blank`

`showcase/originals/identity-crops/identity-black-woman-v001/crop-map.json` records the exact cell coordinates and output hashes. Those seven PNGs are convenience files, never independent identity generations and never a replacement for the unified board.

## Honest evidence boundary

This compact gallery is not a multi-run benchmark and makes no statistical pass-rate claim. Built-in ImageGen has no stable public seed, so `pixel_reproducible` is `false`. What the repository reproduces is the workflow, prompt, reference order, exact retained files, hashes, crop operation, QA contract, approval gates, and export behavior.
