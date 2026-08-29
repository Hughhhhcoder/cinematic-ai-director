# v1.6.6 Adaptive Commercial and TVC Direction

Commercial work is not a film project with a logo added at the end. Before any shot package exists, turn the business problem into an authored viewing idea, then make picture, performance, wardrobe, edit, music, sound and delivery prove the same idea.

This reference applies to broadcast/digital TVCs, fashion films, brand spots, product films, launch films, retail/seasonal work, performance ads and commercial/MV hybrids. It does not impose one pacing template, one visual style or one funnel model.

## Commercial brief

Record the following in `manifests/commercial.json`:

- business objective and the viewer action the work should cause;
- audience, context of viewing, placement and stage in the customer journey;
- one single-minded proposition, product/brand truth and reason to believe;
- product, garment, service or brand assets that must be shown accurately;
- mandatory copy, logo, CTA, legal text, usage rights and prohibited claims;
- brand codes: color sources, typography responsibility, sonic assets, performance tone and permitted polish;
- measurement hypothesis and the variants the campaign actually needs;
- deliverable matrix by market/platform rather than one assumed master.

If these facts are unavailable, the Skill may create an exploratory concept package, but it must label claims and deliverables `unverified`; it cannot call the result a release-ready TVC.

## Original creative reasoning

Develop at least two materially different routes before selecting one. A route is not a genre label. It records:

- `audience_tension`: the human or market tension being addressed;
- `brand_truth`: the fact that makes the route belong to this brand;
- `concept`: the one-sentence viewing idea;
- `creative_device`: the repeatable visual/performance/edit/sound mechanism;
- `visual_rule`, `editorial_rule`, and `sound_rule`;
- `product_or_wardrobe_proof`: what the viewer must actually see;
- `payoff`: how the opening promise resolves into brand, product and CTA;
- risks, rejected alternatives and the selection rationale.

Reject a route when the same film could advertise a direct competitor after replacing only the end logo. Reject a route whose locations, camera moves or transformations are merely decorative. A selected route must explain why each variation exists and what it reveals.

The Skill should think from the brief, not select a fixed preset. Brand film, product proof, fashion transformation, UGC, performance, retail offer and narrative demonstration are useful diagnostic categories only.

## Fashion and outfit-switch work

Create one `wardrobe_look` record per look. Lock garment identity separately from the performer:

- garment/product reference ids and usage rights;
- silhouette, fit points, hem/waist/shoulder position and footwear;
- material, construction, color and hardware that cannot drift;
- intended body proportion and how styling supports it without lens distortion;
- reveal action, detail insert, fabric-motion behavior and viewer takeaway;
- transition mechanism and the exact source/end pose needed for the switch.

Every advertised look needs at least one silhouette proof and one feature/material proof unless the brief explicitly assigns a different function. A performer repeatedly walking in new tops is not automatically a fashion concept. Changing clothes must not change face, skeleton, height, shoulder/hip relationship or leg/body balance.

## Music, editorial rhythm and speed palette

Music is a production clock, not a track placed under finished slow footage. Record:

- licensed soundtrack/version, BPM when meaningful, meter, downbeat offset and structural sections;
- energy curve and meaningful onsets, phrases, breaks, drops, silences and sonic-logo events;
- `tempo_motion_relationship`: synchronous, half-time, counterpoint, dialogue-led or free;
- a project `speed_palette`: real time, overcranked slow motion, undercranked acceleration and variable speed, using only the modes justified by the route;
- per-shot in/out frames, duration in seconds/frames/beats, editorial function, visual energy, action phase, action peak, cut relation, transition, motion vector and audio cue.

Do not force every cut to a beat. Syncopation, holds and counterpoint are valid when authored. But fast music plus uniformly slow walking/turning is a hard failure unless the selected route explicitly uses counterpoint and still supplies visible internal rhythmic events.

For overcranked slow motion:

`playback_rate = delivery_fps / capture_fps`

