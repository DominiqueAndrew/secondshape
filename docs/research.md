# Research comparison

This is a bounded scan of public primary material. It is evidence for a hackathon thesis, not an exhaustive novelty search and not a substitute for interviews. The pain observations below come from government guidance/data, original research, project documentation, and one public first-person woodworking discussion.

## 1. SecondShape: inverse salvage design

**Supported pain.** The US EPA reports 600 million tons of construction and demolition debris in the US in 2018, with just under 145 million tons sent to landfill. It recommends salvaging and reusing wood and designing for adaptability, disassembly, and reuse. A public woodworking post from January 2025 describes a home shop with offcuts piling up “not knowing what I had,” and notes that dimensions determine whether a piece can be used.

- [EPA: Sustainable Management of Construction and Demolition Materials](https://www.epa.gov/smm/sustainable-management-construction-and-demolition-materials)
- [EPA: Best Practices for Reducing, Reusing, and Recycling C&D Materials](https://www.epa.gov/smm/best-practices-reducing-reusing-and-recycling-construction-and-demolition-materials)
- [Public woodworking discussion: Ideas for Off-Cut Management](https://www.reddit.com/r/woodworking/comments/1hvseji/ideas_for_off_cut_management/)

**Existing competitors.** OpenCutList accepts standard panels and arbitrary offcuts, grain direction, blade thickness, and deterministic cutting diagrams. CutList Optimizer also markets optimized layouts that reduce material waste. These tools primarily solve a fixed-parts-to-stock layout problem.

- [OpenCutList cutting diagrams](https://docs.opencutlist.org/features/parts/parts-list/cutting-diagrams/sheet-goods)
- [CutList Optimizer](https://cutlist.work/en/)

**Claimed differentiator and limits.** SecondShape proposes the inverse problem: preserve a small product’s function and assembly constraints, then change its dimensions minimally so a measured scrap inventory can produce every part. The desktop-organizer demo should accept stock dimensions, grain axes, defect zones, and kerf, then emit a geometry certificate listing each part, stock ID, orientation, clearances, and residuals. The claim is not “a new cut optimizer”; it is “inverse, certificate-producing design around the material already available.” It does not prove structural safety, material contamination, or universal woodworking suitability.

**Measurable test.** Run 5–10 inventories against a fixed virgin-stock organizer baseline. Report new-stock area/mass, usable scrap consumed, residual area, dimension deviation, and certificate pass/fail. A result counts only when all parts fit after kerf/defect/grain constraints and the assembly checks pass; report infeasible cases instead of forcing a design.

## 2. Screenshot/print ink avoidance

**Supported pain.** EPA print guidance recommends removing excess advertisements and banners, previewing, using grayscale and multiple pages per sheet, and tracking paper and ink reductions. Its cited case estimates 170,000 sheets saved through formatting changes. The UK National Archives advises avoiding solid opaque ink coverage because large colour areas use more ink and take longer to dry.

- [EPA: Reducing Paper and Printer Ink Usage](https://www.epa.gov/sites/production/files/documents/paper_usage.pdf)
- [National Archives: Planning a paper](https://www.nationalarchives.gov.uk/information-management/producing-official-publications/parliamentary-papers-guidance/parliamentary-papers-planning-checklist/)

**Existing competitors.** PrintFriendly removes ads/navigation and lets users preview/edit before printing or saving a PDF. Ecofont converts characters to ink-saving equivalents and reports up to 46.5% toner savings in its cited independent test.

- [PrintFriendly](https://www.printfriendly.com/)
- [Ecofont](https://www.ecofont.com/)

**Claimed differentiator and limits.** A defensible narrow version would optimize a supplied screenshot/PDF for estimated CMYK coverage while preserving OCR, contrast, and layout, then show a before/after certificate. A generic “clean web page before print” or “ink-saving font” claim is already covered by the competitors. Coverage is an estimate unless a printer’s measured consumption is available; it cannot promise a particular cartridge yield across devices.

**Measurable test.** Use a fixed document set. Compare baseline and optimized outputs on page count, estimated CMYK area, OCR character accuracy, and contrast/readability thresholds. Report any layout or semantic loss, including cases where optimization is rejected.

## 3. Donor-part compatibility for repair

**Supported pain.** iFixit describes rare or out-of-stock parts and recommends “parts-only” or donor devices. It warns that similar-looking models may not interchange and says exact part numbers reduce compatibility mistakes.

- [iFixit: Five Strategies for Finding Out-of-Stock Parts](https://www.ifixit.com/News/56864/finding-out-of-stock-parts)

**Existing competitor.** iFixit’s device compatibility checker identifies a device from its model number and returns green/yellow/red compatibility cues; iFixit explicitly warns about look-alike variants and generational differences.

- [iFixit: Device Compatibility Checker](https://www.ifixit.com/News/108469/no-more-parts-guesswork-with-ifixits-device-compatibility-checker)

**Claimed differentiator and limits.** A viable narrower claim is a donor-to-recipient evidence graph for one device family: part number, connector/geometry facts, revision, and firmware or pairing constraints, with unknown edges blocked. It is not a general replacement-part finder and a photo-only fit guess is not compatibility proof. Coverage and safety depend on service documentation; no claim should be made for unsupported families.

**Measurable test.** Build a small graph from official manuals and part lists, hold out known-compatible and known-incompatible pairs, and report precision/recall plus false-compatible rate. For safety-critical parts, the acceptance threshold is zero false-compatible recommendations; unresolved pairs must be marked unknown.

## 4. Compute result reuse

**Supported pain.** An original research paper on caching and reproducibility describes ad-hoc research software, long-running computationally expensive experiments, and time pressure caused by failures and reruns.

- [Schubotz et al., “Caching and Reproducibility: Making Data Science experiments faster and FAIRer”](https://arxiv.org/abs/2211.04049)

**Existing competitors.** DVC’s run cache reuses a previous pipeline stage when the exact dependencies, parameters, and command recur. `joblib.Memory` persists function outputs and avoids rerunning a function for the same arguments. A Snakemake issue documents an incorrect path parameter causing an already-complete rule to rerun.

- [DVC pipeline/run cache](https://dvc.org/content/docs/start/data-pipelines/data-pipelines.md)
- [joblib.Memory](https://joblib.readthedocs.io/en/latest/user_guide/memory.html)
- [Snakemake issue #1805](https://github.com/snakemake/snakemake/issues/1805)

**Claimed differentiator and limits.** Generic caching is established. A defensible niche would be provenance-safe, energy-aware reuse for small Python analyses, with explicit invalidation when code, dependencies, data, or seeds change. It cannot infer semantic equivalence when inputs are hidden or nondeterministic, and CPU/energy estimates are not the same as measured facility emissions.

**Measurable test.** Repeat a fixed Python pipeline with exact and changed inputs. Report cache-hit rate, wall time, CPU time, energy estimate, and output hash equality. A changed dependency/code/seed must invalidate the result; any stale reuse is a failed trial.

## Decision signal

SecondShape has the clearest original, judgeable gap: existing tools optimize a fixed design against stock, while the proposed demo changes a constrained design to consume known scraps and proves the result geometrically. Donor compatibility is a credible second choice if limited to one family. Print cleanup and generic compute caching have clear pain but much stronger incumbent products, so their differentiation would need a narrower proof than the broad workflow descriptions.
