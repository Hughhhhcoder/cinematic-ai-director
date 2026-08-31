# Official three-skill methods, without platform operation

v1.7 learns from the official `higgsfield-generate`, `higgsfield-soul-id`, and
`higgsfield-product-photoshoot` skills while preserving the project's existing
delivery boundary. The Skill still produces local assets, manifests, prompts,
review boards, edit/audio plans, and a portable offline package. It does not
install a CLI, authenticate, upload, train, generate, poll, or spend credits.

## What was adopted

- Intent-first routing for image, video, audio, analysis, commercial, and
  product-photography tasks.
- One explicit responsibility for every reference in deterministic order.
- Short visible-fact model prompts, with QA and reconstruction evidence kept in
  sidecar JSON.
- Soul source-photo quantity, variety, quality, rights, and consent checks.
- Product truth locking and ten purpose-led Product Photoshoot modes.
- Separate audio work orders tied to picture timing, edit rhythm, and mix role.

## What was not copied

Soul training and provider reference IDs remain provider-only. Product
Photoshoot's backend prompt enhancement remains provider-only. The package
exports a short product intent and approved product truth; it never pretends to
know or expose the backend-enhanced GPT Image 2 prompt.

Model names are dated advisories. A human later using the package must verify
the current schema. The Skill does not treat a larger version number as a
universal upgrade because reference roles, duration, resolution, audio, and
editing behavior can differ.

## Identity separation

The approved single-solve `3×2` Inspector remains the film's first identity
authority. A real-person Soul-readiness record is different: it needs 5–20
unique, lawful, consented, user-provided photographs (8–12 ideal), with one
person, clear eyes, sharp focus, varied angles, lighting, expressions, and
distances. A generated Inspector is never counted as this real-photo set.

## Product truth and modes

Before any campaign derivative, lock product geometry, label text, logo
placement, color, material, scale, moving parts, required details, and allowed
state changes. Then choose one mode from the real placement and objective:
`product_shot`, `lifestyle_scene`, `closeup_product_with_person`,
`moodboard_pin`, `hero_banner`, `social_carousel`, `ad_creative_pack`,
`virtual_model_tryout`, `conceptual_product`, or `restyle`.

## Files added to the same package

- `manifests/higgsfield-methods.json` — local evidence and preparation facts.
- `method-routing.json` — task family, reference roles, prompt budget, and dated
  capability advice.
- `soul-id-prep.json` — lawful real-photo readiness, no training.
- `product-photoshoot-prep.json` — product truth plus short intent, no enhanced
  provider prompt.
- `audio-work-orders.json` — shot-linked sound and rhythm responsibilities.

All execution flags are fixed to false and validated.

See the full [method reference](https://github.com/Hughhhhcoder/cinematic-ai-director/blob/main/references/higgsfield-method-fusion.md).