For a qualified edit, verify `beat_end - beat_start = duration_s × BPM / 60` within 0.05 beat, `duration_frames = duration_s × delivery_fps`, and the sum of all production-shot durations equals the commissioned runtime exactly.

The shutter/exposure belongs to capture fps. A 60/120 fps capture played at 24 fps should normally show less per-frame motion blur than a 24 fps real-time capture at the same shutter angle. Slow movement plus long smeared hands, double contours or interpolation trails is not credible high-speed photography.

Each shot must contain an action with phases that editing can use: anticipation, initiation, contact/reveal, recovery/settle. Define the phase that carries the cut. Do not ask one vague slow action to occupy five musical beats without internal events.

## Sound direction

Plan the full sound field:

- BGM and licensing/version;
- dialogue/VO when required;
- production ambience and location perspective;
- garment, footwear, product and contact Foley;
- transitions, impacts and negative space;
- brand mnemonic/sonic logo;
- mix hierarchy and platform/market delivery targets.

Sound effects must reinforce real events rather than conceal weak motion. Use silence and contrast deliberately. Loudness, peak, codec and sample-rate requirements come from each deliverable; never assume one universal broadcast target.

## Shot-function and edit tests

Every production shot records one primary function such as hook, product/garment reveal, proof, comparison, emotional identification, transition, escalation, payoff, endboard or CTA. It may have secondary functions but cannot exist only because its environment looks expensive.

Before approval, run these tests:

- opening comprehension with and without sound;
- brand/product recall before the endboard;
- removal test: what information or feeling disappears if the shot is removed;
- rhythm test at frame level, not only cut level;
- outfit/product fidelity through motion and occlusion;
- endboard legibility, safe area and hold duration;
- 6/15/30-second and aspect-ratio variant logic where required;
- competitor-swap genericity test.

## Delivery matrix and master QC

Each deliverable specifies market/platform, purpose, duration, exact frame count, aspect, raster, fps/time base, codec/container, color space, audio sample rate/codec/channel layout, loudness/true-peak target, title/legal safe areas and file naming.

A review proxy may be 720p/AAC. A commercial master cannot silently inherit proxy settings. For a conventional 16:9 HD master, use at least 1920×1080 and 48 kHz production audio unless the named destination requires something else. Frame-accurate runtime must match the deliverable; an approximately 30-second file is not automatically a valid 30-second spot.

## Returned-take commercial QA

In addition to temporal QA, inspect:

- brief and selected-route fidelity;
- brand/product/garment identity and legibility;
- internal music/action/edit coherence;
- speed-regime and shutter/blur credibility;
- performance energy and pose repetition;
- transition motivation and motion-vector continuity;
- endboard/copy/CTA legibility;
- audio hierarchy and sync;
- exact technical delivery conformance.

Failed video remains a take record. Do not use it as the only bridge reference, and do not reinterpret a visible identity, garment, pacing or delivery failure as a new creative choice.

## Official Higgsfield evidence boundary

- Higgsfield's current Marketing Studio materials support choosing the ad form from the actual marketing job, using brand/product inputs and reviewing pacing rather than treating every ad as one template.
- Current consistency guidance supports character, location, prop and strongest-frame references with sequence-level reasoning.
- Camera/motion guidance supports authored motion as a pacing layer, but marketing claims do not prove that a complex move or transition will be stable.
- The official character-sheet library shows multiple use-case-specific layouts. This Skill uses one high-resolution 3×2 six-view single-solve board by default for new projects, and retains a separately versioned legacy 4×2 adapter for existing projects. If a live Higgsfield interface requires a different upload form, deterministically export the supported views or block; never regenerate identity panels independently.

Sources: [Marketing Studio](https://higgsfield.ai/blog/new-marketing-studio-higgsfield), [full ad campaign workflow](https://higgsfield.ai/blog/full-ad-campaign-inside-claude), [character/location consistency](https://higgsfield.ai/blog/consistent-characters-locations), [realistic human movement](https://higgsfield.ai/blog/realistic-ai-human-movement), and [AI short-film reference sheet](https://higgsfield.ai/blog/ai-short-film-youtube-guide).
