#!/usr/bin/env python
"""Detects drum hits per frequency band and quantizes them into a 16-step bar grid.

Uses `ffmpeg` + `wave` + `numpy` (and `scipy`/`librosa` when available) to perform
FFT bandpass energy envelope extraction and onset peak picking per drum instrument:
- `b`: Bumbo (30 - 130 Hz)
- `s`: Surdo (80 - 200 Hz, longer decay)
- `t1`: Tom 1 (150 - 350 Hz)
- `c`: Caixa (200 - 4000 Hz)
- `a`: Aro (800 - 3500 Hz, sharp transient with low body energy)
- `h`: Hi-hat fechado (5000 - 15000 Hz, short decay)
- `ha`: Hi-hat semi-aberto (4000 - 14000 Hz, sustained decay)
- `rc`: Cúpula do ride (2400 - 5200 Hz, tonal bell prominence)
- `pa1`: Prato de ataque 1 seco (3500 - 16000 Hz, high energy accent + fast choke/decay)

Step contract:
    python src/workflows/detect_drums.py --inputs <drums.wav> <compassos.json> --outputs <drums_events.json> --params '<json>'
"""
import argparse
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DICT_PATH = ROOT / "config" / "dicionario.yaml"


def load_dictionary(dict_path: Path | None = None) -> dict:
    p = Path(dict_path) if dict_path else DEFAULT_DICT_PATH
    if not p.is_absolute():
        p = ROOT / p
    if p.is_file() and yaml is not None:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {}


