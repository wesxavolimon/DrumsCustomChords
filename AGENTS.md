# AGENTS.md — DrumsCustomChords

## Descrição

**DrumsCustomChords** gera, a partir de músicas (uso pessoal, ex.: playlist YouTube/YT Music ou MP3 local), material de estudo para bateria:

- MP3 sem bateria (backing track) e MP3 só com bateria
- Mapa de bateria em Markdown, por compasso, usando um dicionário de códigos (`[L-h]`, `[L-cbha]`, ...)
- Cifra com letra, acordes e códigos de bateria acima da letra, alinhados por compasso

## Premissas técnicas

- Python 3.12 local (CLI + scripts), Windows, GPU RTX 3060 (12 GB)
- Orquestrador (`src/run.py`) lê `config/pipeline.json` e `config/audio.json`, executando 1 etapa por vez (sequencial por causa de VRAM)
- Cada etapa é independente, com escrita atômica e cache em disco por música (`work/<id>/manifest.json`); saídas em `out/<id>/`
- Gemma-4-12B-it-qat-q4_0.gguf via llama.cpp (porta 11435), só texto (não ouve áudio) — entra nas fases seguintes
- VRAM: Demucs, Whisper e Gemma rodam em sequência, nunca juntos
- Tempos e compassos vêm sempre do código, nunca do LLM (evita alucinação)

## Fluxo de trabalho (Git / OpenSpec)

- Repositório: https://github.com/wesxavolimon/DrumsCustomChords.git
- **Sem pull requests.** Todo o trabalho é feito direto na branch `feature/mvp1`.
- Mudanças são especificadas com OpenSpec em `openspec/changes/`.
- Possui `.gitignore` e `.graphifyignore` configurados na raiz.

## Fases

### Fase 1 — Mapa de bateria (MVP completo)
Download (yt-dlp) → Demucs (drums / no_drums) → beat tracking (BPM, compassos) → detecção de golpes → quantização (16 passos) → agrupamento de compassos similares (L1, L2...) → dicionário YAML → Gemma para revisão → `mapa.md`. Orquestrador CLI com cache e retomada.

### Fase 2 — Cifra e letra alinhadas ao mapa
Vocal (Demucs) → Whisper (faster-whisper / whisper) → leitura do PDF da cifra (pdfplumber) → alinhamento de letra (rapidfuzz) → tempo→compasso → Gemma monta `cifra_bateria.md`. PDF é opcional; sem ele fica só o `mapa.md`.

### Fase 3 (a definir)
Saída em PDF, OCR de PDFs escaneados, mais formatos de cifra.

## Entregável atual: MVP 1 (versão simplificada, a partir de um MP3 local)

Change OpenSpec: `openspec/changes/mvp1-vocal-letra-cifra/`

1. Script que separa o vocal do MP3 (`src/workflows/separate_vocals.py` via container Docker `wesley-demucs` ou Demucs local `--two-stems vocals`)
2. Gera o áudio separado (`work/<id>/vocals.wav`)
3. Script do Whisper (`src/workflows/transcribe.py` via container Docker `wesley-whisper` com `faster-whisper`, ou fallback local)
4. Transcreve a letra com tempo (`work/<id>/letra.json`, segmentos `start`/`end`/`text`)
5. Script que gera tempo-compasso (`src/workflows/tempo_compasso.py` via container Docker `wesley-metronomo` ou Librosa local: BPM, beats e compassos 4/4 em `work/<id>/compassos.json`)
6. Gera o 1º arquivo de cifra (`src/workflows/make_cifra.py`, letra alinhada por compasso em `out/<id>/cifra.md`)

Ainda **fora** deste entregável: download de playlist, detecção de golpes de bateria, dicionário de códigos, Gemma, PDF de cifra.

## Como executar o orquestrador (`src/run.py`)

O arquivo de entrada é configurado em `config/audio.json`:

```json
{
  "dir": "C:\\Users\\User\\Documents\\TI\\Lavi\\docker-composes\\ytdlp\\downloads\\Culto 15-11-2026\\3 - Corpo e família - IPBJA.mp3"
}
```

Comandos:

```powershell
python src/run.py                                  # roda o pipeline (usa cache se disponível)
python src/run.py --dry-run                        # valida preflight e mostra o plano sem executar
python src/run.py --force                          # ignora cache e reexecuta todas as etapas
python src/run.py --from transcribe                # reexecuta a partir de 'transcribe' em diante
python src/run.py --only make_cifra                # executa apenas a etapa 'make_cifra'
python src/run.py --param transcribe.lang=en       # sobrescreve parâmetro em tempo de execução
```

## Testes (`tests/`)

Os testes unitários ficam em `tests/test_mvp1.py` e validam:
- Existência e validade de `config/audio.json` (incluindo verificação do MP3 configurado) e `config/pipeline.json`
- Preflight do orquestrador (`ffmpeg`, scripts de workflow e arquivo MP3)
- Cada um dos 4 scripts de `src/workflows/` (`separate_vocals`, `transcribe`, `tempo_compasso`, `make_cifra`)
- Execução `--dry-run` do orquestrador `src/run.py` sobre o MP3 configurado

Como rodar os testes:

```powershell
python -m unittest discover -s tests -v
```

## Estrutura do projeto

```
DrumsCustomChords/
  AGENTS.md
  requirements.txt
  .gitignore
  .graphifyignore
  config/
    audio.json              # caminho do MP3 de entrada {"dir": "..."}
    pipeline.json           # definição da sequência de etapas do pipeline
  openspec/
    changes/mvp1-vocal-letra-cifra/
  src/
    run.py                  # orquestrador (cache, manifest, escrita atômica, retries)
    workflows/
      separate_vocals.py    # Etapa 1-2: Demucs -> work/<id>/vocals.wav
      transcribe.py         # Etapa 3-4: Whisper -> work/<id>/letra.json
      tempo_compasso.py     # Etapa 5: Librosa -> work/<id>/compassos.json
      make_cifra.py         # Etapa 6: Letra + compassos -> out/<id>/cifra.md
  tests/
    test_mvp1.py            # Testes unitários e de preflight/dry-run com o MP3 configurado
  work/<id>/                # cache e manifest.json (ignorado no git)
  out/<id>/                 # saídas finais como cifra.md (ignorado no git)
```
