# Visual evidence withheld by the v1.6.6 quality gate

The current release does not publish a hero image or a visual showcase.

Three new high-resolution `3×2` white identity Inspectors were generated independently with built-in ImageGen. One failed native full-body pixel coverage; two showed repeated topographic/maze-like facial texture at 100% and 200% inspection. All three were rejected before deterministic cropping, location generation, person insertion, sequence work, or documentation publication.

This is the intended production behavior. A pleasant thumbnail cannot overrule insufficient native detail, synthetic skin topology, oil-film highlights, painterly smear, animation/CG appearance, or repeated cross-material texture. Negative prompt wording is not treated as a repair. Failed pixels are not cleaned, hidden by downsampling, or promoted as evidence.

The anonymized audit is available in [`showcase/evidence.json`](https://github.com/Hughhhhcoder/cinematic-ai-director/blob/main/showcase/evidence.json). It contains no private path, source-generation identifier, prompt containing personal information, or failed image.

Historical visuals remain in Git history for auditability, but they are not current release evidence. New public images will return only when the complete chain passes:

1. one single-call shared identity/body solve;
2. native resolution and subject pixel coverage;
3. geometry and proportion review;
4. thumbnail, fit, 100%, and 200% live-action surface review;
5. clean locked empty location with stable scale and topology;
6. person–world integration under one physical exposure and light field;
7. finite dynamic-range review;
8. dependency-safe approval and export validation.

`pixel_reproducible` remains `false`; the reproducible contract is that rejected stochastic output cannot enter the package.
