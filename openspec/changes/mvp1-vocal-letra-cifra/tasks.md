## 1. Setup
- [x] 1.1 Iniciar repo e criar branch `feature/mvp1`
- [x] 1.2 `requirements.txt`, `.gitignore` e `.graphifyignore`
- [x] 1.3 Orquestrador `src/run.py` + `config/pipeline.json` + `config/audio.json`

## 2. Vocal
- [x] 2.1 `src/workflows/separate_vocals.py` (Demucs two-stems via container `wesley-demucs`)
- [x] 2.2 Gerar `work/<id>/vocals.wav` com cache

## 3. Letra
- [x] 3.1 `src/workflows/transcribe.py` (`wesley-whisper` com faster-whisper, `--lang`)
- [x] 3.2 Gerar `work/<id>/letra.json` com segmentos

## 4. Tempo-compasso
- [x] 4.1 `src/workflows/tempo_compasso.py` (`wesley-metronomo` com librosa: BPM, downbeats, 4/4)
- [x] 4.2 Gerar `work/<id>/compassos.json`

## 5. Cifra e Testes
- [x] 5.1 `src/workflows/make_cifra.py` (letra + compassos)
- [x] 5.2 Gerar `out/<id>/cifra.md`
- [x] 5.3 Testar com 1 música real (`3 - Corpo e família - IPBJA.mp3`), criar `tests/test_mvp1.py` e commitar em `feature/mvp1`
