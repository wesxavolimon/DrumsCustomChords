## Why

A Fase 1 completa (mapa de bateria) é grande. Para validar a base, o MVP 1 entrega a parte mais simples: de um MP3, separar o vocal, transcrever a letra com tempo, calcular compassos e gerar o primeiro arquivo de cifra (letra por compasso).

## What Changes

- Script de separação de vocal (Demucs) → `vocals.wav`
- Script Whisper (faster-whisper) → letra com tempo
- Script de tempo-compasso (BPM e downbeats) → `compassos.json`
- Script que junta letra + compassos → `out/<id>/cifra.md`
- Projeto novo em `./DrumsCustomChords`, trabalho na branch `feature/mvp1`, sem PRs
- `AGENTS.md` com descrição, fases e este entregável

## Capabilities

### New Capabilities
- `vocal-separation`: separa o vocal de um MP3
- `lyrics-transcription`: transcreve a letra com tempo
- `tempo-bars`: detecta BPM e compassos
- `cifra-output`: gera o primeiro arquivo de cifra

## Impact

Código novo, Python local (Demucs, faster-whisper, librosa/madmom). Sem acordes nem códigos de bateria nesta etapa.

