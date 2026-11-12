#!/usr/bin/env python
"""Unit tests for DrumsCustomChords MVP 1.

Validates:
1. Configuration files (`config/audio.json` points to an existing MP3, `config/pipeline.json` is valid)
2. Preflight validation on the configured MP3 (`run.preflight`)
3. Workflow step scripts and their core functions (`separate_vocals`, `transcribe`, `tempo_compasso`, `make_cifra`)
4. End-to-end orchestrator execution (`run.py` --dry-run on the configured MP3, plus cache & failure handling)

Run with:
    python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
import make_cifra  # noqa: E402


class TestConfigAndPreflight(unittest.TestCase):
    """Tests that config/audio.json and config/pipeline.json are valid and point to existing files."""

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

    def test_pipeline_json_and_preflight_pass(self):
        pipeline = orchestrator.load_json(orchestrator.PIPELINE_FILE)
        self.assertIsInstance(pipeline, dict)
        self.assertEqual(pipeline.get("name"), "mvp1")
        step_names = [s["name"] for s in pipeline.get("steps", [])]
        self.assertEqual(
            step_names,
            ["separate_vocals", "transcribe", "tempo_compasso", "make_cifra"],
        )

        audio = orchestrator.load_json(orchestrator.AUDIO_FILE)
        mp3_path = Path(audio["dir"])
        if not mp3_path.is_absolute():
            mp3_path = ROOT / mp3_path
        errors = orchestrator.preflight(pipeline, mp3_path.resolve())
        self.assertEqual(errors, [], f"Preflight errors: {errors}")


class TestWorkflowScripts(unittest.TestCase):
    """Unit tests for each of the 4 workflow steps in src/workflows/."""

    def test_separate_vocals_invokes_demucs_and_writes_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_mp3 = tmp_path / "song.mp3"
            in_mp3.write_bytes(b"ID3-fake-mp3-content")
            out_wav = tmp_path / "work" / "vocals.wav"

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
                (demucs_out / "vocals.wav").write_bytes(b"RIFF-fake-wav")
                return mock.Mock(returncode=0, stdout="ok", stderr="")

            with mock.patch("separate_vocals.subprocess.run", side_effect=fake_run) as m_run:
                res = separate_vocals.separate_vocals(in_mp3, out_wav, {"model": "htdemucs"})
                self.assertEqual(res, out_wav)
                self.assertTrue(out_wav.is_file())
                self.assertEqual(out_wav.read_bytes(), b"RIFF-fake-wav")
                called_cmd = m_run.call_args[0][0]
                self.assertIn("--two-stems", called_cmd)
                self.assertIn("vocals", called_cmd)

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
        # 8 beats at 120 BPM (0.5s per beat) -> 2 bars of 4/4 (0.0-2.0s and 2.0-4.0s)
        beats = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        bars = tempo_compasso.build_bars_from_beats(beats, duration=4.0, beats_per_bar=4)
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0], {"compasso": 1, "inicio": 0.0, "fim": 2.0})
        self.assertEqual(bars[1], {"compasso": 2, "inicio": 2.0, "fim": 4.0})

    def test_make_cifra_aligns_lyrics_to_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            letra_file = tmp_path / "letra.json"
            compassos_file = tmp_path / "compassos.json"
            out_md = tmp_path / "3 - Corpo e família - IPBJA" / "cifra.md"

            letra_file.write_text(
                json.dumps(
                    [
                        {"start": 0.2, "end": 1.8, "text": "Recebi um novo coração do Pai"},
                        {"start": 2.1, "end": 5.5, "text": "Coração regenerado, coração transformado"},
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
                        "duration": 6.0,
                        "compassos": [
                            {"compasso": 1, "inicio": 0.0, "fim": 2.0},
                            {"compasso": 2, "inicio": 2.0, "fim": 4.0},
                            {"compasso": 3, "inicio": 4.0, "fim": 6.0},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            md = make_cifra.make_cifra(letra_file, compassos_file, out_md)
            self.assertTrue(out_md.is_file())
            self.assertIn("# 3 - Corpo e família - IPBJA | BPM 120 | 4/4", md)
            self.assertIn("[Compasso 1]\nRecebi um novo coração do Pai", md)
            self.assertIn("[Compasso 2-3]\nCoração regenerado, coração transformado", md)


class TestOrchestratorDryRun(unittest.TestCase):
    """Tests run.py --dry-run with the real config/audio.json and config/pipeline.json."""

    def test_dry_run_succeeds_with_configured_mp3(self):
        with mock.patch.object(sys, "argv", ["run.py", "--dry-run"]):
            code = orchestrator.main()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

