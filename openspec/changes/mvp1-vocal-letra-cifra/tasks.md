## 1. Setup
- [x] 1.1 Iniciar repo e criar branch `feature/mvp1`
- [x] 1.2 `requirements.txt`, `.gitignore` e `.graphifyignore`
- [x] 1.3 Orquestrador `src/run.py` + `config/pipeline.json` + `config/audio.json`

## 2. Vocal
- [x] 2.1 `src/workflows/separate_vocals.py` (Demucs two-stems)
- [ ] 2.2 Gerar `work/<id>/vocals.wav` com cache

## 3. Letra
- [x] 3.1 `src/workflows/transcribe.py` (faster-whisper / whisper, `--lang`)
- [ ] 3.2 Gerar `work/<id>/letra.json` com segmentos

## 4. Tempo-compasso
- [x] 4.1 `src/workflows/tempo_compasso.py` (BPM, downbeats, 4/4)
- [ ] 4.2 Gerar `work/<id>/compassos.json`

## 5. Cifra e Testes
- [x] 5.1 `src/workflows/make_cifra.py` (letra + compassos)
- [ ] 5.2 Gerar `out/<id>/cifra.md`
- [x] 5.3 Criar teste unitário em `tests/test_mvp1.py` validando config, MP3 e workflows, e commitar em `feature/mvp1`
