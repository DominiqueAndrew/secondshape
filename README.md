# SecondShape

**Let the offcut have a say.** A Python workbench that changes a design brief to fit the reclaimed material you already have.

[Try the live workbench](https://secondshape.vercel.app) · [Public source](https://github.com/DominiqueAndrew/secondshape)

Most cutting workflows start with a fixed list of parts. SecondShape starts one step earlier: **how little could the design change before buying another panel becomes unnecessary?** Its first workflow is a five-panel, nonstructural desktop organizer.

The app includes editable panels and rectangular defects, grain and kerf constraints, a proportional organizer concept, a fixed-brief comparison, clear failed searches, downloadable coordinates and a reproducible proof file. The Python solver executes on every request; the demo is not a precomputed fixture player.

## Run

Python 3.11+ is required. From the repository directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open **http://127.0.0.1:8767**. No API key, account, database or paid service is required. The hosted app sends inventory to its Python server only to compute a result; it has no application database or analytics. Hosting providers may retain their normal request logs.

For a reproducible command-line result:

```bash
.venv/bin/python -m secondshape examples/demo.json --output proof.json
.venv/bin/python -m secondshape proof.json --verify
```

The second command reconstructs the five mandatory panels from the selected brief, checks their provenance against the input inventory, verifies the input fingerprint, and checks the geometry without running the search again. Exit status is nonzero on failed verification. The fingerprint is a reproducibility identifier, **not a signature or proof of physical measurements**.

## What the example actually demonstrates

The supplied inventory is **illustrative, not field measured**: a 590 × 510 mm reclaimed plywood panel with a damaged edge, and a 760 × 260 mm old shelf. Both are 18 mm thick, with grain along their width. Saw kerf is 3 mm.

| Calculated result | Fixed brief | Second shape |
|---|---:|---:|
| Organizer width × depth | 600 × 240 mm | 560 × 240 mm |
| Required parts | 5 | 5 |
| New 1220 × 610 mm panels used by this heuristic | 1 | 0 |
| Purchased panel area | 0.7442 m² | 0 m² |
| Part area | 0.44928 m² | 0.43008 m² |

The concession is **40 mm of width**, and the resulting parts contain **4.3% less area**. The comparison is explicitly between different design dimensions. It is not a controlled claim of identical output. The selected inventory has 0.4985 m² total area; its geometric residual includes unused material, damaged areas and cut allowances, and is not synonymous with reusable offcut or landfill waste.

**No CO₂, landfill, mass, embodied-energy or lifetime savings are inferred.** A shop trial with measured inventory, a documented purchasing counterfactual and actual builds would be needed to establish environmental benefit. A heuristic finding is not a proof of globally minimum purchases or mathematical impossibility.

## How the Python engine works

1. Validate bounded finite dimensions, matching material/thickness, unique board IDs, rectangular defects and a physically admissible five-panel brief.
2. Sample a bounded descending width/depth grid within the user's allowed range.
3. Try deterministic part orderings and candidate placements near board, part and defect edges, under explicit search budgets.
4. Reject rectangles outside a board, across a defect safety margin, too close to another part, or in a forbidden grain orientation.
5. Rank found feasible designs by combined normalized width/depth concession, then retained footprint area.
6. Independently validate every returned part. Compare with the original dimensions using the same heuristic and up to four standardized new panels.

There is no LLM in the runtime. AI tools assisted development, research and testing. The result comes from deterministic Python geometry and a separate validator.

## Geometry and scope

- Top and base are `width × depth`; two sides and one divider are `(height − 2 × thickness) × depth`.
- The conceptual organizer has positive openings: width exceeds three board thicknesses, and height exceeds two.
- Rectangles use millimetres. A board's `width` is its x axis; `height` is its y axis. All boards in a run share material and thickness.
- Grain `x` prevents rotation. Grain `none` permits it.
- Kerf is a minimum separating gap between part rectangles, with a half-kerf safety expansion around defect rectangles. This is a geometric allowance, not a sawpath simulation.
- Raw panels are assumed rectangular, flat, square, measured correctly and otherwise usable. No edge-trimming allowance is assumed.
- **Joinery, fasteners, tool access, guillotine cut sequence, strength, contamination, hidden nails and safe manufacture are not assessed.** The proportional 3D sketch is a concept preview, not a fabrication or assembly guarantee.
- `no_fit` means the bounded search found no checked solution; it does not prove that no possible layout exists.

## Validation

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m scripts.benchmark
node --check public/static/app.js
```

With the server running and a Playwright Chromium installation available:

```bash
.venv/bin/python -m playwright install chromium
.venv/bin/python -m scripts.verify_browser
```

The browser script exercises the actual server and UI, downloads and reads a proof, checks stale-export protection, compares fixed and salvage plans, refuses an inflexible brief, rejects malformed inventory, changes a defect, and adds/removes an offcut. It records screenshots and overflow measurements at **390×844, 768×1024, 1366×768, 1440×900, 1920×1080 and 2560×1440**, device scale factor 1. Generated evidence goes in `output/` and is ignored by Git. See [the validation receipt](docs/validation.md) for the completed run.

## API

| Route | Purpose |
|---|---|
| `GET /api/health` | Actual Python service/version/revision |
| `GET /api/example` | Labeled illustrative input |
| `POST /api/solve` | Compute a new plan from submitted input |
| `POST /api/verify` | Recheck a full exported salvage proof against its brief and inventory |

Requests are limited to 100 KB. Invalid input returns HTTP 400, oversized input HTTP 413. A valid but unsolved design returns HTTP 200 with `status: "no_fit"` and a failed salvage certificate. No purchases, messages or physical operations are performed.

## Deployment

The included Flask entrypoint and `public/` assets deploy on Vercel's Python runtime:

```bash
vercel --prod
```

The project follows [Vercel's Flask deployment documentation](https://vercel.com/docs/frameworks/backend/flask). No provider is required for local use.

## Project notes

- [Idea comparison and primary-source evidence](docs/research.md)
- [Portable submission copy](docs/submission.md)
- [Validation and release receipt](docs/validation.md)
- [Demo video and media provenance](docs/demo.md)

This project was started on 2026-09-08 after the published PyStorm opening time. **The author is ineligible for PyStorm because of its Quebec exclusion; no PyStorm registration or submission is claimed.** Any future event requires a fresh eligibility and rules check. This web/Python project does not claim a native mobile/macOS or RevenueCat integration.

MIT licensed. No source from the older projects in the parent worktree was reused or published as part of this repository.
