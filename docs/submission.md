# Portable project description — SecondShape

**Eligibility status:** PyStorm ineligible (Quebec residence). Do not submit there. This copy is portable; it is not evidence of eligibility for another event. The current project is a Python web app, not a RevenueCat/native-app entry.

## Name and tagline

**SecondShape** — Let the offcut have a say.

## Inspiration

A fixed shopping list treats leftover material as a second-class option. A slightly flexible brief can reverse that relationship. We wanted to ask: what is the smallest change to this project that makes the material already in the workshop enough?

Public woodworking accounts describe offcuts accumulating without a useful inventory. Existing cutting tools already handle stock sizes, grain and kerf. Our opportunity was one step before the cut list: negotiate the dimensions of a constrained object around the material, then make the resulting claim independently checkable. The [research note](research.md) links the supporting sources and limits the novelty claim.

## What it does

SecondShape is an interactive workbench for a five-panel desktop organizer. Enter rectangular reclaimed panels, damaged areas, grain direction and kerf. Set the ideal width and depth, plus how much you are willing to change. A Python engine searches for a nearby design whose every part fits the available material.

The result shows a proportional concept, actual cutting rectangles, the precise dimension concession, a fixed-brief purchased-stock comparison and an exportable proof. If nothing passes, the application reports a failed salvage search while preserving the separate new-stock comparison. It never silently omits a required part.

## How we built it

The core is deterministic Python: validated input, bounded grid sampling, multiple packing orders, candidate placement search, material/grain matching and kerf/defect exclusion. A separate geometry validator checks the returned rectangles. An export verifier independently reconstructs the five required parts from the selected brief and binds them to the input inventory and fingerprint.

Flask exposes the solver and verifier. A dependency-free HTML/CSS/JavaScript frontend draws actual coordinates as SVG, marks changed input stale, and exports JSON/CSV. The application has no LLM runtime or external inference calls. AI tools assisted the implementation and review.

## What we measured

On the clearly labeled illustrative inventory, the fixed 600 × 240 mm design uses one new 1220 × 610 mm panel in our heuristic. At 560 × 240 mm, all five parts fit two existing panels. That is 0.7442 m² less purchased panel area in the model, alongside a 40 mm width concession and 4.3% less part area.

These are computed fixture results, not field-validated environmental savings. We do not infer carbon, landfill or lifetime impact. The purchased-panel baseline is a heuristic result, not a proven optimum.

## Challenges and what we learned

Getting an attractive layout was easier than earning the checkmark. Independent review exposed non-finite geometry that could slip through a validator and a risk of excessive search work. We fixed those, added adversarial tests, and made exports check the mandatory part list and input provenance. We also separated a failed salvage plan from a successful purchased-stock baseline in the interface.

## What's next

A workshop pilot with measured panels and actual builds; validated tool-specific cut sequences; user-defined parametric objects; and reusable offcut inventories. Structural design, contamination detection and physical manufacture remain outside the current project's scope.

## Built with

Python, Flask, JavaScript, SVG, HTML, CSS, pytest, Playwright, FFmpeg.

## Submission links

Use the links and exact code revision recorded in [the release receipt](validation.md). A captioned MP4 is provided separately. No registration, submission, award or provider integration should be inferred from this description.
