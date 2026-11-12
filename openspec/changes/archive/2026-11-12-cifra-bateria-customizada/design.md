## Decisões Arquiteturais

1. **Separação de Stems (Demucs)**
   - Utilizar o container `wesley-demucs` (ou Demucs local `htdemucs`) para extrair `vocals.wav`, `drums.wav` e `no_drums.wav` em `work/<id>/`.
   - Caso seja usado `htdemucs` de 4 stems (`drums`, `bass`, `other`, `vocals`), `no_drums.wav` é obtido pela soma de `bass + other + vocals`.

2. **Detecção de Golpes por Banda de Frequência + Onsets (`src/workflows/detect_drums.py`)**
   - Entrada: `work/<id>/drums.wav` e `work/<id>/compassos.json`.
   - Filtros passa-faixa (Butterworth via `scipy.signal` / `librosa`) para separar bandas principais do kit:
     - **Bumbo (`b`)**: 30 – 130 Hz
     - **Surdo (`s`)**: 80 – 200 Hz (com decaimento tonal mais longo que o bumbo)
     - **Tom 1 (`t1`)**: 150 – 350 Hz
     - **Caixa (`c`) / Aro (`a`)**: 200 – 4000 Hz (diferenciando aro vs. caixa pela razão de energia de alta frequência / centróide espectral e envelope)
     - **Hi-hat (`h` / `ha`) / Ride (`rc`) / Ataque (`pa1`)**: 4000 – 16000 Hz (diferenciando fechado `h` vs. semi-aberto `ha` vs. ataque `pa1` pela duração do decaimento do envelope RMS e cúpula `rc` por proeminência tonal em 2.5–5 kHz)
   - Cada onset detectado é quantizado na grade de 16 passos (semicolcheias) de cada compasso de `compassos.json`, gerando `work/<id>/drums_events.json`.

3. **Dicionário de Códigos (`config/dicionario.yaml` e `src/workflows/classify_drums.py`)**
   - As regras iniciais ficam em `config/dicionario.yaml`:
     - `S`: Nenhum evento de bateria no compasso/trecho (silêncio de bateria)
     - `L-h`: Levada só com hi-hat fechado
     - `L-abh`: Levada com aro + bumbo + hi-hat fechado
     - `L-cbh`: Levada com caixa + bumbo + hi-hat fechado
     - `L-cbha`: Levada com caixa + bumbo + hi-hat semi-aberto
     - `L-cbrc`: Levada com caixa + bumbo + cúpula do ride
     - `CR-cs`: Crescendo de caixa + surdo em colcheias (intensidade crescente nos passos)
     - `V-cs`: Virada de caixa + surdo
     - `V-ct1s`: Virada caixa → tom 1 → surdo
     - `BQ-bpa1`: Baque / acento de bumbo + prato de ataque 1 seco
   - O classificador avalia tanto o compasso inteiro quanto mudanças intracompasso (ex.: levada seguida de baque, silêncio `S` e virada `V-cs` nos tempos finais), associando cada código ao seu timestamp inicial/final em `work/<id>/drums_patterns.json`.

4. **Alinhamento com a Letra e Posicionamento Horizontal (`src/workflows/make_cifra.py`)**
   - Os segmentos de `work/<id>/letra.json` (com timestamps de palavras quando disponíveis no `faster-whisper` via `word_timestamps=True`, ou interpolados linearmente pelo tempo do segmento) são cruzados com `work/<id>/drums_patterns.json`.
   - Os códigos são formatados **sem colchetes** na linha imediatamente acima da letra (`L-cbh`, `BQ-bpa1`, `S`, `V-cs`), alinhados por coluna (espaços em branco) exatamente sobre a palavra ou pausa (ex.: `(silêncio: só a voz)`) onde o evento de bateria acontece.

5. **Revisão com Gemma via llama.cpp (porta 11435)**
   - Como Demucs e Whisper já finalizaram em etapas anteriores do `src/run.py`, a VRAM está livre para consultar o `llama.cpp` em `http://localhost:11435/v1/chat/completions` (modelo `Gemma-4-12B-it-qat-q4_0.gguf`).
   - Os tempos, compassos e posições vêm 100% do código Python (evitando alucinação); o Gemma atua revisando a legibilidade das quebras de linha e observações de dinâmica/pausa. Se o servidor `llama.cpp` não estiver acessível no momento da execução, o script grava a montagem determinística diretamente (com aviso no log) para não bloquear o pipeline.

6. **Arquivo Final (`out/<id>/<id>-cifra.md`)**
   - O arquivo de saída recebe o nome da música acrescido de `-cifra.md` dentro de `out/<id>/` (ex.: `out/3 - Corpo e família - IPBJA/3 - Corpo e família - IPBJA-cifra.md`).

## Exemplo de Saída (`out/<id>/<id>-cifra.md`)

```markdown
# <id> | BPM 120 | 4/4

L-cbh
Eu tentei fugir de tudo
          BQ-bpa1           S                     V-cs
Mas o tempo...     (silêncio: só a voz) ...não parou!
```

## Riscos e Mitigações

- **Precisão de timbres sutis (aro vs. caixa, cúpula vs. hi-hat)**: os limiares espectrais e de decaimento ficam parametrizados em `config/dicionario.yaml` para fácil ajuste sem alterar código.
- **Alinhamento sobre sílaba/palavra**: habilitar `word_timestamps=True` no `transcribe.py` melhora a precisão da coluna onde cada código (`BQ-bpa1`, `S`, `V-cs`) é posicionado; se ausente, usa interpolação proporcional ao comprimento do texto no intervalo `[start, end]`.

