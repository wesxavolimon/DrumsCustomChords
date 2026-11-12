#!/usr/bin/env python
"""Orchestrator for DrumsCustomChords.

Reads pipeline.json, runs each step as a subprocess, one at a time (VRAM),
and keeps per-song state in work/<id>/manifest.json.

Step script contract:
    python <script> --inputs <file>... --outputs <file>... --params '<json>'
Scripts must write to the given --outputs paths (the orchestrator passes
temporary paths and renames them only after the step succeeds).

Usage:
    python src/run.py [--force] [--from STEP] [--only STEP] [--dry-run]
                  [--param step.key=value ...]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # project root (parent of src/)
PIPELINE_FILE = ROOT / "config" / "pipeline.json"
AUDIO_FILE = ROOT / "config" / "audio.json"  # {"dir": "path/to/song.mp3"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def file_sig(path):
    st = Path(path).stat()
    return f"{path.name}:{st.st_size}:{int(st.st_mtime)}"


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def tmp_path(p):
    p = Path(p)
    return p.with_name(f"{p.stem}.tmp{p.suffix}")


def nonempty(p):
    p = Path(p)
    return p.exists() and (p.stat().st_size > 0 if p.is_file() else any(p.iterdir()))


def parse_overrides(items):
    out = {}
    for item in items or []:
        try:
            key, value = item.split("=", 1)
            step, param = key.split(".", 1)
        except ValueError:
            sys.exit(f"Invalid --param '{item}', expected step.key=value")
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
        out.setdefault(step, {})[param] = value
    return out


def preflight(pipeline, input_path):
    errors = []
    if not input_path.is_file():
        errors.append(f"input file not found: {input_path}")
    for b in pipeline.get("preflight", {}).get("binaries", []):
        if shutil.which(b) is None:
            errors.append(f"binary not found on PATH: {b}")
    for step in pipeline["steps"]:
        if not (ROOT / step["script"]).is_file():
            errors.append(f"script not found for step '{step['name']}': {step['script']}")
    names = [s["name"] for s in pipeline["steps"]]
    if len(names) != len(set(names)):
        errors.append("duplicate step names in pipeline.json")
    return errors


def run_step(step, ctx, params, inputs, outputs, log_file, timeout=None):
    tmp_outputs = [tmp_path(o) for o in outputs]
    for t in tmp_outputs:
        if t.is_dir():
            shutil.rmtree(t)
        elif t.exists():
            t.unlink()
        t.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(ROOT / step["script"]),
           "--inputs", *map(str, inputs),
           "--outputs", *map(str, tmp_outputs),
           "--params", json.dumps(params)]
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as lf:
        lf.write(f"\n=== {now()} :: {' '.join(cmd)}\n")
        lf.flush()
        proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT,
                              cwd=ROOT, timeout=timeout)
    if proc.returncode != 0:
        return False, f"exit code {proc.returncode}"
    for t in tmp_outputs:
        if not nonempty(t):
            return False, f"missing or empty output: {t.name}"
    for t, o in zip(tmp_outputs, outputs):
        o = Path(o)
        o.parent.mkdir(parents=True, exist_ok=True)
        if o.is_dir():
            shutil.rmtree(o)
        os.replace(t, o)
    return True, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="ignore cache, rerun all steps")
    ap.add_argument("--from", dest="from_step", help="rerun this step and all following")
    ap.add_argument("--only", help="run only this step")
    ap.add_argument("--dry-run", action="store_true", help="show the plan without running")
    ap.add_argument("--param", action="append", help="override: step.key=value")
    args = ap.parse_args()

    pipeline = load_json(PIPELINE_FILE)
    if pipeline is None:
        sys.exit(f"cannot read {PIPELINE_FILE}")
    steps = pipeline["steps"]
    names = [s["name"] for s in steps]
    for opt in (args.from_step, args.only):
        if opt and opt not in names:
            sys.exit(f"unknown step '{opt}'. Available: {', '.join(names)}")

    audio = load_json(AUDIO_FILE)
    if not audio or not audio.get("dir"):
        sys.exit(f"cannot read 'dir' from {AUDIO_FILE}")
    input_path = Path(audio["dir"])
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    input_path = input_path.resolve()
    errors = preflight(pipeline, input_path)
    if errors:
        print("Preflight failed:")
        for e in errors:
            print(f"  - {e}")
        return 2

    song_id = input_path.stem
    fmt = {"id": song_id, "input": str(input_path)}
    paths = {k: (ROOT / v.format(**fmt)) for k, v in pipeline["paths"].items()}
    fmt.update(work=str(paths["work"]), out=str(paths["out"]))
    overrides = parse_overrides(args.param)

    manifest = load_json(paths["manifest"], {})
    manifest.update(id=song_id, input=str(input_path), pipeline=pipeline["name"])
    manifest.setdefault("steps", {})
    manifest["input_sig"] = file_sig(input_path)

    invalidate_rest = args.force
    prev_hash = manifest["input_sig"]
    failed = None

    for step in steps:
        name = step["name"]
        params = {**step.get("params", {}), **overrides.get(name, {})}
        inputs = [Path(i.format(**fmt)) for i in step["inputs"]]
        outputs = [Path(o.format(**fmt)) for o in step["outputs"]]
        step_hash = sha(prev_hash, step["script"], json.dumps(params, sort_keys=True))
        prev_hash = step_hash
        state = manifest["steps"].get(name, {})

        if args.from_step == name:
            invalidate_rest = True
        selected = args.only in (None, name)
        cached = (state.get("status") == "ok" and state.get("hash") == step_hash
                  and all(nonempty(o) for o in outputs))

        if not selected:
            print(f"[skip ] {name} (not selected)")
            continue
        if cached and not invalidate_rest:
            print(f"[cache] {name}")
            continue
        if args.dry_run:
            print(f"[plan ] {name} -> would run")
            continue

        missing = [str(i) for i in inputs if not nonempty(i)]
        if missing:
            msg = f"missing inputs: {', '.join(missing)}"
            print(f"[fail ] {name}: {msg}")
            manifest["steps"][name] = {"status": "failed", "error": msg, "finished": now()}
            failed = name
            break

        print(f"[run  ] {name} ...", flush=True)
        # a changed step invalidates every following step
        invalidate_rest = True
        attempts = step.get("retries", 0) + 1
        ok, err, started = False, None, time.time()
        manifest["steps"][name] = {"status": "running", "started": now(), "hash": step_hash}
        save_json_atomic(paths["manifest"], manifest)
        for attempt in range(1, attempts + 1):
            try:
                ok, err = run_step(step, fmt, params, inputs, outputs,
                                   paths["logs"] / f"{name}.log",
                                   timeout=step.get("timeout"))
            except subprocess.TimeoutExpired:
                ok, err = False, "timeout"
            if ok:
                break
            print(f"        attempt {attempt}/{attempts} failed: {err}")
        duration = round(time.time() - started, 1)
        if ok:
            manifest["steps"][name] = {
                "status": "ok", "hash": step_hash, "params": params,
                "inputs": [str(i) for i in inputs], "outputs": [str(o) for o in outputs],
                "duration_s": duration, "finished": now(), "attempts": attempt,
            }
            print(f"[ ok  ] {name} ({duration}s)")
            save_json_atomic(paths["manifest"], manifest)
        else:
            manifest["steps"][name] = {
                "status": "failed", "hash": step_hash, "params": params,
                "error": err, "duration_s": duration, "finished": now(),
                "log": str(paths["logs"] / f"{name}.log"),
            }
            print(f"[fail ] {name}: {err} (see {paths['logs'] / (name + '.log')})")
            failed = name
            break

    if not args.dry_run:
        manifest["updated"] = now()
        manifest["status"] = "failed" if failed else "ok"
        save_json_atomic(paths["manifest"], manifest)
    if failed:
        print(f"Stopped at '{failed}'. Fix and rerun; finished steps are cached.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

