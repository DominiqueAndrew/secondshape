# Demo video and media provenance

The current video is a **70-second silent, English-captioned intermediate** showing the actual running application. It uses restrained caption fades and real browser scrolling/clicks. It is ready for natural narration to be mixed in; natural model-generated TTS is required by the user's latest direction and is being coordinated separately.

Local artifact: `output/demo/secondshape-demo.mp4` (H.264, 1440×810, 24 fps, yuv420p, faststart; no audio track). The reproducible recorder is `scripts/record_demo.py`. `output/demo/receipt.json` contains precise scene timestamps; `captions.ass` preserves the motion styling and `captions.srt` the readable caption transcript.

No Apple System Voices, eSpeak, Python/system synthesized voices, music, stock footage or generative visual media are included. The UI footage and written captions were created for this project. The computer-generated concept sketch represents the calculated proportions; it is not a photograph of a built object. No public video account upload or final narrated-video publication is claimed here.

## Reproduce the capture

With the Python app running:

```bash
.venv/bin/python -m scripts.record_demo
```

The recorder exercises nine real scenes: introduction, fixed brief, salvage design, changed defect, no-fit refusal, fixed baseline after failure, proof export/recheck, evidence limitations and closing. Each result is asserted before the caption makes a claim. A download from the recorded session is saved as `output/demo/recorded-proof.json`.

## Natural narration handoff

Use `output/demo/narration-script.md` and `output/demo/narration-segments.json`. The latter supplies original scene start/end times and target durations. Read naturally; extend quiet holds if needed rather than rushing the voice. The base MP4 has captions already embedded and no audio to remove.

After producing an approved, licensed natural narration track, mix it without changing the recorded UI:

```bash
ffmpeg -i output/demo/secondshape-demo.mp4 -i approved-narration.wav -c:v copy -c:a aac -b:a 192k -movflags +faststart output/demo/secondshape-narrated.mp4
```

Confirm audio/video duration, decode the entire output and listen to the rendered result before publication. The command alone is not publication or synchronization proof.