def load_audio_mono(audio_path: Path, target_sr: int = 22050) -> tuple[np.ndarray, int]:
    """Loads audio file into a mono float32 numpy array in [-1, 1]."""
    def _read_wav(wav_file: Path) -> tuple[np.ndarray, int]:
        with wave.open(str(wav_file), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
        if sampwidth == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 4:
            data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            data = (data - 128.0) / 128.0
        if n_channels > 1:
            data = data.reshape(-1, n_channels).mean(axis=1)
        return data, sr

    try:
        return _read_wav(audio_path)
    except Exception:
        with tempfile.TemporaryDirectory(prefix="drums_wav_") as tmp:
            tmp_wav = Path(tmp) / "converted.wav"
            cmd = [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ac", "1", "-ar", str(target_sr), "- sample_fmt", "s16",
                str(tmp_wav),
            ]
            # Fix flag spacing for sample_fmt
            cmd = [
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ac", "1", "-ar", str(target_sr),
                str(tmp_wav),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0 or not tmp_wav.is_file():
                raise RuntimeError(f"Could not read audio {audio_path}: {proc.stderr}")
            return _read_wav(tmp_wav)


def analyze_bar_steps(
    samples: np.ndarray,
    sr: int,
    bars: list[dict],
    steps_per_bar: int = 16,
    dict_config: dict | None = None,
) -> list[dict]:
    """Quantizes drum audio into `steps_per_bar` subdivisions per bar and detects active instruments."""
    total_samples = len(samples)
    if total_samples == 0 or not bars:
        return []

    global_rms = float(np.sqrt(np.mean(samples ** 2))) + 1e-8
    silence_rms_floor = max(global_rms * 0.12, 1e-4)

    # First pass: compute per-step band energies across all bars for adaptive normalization
    raw_bars = []
    max_low = 1e-8
    max_surdo = 1e-8
    max_tom = 1e-8
    max_mid = 1e-8
    max_bell = 1e-8
    max_high = 1e-8

    for bar in bars:
        bar_num = int(bar["compasso"])
        start_t = float(bar["inicio"])
        end_t = float(bar["fim"])
        dur = max(end_t - start_t, 0.05)
        step_dur = dur / steps_per_bar

        step_feats = []
        for s_idx in range(steps_per_bar):
            st0 = start_t + s_idx * step_dur
            st1 = st0 + step_dur
            i0 = max(0, min(total_samples, int(st0 * sr)))
            i1 = max(i0, min(total_samples, int(st1 * sr)))
            seg = samples[i0:i1]
            if len(seg) < 32:
                step_feats.append(None)
                continue

            rms = float(np.sqrt(np.mean(seg ** 2)))
            # Compute first-half vs second-half RMS for transient/decay estimation
            half = max(1, len(seg) // 2)
            rms_first = float(np.sqrt(np.mean(seg[:half] ** 2)))
            rms_second = float(np.sqrt(np.mean(seg[half:] ** 2))) + 1e-8
            decay_ratio = rms_second / (rms_first + 1e-8)

            windowed = seg * np.hanning(len(seg))
            spec = np.abs(np.fft.rfft(windowed))
            freqs = np.fft.rfftfreq(len(seg), d=1.0 / sr)

            def band_energy(f_lo: float, f_hi: float) -> float:
                mask = (freqs >= f_lo) & (freqs < f_hi)
                if not np.any(mask):
                    return 0.0
                return float(np.sqrt(np.mean(spec[mask] ** 2)))

            e_low = band_energy(30, 130)       # Bumbo (b)
            e_surdo = band_energy(80, 200)     # Surdo (s)
            e_tom = band_energy(150, 350)      # Tom 1 (t1)
            e_body = band_energy(200, 900)     # Corpo da caixa
            e_mid = band_energy(200, 4000)     # Caixa / Aro (c / a)
            e_rim = band_energy(900, 3200)     # Aro (a)
            e_bell = band_energy(2400, 5200)   # Cúpula ride (rc)
            e_high = band_energy(4500, min(15000, sr / 2 - 100))  # Hi-hat / Crash (h, ha, pa1)

            max_low = max(max_low, e_low)
            max_surdo = max(max_surdo, e_surdo)
            max_tom = max(max_tom, e_tom)
            max_mid = max(max_mid, e_mid)
            max_bell = max(max_bell, e_bell)
            max_high = max(max_high, e_high)

            step_feats.append({
                "step": s_idx + 1,
                "time": round(st0, 2),
                "rms": rms,
                "rms_first": rms_first,
                "decay_ratio": decay_ratio,
                "e_low": e_low,
                "e_surdo": e_surdo,
                "e_tom": e_tom,
                "e_body": e_body,
                "e_mid": e_mid,
                "e_rim": e_rim,
                "e_bell": e_bell,
                "e_high": e_high,
            })

        raw_bars.append({
            "compasso": bar_num,
            "inicio": round(start_t, 2),
            "fim": round(end_t, 2),
            "step_feats": step_feats,
        })

    # Second pass: detect instruments per step using normalized band energies and onset deltas
    result_bars = []
    for b_info in raw_bars:
        feats = b_info["step_feats"]
        events = []
        prev_low = 0.0
        prev_mid = 0.0
        prev_high = 0.0

        for sf in feats:
            if sf is None or sf["rms"] < silence_rms_floor:
                prev_low = 0.0
                prev_mid = 0.0
                prev_high = 0.0
                continue

            n_low = sf["e_low"] / max_low
            n_surdo = sf["e_surdo"] / max_surdo
            n_tom = sf["e_tom"] / max_tom
            n_mid = sf["e_mid"] / max_mid
            n_bell = sf["e_bell"] / max_bell
            n_high = sf["e_high"] / max_high

            instruments = []

            # Low frequency: Bumbo (b) vs Surdo (s) vs Tom 1 (t1)
            if n_low >= 0.24 and n_low >= prev_low * 0.75:
                if n_surdo > n_low * 1.15 and sf["decay_ratio"] > 0.55 and sf["step"] >= 9:
                    instruments.append("s")
                else:
                    instruments.append("b")
            elif n_surdo >= 0.30 and sf["step"] >= 9:
                instruments.append("s")

            if n_tom >= 0.32 and n_tom > n_low * 1.1:
                instruments.append("t1")

            # Mid frequency: Caixa (c) vs Aro (a)
            if n_mid >= 0.23 and n_mid >= prev_mid * 0.75:
                rim_to_body = sf["e_rim"] / (sf["e_body"] + 1e-8)
                if rim_to_body > 1.45 and n_mid < 0.62:
                    instruments.append("a")
                else:
                    instruments.append("c")

            # High frequency: Crash (pa1) vs Ride bell (rc) vs Open/Closed Hi-hat (ha / h)
            if n_high >= 0.16 or n_bell >= 0.26:
                if (
                    n_high >= 0.88
                    and sf["rms"] >= global_rms * 2.1
                    and ("b" in instruments)
                    and sf["step"] in (1, 5, 9, 13)
                ):
                    instruments.append("pa1")
                elif n_bell >= 0.35 and (sf["e_bell"] / (sf["e_high"] + 1e-8)) > 1.25:
                    instruments.append("rc")
                elif n_high >= 0.16 and n_high >= prev_high * 0.65:
                    if sf["decay_ratio"] > 0.62 and n_high >= 0.28:
                        instruments.append("ha")
                    else:
                        instruments.append("h")

            prev_low = n_low
            prev_mid = n_mid
            prev_high = n_high

            if instruments:
                events.append({
                    "step": sf["step"],
                    "time": sf["time"],
                    "instruments": instruments,
                    "intensity": round(min(1.0, float(sf["rms"] / (global_rms * 2.5))), 3),
                })

        result_bars.append({
            "compasso": b_info["compasso"],
            "inicio": b_info["inicio"],
            "fim": b_info["fim"],
            "events": events,
        })

    return result_bars


def detect_drums(
    drums_wav: Path,
    compassos_json: Path,
    output_json: Path,
    params: dict | None = None,
) -> dict:
    if not drums_wav.is_file():
        raise FileNotFoundError(f"Drums audio not found: {drums_wav}")
    if not compassos_json.is_file():
        raise FileNotFoundError(f"Compassos file not found: {compassos_json}")

    params = params or {}
    steps_per_bar = int(params.get("steps_per_bar", 16))
    dict_cfg = load_dictionary(params.get("dictionary"))

    tempo_data = json.loads(compassos_json.read_text(encoding="utf-8"))
    bars = tempo_data if isinstance(tempo_data, list) else tempo_data.get("compassos", [])

    samples, sr = load_audio_mono(drums_wav)
    bar_events = analyze_bar_steps(samples, sr, bars, steps_per_bar=steps_per_bar, dict_config=dict_cfg)

    payload = {
        "steps_per_bar": steps_per_bar,
        "compassos": bar_events,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True, help="Inputs: <drums.wav> <compassos.json>")
    ap.add_argument("--outputs", nargs="+", required=True, help="Output: <drums_events.json>")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if len(args.inputs) < 2:
        sys.exit("detect_drums requires 2 inputs: <drums.wav> <compassos.json>")
    params = json.loads(args.params or "{}")
    detect_drums(Path(args.inputs[0]), Path(args.inputs[1]), Path(args.outputs[0]), params)
    return 0


if __name__ == "__main__":
    sys.exit(main())

