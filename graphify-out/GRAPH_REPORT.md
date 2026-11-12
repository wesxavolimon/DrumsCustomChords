# Graph Report - DrumsCustomChords  (2026-11-12)

## Corpus Check
- 26 files · ~13,081 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 207 nodes · 252 edges · 27 communities (20 shown, 7 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `84f134b3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

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
- ADDED Requirements
- Requirements
- AGENTS.md — DrumsCustomChords
- ADDED Requirements
- proposal.md
- tasks.md
- proposal.md
- tasks.md
- design.md
- design.md
- MVP 1 deliverable
- Phase 1 - Drum map
- Phase 2 - Chord sheet and lyrics aligned to map
- Phase 3 - PDF output, OCR (TBD)
- DrumsCustomChords project
- Technical premises (local Python, cache, sequential VRAM, timing from code not LLM)

## God Nodes (most connected - your core abstractions)
1. `Pipeline Música → Mapa de Bateria (MVP)` - 12 edges
2. `main()` - 10 edges
3. `AGENTS.md — DrumsCustomChords` - 9 edges
4. `Fase 2: Cifra e letra alinhadas ao mapa de bateria` - 9 edges
5. `separate_vocals()` - 7 edges
6. `TestWorkflowScripts` - 7 edges
7. `detect_drums()` - 6 edges
8. `detect_tempo_and_bars()` - 6 edges
9. `transcribe_audio()` - 6 edges
10. `ADDED Requirements` - 6 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (27 total, 7 thin omitted)

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
Cohesion: 0.11
Nodes (7): Verifies that <id>-cifra.md is created and contains custom drum annotations abov, Tests run.py --dry-run and checks the generated out/<id>/<id>-cifra.md annotatio, Tests that config/audio.json, config/pipeline.json, and config/dicionario.yaml a, Unit tests for each workflow step in src/workflows/., TestConfigAndPreflight, TestOrchestratorAndGeneratedOutput, TestWorkflowScripts

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
Cohesion: 0.10
Nodes (20): Detalhes, Dicionário (regras iniciais), Etapas, Etapas, Exemplo Cifra, Fase 2: Cifra e letra alinhadas ao mapa de bateria, Fluxo, Fluxo (+12 more)

### Community 10 - "Community 10"
Cohesion: 0.15
Nodes (12): Cifra de Bateria Customizada Specification, Requirement: Classificação por dicionário de bateria, Requirement: Detecção e quantização de golpes de bateria, Requirement: Geração da cifra de bateria customizada com revisão Gemma, Requirement: Separação de bateria e vocal, Requirement: Teste unitário de validação das anotações no arquivo final, Requirements, Scenario: Arquivo final com nome da música + `-cifra.md` (+4 more)

### Community 11 - "ADDED Requirements"
Cohesion: 0.17
Nodes (11): ADDED Requirements, Requirement: Classificação por dicionário de bateria, Requirement: Detecção e quantização de golpes de bateria, Requirement: Geração da cifra de bateria customizada com revisão Gemma, Requirement: Separação de bateria e vocal, Requirement: Teste unitário de validação das anotações no arquivo final, Scenario: Arquivo final com nome da música + `-cifra.md`, Scenario: Extração de stems com cache (+3 more)

### Community 12 - "Requirements"
Cohesion: 0.18
Nodes (10): MVP 1 Specification, Requirement: Primeiro arquivo de cifra, Requirement: Separação de vocal, Requirement: Tempo-compasso, Requirement: Transcrição da letra, Requirements, Scenario: Idioma informado, Scenario: Letra e compassos disponíveis (+2 more)

### Community 13 - "AGENTS.md — DrumsCustomChords"
Cohesion: 0.20
Nodes (9): AGENTS.md — DrumsCustomChords, Como executar o orquestrador (`src/run.py`), Descrição, Dicionário (`config/dicionario.yaml`), Entregável atual: Cifra de Bateria Customizada (`cifra-bateria-customizada`), Estrutura do projeto, Fluxo de trabalho (Git / OpenSpec), Premissas técnicas (+1 more)

### Community 14 - "ADDED Requirements"
Cohesion: 0.20
Nodes (9): ADDED Requirements, Requirement: Primeiro arquivo de cifra, Requirement: Separação de vocal, Requirement: Tempo-compasso, Requirement: Transcrição da letra, Scenario: Idioma informado, Scenario: Letra e compassos disponíveis, Scenario: MP3 válido (+1 more)

### Community 15 - "proposal.md"
Cohesion: 0.29
Nodes (6): Capabilities, Impact, Modified Capabilities, New Capabilities, What Changes, Why

### Community 16 - "tasks.md"
Cohesion: 0.33
Nodes (5): 1. Configuração e Dicionário, 2. Separação de Stems e Transcrição com Word Timestamps, 3. Detecção, Quantização e Classificação de Bateria, 4. Montagem da Cifra Customizada e Integração Gemma, 5. Testes e Documentação

### Community 17 - "proposal.md"
Cohesion: 0.33
Nodes (5): Capabilities, Impact, New Capabilities, What Changes, Why

### Community 18 - "tasks.md"
Cohesion: 0.33
Nodes (5): 1. Setup, 2. Vocal, 3. Letra, 4. Tempo-compasso, 5. Cifra e Testes

### Community 19 - "design.md"
Cohesion: 0.50
Nodes (3): Decisões Arquiteturais, Exemplo de Saída (`out/<id>/<id>-cifra.md`), Riscos e Mitigações

### Community 20 - "design.md"
Cohesion: 0.50
Nodes (3): Decisões, Formato de `cifra.md`, Riscos

## Knowledge Gaps
- **76 isolated node(s):** `Descrição`, `Premissas técnicas`, `Fluxo de trabalho (Git / OpenSpec)`, `Entregável atual: Cifra de Bateria Customizada (`cifra-bateria-customizada`)`, `Dicionário (`config/dicionario.yaml`)` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Classifies a slice of step events into one of the custom drum codes.`, `Classifies a bar and also extracts intra-bar sub-segments if distinct patterns o`, `Loads audio file into a mono float32 numpy array in [-1, 1].` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 5` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Should `Community 9` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._