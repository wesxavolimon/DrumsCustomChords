## Why

O MVP 1 entregou a separação de vocal, transcrição da letra com tempo, detecção de compassos e geração de uma cifra básica (`cifra.md`). Agora precisamos refazer e expandir esse fluxo para incluir a **cifra de bateria customizada**: separar também a bateria (`drums.wav` e `no_drums.wav`), detectar os golpes por banda de frequência e onsets, quantizar e classificar cada compasso/trecho segundo o dicionário (`config/dicionario.yaml`), revisar e formatar com o modelo local Gemma via `llama.cpp` (porta 11435), e gerar o arquivo final `out/<id>/<id>-cifra.md` com os códigos de bateria customizados posicionados acima da letra no ponto exato em que ocorrem.

## What Changes

- **Separação de stems completa (Demucs)**: além de `vocals.wav`, gerar `drums.wav` e `no_drums.wav` (ou converter para MP3 em `out/<id>/`).
- **Beat tracking sobre a bateria**: `tempo_compasso.py` passa a usar `drums.wav` (quando disponível) para maior precisão de BPM e downbeats.
- **Detecção de golpes e quantização (`src/workflows/detect_drums.py`)**: filtros por banda de frequência + detecção de onsets sobre `drums.wav`, quantizados em grade de 16 passos por compasso (`work/<id>/drums_events.json`).
- **Dicionário de códigos (`config/dicionario.yaml` + `src/workflows/classify_drums.py`)**: regras iniciais configuráveis para mapear padrões de bateria nos códigos (`S`, `L-h`, `L-abh`, `L-cbh`, `L-cbha`, `L-cbrc`, `CR-cs`, `V-cs`, `V-ct1s`, `BQ-bpa1`), gerando `work/<id>/drums_patterns.json`.
- **Alinhamento fino e revisão com Gemma (`src/workflows/make_cifra.py`)**: posiciona os códigos de bateria (sem colchetes na linha acima da letra, ex.: `L-cbh`, `BQ-bpa1`, `S`, `V-cs`) sobre a palavra/tempo correspondente e utiliza o Gemma (`llama.cpp` na porta 11435, com fallback determinístico caso o servidor não esteja ativo) para revisar e formatar a saída.
- **Novo nome de arquivo de saída**: o arquivo final passa a ser gravado em `out/<id>/<id>-cifra.md` (nome da música + `-cifra.md`).

## Capabilities

### New Capabilities
- `drum-separation`: separa `drums.wav` e `no_drums.wav` a partir do MP3 de entrada via Demucs.
- `drum-detection-quantization`: detecta golpes por banda de frequência/onsets em `drums.wav` e quantiza em grade de 16 passos por compasso.
- `drum-dictionary-classification`: classifica cada compasso/subdivisão usando `config/dicionario.yaml` nos códigos customizados (`S`, `L-h`, `L-abh`, `L-cbh`, `L-cbha`, `L-cbrc`, `CR-cs`, `V-cs`, `V-ct1s`, `BQ-bpa1`).
- `gemma-cifra-formatting`: monta e revisa a cifra customizada com códigos posicionados acima da letra via Gemma (`llama.cpp` porta 11435) salvando em `out/<id>/<id>-cifra.md`.

### Modified Capabilities
- `mvp1`: atualiza a separação de stems, o beat tracking e o formato/nome do arquivo de saída da cifra (`out/<id>/<id>-cifra.md`).

## Impact

- Novos scripts em `src/workflows/` (`detect_drums.py`, `classify_drums.py`) e atualização de `separate_vocals.py`, `tempo_compasso.py` e `make_cifra.py`.
- Novo arquivo de configuração `config/dicionario.yaml` e atualização de `config/pipeline.json`.
- Integração HTTP com `llama.cpp` (`http://localhost:11435/v1/chat/completions`) executada em sequência após Demucs e Whisper para respeitar o limite de 12 GB de VRAM da RTX 3060.

