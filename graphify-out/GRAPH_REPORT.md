# Graph Report - .  (2026-11-12)

## Corpus Check
- Corpus is ~2,090 words - fits in a single context window. You may not need a graph.

## Summary
- 29 nodes · 42 edges · 5 communities (4 shown, 1 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- MVP1 OpenSpec Change
- Orchestrator Core
- Project Phases and Premises
- Step Execution Helpers
- RTK Rules

## God Nodes (most connected - your core abstractions)
1. `main()` - 10 edges
2. `MVP1 proposal` - 7 edges
3. `run_step()` - 5 edges
4. `DrumsCustomChords project` - 5 edges
5. `Capability: cifra-output` - 4 edges
6. `now()` - 3 edges
7. `nonempty()` - 3 edges
8. `MVP1 design decisions (cache per step, Demucs, faster-whisper, librosa)` - 3 edges
9. `Capability: lyrics-transcription` - 3 edges
10. `sha()` - 2 edges

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

## Communities (5 total, 1 thin omitted)

### Community 0 - "MVP1 OpenSpec Change"
Cohesion: 0.33
Nodes (9): cifra.md format, MVP1 design decisions (cache per step, Demucs, faster-whisper, librosa), MVP1 risks (Whisper errors, non-4/4 beat tracking), MVP1 proposal, Capability: cifra-output, Capability: lyrics-transcription, Capability: tempo-bars, Capability: vocal-separation (+1 more)

### Community 1 - "Orchestrator Core"
Cohesion: 0.46
Nodes (7): file_sig(), load_json(), main(), parse_overrides(), preflight(), save_json_atomic(), sha()

### Community 2 - "Project Phases and Premises"
Cohesion: 0.29
Nodes (7): Git/OpenSpec workflow (feature/mvp1, no PRs), MVP 1 deliverable, Phase 1 - Drum map, Phase 2 - Chord sheet and lyrics aligned to map, Phase 3 - PDF output, OCR (TBD), DrumsCustomChords project, Technical premises (local Python, cache, sequential VRAM, timing from code not LLM)

### Community 3 - "Step Execution Helpers"
Cohesion: 0.50
Nodes (4): nonempty(), now(), run_step(), tmp_path()

## Knowledge Gaps
- **7 isolated node(s):** `Technical premises (local Python, cache, sequential VRAM, timing from code not LLM)`, `Phase 1 - Drum map`, `Phase 3 - PDF output, OCR (TBD)`, `Git/OpenSpec workflow (feature/mvp1, no PRs)`, `MVP1 risks (Whisper errors, non-4/4 beat tracking)` (+2 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MVP1 proposal` connect `MVP1 OpenSpec Change` to `Project Phases and Premises`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Why does `MVP 1 deliverable` connect `Project Phases and Premises` to `MVP1 OpenSpec Change`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **What connects `Technical premises (local Python, cache, sequential VRAM, timing from code not LLM)`, `Phase 1 - Drum map`, `Phase 3 - PDF output, OCR (TBD)` to the rest of the system?**
  _7 weakly-connected nodes found - possible documentation gaps or missing edges._