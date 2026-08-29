# Public visual evidence status

The v1.6.6 public image set is intentionally withheld.

Three independent, single-call `3×2` identity Inspectors were generated with built-in ImageGen for the release audit. None passed the native-detail gate:

- one board did not provide enough native full-body pixel coverage;
- two boards showed repeated low-contrast topographic/maze texture on facial skin at 100% and 200% inspection.

Thumbnail appeal cannot override a native-scale failure. The failed boards, their crops, and all dependent location/person frames are therefore absent from this repository and from the release archive. No cleanup, downsampling, sharpening, or selective retouching was used to hide the defects.

This directory publishes only the machine-readable audit in [`evidence.json`](evidence.json). Historical v1.6.5 material remains recoverable through Git history, but is no longer presented as current quality evidence.

The reproducible result is the gate itself: a failed stochastic image cannot become an identity authority, approval asset, downstream reference, documentation image, or Higgsfield export.
