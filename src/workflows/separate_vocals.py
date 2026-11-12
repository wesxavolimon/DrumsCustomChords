#!/usr/bin/env python
"""Separates the vocal stem from an input audio file using Demucs.

Step contract:
    python src/workflows/separate_vocals.py --inputs <audio.mp3> --outputs <vocals.wav> --params '<json>'

Params:
    model (str): Demucs model name (default: "htdemucs").
    device (str): "cuda" or "cpu" (optional).
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def separate_vocals(input_audio: Path, output_wav: Path, params: dict) -> Path:
    if not input_audio.is_file():
        raise FileNotFoundError(f"Input audio not found: {input_audio}")

    model = params.get("model", "htdemucs")
    device = params.get("device")

    with tempfile.TemporaryDirectory(prefix="demucs_") as tmp_dir:
        tmp_out = Path(tmp_dir)
        cmd = [
            sys.executable, "-m", "demucs.separate",
            "-n", str(model),
            "--two-stems", "vocals",
            "-o", str(tmp_out),
        ]
        if device:
            cmd.extend(["-d", str(device)])
        cmd.append(str(input_audio))

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Demucs failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
            )

        candidates = list(tmp_out.rglob("vocals.wav"))
        if not candidates:
            raise FileNotFoundError(f"Demucs did not produce vocals.wav in {tmp_out}")

        output_wav.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidates[0], output_wav)

    return output_wav


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True, help="Input audio path")
    ap.add_argument("--outputs", nargs="+", required=True, help="Output vocals.wav path")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    params = json.loads(args.params or "{}")
    separate_vocals(Path(args.inputs[0]), Path(args.outputs[0]), params)
    return 0


if __name__ == "__main__":
    sys.exit(main())

