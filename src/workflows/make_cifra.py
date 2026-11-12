#!/usr/bin/env python
"""Generates the initial chord/lyrics sheet (cifra.md) aligning lyrics to bars.

Step contract:
    python src/workflows/make_cifra.py --inputs <letra.json> <compassos.json> --outputs <cifra.md> --params '<json>'
"""
import argparse
import json
import sys
from pathlib import Path


def find_bar_for_time(t: float, bars: list[dict]) -> int:
    if not bars:
        return 1
    for bar in bars:
        if float(bar["inicio"]) <= t < float(bar["fim"]):
            return int(bar["compasso"])
    if t < float(bars[0]["inicio"]):
        return int(bars[0]["compasso"])
    return int(bars[-1]["compasso"])


def render_cifra(song_id: str, segments: list[dict], tempo_data: dict | list) -> str:
    if isinstance(tempo_data, list):
        bars = tempo_data
        bpm = 0
        formula = "4/4"
    else:
        bars = tempo_data.get("compassos", [])
        bpm = tempo_data.get("bpm", 0)
        formula = tempo_data.get("formula", "4/4")

    bpm_str = f"{int(round(bpm))}" if bpm else "?"
    lines = [f"# {song_id} | BPM {bpm_str} | {formula}", ""]

    if not segments:
        lines.append("_(Sem letra transcrita)_")
        return "\n".join(lines) + "\n"

    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        bar_start = find_bar_for_time(start, bars)
        bar_end = find_bar_for_time(max(start, end - 0.01), bars)
        if bar_end > bar_start:
            header = f"[Compasso {bar_start}-{bar_end}]"
        else:
            header = f"[Compasso {bar_start}]"
        lines.append(header)
        lines.append(text)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def make_cifra(letra_path: Path, compassos_path: Path, output_md: Path, params: dict | None = None) -> str:
    if not letra_path.is_file():
        raise FileNotFoundError(f"Lyrics file not found: {letra_path}")
    if not compassos_path.is_file():
        raise FileNotFoundError(f"Bars file not found: {compassos_path}")

    segments = json.loads(letra_path.read_text(encoding="utf-8"))
    tempo_data = json.loads(compassos_path.read_text(encoding="utf-8"))
    song_id = (params or {}).get("song_id") or output_md.parent.name or letra_path.parent.name

    content = render_cifra(song_id, segments, tempo_data)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(content, encoding="utf-8")
    return content


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True, help="Inputs: <letra.json> <compassos.json>")
    ap.add_argument("--outputs", nargs="+", required=True, help="Output: <cifra.md>")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if len(args.inputs) < 2:
        sys.exit("make_cifra requires 2 inputs: <letra.json> <compassos.json>")
    params = json.loads(args.params or "{}")
    make_cifra(Path(args.inputs[0]), Path(args.inputs[1]), Path(args.outputs[0]), params)
    return 0


if __name__ == "__main__":
    sys.exit(main())

