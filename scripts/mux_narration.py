#!/usr/bin/env python3
"""Mux real Coral narration into the nine-scene SecondShape demo.

The script is intentionally fail-closed.  It reads the scene timing from the
recording receipt, measures each supplied MP3 with ffprobe, and refuses to
start ffmpeg until all nine inputs are present and valid.  Video is retimed by
holding a scene's final frame when narration needs more time; narration is
never sped up.  The generated receipt records all input/output hashes and
frame-rounded timings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


FPS = 24
SCENE_COUNT = 9
AUDIO_TAIL_SECONDS = 0.3
Loudness_FILTER = "loudnorm=I=-16:TP=-1.5:LRA=11:linear=true"


class MuxError(RuntimeError):
    """Raised for missing inputs, invalid metadata, or failed muxing."""


def _finite_number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MuxError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise MuxError(f"{name} must be finite" + (" and positive" if positive else ""))
    return result


def _run(command: Sequence[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            check=True,
            text=True,
            capture_output=capture,
        )
    except FileNotFoundError as exc:
        raise MuxError(f"required executable is unavailable: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise MuxError(f"command failed ({command[0]}): {detail[-1200:]}") from exc


def _probe(path: Path) -> Dict[str, Any]:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,width,height,r_frame_rate,avg_frame_rate,nb_frames",
            "-of",
            "json",
            str(path),
        ]
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MuxError(f"ffprobe returned invalid JSON for {path}") from exc
    format_data = data.get("format", {})
    raw_duration = format_data.get("duration")
    try:
        # ffprobe emits format.duration as a JSON string on some builds.
        duration = float(raw_duration)
    except (TypeError, ValueError):
        raise MuxError(f"{path} has no numeric duration") from None
    duration = _finite_number(duration, f"{path} duration", positive=True)
    streams = data.get("streams", [])
    if not isinstance(streams, list):
        raise MuxError(f"ffprobe returned no stream list for {path}")
    return {"duration_seconds": duration, "streams": streams}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_receipt(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise MuxError(f"recording receipt is missing: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise MuxError(f"cannot read recording receipt: {path}") from exc
    if not isinstance(receipt, Mapping):
        raise MuxError("recording receipt must be a JSON object")
    raw_scenes = receipt.get("scenes")
    if not isinstance(raw_scenes, list) or len(raw_scenes) != SCENE_COUNT:
        raise MuxError(f"recording receipt must contain exactly {SCENE_COUNT} scenes")
    scenes: List[Dict[str, Any]] = []
    previous_end = 0.0
    for index, raw_scene in enumerate(raw_scenes, start=1):
        if not isinstance(raw_scene, Mapping):
            raise MuxError(f"receipt scene {index} must be an object")
        start = _finite_number(raw_scene.get("start"), f"scene {index} start")
        end = _finite_number(raw_scene.get("end"), f"scene {index} end")
        if start < 0 or end <= start:
            raise MuxError(f"scene {index} has invalid start/end")
        if index > 1 and start < previous_end - 0.1:
            raise MuxError(f"scene {index} starts before the preceding scene ends")
        previous_end = end
        scenes.append(
            {
                "index": index,
                "start_seconds": start,
                "end_seconds": end,
                "title": str(raw_scene.get("title", "")),
                "text": str(raw_scene.get("text", "")),
            }
        )
    receipt_duration = _finite_number(receipt.get("duration_seconds"), "receipt duration", positive=True)
    if previous_end > receipt_duration + 0.2:
        raise MuxError("receipt scenes extend beyond receipt duration")
    return {"duration_seconds": receipt_duration, "scenes": scenes}


def _font_file() -> Path:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise MuxError("no usable system font found for the required narration credit")


def _frame_round(seconds: float) -> Dict[str, float | int]:
    frames = max(1, int(math.ceil(seconds * FPS - 1e-9)))
    return {"frames": frames, "seconds": frames / FPS}


def _escape_filter_text(value: str) -> str:
    # ffmpeg filter option separators must be escaped even though arguments
    # are passed without a shell.  Apostrophes are avoided in the credit.
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _build_filter_graph(
    scenes: Sequence[Mapping[str, Any]],
    video_limit: float,
    audio_meta: Sequence[Mapping[str, Any]],
    fontfile: Path,
    credit: str,
) -> tuple[str, List[float]]:
    video_parts: List[str] = []
    audio_parts: List[str] = []
    target_durations: List[float] = []
    split_outputs = "".join(f"[vin{index}]" for index in range(len(scenes)))
    video_parts.append(f"[0:v]split={len(scenes)}{split_outputs}")
    for index, scene in enumerate(scenes):
        source_start = min(float(scene["start_seconds"]), video_limit)
        source_end = min(float(scene["end_seconds"]), video_limit)
        source_duration = max(0.0, source_end - source_start)
        if source_duration <= 0:
            raise MuxError(f"scene {index + 1} has no video after clipping to {video_limit:.6f}s")
        narration_duration = float(audio_meta[index]["duration_seconds"])
        requested_duration = max(source_duration, narration_duration + AUDIO_TAIL_SECONDS)
        rounded = _frame_round(requested_duration)
        target = float(rounded["seconds"])
        target_durations.append(target)
        hold = max(0.0, target - source_duration)
        video_filter = (
            f"[vin{index}]trim=start={source_start:.9f}:end={source_end:.9f},"
            f"setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={hold:.9f},"
            f"fps={FPS},trim=duration={target:.9f},setpts=PTS-STARTPTS,"
            f"drawtext=fontfile='{_escape_filter_text(str(fontfile))}':"
            f"text='{_escape_filter_text(credit)}':"
            "fontcolor=white@0.62:fontsize=12:x=16:y=h-14:"
            "shadowcolor=black@0.4:shadowx=1:shadowy=1"
            f"[v{index}]"
        )
        video_parts.append(video_filter)
        audio_filter = (
            f"[{index + 1}:a]aresample=48000,"
            f"{Loudness_FILTER},aformat=sample_rates=48000:channel_layouts=stereo,"
            f"apad,atrim=duration={target:.9f},"
            f"asetpts=PTS-STARTPTS[a{index}]"
        )
        audio_parts.append(audio_filter)
    # concat expects each segment's video and audio pads interleaved.
    concat_inputs = "".join(f"[v{index}][a{index}]" for index in range(len(scenes)))
    concat = f"{concat_inputs}concat=n={len(scenes)}:v=1:a=1:unsafe=0[vout][aout]"
    return ";".join(video_parts + audio_parts + [concat]), target_durations


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--video", type=Path, default=root / "output/demo/secondshape-motion-silent.mp4", help="silent base video")
    parser.add_argument("--receipt", type=Path, default=root / "output/demo/receipt.json", help="recording scene receipt")
    parser.add_argument("--audio-dir", type=Path, default=root / "output/narration", help="directory containing 01.mp3 through 09.mp3")
    parser.add_argument("--output", type=Path, default=root / "output/demo/secondshape-final.mp4", help="narrated output MP4")
    parser.add_argument("--final-receipt", type=Path, default=root / "output/demo/final-receipt.json", help="output timing/hash receipt")
    parser.add_argument("--provider", default="unspecified", help="narration provider recorded in the receipt")
    parser.add_argument("--model", default="unspecified", help="narration model recorded in the receipt")
    parser.add_argument("--voice", default="unspecified", help="narration voice recorded in the receipt")
    parser.add_argument("--credit", default="AI narration: generated voice", help="visible bottom-bar narration credit")
    return parser.parse_args(list(argv))


def mux(args: argparse.Namespace) -> Dict[str, Any]:
    video = args.video.resolve()
    receipt_path = args.receipt.resolve()
    audio_dir = args.audio_dir.resolve()
    output = args.output.resolve()
    final_receipt = args.final_receipt.resolve()

    if not video.is_file():
        raise MuxError(f"silent base video is missing: {video}")
    receipt = _load_receipt(receipt_path)
    audio_paths = [audio_dir / f"{index:02d}.mp3" for index in range(1, SCENE_COUNT + 1)]
    missing = [str(path) for path in audio_paths if not path.is_file()]
    if missing:
        raise MuxError("all nine real narration files are required; missing: " + ", ".join(missing))

    video_probe = _probe(video)
    audio_probes = [_probe(path) for path in audio_paths]
    for index, probe in enumerate(audio_probes, start=1):
        audio_streams = [stream for stream in probe["streams"] if stream.get("codec_type") == "audio"]
        if not audio_streams:
            raise MuxError(f"narration {index:02d}.mp3 has no audio stream")
    video_streams = [stream for stream in video_probe["streams"] if stream.get("codec_type") == "video"]
    if not video_streams:
        raise MuxError("silent base video has no video stream")
    actual_video_duration = float(video_probe["duration_seconds"])
    video_limit = min(actual_video_duration, float(receipt["duration_seconds"]))
    audio_meta = [{"duration_seconds": float(probe["duration_seconds"])} for probe in audio_probes]
    fontfile = _font_file()
    provider = str(args.provider).strip()
    model = str(args.model).strip()
    voice = str(args.voice).strip()
    credit = str(args.credit).strip()
    if not provider or not model or not voice or not credit:
        raise MuxError("provider, model, voice, and credit must be non-empty")
    filter_graph, target_durations = _build_filter_graph(receipt["scenes"], video_limit, audio_meta, fontfile, credit)

    output.parent.mkdir(parents=True, exist_ok=True)
    final_receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    if temporary_output.exists():
        temporary_output.unlink()
    command: List[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video)]
    for audio_path in audio_paths:
        command.extend(["-i", str(audio_path)])
    command.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            "48000",
            "-f",
            "mp4",
            "-movflags",
            "+faststart",
            str(temporary_output),
        ]
    )
    try:
        _run(command)
        output_probe = _probe(temporary_output)
        os.replace(temporary_output, output)
    except Exception:
        if temporary_output.exists():
            temporary_output.unlink()
        raise

    scene_receipts: List[Dict[str, Any]] = []
    for index, scene in enumerate(receipt["scenes"]):
        source_start = min(float(scene["start_seconds"]), video_limit)
        source_end = min(float(scene["end_seconds"]), video_limit)
        source_duration = max(0.0, source_end - source_start)
        target = target_durations[index]
        scene_receipts.append(
            {
                "index": index + 1,
                "title": scene["title"],
                "source_start_seconds": round(source_start, 9),
                "source_end_seconds": round(source_end, 9),
                "source_duration_seconds": round(source_duration, 9),
                "audio_duration_seconds": round(float(audio_meta[index]["duration_seconds"]), 9),
                "target_duration_seconds": round(target, 9),
                "target_frames_24fps": int(round(target * FPS)),
                "held_last_frame_seconds": round(max(0.0, target - source_duration), 9),
            }
        )
    final_receipt_data: Dict[str, Any] = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output": str(output),
        "output_sha256": _sha256(output),
        "output_probe": output_probe,
        "video": {
            "path": str(video),
            "sha256": _sha256(video),
            "ffprobe_duration_seconds": round(actual_video_duration, 9),
            "receipt_duration_seconds": round(float(receipt["duration_seconds"]), 9),
            "clipped_source_limit_seconds": round(video_limit, 9),
        },
        "recording_receipt": {
            "path": str(receipt_path),
            "sha256": _sha256(receipt_path),
        },
        "narration": {
            "provider": provider,
            "model": model,
            "voice": voice,
            "normalization": "loudnorm I=-16 LUFS TP=-1.5 dB LRA=11, AAC 160 kb/s, 48 kHz",
            "files": [
                {
                    "scene_index": index + 1,
                    "path": str(path),
                    "sha256": _sha256(path),
                    "ffprobe_duration_seconds": round(float(audio_meta[index]["duration_seconds"]), 9),
                }
                for index, path in enumerate(audio_paths)
            ],
        },
        "credit": credit,
        "fps": FPS,
        "scenes": scene_receipts,
        "target_duration_seconds": round(sum(target_durations), 9),
    }
    with final_receipt.open("w", encoding="utf-8") as handle:
        json.dump(final_receipt_data, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    return final_receipt_data


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = mux(args)
    except MuxError as exc:
        print(f"mux_narration: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"output": result["output"], "output_sha256": result["output_sha256"], "target_duration_seconds": result["target_duration_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
