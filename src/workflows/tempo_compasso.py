#!/usr/bin/env python
"""Detects BPM, beats, and bar boundaries (compassos) from an audio file.

Step contract:
    python src/workflows/tempo_compasso.py --inputs <audio.mp3> --outputs <compassos.json> --params '<json>'

Params:
    beats_per_bar (int): Beats per measure (default: 4 for 4/4).
"""
import argparse
import json
import sys
from pathlib import Path


def build_bars_from_beats(beat_times: list[float], duration: float, beats_per_bar: int = 4) -> list[dict]:
    if beats_per_bar <= 0:
        raise ValueError("beats_per_bar must be positive")

    bars = []
    if not beat_times:
        return bars

    total_beats = len(beat_times)
    bar_num = 1
    for i in range(0, total_beats, beats_per_bar):
        start = float(beat_times[i])
        next_idx = i + beats_per_bar
        if next_idx < total_beats:
            end = float(beat_times[next_idx])
        else:
            if total_beats >= 2:
                avg_beat = (beat_times[-1] - beat_times[0]) / (total_beats - 1)
                remaining_beats = next_idx - (total_beats - 1)
                est_end = beat_times[-1] + avg_beat * remaining_beats
                end = min(float(duration), est_end) if duration > start else est_end
            else:
                end = max(float(duration), start)
        bars.append({
            "compasso": bar_num,
            "inicio": round(start, 2),
            "fim": round(max(end, start), 2),
        })
        bar_num += 1
    return bars


def detect_tempo_and_bars(input_audio: Path, output_json: Path, params: dict) -> dict:
    if not input_audio.is_file():
        raise FileNotFoundError(f"Input audio not found: {input_audio}")

    import librosa
    import numpy as np

    beats_per_bar = int(params.get("beats_per_bar", 4))
    y, sr = librosa.load(str(input_audio), sr=None)
    duration = float(librosa.get_duration(y=y, sr=sr))

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    bpm = float(np.asarray(tempo).flat[0]) if np.size(tempo) else 120.0
    beat_times = [float(t) for t in librosa.frames_to_time(beat_frames, sr=sr)]

    if not beat_times and bpm > 0 and duration > 0:
        step = 60.0 / bpm
        t = 0.0
        while t < duration:
            beat_times.append(t)
            t += step

    bars = build_bars_from_beats(beat_times, duration, beats_per_bar=beats_per_bar)
    payload = {
        "bpm": round(bpm, 1),
        "formula": f"{beats_per_bar}/4",
        "beats_per_bar": beats_per_bar,
        "duration": round(duration, 2),
        "compassos": bars,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True, help="Input audio path")
    ap.add_argument("--outputs", nargs="+", required=True, help="Output compassos.json path")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    params = json.loads(args.params or "{}")
    detect_tempo_and_bars(Path(args.inputs[0]), Path(args.outputs[0]), params)
    return 0


if __name__ == "__main__":
    sys.exit(main())

