# Demo video and media provenance

The current video is a **69.92-second silent, English-captioned motion edit** showing the actual running application. It adds an animated opening, a sequential offcuts → flexible brief → second life concept diagram, timed result callouts and transitions around real browser scrolling/clicks. Natural model-generated narration is required for the final video and remains incomplete.

Current local artifact: `output/demo/secondshape-motion-silent.mp4` (H.264, 1440×810, 24 fps, yuv420p, faststart; no audio track). The reproducible recorder is `scripts/record_demo.py`; `scripts/style_demo.py` adds the motion design. `output/demo/receipt.json` contains precise scene timestamps; `motion.ass` preserves the editable motion styling and `captions.srt` the caption transcript. Full video decoding passed; the opening and result frames were visually inspected.

No Apple System Voices, eSpeak, Python/system synthesized voices, music, stock footage or generative visual media are included. The UI footage and written captions were created for this project. The computer-generated concept sketch represents the calculated proportions; it is not a photograph of a built object. No public video account upload or final narrated-video publication is claimed here.

## Reproduce the capture

With the Python app running:

```bash
.venv/bin/python -m scripts.record_demo
.venv/bin/python -m scripts.style_demo
```

The recorder exercises nine real scenes: introduction, fixed brief, salvage design, changed defect, no-fit refusal, fixed baseline after failure, proof export/recheck, evidence limitations and closing. Each result is asserted before the caption makes a claim. A download from the recorded session is saved as `output/demo/recorded-proof.json`.

## Natural narration handoff

Use `output/demo/narration-script.md` and `output/demo/narration-segments.json`. The latter supplies original scene start/end times and target durations. Read naturally; extend quiet holds if needed rather than rushing the voice. The base MP4 has captions already embedded and no audio to remove.

One natural introductory segment was generated through the normal OpenAI.fm interface using GPT-4o mini TTS, voice Cedar. It is preserved as `output/narration/01-cedar-intro.mp3`, duration 4.752 seconds, SHA-256 `9f5e55011aec4016fb7c1b6f27986df6612e4063b674abca8fa4905c9a1ede65`. It is not a complete voice track. `output/narration/provenance.json` records the exact script and provenance.

At 00:52 UTC the provider displayed **Download limit reached**, with an explicit limit of ten downloads per week. Downloads stopped. No alternate browser, hidden endpoint, recording workaround or system-voice substitute was used to circumvent this limit. An authorized provider route is being handled by the coordinator.

After producing all nine natural narration segments, put them in `output/narration/01.mp3` through `09.mp3` and use the narration assembly script:

```bash
.venv/bin/python -m scripts.mux_narration --help
```

The assembler preserves normal speech speed and extends a scene's final frame when needed. Its receipt binds source video, audio hashes, revised scene timing and output metadata. Confirm synchronization, decode the entire output and listen to the rendered result before publication. Until all segments are supplied and the result inspected, no final narrated video or audio-quality pass is claimed.
