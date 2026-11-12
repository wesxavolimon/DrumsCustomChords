## ADDED Requirements

### Requirement: Separação de bateria e vocal
O sistema SHALL separar o MP3 de entrada em `work/<id>/vocals.wav`, `work/<id>/drums.wav` e `work/<id>/no_drums.wav` usando Demucs.

#### Scenario: Extração de stems com cache
- **WHEN** o script de separação processa um MP3 válido
- **THEN** `vocals.wav`, `drums.wav` e `no_drums.wav` são gerados em `work/<id>/` e reaproveitados do cache em execuções seguintes

### Requirement: Detecção e quantização de golpes de bateria
O sistema SHALL analisar `work/<id>/drums.wav` usando filtros de banda de frequência e detecção de onsets, quantizando os eventos em uma grade de 16 passos por compasso (`work/<id>/drums_events.json`).

#### Scenario: Quantização por compasso
- **WHEN** `drums.wav` e `compassos.json` existem
- **THEN** `drums_events.json` é gerado com os eventos detectados (instrumento, tempo, passo 1..16 e intensidade) para cada compasso

### Requirement: Classificação por dicionário de bateria
O sistema SHALL classificar os eventos quantizados usando as regras de `config/dicionario.yaml` nos códigos customizados (`S`, `L-h`, `L-abh`, `L-cbh`, `L-cbha`, `L-cbrc`, `CR-cs`, `V-cs`, `V-ct1s`, `BQ-bpa1`) e gravar `work/<id>/drums_patterns.json`.

#### Scenario: Mudança de padrão e silêncio
- **WHEN** um compasso ou trecho não possui eventos de bateria ou muda para baque/virada
- **THEN** o classificador atribui o código correspondente (`S`, `BQ-bpa1`, `V-cs`, etc.) com seu intervalo de tempo exato

### Requirement: Geração da cifra de bateria customizada com revisão Gemma
O sistema SHALL alinhar os códigos de bateria (sem colchetes) na linha acima da letra, posicionados horizontalmente sobre a palavra ou pausa correspondente, consultar o Gemma (`llama.cpp` na porta 11435) para revisão textual e gravar o arquivo final em `out/<id>/<id>-cifra.md`.

#### Scenario: Arquivo final com nome da música + `-cifra.md`
- **WHEN** `letra.json`, `compassos.json` e `drums_patterns.json` são processados por `make_cifra.py`
- **THEN** o arquivo `out/<id>/<id>-cifra.md` é gerado contendo os códigos sem colchetes na linha acima da letra alinhados com as palavras e pausas correspondentes

### Requirement: Teste unitário de validação das anotações no arquivo final
O sistema SHALL possuir testes unitários que verifiquem se o arquivo `out/<id>/<id>-cifra.md` foi criado e se contém de fato as anotações dos códigos de bateria customizados (ex.: `L-cbh`, `L-h`, `BQ-bpa1`, `S`, `V-cs`, etc.) posicionadas nas linhas acima da letra.

#### Scenario: Verificação de presença de anotações de bateria na cifra gerada
- **WHEN** a suíte de testes unitários é executada
- **THEN** o teste valida a existência de `out/<id>/<id>-cifra.md` e confirma via regex/parsing que há linhas de anotação com códigos válidos do `config/dicionario.yaml` imediatamente acima das linhas de letra


