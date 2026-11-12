#!/usr/bin/env python
"""Generates the custom drum sheet (`<id>-cifra.md`) aligning custom drum codes above the lyrics.

Formats custom drum codes WITHOUT brackets (`L-cbh`, `BQ-bpa1`, `S`, `V-cs`, etc.)
on the line immediately above the lyrics, horizontally positioned over the exact word
or vocal pause where the drum pattern starts or changes.

Optionally sends the deterministic sheet to Gemma (`llama.cpp` at port 11435) for review,
falling back safely to the deterministic sheet if the server is unreachable or alters annotations.

Step contract:
    python src/workflows/make_cifra.py --inputs <letra.json> <compassos.json> [<drums_patterns.json>] --outputs <<id>-cifra.md> --params '<json>'
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

KNOWN_DRUM_CODES = (
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

DRUM_CODE_REGEX = re.compile(
    r"\b(?:S|L-cbha|L-cbrc|L-abh|L-cbh|L-h|CR-cs|V-ct1s|V-cs|BQ-bpa1)\b"
)


def find_bar_for_time(t: float, bars: list[dict]) -> int:
    if not bars:
        return 1
    for bar in bars:
        if float(bar["inicio"]) <= t < float(bar["fim"]):
            return int(bar["compasso"])
    if t < float(bars[0]["inicio"]):
        return int(bars[0]["compasso"])
    return int(bars[-1]["compasso"])


def _split_long_segment(seg: dict, max_chars: int = 72) -> list[dict]:
    """Splits a long Whisper segment into readable lyric lines with interpolated timestamps."""
    text = (seg.get("text") or "").strip()
    if not text:
        return []
    start = float(seg.get("start", 0.0))
    end = max(start + 0.1, float(seg.get("end", start + 0.1)))
    words = seg.get("words")

    if len(text) <= max_chars:
        return [{"start": round(start, 2), "end": round(end, 2), "text": text, "words": words}]

    # Split by punctuation first (commas, periods, semicolons) or word budget
    clauses = [c.strip() for c in re.split(r"(?<=[,.;!?])\s+", text) if c.strip()]
    merged_lines: list[str] = []
    cur = ""
    for cl in clauses:
        if not cur:
            cur = cl
        elif len(cur) + 1 + len(cl) <= max_chars:
            cur = f"{cur} {cl}"
        else:
            merged_lines.append(cur)
            cur = cl
    if cur:
        merged_lines.append(cur)

    # If a single clause is still too long, split by word count
    final_chunks: list[str] = []
    for line in merged_lines:
        if len(line) <= max_chars:
            final_chunks.append(line)
        else:
            w_list = line.split()
            buf = []
            for w in w_list:
                if buf and len(" ".join(buf + [w])) > max_chars:
                    final_chunks.append(" ".join(buf))
                    buf = [w]
                else:
                    buf.append(w)
            if buf:
                final_chunks.append(" ".join(buf))

    total_chars = sum(len(c) for c in final_chunks) or 1
    dur = end - start
    out: list[dict] = []
    cursor = start
    for i, chunk in enumerate(final_chunks):
        frac = len(chunk) / total_chars
        c_end = end if i == len(final_chunks) - 1 else cursor + dur * frac
        out.append({
            "start": round(cursor, 2),
            "end": round(c_end, 2),
            "text": chunk,
        })
        cursor = c_end
    return out


def _extract_timeline(drums_patterns: dict | list | None, bars: list[dict]) -> list[dict]:
    if not drums_patterns:
        # Default fallback if no drums_patterns provided: assign L-cbh to bars
        return [
            {
                "compasso": int(b.get("compasso", idx + 1)),
                "inicio": float(b.get("inicio", 0.0)),
                "fim": float(b.get("fim", 0.0)),
                "code": "L-cbh",
            }
            for idx, b in enumerate(bars)
        ]

    if isinstance(drums_patterns, dict):
        if "timeline" in drums_patterns and drums_patterns["timeline"]:
            return drums_patterns["timeline"]
        if "compassos" in drums_patterns:
            items = []
            for b in drums_patterns["compassos"]:
                if "segments" in b and b["segments"]:
                    for s in b["segments"]:
                        items.append({
                            "compasso": b.get("compasso", 1),
                            "inicio": float(s["inicio"]),
                            "fim": float(s["fim"]),
                            "code": str(s["code"]).strip("[]"),
                        })
                else:
                    items.append({
                        "compasso": b.get("compasso", 1),
                        "inicio": float(b["inicio"]),
                        "fim": float(b["fim"]),
                        "code": str(b.get("code", "L-cbh")).strip("[]"),
                    })
            return items
    elif isinstance(drums_patterns, list):
        return [
            {
                "compasso": item.get("compasso", idx + 1),
                "inicio": float(item.get("inicio", 0.0)),
                "fim": float(item.get("fim", 0.0)),
                "code": str(item.get("code", "L-cbh")).strip("[]"),
            }
            for idx, item in enumerate(drums_patterns)
        ]
    return []


def build_annotation_line_for_lyric(
    lyric_line: dict,
    timeline: list[dict],
) -> tuple[str, str]:
    """Builds `(annotation_line, lyric_text)` with drum codes positioned above the corresponding words."""
    text = (lyric_line.get("text") or "").strip()
    l_start = float(lyric_line.get("start", 0.0))
    l_end = max(l_start + 0.1, float(lyric_line.get("end", l_start + 0.1)))
    l_dur = l_end - l_start

    # Find all drum timeline events overlapping [l_start, l_end]
    overlapping = [
        ev for ev in timeline
        if float(ev["fim"]) > l_start and float(ev["inicio"]) < l_end
    ]
    if not overlapping and timeline:
        # Pick the closest drum event in time
        closest = min(timeline, key=lambda ev: abs(float(ev["inicio"]) - l_start))
        overlapping = [closest]

    # Deduplicate consecutive identical codes within the same lyric line
    distinct_events: list[dict] = []
    for ev in overlapping:
        code = str(ev.get("code", "L-cbh")).strip("[]")
        if not distinct_events or distinct_events[-1]["code"] != code:
            distinct_events.append({
                "code": code,
                "inicio": float(ev.get("inicio", l_start)),
                "fim": float(ev.get("fim", l_end)),
            })

    if not distinct_events:
        distinct_events = [{"code": "L-cbh", "inicio": l_start, "fim": l_end}]

    # Keep at most 4 most prominent pattern transitions per single lyric line so codes
    # stay aligned directly over the words and never overflow past the lyric text
    if len(distinct_events) > 4:
        first_ev = distinct_events[0]
        last_ev = distinct_events[-1]
        mid_candidates = distinct_events[1:-1]
        # Prioritize fills, accents, or silence in the middle
        priority = {"BQ-bpa1": 0, "S": 1, "CR-cs": 2, "V-ct1s": 3, "V-cs": 4}
        mid_sorted = sorted(
            mid_candidates,
            key=lambda e: (priority.get(e["code"], 10), -(e["fim"] - e["inicio"])),
        )[:2]
        mid_sorted.sort(key=lambda e: e["inicio"])
        distinct_events = [first_ev, *mid_sorted, last_ev]
        # Re-deduplicate if adjacent became identical
        deduped = []
        for ev in distinct_events:
            if not deduped or deduped[-1]["code"] != ev["code"]:
                deduped.append(ev)
        distinct_events = deduped

    # If there is an intra-line silence ('S') surrounded by other patterns and the lyric does not yet
    # mention silence, we keep the lyric text and align the codes proportionally to character columns.
    line_len = max(len(text), 20)
    placements: list[tuple[int, str]] = []

    for idx, ev in enumerate(distinct_events):
        code = ev["code"]
        if idx == 0 and ev["inicio"] <= l_start + 0.25:
            col = 0
        else:
            rel = max(0.0, min(0.92, (ev["inicio"] - l_start) / l_dur))
            raw_col = int(round(rel * len(text)))
            # Snap to nearest word start in `text` for clean visual alignment
            word_starts = [m.start() for m in re.finditer(r"\S+", text)]
            col = min(word_starts, key=lambda ws: abs(ws - raw_col)) if word_starts else raw_col

        if placements:
            prev_col, prev_code = placements[-1]
            min_next_col = prev_col + len(prev_code) + 2
            if col < min_next_col:
                col = min_next_col
        placements.append((col, code))

    canvas_len = max(line_len, placements[-1][0] + len(placements[-1][1]) if placements else 0)
    chars = [" "] * canvas_len
    for col, code in placements:
        for i, ch in enumerate(code):
            if col + i < len(chars):
                chars[col + i] = ch
            else:
                chars.append(ch)

    annotation_line = "".join(chars).rstrip()
    return annotation_line, text


def review_with_gemma(markdown_text: str, llm_url: str, timeout: float = 12.0) -> str:
    """Optionally asks local Gemma via llama.cpp (port 11435) to review formatting without changing codes/lyrics."""
    prompt = (
        "Você é um revisor de cifras de bateria customizadas. "
        "Mantenha EXATAMENTE todas as linhas de códigos de bateria (ex.: L-cbh, L-h, L-abh, L-cbha, L-cbrc, "
        "CR-cs, V-cs, V-ct1s, BQ-bpa1, S) sem colchetes na linha acima da letra e mantenha toda a letra original. "
        "Retorne apenas o conteúdo Markdown final, sem blocos de código extras.\n\n"
        f"{markdown_text}"
    )
    payload = {
        "model": "gemma",
        "messages": [
            {"role": "system", "content": "Retorne apenas a cifra em Markdown mantendo todos os códigos de bateria acima da letra."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 2048,
    }
    req = urllib.request.Request(
        llm_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            candidate = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            # Only accept LLM output if it preserved the drum codes and song header
            if candidate and len(DRUM_CODE_REGEX.findall(candidate)) >= len(DRUM_CODE_REGEX.findall(markdown_text)):
                return candidate + "\n"
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError):
        pass
    return markdown_text


def render_cifra(
    song_id: str,
    segments: list[dict],
    tempo_data: dict | list,
    drums_patterns: dict | list | None = None,
) -> str:
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

    timeline = _extract_timeline(drums_patterns, bars)

    if not segments:
        if timeline:
            first_code = timeline[0]["code"]
            lines.append(first_code)
        lines.append("_(Sem letra transcrita)_")
        return "\n".join(lines) + "\n"

    # Check if there is an instrumental intro before the first vocal segment
    first_vocal_start = float(segments[0].get("start", 0.0))
    intro_events = [ev for ev in timeline if float(ev["fim"]) <= first_vocal_start]
    if intro_events:
        intro_codes: list[str] = []
        for ev in intro_events:
            c = str(ev["code"]).strip("[]")
            if not intro_codes or intro_codes[-1] != c:
                intro_codes.append(c)
        if intro_codes:
            lines.append("  ".join(intro_codes))
            lines.append("(Introdução)")
            lines.append("")

    for seg in segments:
        sub_lines = _split_long_segment(seg)
        for sub in sub_lines:
            annot, lyric = build_annotation_line_for_lyric(sub, timeline)
            lines.append(annot)
            lines.append(lyric)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def make_cifra(
    letra_path: Path,
    compassos_path: Path,
    output_md: Path,
    params: dict | None = None,
    drums_patterns_path: Path | None = None,
) -> str:
    if not letra_path.is_file():
        raise FileNotFoundError(f"Lyrics file not found: {letra_path}")
    if not compassos_path.is_file():
        raise FileNotFoundError(f"Bars file not found: {compassos_path}")

    params = params or {}
    segments = json.loads(letra_path.read_text(encoding="utf-8"))
    tempo_data = json.loads(compassos_path.read_text(encoding="utf-8"))

    drums_patterns = None
    if drums_patterns_path and Path(drums_patterns_path).is_file():
        drums_patterns = json.loads(Path(drums_patterns_path).read_text(encoding="utf-8"))
    else:
        # Also check sibling drums_patterns.json in work/<id>/ automatically
        sibling = compassos_path.parent / "drums_patterns.json"
        if sibling.is_file():
            drums_patterns = json.loads(sibling.read_text(encoding="utf-8"))

    song_id = params.get("song_id")
    if not song_id:
        if output_md.stem.endswith("-cifra"):
            song_id = output_md.stem[:-6]
        else:
            song_id = output_md.parent.name or letra_path.parent.name

    content = render_cifra(song_id, segments, tempo_data, drums_patterns=drums_patterns)

    if params.get("use_llm", False):
        llm_url = params.get("llm_url", "http://localhost:11435/v1/chat/completions")
        content = review_with_gemma(content, llm_url=llm_url)

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(content, encoding="utf-8")
    return content


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--inputs",
        nargs="+",
        required=True,
        help="Inputs: <letra.json> <compassos.json> [<drums_patterns.json>]",
    )
    ap.add_argument("--outputs", nargs="+", required=True, help="Output: <<id>-cifra.md>")
    ap.add_argument("--params", default="{}", help="JSON parameters")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if len(args.inputs) < 2:
        sys.exit("make_cifra requires at least 2 inputs: <letra.json> <compassos.json> [<drums_patterns.json>]")
    params = json.loads(args.params or "{}")
    drums_path = Path(args.inputs[2]) if len(args.inputs) >= 3 else None
    make_cifra(
        Path(args.inputs[0]),
        Path(args.inputs[1]),
        Path(args.outputs[0]),
        params=params,
        drums_patterns_path=drums_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
