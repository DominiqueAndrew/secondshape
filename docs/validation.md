# Validation receipt

Recorded 2026-09-08. This is a portable project, not a PyStorm submission: Quebec residence makes the author ineligible.

## Verified implementation

- Python engine, independent geometry validator and full export verifier.
- Five mandatory part IDs reconstructed from the selected dimensions; no omission by deleting both a part and its placement.
- All board/part/defect geometry rejects NaN, infinity, booleans and invalid dimensions. Selected dimensions obey the brief and positive-opening constraints.
- Early verifier bounds: at most ten boards and five parts/placements for generic geometry; the exported organizer requires exactly five placements.
- Malformed nested proof objects return a failed check rather than a server exception. A 600-placement duplicate flood returns one bounded error.
- Fixed-brief comparison remains usable when salvage alone has no solution.
- JSON/CSV downloads, independent proof recheck, reset completion and stale export protection.

## Commands and observed results

Run from the project root with its `.venv`:

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest -q` | 21 passed in 2.77 s |
| `.venv/bin/python -m compileall -q secondshape app.py` | Pass |
| `node --check public/static/app.js` | Pass |
| `.venv/bin/python -m scripts.benchmark` | 8 illustrative scenarios: 5 feasible, 2 no-fit, 1 incompatible-thickness input rejected |
| `.venv/bin/python -m scripts.verify_browser` | Actual server/UI flows passed at all six sizes; no page errors or horizontal overflow |
| `.venv/bin/python -m secondshape examples/demo.json --output output/live/cli-proof.json` followed by `.venv/bin/python -m secondshape output/live/cli-proof.json --verify` | CLI export succeeded; all twelve proof checks true; both exit 0 |

A later repeat of the engine/API suite passed all 21 tests in 40.17 s. The narration assembler passed compilation, help output, real MP3/video metadata probes, and a missing-input check that exited 2 without creating a final video. Its complete render remains unverified until the required nine narration files are supplied.

The eight-case benchmark saves inputs/results/fingerprints under `output/benchmark/`. The demo selected 560 × 240 mm; separate local measurements were approximately 0.35–0.51 s, with runtime depending on concurrent work. The interior-defect case took approximately 1.27 s in the recorded matrix. These are local timings, not a hosted latency guarantee.

## Responsive evidence

Device scale factor 1, 100% zoom, Chromium. **54 viewport screenshots** cover initial view, salvage layout, fixed brief, evidence, stale inputs, no-fit, fixed brief after no-fit, malformed-input error and cleared-defect result.

| Viewport | Screenshot prefix | Visual verdict |
|---|---|---|
| Mobile 390×844 | `output/playwright/mobile-390x844-` | Balanced two-line headline, dimension values stay together, controls within viewport; long layouts scroll vertically |
| Tablet 768×1024 | `output/playwright/tablet-768x1024-` | Two-column workbench, stacked sheet diagrams, controls accessible |
| Laptop 1366×768 | `output/playwright/laptop-1366x768-` | Clear layout and comparison after normal page scroll |
| Desktop 1440×900 | `output/playwright/desktop-1440x900-` | Clear hierarchy, readable board layout and proof action |
| Large 1920×1080 | `output/playwright/large-1920x1080-` | Increased diagram scale; no detached controls or clipping |
| Wide 2560×1440 | `output/playwright/wide-2560x1440-` | Intentional centered maximum content width; full workbench and evidence visible |

All captures were visually inspected in per-viewport contact sheets, with initial desktop footage inspected separately. `output/playwright/report.json` records each exact image path, document/client widths and clipped-control results. Native Safari, Firefox, assistive-technology and touch-device testing were not performed.

## Independent review

A separate reviewer reproduced the original non-finite certificate bug, then verified it was fixed with proper placements. It also challenged missing parts, selected dimensions, defect mutation and board provenance. The final follow-up identified malformed nested types and duplicate-array amplification; targeted regressions now pass. An independent parent API check also confirmed feasible, fully defective no-fit and invalid-minimum cases.

## Boundaries

- Geometry and conceptual panel dimensions are checked. Physical build quality, assembly, joinery, safe toolpaths, structural strength and contamination are not.
- Bounded search is not a global optimum or impossibility proof. Purchased stock counts are heuristic.
- Environmental evidence is synthetic fixture measurement only. No emissions or actual disposal reduction is established.
- A captioned motion video is available; complete natural model TTS and final account publication remain coordinated separately. The free voice provider explicitly reached its download quota after one verified narration segment.
- No native macOS app or RevenueCat integration is claimed.

## Public runtime verification

The public workbench is [secondshape.vercel.app](https://secondshape.vercel.app); source is [DominiqueAndrew/secondshape](https://github.com/DominiqueAndrew/secondshape). The first reviewed application revision is `a3ce08681f73e16b742f6f1db77395671e72bfcc`, deployed at immutable URL [secondshape-99k0pi33l-rhetorix.vercel.app](https://secondshape-99k0pi33l-rhetorix.vercel.app).

At 00:49 UTC on 2026-09-08, HTTPS readback verified the actual Python service and matching revision, computed the 560 × 240 mm salvage plan, rechecked all twelve exported-proof checks, returned a bounded failed verification for a malformed nested design, and returned no-fit for an inflexible brief. These are hosted API results, not local fixtures. `output/live/runtime.json` preserves the response receipt.

At 00:55 UTC, the public HTML, JavaScript and CSS returned HTTP 200 and their SHA-256 hashes matched the reviewed local files exactly. `output/live/assets.json` records this comparison. The six-size visual inspection was performed locally against those same assets; a separate six-size hosted-browser run was not performed.
