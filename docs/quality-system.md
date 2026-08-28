# Live-action quality evidence

## A positive photographic floor

“No obvious artifact” is insufficient. An approved image must show why a camera could have recorded it:

- reachable witness position and a plausible reason for the camera to exist;
- highlight shape, size, direction, and intensity that match a real source;
- continuous skin hue/value across forehead, eyes, nose, cheeks, jaw, ears, and hands;
- separate roughness and edge behavior for skin, hair, fabric, wall paint, wood, glass, and metal;
- natural middle tones, highlight transition, shadow floor, focus plane, and distance falloff;
- production design caused by living, work, construction, period, and story;
- performance caused by a task rather than a poster pose.

## Skin-state contract

Allowed states are `natural_dry`, `normal`, `perspiration`, `rain_wet`, `submerged`, and `cosmetic_sheen`. Non-default states require an explicit cause, bounded regions, and shot duration.

Uniform facial oil, repeated white glints, wax/plastic skin, local skin-tone discontinuity, unmotivated colored edge light, or a glint that crawls between frames is a hard failure.

## Four inspection scales

| Scale | Primary decision |
|---|---|
| Thumbnail | Does it immediately read as a real photograph rather than animation, game art, or promotion? |
| Fit | Are the photographic event, task, light, space, posture, and story polish plausible? |
| 100% | Do face, eyes, hair, hands, clothing edges, contacts, highlights, shadows, and materials survive? |
| 200% | Is there patch smear, swirl/scale/cellular repetition, cross-material copying, sharpening halo, or pixel pollution? |

Positive evidence is stored for every QA check. A face or authority asset failing at any scale cannot proceed.

## Ordinary-light person/world probe

A clean Inspector and a clean location do not prove that ImageGen will integrate them as one photograph. Before Looks, special atmosphere, multi-person frames, Photoboards, keyframes, Ready shots, or export, the project must pass one `live_action_probe`: one approved adult, one approved place, one simple task/contact, one reachable medium camera, ordinary broad source light, and finite exposure. It deliberately contains no cinematic styling, equipment brand, film reference, grain, halation, colored rim, or special weather.

The approved empty location is the probe's first reference and immutable edit target; the unified Inspector is second and supplies identity only. Every candidate independently edits that same plate and may change only the bounded person/contact/cast-shadow regions. The probe passes only when person and world share projection, light, focus, occlusion, contact, color contamination, edge behavior, and tone mapping at all four scales—and when table/counter geometry, door/window construction, fixtures, spatial anchor, camera, crop and background detail remain corresponding. At least six landmarks and edit-region-excluded pixel statistics are required. Oily/waxy/plastic skin, a game-rendered person, cut-out edges, separate subject HDR/sharpening, copied artifact texture, or location drift is a hard failure. After two independent failed batches the pair becomes `backend_realism_blocked`; the workflow requests lawful real-photo references or remains package-only rather than hiding the failure with style.

## Finite dynamic range

Real capture does not reveal every highlight and shadow with equal local contrast. Every photographic asset stores its own `dynamic_range_plan`: finite working latitude, estimated scene contrast, stops above and below middle gray, exposure priority, middle-tone anchor, highlight behavior, shadow floor, allowed clipping, allowed shadow loss, and a narrative reason.

When estimated scene contrast exceeds working latitude, the plan must sacrifice highlight or shadow information. `local_tone_mapping:false` and `multi_exposure_hdr:false` are hard requirements. QA records the visible transition or loss and fails global HDR lift, clarity halos, flattened source hierarchy, or an image in which every dark recess and bright source is independently “recovered.” Neutral identity boards use a controlled low-contrast plan; a night exterior may deliberately protect skin/practicals and let distant lamps clip or unlit recesses lose texture.

## Candidate isolation

Critical assets receive three independent candidates; derivatives receive two. Candidates cannot edit or derive from one another. The integration probe is the sole controlled exception to generate-only candidates: each candidate may edit the same approved empty-location authority, never another candidate. If the entire first batch fails, one highest-priority prompt variable may change and two independent retries are allowed. A second complete failure becomes `model_blocked` and requests a lawful real reference.

Failure is therefore expected and contained. Stability means a failed candidate never reaches users or production—not that stochastic generation becomes deterministic.
