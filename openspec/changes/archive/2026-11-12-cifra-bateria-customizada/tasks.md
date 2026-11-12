## 1. Configuração e Dicionário
- [x] 1.1 Criar `config/dicionario.yaml` com as regras de detecção e limiares de frequência/envelope para `S`, `L-h`, `L-abh`, `L-cbh`, `L-cbha`, `L-cbrc`, `CR-cs`, `V-cs`, `V-ct1s`, `BQ-bpa1`
- [x] 1.2 Atualizar `config/pipeline.json` incluindo as etapas `detect_drums` e `classify_drums` e o novo caminho de saída `out/<id>/<id>-cifra.md`

## 2. Separação de Stems e Transcrição com Word Timestamps
- [x] 2.1 Atualizar `src/workflows/separate_vocals.py` para extrair também `work/<id>/drums.wav` e `work/<id>/no_drums.wav` além de `vocals.wav`
- [x] 2.2 Atualizar `src/workflows/transcribe.py` para incluir timestamps por palavra (`word_timestamps=True`) em `work/<id>/letra.json`
- [x] 2.3 Atualizar `src/workflows/tempo_compasso.py` para priorizar `work/<id>/drums.wav` no cálculo de BPM e downbeats

## 3. Detecção, Quantização e Classificação de Bateria
- [x] 3.1 Criar `src/workflows/detect_drums.py` (filtros por banda de frequência + onsets + quantização em 16 passos por compasso → `work/<id>/drums_events.json`)
- [x] 3.2 Criar `src/workflows/classify_drums.py` (aplicação das regras de `config/dicionario.yaml` sobre `drums_events.json` → `work/<id>/drums_patterns.json`)

## 4. Montagem da Cifra Customizada e Integração Gemma
- [x] 4.1 Atualizar `src/workflows/make_cifra.py` para posicionar os códigos sem colchetes (`L-cbh`, `BQ-bpa1`, `S`, `V-cs`, etc.) na linha acima da letra sobre a palavra/pausa correspondente
- [x] 4.2 Integrar revisão opcional/sequencial via Gemma (`http://localhost:11435/v1/chat/completions`) com fallback determinístico e salvar em `out/<id>/<id>-cifra.md`

## 5. Testes e Documentação
- [x] 5.1 Atualizar `tests/test_mvp1.py` (incluindo testes para `detect_drums`, `classify_drums`, `dicionario.yaml`, verificação de criação do arquivo `out/<id>/<id>-cifra.md` e asserção explícita de que as anotações de códigos de bateria customizados foram criadas acima das linhas da letra no arquivo gerado)
- [x] 5.2 Executar o pipeline com a música configurada em `config/audio.json` e validar a geração de `out/<id>/<id>-cifra.md`
- [x] 5.3 Atualizar `AGENTS.md` refletindo o novo fluxo e entregável
