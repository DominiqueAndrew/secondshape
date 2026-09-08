# Learning candidate: capture reset completion, not a reused success label

Date: 2026-09-08. Status: local proposal and project regression only; not promoted to global instructions or memory.

During real browser video capture, a reset began an asynchronous example fetch while the previous result still displayed its success label. The recorder observed that old label and edited fields before reset completed. The next result used the restored example instead of the intended no-fit brief.

The project fix enters an explicit loading state synchronously, blocks solve/export during example loading, and keeps input revisions on computations. The browser verification now resets from a previously feasible result and asserts the restored width delta. The corrected recording also waits on completed UI states before each claim.

Proposed reusable pattern: in interactive recording or QA scripts, a reset completion assertion must distinguish the new run from the previous successful state. Prefer a run identifier or a synchronous loading transition followed by the expected final value. A generic reusable helper is unnecessary until the same pattern recurs in another application.

Minor patch-format friction was resolved locally by using update hunks with explicit context; no persistent shell or agent rule was changed.
