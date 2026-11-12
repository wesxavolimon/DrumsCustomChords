#!/usr/bin/env python
"""Separates the vocal stem from an input audio file using Demucs.

Supports local Python `demucs` module or fallback to the `wesley-demucs` Docker container.

Step contract:
    python src/workflows/separate_vocals.py --inputs <audio.mp3> --outputs <vocals.wav> --params '<json>'

Params:
    model (str): Demucs model name (default: "htdemucs").
    device (str): "cuda" or "cpu" (optional).
    docker_image (str): Docker image to use when local demucs is unavailable (default: "wesley-demucs").
"""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _build_demucs_cmd(
    input_audio: Path,
    tmp_out: Path,
    model: str,
    device: str | None,
    docker_image: str,
    use_docker: bool,
) -> list[str]:
    if not use_docker:
        cmd = [
            sys.executable, "-m", "demucs.separate",
            "-n", str(model),
            "--two-stems", "vocals",
            "--mp3",
            "-o", str(tmp_out),
        ]
        if device:
            cmd.extend(["-d", str(device)])
        cmd.append(str(input_audio))
        return cmd

    in_dir = str(input_audio.resolve().parent)
    out_dir = str(tmp_out.resolve())
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{in_dir}:/in",
        "-v", f"{out_dir}:/out",
        docker_image,
        "-n", str(model),
        "--two-stems", "vocals",
        "--mp3",
        "-o", "/out",
    ]
    if device:
        cmd.extend(["-d", str(device)])
    cmd.append(f"/in/{input_audio.name}")
    return cmd


def separate_vocals(input_audio: Path, output_wav: Path, params: dict) -> Path:
    if not input_audio.is_file():
        raise FileNotFoundError(f"Input audio not found: {input_audio}")

    model = params.get("model", "htdemucs")
    device = params.get("device")
    docker_image = params.get("docker_image", "wesley-demucs")
    use_docker = params.get("use_docker")
    if use_docker is None:
        use_docker = importlib.util.find_spec("demucs") is None

    with tempfile.TemporaryDirectory(prefix="demucs_") as tmp_dir:
        tmp_out = Path(tmp_dir)
        cmd = _build_demucs_cmd(input_audio, tmp_out, model, device, docker_image, bool(use_docker))

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Demucs failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
            )

        candidates = list(tmp_out.rglob("vocals.wav")) + list(tmp_out.rglob("vocals.mp3"))
        if not candidates:
            raise FileNotFoundError(f"Demucs did not produce vocals track in {tmp_out}")

        src_file = candidates[0]
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        if src_file.suffix.lower() == output_wav.suffix.lower():
            shutil.copy2(src_file, output_wav)
        else:
            conv = subprocess.run(
                ["ffmpeg", "-y", "-i", str(src_file), str(output_wav)],
                capture_output=True,
                text=True,
            )
            if conv.returncode != 0 or not output_wav.is_file():
                shutil.copy2(src_file, output_wav)

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
