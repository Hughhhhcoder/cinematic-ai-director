# Adaptive commercial and TVC direction

Commercial work needs a business and editorial argument, not a fixed “premium cinematic” look. Initialize a project with `--project-kind commercial-tvc` (or `music-video`) and complete `manifests/commercial.json` before a shot becomes Ready.

## Brief before imagery

The plan records the objective, audience, placement, commissioned runtime, single proposition, reasons to believe, mandatories, brand codes, product truth, legal copy, and destination deliverables. It then proposes at least two materially different creative routes. A route that still works unchanged after swapping in a competitor is too generic and fails.

The selected route must explain how the idea changes casting, performance, production design, camera witness, edit structure, product or wardrobe proof, sound, and final brand memory. This reasoning is project-specific; the Skill does not recycle a luxury montage, slow-motion walk, teal–orange grade, or hero rim light.

## Fashion and product proof

A fashion TVC tracks each look as production evidence: garment authority, silhouette, fit, construction, material response, reveal, detail coverage, movement behavior, transition logic, and continuity. Repeating the same walk/turn while only changing the top is not six meaningful outfit stories.

Every shot has one necessary communication function and a removal test. Coverage should distinguish silhouette, fit, craft/material, movement, product use, emotional payoff, brand mnemonic, and end-card obligations instead of treating every shot as mood.

## Music, motion, edit, and speed

The rhythm map stores BPM, meter, downbeat, phrase boundaries, energy contour, shot duration in frames and beats, internal action peaks, cut point, transition sound, and narrative purpose. These are checked mathematically:

```text
duration_frames = duration_s × delivery_fps
beat_end - beat_start = duration_s × BPM / 60
playback_rate = delivery_fps / capture_fps
exposure_time_s = shutter_angle / (360 × capture_fps)
```

The complete shot-duration sum must equal the commissioned runtime. A fast track over uniformly low-energy slow motion is blocked unless a deliberate, readable half-time or counterpoint design includes internal events that answer the music. Slow motion is a local expressive tool, not a global quality filter.

Motion blur follows capture fps, shutter angle, camera path, subject velocity, playback mapping, direction, stable reference regions, and occlusion edges. Frame blending, double limbs, interpolation smear, texture crawling, and oil-highlight flicker are failures.

## Complete sound and delivery

The plan separates dialogue/VO, edited music, ambience, Foley, transition accents, mnemonic, and mix hierarchy. Audio is designed with picture rather than attached after the edit.

Delivery is destination-specific: exact duration and frame count, raster, aspect/crop, codec, color, safe areas, captions/legal, audio sample rate, loudness/true peak, and master versus proxy status. A 720p/32 kHz review file may be declared a proxy, but cannot silently pass as a conventional commercial master.

## Higgsfield boundary

Only picture-relevant, supported facts are folded into the dated Higgsfield adapter and official prompt order. The complete commercial reasoning, legal, mix, and delivery facts remain in sidecar JSON. The Skill does not claim that every business field is a model prompt token, log in, upload files, or consume credits.
