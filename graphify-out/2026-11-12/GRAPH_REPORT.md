# Graph Report - .  (2026-11-12)

## Corpus Check
- Corpus is ~12,888 words - fits in a single context window. You may not need a graph.

## Summary
- 107 nodes · 173 edges · 11 communities (10 shown, 1 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Orchestrator & Workflows
- Drum Detection & Classification
- Cifra Formatting & Gemma
- OpenSpec & Project Docs
- Unit Tests & Validation
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10

## God Nodes (most connected - your core abstractions)
1. `main()` - 10 edges
2. `MVP1 proposal` - 7 edges
3. `separate_vocals()` - 7 edges
4. `TestWorkflowScripts` - 7 edges
5. `detect_drums()` - 6 edges
6. `detect_tempo_and_bars()` - 6 edges
7. `transcribe_audio()` - 6 edges
8. `run_step()` - 5 edges
9. `DrumsCustomChords project` - 5 edges
10. `classify_drums()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `MVP1 proposal` --implements--> `MVP 1 deliverable`  [EXTRACTED]
  openspec/changes/mvp1-vocal-letra-cifra/proposal.md → AGENTS.md
- `cifra.md format` --implements--> `Capability: cifra-output`  [INFERRED]
  openspec/changes/mvp1-vocal-letra-cifra/design.md → openspec/changes/mvp1-vocal-letra-cifra/specs/mvp1/spec.md
- `MVP1 proposal` --references--> `Capability: tempo-bars`  [EXTRACTED]
  openspec/changes/mvp1-vocal-letra-cifra/proposal.md → openspec/changes/mvp1-vocal-letra-cifra/specs/mvp1/spec.md
- `MVP1 proposal` --references--> `Capability: vocal-separation`  [EXTRACTED]
  openspec/changes/mvp1-vocal-letra-cifra/proposal.md → openspec/changes/mvp1-vocal-letra-cifra/specs/mvp1/spec.md
- `MVP1 task list` --implements--> `MVP1 proposal`  [EXTRACTED]
  openspec/changes/mvp1-vocal-letra-cifra/tasks.md → openspec/changes/mvp1-vocal-letra-cifra/proposal.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **MVP1 pipeline: vocals to lyrics and bars to cifra** — drumscustomchords_spec_vocal_separation, drumscustomchords_spec_lyrics_transcription, drumscustomchords_spec_tempo_bars, drumscustomchords_spec_cifra_output [EXTRACTED 1.00]

## Communities (11 total, 1 thin omitted)

### Community 0 - "Orchestrator & Workflows"
Cohesion: 0.16
Nodes (16): Git/OpenSpec workflow (feature/mvp1, no PRs), MVP 1 deliverable, Phase 1 - Drum map, Phase 2 - Chord sheet and lyrics aligned to map, Phase 3 - PDF output, OCR (TBD), DrumsCustomChords project, Technical premises (local Python, cache, sequential VRAM, timing from code not LLM), cifra.md format (+8 more)

### Community 1 - "Drum Detection & Classification"
Cohesion: 0.23
Nodes (12): build_annotation_line_for_lyric(), _extract_timeline(), main(), make_cifra(), parse_args(), Path, Builds `(annotation_line, lyric_text)` with drum codes positioned above the corr, Optionally asks local Gemma via llama.cpp (port 11435) to review formatting with (+4 more)

### Community 2 - "Cifra Formatting & Gemma"
Cohesion: 0.35
Nodes (11): file_sig(), load_json(), main(), nonempty(), now(), parse_overrides(), preflight(), run_step() (+3 more)

### Community 3 - "OpenSpec & Project Docs"
Cohesion: 0.35
Nodes (10): ndarray, analyze_bar_steps(), detect_drums(), load_audio_mono(), load_dictionary(), main(), parse_args(), Path (+2 more)

### Community 4 - "Unit Tests & Validation"
Cohesion: 0.36
Nodes (9): classify_bar(), classify_drums(), classify_events_slice(), load_dictionary(), main(), parse_args(), Path, Classifies a bar and also extracts intra-bar sub-segments if distinct patterns o (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (4): Tests run.py --dry-run and checks the generated out/<id>/<id>-cifra.md annotatio, Tests that config/audio.json, config/pipeline.json, and config/dicionario.yaml a, TestConfigAndPreflight, TestOrchestratorAndGeneratedOutput

### Community 6 - "Community 6"
Cohesion: 0.56
Nodes (8): _build_demucs_cmd(), _copy_or_convert(), _find_stem(), main(), _mix_stems_with_ffmpeg(), parse_args(), Path, separate_vocals()

### Community 7 - "Community 7"
Cohesion: 0.54
Nodes (7): _analyze_with_docker(), _analyze_with_local_librosa(), build_bars_from_beats(), detect_tempo_and_bars(), main(), parse_args(), Path

### Community 8 - "Community 8"
Cohesion: 0.57
Nodes (7): main(), parse_args(), Path, transcribe_audio(), _transcribe_faster_whisper(), _transcribe_openai_whisper(), _transcribe_with_docker()

### Community 9 - "Community 9"
Cohesion: 0.25
Nodes (3): Verifies that <id>-cifra.md is created and contains custom drum annotations abov, Unit tests for each workflow step in src/workflows/., TestWorkflowScripts

## Knowledge Gaps
- **7 isolated node(s):** `Technical premises (local Python, cache, sequential VRAM, timing from code not LLM)`, `Phase 1 - Drum map`, `Phase 3 - PDF output, OCR (TBD)`, `Git/OpenSpec workflow (feature/mvp1, no PRs)`, `MVP1 risks (Whisper errors, non-4/4 beat tracking)` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestWorkflowScripts` connect `Community 9` to `Community 5`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **What connects `Technical premises (local Python, cache, sequential VRAM, timing from code not LLM)`, `Phase 1 - Drum map`, `Phase 3 - PDF output, OCR (TBD)` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._