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
- A captioned silent video is available; natural model TTS and final account publication remain coordinated separately.
- No native macOS app or RevenueCat integration is claimed.

The exact public source revision and hosted runtime readback are recorded in the release handoff after publication. Until that readback exists, local verification alone is not proof of a hosted service.
