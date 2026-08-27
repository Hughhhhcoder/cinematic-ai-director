# Cinematography, atmosphere, camera, and time

## Original treatment

Named films, directors, camera brands, and “cinematic” adjectives are translated internally into observable behavior: narrative distance, observer identity, composition order, working distance and perspective, focus, motivated sources, color sources, support/inertia, temporal rhythm, environmental medium, polish ceiling, and a return rule.

Naturalistic dialogue, nocturnal crime, grounded horror, period reconstruction, epic environment, kinetic action, intimate romance, precision commercial, performance/MV, and archive/surveillance are starting questions—not presets or LUTs.

## Format gate

The format plan stores capture, working, and delivery aspect; crop and safe area; anamorphic squeeze/desqueeze; sequence transitions; and `baked_black_bars:false`. The default is 16:9. Other formats need narrative benefit and approval before Look Tests.

## Physical atmosphere and light

Each environment records source, coverage, strength, visibility, scale, direction/wind, accumulation, body/material response, attenuation/scattering, focus/exposure, sound, and temporal bounds. Fog reduces contrast with distance. Rain requires readable background or source light and develops wetness over exposure time. Fire, lightning, police light, welding, and projection propagate through walls, ground, glass, metal, eyes, skin, exposure, and shadows.

## Finite scene-referred latitude

The capture profile and every asset/shot plan estimate scene contrast against a finite working range. Exposure chooses a priority—skin, highlights, shadows, skin plus practicals, or balanced middle tones—and declares a middle-gray anchor. The plan then names what may clip, roll into the source core, or fall below the texture floor. It never promises simultaneous maximum detail at both ends.

This is a simulated physical behavior, not a claim that an ImageGen output has camera EXIF or measured sensor stops. Camera-brand or film-stock names remain optional context; the observable highlight transition, shadow floor, color separation, and exposure sacrifice are authoritative. See the [ARRI dynamic-range white paper](https://www.arri.com/resource/blob/295460/e10ff8a5b3abf26c33f8754379b57442/2022-09-28-arri-dynamic-range-whitepaper-data.pdf), [Sony VENICE 2 latitude description](https://pro.sony/en_GB/products/digital-cinema-cameras/venice2), and [Kodak VISION3 500T](https://www.kodak.com/content/pdfs/motion/KODAK-VISION3-500T-5219-7219-brochure.pdf).

## Reconstructable camera path

The path stores primitive, support, start/end marks and coordinates, translation/rotation, duration, speed curve, clearance, horizon/axis policy, expected parallax, framing, occlusion, focus change, and settle. Pan/tilt/roll rotate; dolly/truck/pedestal/orbit translate. Zoom cannot stand in for a dolly.

## Temporal capture and blur

`exposure_time_s = shutter_angle / (360 × capture_fps)`.

Slow motion changes capture fps and playback mapping; a text adjective is insufficient. Blur records camera/subject/atmosphere source, amount, image direction, affected and stable areas, occlusion edges, and narrative purpose. Locked-camera backgrounds remain stable; pan backgrounds blur with the sweep; dolly and orbit preserve parallax. Frame blending, double contours, ghost limbs, jelly warping, and texture crawl are prohibited.
