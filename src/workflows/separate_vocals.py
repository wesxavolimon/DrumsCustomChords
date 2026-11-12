#!/usr/bin/env python
"""Separates vocals, drums, and no_drums stems from an input audio file using Demucs.

Supports local Python `demucs` module or fallback to the `wesley-demucs` Docker container.
Can output just `<vocals.wav>` or `<vocals.wav> <drums.wav> <no_drums.wav>`.

Step contract:
    python src/workflows/separate_vocals.py --inputs <audio.mp3> --outputs <vocals.wav> [<drums.wav> <no_drums.wav>] --params '<json>'
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
    two_stems: str | None = "vocals",
) -> list[str]:
    if not use_docker:
        cmd = [
            sys.executable, "-m", "demucs.separate",
            "-n", str(model),
            "--mp3",
            "-o", str(tmp_out),
        ]
        if two_stems:
            cmd.extend(["--two-stems", str(two_stems)])
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
        "--mp3",
        "-o", "/out",
    ]
    if two_stems:
        cmd.extend(["--two-stems", str(two_stems)])
    if device:
        cmd.extend(["-d", str(device)])
    cmd.append(f"/in/{input_audio.name}")
    return cmd


def _copy_or_convert(src_file: Path, dest_file: Path) -> None:
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    if src_file.suffix.lower() == dest_file.suffix.lower():
        shutil.copy2(src_file, dest_file)
        return
    conv = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src_file), str(dest_file)],
        capture_output=True,
        text=True,
    )
    if conv.returncode != 0 or not dest_file.is_file():
        shutil.copy2(src_file, dest_file)


def _mix_stems_with_ffmpeg(sources: list[Path], dest_file: Path) -> None:
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    if len(sources) == 1:
        _copy_or_convert(sources[0], dest_file)
        return
    cmd = ["ffmpeg", "-y"]
    for s in sources:
        cmd.extend(["-i", str(s)])
    cmd.extend([
        "-filter_complex",
        f"amix=inputs={len(sources)}:duration=longest:normalize=0",
        str(dest_file),
    ])
    conv = subprocess.run(cmd, capture_output=True, text=True)
    if conv.returncode != 0 or not dest_file.is_file():
        _copy_or_convert(sources[0], dest_file)


def _find_stem(tmp_out: Path, stem_name: str) -> Path | None:
    candidates = list(tmp_out.rglob(f"{stem_name}.wav")) + list(tmp_out.rglob(f"{stem_name}.mp3"))
    return candidates[0] if candidates else None


def separate_vocals(
    input_audio: Path,
    output_wav: Path,
    params: dict,
    drums_wav: Path | None = None,
    no_drums_wav: Path | None = None,
) -> Path:
    if not input_audio.is_file():
        raise FileNotFoundError(f"Input audio not found: {input_audio}")

    model = params.get("model", "htdemucs")
    device = params.get("device")
    docker_image = params.get("docker_image", "wesley-demucs")
    use_docker = params.get("use_docker")
    if use_docker is None:
        use_docker = importlib.util.find_spec("demucs") is None

    need_drums = drums_wav is not None or no_drums_wav is not None
    two_stems = None if need_drums else "vocals"

    with tempfile.TemporaryDirectory(prefix="demucs_") as tmp_dir:
        tmp_out = Path(tmp_dir)
        cmd = _build_demucs_cmd(
            input_audio, tmp_out, model, device, docker_image, bool(use_docker), two_stems=two_stems
        )

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Demucs failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
            )

        vocals_src = _find_stem(tmp_out, "vocals")
        if not vocals_src:
            raise FileNotFoundError(f"Demucs did not produce vocals track in {tmp_out}")
        _copy_or_convert(vocals_src, output_wav)

        if drums_wav is not None:
            drums_src = _find_stem(tmp_out, "drums")
            if drums_src:
                _copy_or_convert(drums_src, drums_wav)
            else:
                _copy_or_convert(vocals_src, drums_wav)

        if no_drums_wav is not None:
            no_drums_src = _find_stem(tmp_out, "no_drums")
            if no_drums_src:
                _copy_or_convert(no_drums_src, no_drums_wav)
            else:
                other_stems = [
                    p for name in ("bass", "other", "vocals")
                    if (p := _find_stem(tmp_out, name)) is not None
                ]
                if other_stems:
                    _mix_stems_with_ffmpeg(other_stems, no_drums_wav)
                else:
                    _copy_or_convert(vocals_src, no_drums_wav)

    return output_wav


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True, help="Input audio path")
    ap.add_argument("--outputs", nargs="+", required=True, help="Output paths: vocals.wav [drums.wav no_drums.wav]")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    params = json.loads(args.params or "{}")
    vocals_out = Path(args.outputs[0])
    drums_out = Path(args.outputs[1]) if len(args.outputs) > 1 else None
    no_drums_out = Path(args.outputs[2]) if len(args.outputs) > 2 else None
    separate_vocals(Path(args.inputs[0]), vocals_out, params, drums_wav=drums_out, no_drums_wav=no_drums_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
