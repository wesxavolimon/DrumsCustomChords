#!/usr/bin/env python
"""Unit tests for DrumsCustomChords (Cifra de Bateria Customizada).

Validates:
1. Configuration files (`config/audio.json`, `config/pipeline.json`, `config/dicionario.yaml`)
2. Preflight validation on the configured MP3 (`run.preflight`)
3. Workflow step scripts (`separate_vocals`, `transcribe`, `tempo_compasso`, `detect_drums`, `classify_drums`, `make_cifra`)
4. Verification that the generated `<id>-cifra.md` file is created AND contains the custom drum code annotations (`L-cbh`, `BQ-bpa1`, `S`, `V-cs`, etc.) above the lyric lines
5. End-to-end orchestrator execution (`run.py` --dry-run) and validation of the real generated output file in `out/<id>/<id>-cifra.md` when present.

Run with:
    python -m unittest discover -s tests -v
"""
import json
import math
import re
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
WORKFLOWS = SRC / "workflows"
for p in (str(SRC), str(WORKFLOWS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import run as orchestrator  # noqa: E402
import separate_vocals  # noqa: E402
import transcribe  # noqa: E402
import tempo_compasso  # noqa: E402
import detect_drums  # noqa: E402
import classify_drums  # noqa: E402
import make_cifra  # noqa: E402


class TestConfigAndPreflight(unittest.TestCase):
    """Tests that config/audio.json, config/pipeline.json, and config/dicionario.yaml are valid."""

    def test_audio_json_points_to_existing_mp3(self):
        self.assertTrue(orchestrator.AUDIO_FILE.is_file(), f"Missing {orchestrator.AUDIO_FILE}")
        audio = orchestrator.load_json(orchestrator.AUDIO_FILE)
        self.assertIsInstance(audio, dict)
        self.assertIn("dir", audio)
        mp3_path = Path(audio["dir"])
        if not mp3_path.is_absolute():
            mp3_path = ROOT / mp3_path
        mp3_path = mp3_path.resolve()
        self.assertTrue(mp3_path.is_file(), f"Configured MP3 does not exist: {mp3_path}")
        self.assertGreater(mp3_path.stat().st_size, 0, "Configured MP3 is empty")

    def test_dicionario_yaml_has_custom_drum_codes(self):
        dict_cfg = classify_drums.load_dictionary()
        self.assertIsInstance(dict_cfg, dict)
        codes = {c["code"] for c in dict_cfg.get("codes", [])}
        for expected in ("S", "L-h", "L-abh", "L-cbh", "L-cbha", "L-cbrc", "CR-cs", "V-cs", "V-ct1s", "BQ-bpa1"):
            self.assertIn(expected, codes, f"Missing drum code {expected} in config/dicionario.yaml")

    def test_pipeline_json_and_preflight_pass(self):
        pipeline = orchestrator.load_json(orchestrator.PIPELINE_FILE)
        self.assertIsInstance(pipeline, dict)
        self.assertEqual(pipeline.get("name"), "cifra-bateria-customizada")
        step_names = [s["name"] for s in pipeline.get("steps", [])]
        self.assertEqual(
            step_names,
            [
                "separate_vocals",
                "transcribe",
                "tempo_compasso",
                "detect_drums",
                "classify_drums",
                "make_cifra",
            ],
        )

        # Verify output filename pattern in pipeline.json is {out}/{id}-cifra.md
        make_cifra_step = next(s for s in pipeline["steps"] if s["name"] == "make_cifra")
        self.assertEqual(make_cifra_step["outputs"], ["{out}/{id}-cifra.md"])

        audio = orchestrator.load_json(orchestrator.AUDIO_FILE)
        mp3_path = Path(audio["dir"])
        if not mp3_path.is_absolute():
            mp3_path = ROOT / mp3_path
        errors = orchestrator.preflight(pipeline, mp3_path.resolve())
        self.assertEqual(errors, [], f"Preflight errors: {errors}")


class TestWorkflowScripts(unittest.TestCase):
    """Unit tests for each workflow step in src/workflows/."""

    def test_separate_vocals_extracts_vocals_drums_and_no_drums(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_mp3 = tmp_path / "song.mp3"
            in_mp3.write_bytes(b"ID3-fake-mp3-content")
            out_vocals = tmp_path / "work" / "vocals.wav"
            out_drums = tmp_path / "work" / "drums.wav"
            out_no_drums = tmp_path / "work" / "no_drums.wav"

            def fake_run(cmd, capture_output, text):
                demucs_out = tmp_path / "htdemucs" / "song"
                if "-o" in cmd:
                    out_arg = cmd[cmd.index("-o") + 1]
                    if out_arg != "/out":
                        demucs_out = Path(out_arg) / "htdemucs" / "song"
                    else:
                        for i, c in enumerate(cmd):
                            if c == "-v" and i + 1 < len(cmd) and cmd[i + 1].endswith(":/out"):
                                host_out = cmd[i + 1][:-5]
                                demucs_out = Path(host_out) / "htdemucs" / "song"
                demucs_out.mkdir(parents=True, exist_ok=True)
                (demucs_out / "vocals.wav").write_bytes(b"RIFF-fake-vocals")
                (demucs_out / "drums.wav").write_bytes(b"RIFF-fake-drums")
                (demucs_out / "no_drums.wav").write_bytes(b"RIFF-fake-no-drums")
                return mock.Mock(returncode=0, stdout="ok", stderr="")

            with mock.patch("separate_vocals.subprocess.run", side_effect=fake_run):
                res = separate_vocals.separate_vocals(
                    in_mp3, out_vocals, {"model": "htdemucs"}, drums_wav=out_drums, no_drums_wav=out_no_drums
                )
                self.assertEqual(res, out_vocals)
                self.assertTrue(out_vocals.is_file())
                self.assertTrue(out_drums.is_file())
                self.assertTrue(out_no_drums.is_file())

    def test_transcribe_writes_timestamped_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_wav = tmp_path / "vocals.wav"
            in_wav.write_bytes(b"RIFF-fake-wav")
            out_json = tmp_path / "letra.json"

            fake_segments = [
                {"start": 0.5, "end": 3.2, "text": "Recebi um novo coração do Pai"},
                {"start": 3.5, "end": 7.8, "text": "Coração regenerado, coração transformado"},
            ]
            with mock.patch(
                "transcribe._transcribe_openai_whisper", return_value=fake_segments
            ):
                res = transcribe.transcribe_audio(
                    in_wav, out_json, {"backend": "whisper", "model": "large-v3", "lang": "pt"}
                )
                self.assertEqual(len(res), 2)
                self.assertTrue(out_json.is_file())
                saved = json.loads(out_json.read_text(encoding="utf-8"))
                self.assertEqual(saved[0]["text"], "Recebi um novo coração do Pai")

    def test_tempo_compasso_builds_4_4_bars(self):
        beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        bars = tempo_compasso.build_bars_from_beats(beats, duration=4.0, beats_per_bar=4)
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0], {"compasso": 1, "inicio": 0.0, "fim": 2.0})
        self.assertEqual(bars[1], {"compasso": 2, "inicio": 2.0, "fim": 4.0})

    def test_detect_and_classify_drums_on_synthetic_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            drums_wav = tmp_path / "drums.wav"
            compassos_json = tmp_path / "compassos.json"
            events_json = tmp_path / "drums_events.json"
            patterns_json = tmp_path / "drums_patterns.json"

            # Create a 4-second synthetic WAV (sr=22050):
            # Bar 1 (0.0-2.0s): Kick (60Hz) + Snare (800Hz) + Hi-Hat (7000Hz) -> L-cbh
            # Bar 2 (2.0-4.0s): Silence -> S
            sr = 22050
            t = np.linspace(0, 4.0, sr * 4, endpoint=False)
            sig = np.zeros_like(t)
            # Step 1 (0.0 - 0.04s): Kick 60Hz + Closed Hi-hat 7000Hz (short decay)
            s1 = (t >= 0.0) & (t < 0.04)
            sig[s1] += 0.6 * np.sin(2 * math.pi * 60 * t[s1]) + 0.3 * np.sin(2 * math.pi * 7000 * t[s1])
            # Step 5 (0.5 - 0.54s): Snare 600Hz + Closed Hi-hat 7000Hz (short decay)
            s5 = (t >= 0.5) & (t < 0.54)
            sig[s5] += 0.6 * np.sin(2 * math.pi * 600 * t[s5]) + 0.3 * np.sin(2 * math.pi * 7000 * t[s5])

            pcm = np.clip(sig * 32767, -32768, 32767).astype(np.int16)
            with wave.open(str(drums_wav), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm.tobytes())

            compassos_json.write_text(
                json.dumps({
                    "bpm": 120.0,
                    "formula": "4/4",
                    "compassos": [
                        {"compasso": 1, "inicio": 0.0, "fim": 2.0},
                        {"compasso": 2, "inicio": 2.0, "fim": 4.0},
                    ],
                }),
                encoding="utf-8",
            )

            ev_data = detect_drums.detect_drums(drums_wav, compassos_json, events_json)
            self.assertTrue(events_json.is_file())
            self.assertEqual(len(ev_data["compassos"]), 2)
            self.assertGreater(len(ev_data["compassos"][0]["events"]), 0)
            self.assertEqual(len(ev_data["compassos"][1]["events"]), 0)

            pat_data = classify_drums.classify_drums(events_json, compassos_json, patterns_json)
            self.assertTrue(patterns_json.is_file())
            self.assertEqual(pat_data["compassos"][0]["code"], "L-cbh")
            self.assertEqual(pat_data["compassos"][1]["code"], "S")

    def test_make_cifra_creates_custom_drum_annotations_above_lyrics(self):
        """Verifies that <id>-cifra.md is created and contains custom drum annotations above lyric lines."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            song_id = "3 - Corpo e família - IPBJA"
            letra_file = tmp_path / "letra.json"
            compassos_file = tmp_path / "compassos.json"
            patterns_file = tmp_path / "drums_patterns.json"
            out_md = tmp_path / song_id / f"{song_id}-cifra.md"

            letra_file.write_text(
                json.dumps(
                    [
                        {"start": 0.0, "end": 2.0, "text": "Eu tentei fugir de tudo"},
                        {"start": 2.0, "end": 4.0, "text": "Mas o tempo... (silêncio: só a voz) ...não parou!"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            compassos_file.write_text(
                json.dumps(
                    {
                        "bpm": 120.0,
                        "formula": "4/4",
                        "beats_per_bar": 4,
                        "duration": 4.0,
                        "compassos": [
                            {"compasso": 1, "inicio": 0.0, "fim": 2.0},
                            {"compasso": 2, "inicio": 2.0, "fim": 4.0},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            patterns_file.write_text(
                json.dumps(
                    {
                        "timeline": [
                            {"compasso": 1, "inicio": 0.0, "fim": 2.0, "code": "L-cbh"},
                            {"compasso": 2, "inicio": 2.3, "fim": 2.8, "code": "BQ-bpa1"},
                            {"compasso": 2, "inicio": 2.8, "fim": 3.5, "code": "S"},
                            {"compasso": 2, "inicio": 3.5, "fim": 4.0, "code": "V-cs"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            md = make_cifra.make_cifra(
                letra_file,
                compassos_file,
                out_md,
                params={"use_llm": False},
                drums_patterns_path=patterns_file,
            )

            # 1. File must be created with the exact `<id>-cifra.md` name
            self.assertTrue(out_md.is_file(), f"Expected output file not created: {out_md}")
            self.assertEqual(out_md.name, f"{song_id}-cifra.md")

            # 2. Check header and drum annotations above the lyric lines
            self.assertIn(f"# {song_id} | BPM 120 | 4/4", md)
            lines = [ln for ln in md.splitlines() if ln.strip()]

            # Find the line "Eu tentei fugir de tudo" and verify the line immediately above it has "L-cbh"
            idx_line1 = lines.index("Eu tentei fugir de tudo")
            self.assertGreater(idx_line1, 0)
            annot_line1 = lines[idx_line1 - 1]
            self.assertIn("L-cbh", annot_line1)
            self.assertNotIn("[L-cbh]", annot_line1)

            # Find the second lyric line and verify the line above it has BQ-bpa1, S, V-cs positioned in order
            idx_line2 = lines.index("Mas o tempo... (silêncio: só a voz) ...não parou!")
            annot_line2 = lines[idx_line2 - 1]
            self.assertIn("BQ-bpa1", annot_line2)
            self.assertIn("S", annot_line2)
            self.assertIn("V-cs", annot_line2)
            self.assertLess(annot_line2.index("BQ-bpa1"), annot_line2.index("S"))
            self.assertLess(annot_line2.index("S"), annot_line2.index("V-cs"))


class TestOrchestratorAndGeneratedOutput(unittest.TestCase):
    """Tests run.py --dry-run and checks the generated out/<id>/<id>-cifra.md annotations."""

    def test_dry_run_succeeds_with_configured_mp3(self):
        with mock.patch.object(sys, "argv", ["run.py", "--dry-run"]):
            code = orchestrator.main()
        self.assertEqual(code, 0)

    def test_real_generated_cifra_file_has_annotations_when_present(self):
        audio = orchestrator.load_json(orchestrator.AUDIO_FILE)
        song_id = Path(audio["dir"]).stem
        expected_cifra = ROOT / "out" / song_id / f"{song_id}-cifra.md"
        if expected_cifra.is_file():
            content = expected_cifra.read_text(encoding="utf-8")
            matches = make_cifra.DRUM_CODE_REGEX.findall(content)
            self.assertGreater(
                len(matches),
                0,
                f"Expected drum code annotations in {expected_cifra}, found none.",
            )
            # Check that every non-header, non-annotation lyric line is preceded by an annotation line
            raw_lines = [ln for ln in content.splitlines() if ln.strip() and not ln.startswith("#")]
            self.assertGreaterEqual(len(raw_lines), 2)
            # Every even-indexed line in raw_lines (0, 2, 4...) is an annotation line with valid drum codes
            for i in range(0, len(raw_lines) - 1, 2):
                annot = raw_lines[i]
                self.assertIsNotNone(
                    make_cifra.DRUM_CODE_REGEX.search(annot),
                    f"Line {i} above lyric is missing a valid drum code annotation: '{annot}'",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
