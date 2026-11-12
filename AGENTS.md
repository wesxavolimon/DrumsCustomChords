# AGENTS.md — DrumsCustomChords

## Descrição

**DrumsCustomChords** gera, a partir de músicas (uso pessoal, ex.: playlist YouTube/YT Music ou MP3 local), material de estudo para bateria:

- MP3/WAV sem bateria (backing track `no_drums.wav`) e só com bateria (`drums.wav`) + vocal (`vocals.wav`)
- Detecção de golpes por banda de frequência, quantização em 16 passos por compasso e classificação em códigos customizados (`config/dicionario.yaml`)
- Cifra com letra e códigos de bateria customizados (`L-cbh`, `L-h`, `L-abh`, `L-cbha`, `L-cbrc`, `CR-cs`, `V-cs`, `V-ct1s`, `BQ-bpa1`, `S`) posicionados na linha acima da letra, em `out/<id>/<id>-cifra.md`

## Premissas técnicas

- Python 3.12 local (CLI + scripts), Windows, GPU RTX 3060 (12 GB)
- Orquestrador (`src/run.py`) lê `config/pipeline.json` e `config/audio.json`, executando 1 etapa por vez (sequencial por causa de VRAM)
- Cada etapa é independente, com escrita atômica e cache em disco por música (`work/<id>/manifest.json`); saídas em `out/<id>/<id>-cifra.md`
- Gemma-4-12B-it-qat-q4_0.gguf via llama.cpp (porta 11435), só texto (não ouve áudio), com fallback determinístico quando offline
- VRAM: Demucs, Whisper e Gemma rodam em sequência, nunca juntos
- Tempos, compassos e posições de códigos vêm sempre do código Python, nunca do LLM (evita alucinação)

## Fluxo de trabalho (Git / OpenSpec)

- Repositório: https://github.com/wesxavolimon/DrumsCustomChords.git
- **Sem pull requests.** Todo o trabalho é feito direto na branch `feature/mvp1`.
- Mudanças são especificadas com OpenSpec em `openspec/changes/` (histórico arquivado em `openspec/changes/archive/`).
- Possui `.gitignore` e `.graphifyignore` configurados na raiz.

## Entregável atual: Cifra de Bateria Customizada (`cifra-bateria-customizada`)

Change OpenSpec: `openspec/changes/cifra-bateria-customizada/`

1. Separação de stems (`src/workflows/separate_vocals.py` via container Docker `wesley-demucs` ou Demucs local) → `work/<id>/vocals.wav`, `work/<id>/drums.wav`, `work/<id>/no_drums.wav`
2. Transcrição da letra com tempo (`src/workflows/transcribe.py` via container Docker `wesley-whisper` com `faster-whisper`, ou fallback local) → `work/<id>/letra.json`
3. Tempo e compassos (`src/workflows/tempo_compasso.py` via container Docker `wesley-metronomo` ou Librosa local sobre `drums.wav`) → `work/<id>/compassos.json`
4. Detecção de golpes e quantização em 16 passos (`src/workflows/detect_drums.py`) → `work/<id>/drums_events.json`
5. Classificação pelo dicionário (`src/workflows/classify_drums.py` + `config/dicionario.yaml`) → `work/<id>/drums_patterns.json`
6. Geração da cifra com códigos de bateria customizados acima da letra + revisão opcional via Gemma (`src/workflows/make_cifra.py`) → `out/<id>/<id>-cifra.md`

## Dicionário (`config/dicionario.yaml`)

| Código | Regra de detecção |
| --- | --- |
| `S` | Nenhum evento no compasso |
| `L-h` | Só hi-hat fechado |
| `L-abh` | Aro + bumbo + hi-hat fechado |
| `L-cbh` | Caixa + bumbo + hi-hat fechado |
| `L-cbha` | Caixa + bumbo + hi-hat semi-aberto |
| `L-cbrc` | Caixa + bumbo + cúpula do ride |
| `CR-cs` | Crescendo de caixa + surdo em colcheias |
| `V-cs` | Virada caixa → surdo |
| `V-ct1s` | Virada caixa → tom 1 → surdo |
| `BQ-bpa1` | Bumbo + ataque 1 seco |

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
python src/run.py --from detect_drums              # reexecuta a partir de 'detect_drums' em diante
python src/run.py --only make_cifra                # executa apenas a etapa 'make_cifra'
python src/run.py --param transcribe.lang=en       # sobrescreve parâmetro em tempo de execução
```

## Testes (`tests/`)

Os testes unitários ficam em `tests/test_mvp1.py` e validam:
- Existência e validade de `config/audio.json`, `config/pipeline.json` e `config/dicionario.yaml`
- Preflight do orquestrador (`ffmpeg`, scripts de workflow e arquivo MP3)
- Cada um dos 6 scripts de `src/workflows/` (`separate_vocals`, `transcribe`, `tempo_compasso`, `detect_drums`, `classify_drums`, `make_cifra`)
- Verificação unitária de que o arquivo `out/<id>/<id>-cifra.md` é criado e contém as anotações de bateria customizadas acima das linhas da letra
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
    dicionario.yaml         # regras e bandas de frequência dos códigos de bateria
    pipeline.json           # definição da sequência de etapas do pipeline
  openspec/
    specs/mvp1/spec.md
    changes/
      archive/2026-11-12-mvp1-vocal-letra-cifra/
      cifra-bateria-customizada/
  src/
    run.py                  # orquestrador (cache, manifest, escrita atômica, retries)
    workflows/
      separate_vocals.py    # Etapa 1: Demucs -> vocals.wav, drums.wav, no_drums.wav
      transcribe.py         # Etapa 2: Whisper -> letra.json
      tempo_compasso.py     # Etapa 3: Librosa -> compassos.json
      detect_drums.py       # Etapa 4: Bandas + onsets + 16 passos -> drums_events.json
      classify_drums.py     # Etapa 5: Dicionário YAML -> drums_patterns.json
      make_cifra.py         # Etapa 6: Letra + padrões + Gemma -> out/<id>/<id>-cifra.md
  tests/
    test_mvp1.py            # Testes unitários, validação das anotações na cifra e dry-run
  work/<id>/                # cache e manifest.json (ignorado no git)
  out/<id>/                 # saídas finais como <id>-cifra.md (ignorado no git)
```
