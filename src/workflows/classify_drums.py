#!/usr/bin/env python
"""Classifies quantized 16-step drum events per bar/sub-bar using config/dicionario.yaml.

Maps each bar (and intra-bar changes such as accent -> silence -> fill) to the
dictionary codes:
- `S`: Nenhum evento no compasso/trecho
- `L-h`: Só hi-hat fechado
- `L-abh`: Aro + bumbo + hi-hat fechado
- `L-cbh`: Caixa + bumbo + hi-hat fechado
- `L-cbha`: Caixa + bumbo + hi-hat semi-aberto
- `L-cbrc`: Caixa + bumbo + cúpula do ride
- `CR-cs`: Crescendo de caixa + surdo em colcheias
- `V-cs`: Virada caixa -> surdo
- `V-ct1s`: Virada caixa -> tom 1 -> surdo
- `BQ-bpa1`: Bumbo + ataque 1 seco

Step contract:
    python src/workflows/classify_drums.py --inputs <drums_events.json> <compassos.json> --outputs <drums_patterns.json> --params '<json>'
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DICT_PATH = ROOT / "config" / "dicionario.yaml"

VALID_CODES = (
    "S",
    "L-h",
    "L-abh",
    "L-cbh",
    "L-cbha",
    "L-cbrc",
    "CR-cs",
    "V-cs",
    "V-ct1s",
    "BQ-bpa1",
)


def load_dictionary(dict_path: Path | None = None) -> dict:
    p = Path(dict_path) if dict_path else DEFAULT_DICT_PATH
    if not p.is_absolute():
        p = ROOT / p
    if p.is_file() and yaml is not None:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {}


def classify_events_slice(events: list[dict], allowed_codes: set[str] | None = None) -> str:
    """Classifies a slice of step events into one of the custom drum codes."""
    if not events:
        return "S"

    inst_set: set[str] = set()
    ordered_insts: list[str] = []
    intensities: list[float] = []

    for ev in sorted(events, key=lambda e: int(e.get("step", 1))):
        insts = ev.get("instruments", [])
        for inst in insts:
            inst_set.add(inst)
            ordered_insts.append(inst)
        intensities.append(float(ev.get("intensity", 0.5)))

    if not inst_set:
        return "S"

    # 1. Accent / Baque: Bumbo + prato de ataque 1 seco (few steps, no snare groove)
    if "b" in inst_set and "pa1" in inst_set and "c" not in inst_set and len(events) <= 4:
        return "BQ-bpa1"

    # 2. Crescendo de caixa + surdo em colcheias (CR-cs)
    if "c" in inst_set and "s" in inst_set and len(events) >= 4:
        if len(intensities) >= 3 and intensities[-1] > intensities[0] * 1.12:
            if "h" not in inst_set and "ha" not in inst_set and "rc" not in inst_set:
                return "CR-cs"

    # 3. Viradas (Fills): V-ct1s (caixa -> tom 1 -> surdo) or V-cs (caixa -> surdo)
    if "c" in inst_set and "t1" in inst_set and "s" in inst_set:
        first_c = ordered_insts.index("c")
        last_s = len(ordered_insts) - 1 - ordered_insts[::-1].index("s")
        t1_indices = [i for i, x in enumerate(ordered_insts) if x == "t1"]
        if any(first_c <= ti <= last_s for ti in t1_indices) or len(events) <= 8:
            return "V-ct1s"

    if "c" in inst_set and "s" in inst_set and ("h" not in inst_set and "ha" not in inst_set and "rc" not in inst_set):
        return "V-cs"

    # 4. Grooves / Levadas
    if "c" in inst_set and "b" in inst_set and "rc" in inst_set:
        return "L-cbrc"
    if "c" in inst_set and "b" in inst_set and "ha" in inst_set:
        return "L-cbha"
    if "c" in inst_set and "b" in inst_set and "h" in inst_set:
        return "L-cbh"
    if "a" in inst_set and "b" in inst_set and ("h" in inst_set or "ha" in inst_set):
        return "L-abh"
    if "a" in inst_set and "b" in inst_set:
        return "L-abh"
    if "c" in inst_set and "b" in inst_set:
        return "L-cbh"
    if "b" in inst_set and "pa1" in inst_set:
        return "BQ-bpa1"
    if "h" in inst_set or "ha" in inst_set or "rc" in inst_set:
        return "L-h"
    if "c" in inst_set and "t1" in inst_set:
        return "V-ct1s"
    if "c" in inst_set or "s" in inst_set:
        return "V-cs"
    return "L-h"


def classify_bar(bar_entry: dict, allowed_codes: set[str] | None = None) -> dict:
    """Classifies a bar and also extracts intra-bar sub-segments if distinct patterns occur."""
    bar_num = int(bar_entry["compasso"])
    start_t = float(bar_entry["inicio"])
    end_t = float(bar_entry["fim"])
    dur = max(end_t - start_t, 0.05)
    events = bar_entry.get("events", [])

    full_code = classify_events_slice(events, allowed_codes=allowed_codes)
    sub_events = []

    # Check if the bar has distinct intra-bar sections (e.g. BQ-bpa1 on beat 1, S in middle, V-cs/V-ct1s at end)
    q1 = [e for e in events if 1 <= int(e.get("step", 1)) <= 4]
    q23 = [e for e in events if 5 <= int(e.get("step", 1)) <= 12]
    q4 = [e for e in events if 13 <= int(e.get("step", 1)) <= 16]

    # Case A: Accent at start, silence in middle, fill at end
    if q1 and not q23 and q4:
        c1 = classify_events_slice(q1, allowed_codes)
        c2 = "S"
        c3 = classify_events_slice(q4, allowed_codes)
        sub_events = [
            {"code": c1, "inicio": round(start_t, 2), "fim": round(start_t + dur * 0.25, 2)},
            {"code": c2, "inicio": round(start_t + dur * 0.25, 2), "fim": round(start_t + dur * 0.75, 2)},
            {"code": c3, "inicio": round(start_t + dur * 0.75, 2), "fim": round(end_t, 2)},
        ]
    # Case B: Groove in first 3 beats, fill in beat 4 (with tom/surdo)
    elif (q1 or q23) and q4:
        q4_insts = {inst for e in q4 for inst in e.get("instruments", [])}
        if ("s" in q4_insts or "t1" in q4_insts) and "c" in q4_insts:
            c_main = classify_events_slice(q1 + q23, allowed_codes)
            c_fill = "V-ct1s" if "t1" in q4_insts else "V-cs"
            if c_main != c_fill:
                sub_events = [
                    {"code": c_main, "inicio": round(start_t, 2), "fim": round(start_t + dur * 0.75, 2)},
                    {"code": c_fill, "inicio": round(start_t + dur * 0.75, 2), "fim": round(end_t, 2)},
                ]

    if not sub_events:
        sub_events = [
            {"code": full_code, "inicio": round(start_t, 2), "fim": round(end_t, 2)}
        ]

    return {
        "compasso": bar_num,
        "inicio": round(start_t, 2),
        "fim": round(end_t, 2),
        "code": full_code,
        "segments": sub_events,
    }


def classify_drums(
    events_json: Path,
    compassos_json: Path,
    output_json: Path,
    params: dict | None = None,
) -> dict:
    if not events_json.is_file():
        raise FileNotFoundError(f"Drums events file not found: {events_json}")
    if not compassos_json.is_file():
        raise FileNotFoundError(f"Compassos file not found: {compassos_json}")

    params = params or {}
    dict_cfg = load_dictionary(params.get("dictionary"))
    allowed_codes = {
        str(c["code"]) for c in dict_cfg.get("codes", []) if isinstance(c, dict) and "code" in c
    } or set(VALID_CODES)

    events_data = json.loads(events_json.read_text(encoding="utf-8"))
    bar_entries = events_data.get("compassos", []) if isinstance(events_data, dict) else events_data

    classified_bars = [classify_bar(b, allowed_codes=allowed_codes) for b in bar_entries]

    # Build a flat timeline of pattern changes
    timeline = []
    for cb in classified_bars:
        for seg in cb["segments"]:
            timeline.append({
                "compasso": cb["compasso"],
                "inicio": seg["inicio"],
                "fim": seg["fim"],
                "code": seg["code"],
            })

    payload = {
        "codes_available": sorted(allowed_codes),
        "compassos": classified_bars,
        "timeline": timeline,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True, help="Inputs: <drums_events.json> <compassos.json>")
    ap.add_argument("--outputs", nargs="+", required=True, help="Output: <drums_patterns.json>")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if len(args.inputs) < 2:
        sys.exit("classify_drums requires 2 inputs: <drums_events.json> <compassos.json>")
    params = json.loads(args.params or "{}")
    classify_drums(Path(args.inputs[0]), Path(args.inputs[1]), Path(args.outputs[0]), params)
    return 0


if __name__ == "__main__":
    sys.exit(main())

