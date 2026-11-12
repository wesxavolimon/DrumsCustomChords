#!/usr/bin/env python
"""Transcribes vocals audio into timestamped lyrics segments using Whisper.

Supports the `wesley-whisper` Docker container (default when faster_whisper is not installed locally),
local `faster-whisper`, or local `openai-whisper`.

Step contract:
    python src/workflows/transcribe.py --inputs <vocals.wav> --outputs <letra.json> --params '<json>'

Params:
    model (str): Whisper model size (default: "large-v3").
    lang (str): Language code such as "pt" or "en" (default: "pt").
    device (str): "cuda", "cpu", or "auto" (default: "auto").
    compute_type (str): faster-whisper compute type (default: "float16" on cuda, "int8" on cpu).
    docker_image (str): Docker image to use (default: "wesley-whisper").
    use_docker (bool): Force Docker usage (default: True when faster_whisper is not installed locally).
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


def _transcribe_with_docker(
    audio_path: Path,
    output_json: Path,
    model_name: str,
    lang: str | None,
    device: str,
    compute_type: str | None,
    docker_image: str,
) -> list[dict]:
    in_dir = str(audio_path.resolve().parent)
    out_dir = str(output_json.resolve().parent)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    docker_device = "cpu" if device in ("auto", None, "") else str(device)
    docker_compute = compute_type or ("float16" if docker_device == "cuda" else "int8")

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{in_dir}:/in",
        "-v", f"{out_dir}:/out",
        "-v", "wesley-whisper-cache:/root/.cache/huggingface",
        docker_image,
        f"/in/{audio_path.name}",
        "-o", f"/out/{output_json.name}",
        "--model", str(model_name),
        "--device", docker_device,
        "--compute-type", docker_compute,
    ]
    if lang:
        cmd.extend(["--lang", str(lang)])

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Docker whisper ({docker_image}) failed (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}"
        )
    if not output_json.is_file():
        raise FileNotFoundError(f"Docker whisper did not write {output_json}")
    return json.loads(output_json.read_text(encoding="utf-8"))


def _transcribe_faster_whisper(audio_path: Path, model_name: str, lang: str | None, device: str, compute_type: str | None) -> list[dict]:
    from faster_whisper import WhisperModel

    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"
    if not compute_type:
        compute_type = "float16" if device == "cuda" else "int8"

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(str(audio_path), language=lang or None, vad_filter=True)
    result = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            result.append({
                "start": round(float(seg.start), 2),
                "end": round(float(seg.end), 2),
                "text": text,
            })
    return result


def _transcribe_openai_whisper(audio_path: Path, model_name: str, lang: str | None, device: str) -> list[dict]:
    import whisper

    kwargs = {}
    if device and device != "auto":
        kwargs["device"] = device
    model = whisper.load_model(model_name, **kwargs)
    out = model.transcribe(str(audio_path), language=lang or None)
    result = []
    for seg in out.get("segments", []):
        text = (seg.get("text") or "").strip()
        if text:
            result.append({
                "start": round(float(seg["start"]), 2),
                "end": round(float(seg["end"]), 2),
                "text": text,
            })
    return result


def transcribe_audio(input_wav: Path, output_json: Path, params: dict) -> list[dict]:
    if not input_wav.is_file():
        raise FileNotFoundError(f"Input audio not found: {input_wav}")

    model_name = params.get("model", "large-v3")
    lang = params.get("lang", "pt")
    device = params.get("device", "auto")
    compute_type = params.get("compute_type")
    backend = params.get("backend", "auto")
    docker_image = params.get("docker_image", "wesley-whisper")
    use_docker = params.get("use_docker")

    if backend == "docker" or use_docker is True:
        return _transcribe_with_docker(input_wav, output_json, model_name, lang, device, compute_type, docker_image)

    if backend == "faster-whisper" or (backend == "auto" and importlib.util.find_spec("faster_whisper")):
        segments = _transcribe_faster_whisper(input_wav, model_name, lang, device, compute_type)
    elif backend == "whisper":
        segments = _transcribe_openai_whisper(input_wav, model_name, lang, device)
    elif backend == "auto" and use_docker is None:
        return _transcribe_with_docker(input_wav, output_json, model_name, lang, device, compute_type, docker_image)
    elif importlib.util.find_spec("whisper"):
        segments = _transcribe_openai_whisper(input_wav, model_name, lang, device)
    else:
        raise RuntimeError("No Whisper backend available (wesley-whisper Docker, faster_whisper, or whisper).")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8")
    return segments


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True, help="Input vocals.wav path")
    ap.add_argument("--outputs", nargs="+", required=True, help="Output letra.json path")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    params = json.loads(args.params or "{}")
    transcribe_audio(Path(args.inputs[0]), Path(args.outputs[0]), params)
    return 0


if __name__ == "__main__":
    sys.exit(main())
