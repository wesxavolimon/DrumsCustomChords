# MVP 1 Specification

## Requirements

### Requirement: Separação de vocal
O sistema SHALL separar o vocal de um MP3 e gravar `work/<id>/vocals.wav`.

#### Scenario: MP3 válido
- **WHEN** o script recebe um MP3 existente
- **THEN** `vocals.wav` é gerado e a etapa é pulada em execuções seguintes (cache)

### Requirement: Transcrição da letra
O sistema SHALL transcrever `vocals.wav` com Whisper e gravar `letra.json` com início, fim e texto de cada segmento.

#### Scenario: Idioma informado
- **WHEN** o usuário passa `--lang pt`
- **THEN** o Whisper usa esse idioma

### Requirement: Tempo-compasso
O sistema SHALL calcular BPM e limites de compasso (4/4) e gravar `compassos.json`.

#### Scenario: Música em 4/4
- **WHEN** o script processa o MP3
- **THEN** cada compasso tem número, início e fim em segundos

### Requirement: Primeiro arquivo de cifra
O sistema SHALL gerar `out/<id>/cifra.md` associando cada segmento da letra ao compasso onde ele começa.

#### Scenario: Letra e compassos disponíveis
- **WHEN** `letra.json` e `compassos.json` existem
- **THEN** `cifra.md` lista a letra agrupada por compasso, com BPM e fórmula no cabeçalho

