## Decisões

- Entrada: caminho de um MP3 local; `<id>` = nome do arquivo sem extensão.
- Cache por etapa: se a saída existir em `work/<id>/`, a etapa é pulada (`--force` refaz).
- Separação: Demucs `htdemucs --two-stems=vocals` → `work/<id>/vocals.wav`.
- Whisper: faster-whisper, modelo `large-v3` (ou `medium`), idioma configurável (`--lang pt|en`) → `work/<id>/letra.json` com `[{start, end, text}]`.
- Tempo-compasso: librosa (madmom como alternativa), assume 4/4, calcula BPM e downbeats → `work/<id>/compassos.json` com `[{compasso, inicio, fim}]`.
- Cifra: cada segmento da letra é associado ao compasso onde começa; `out/<id>/cifra.md` lista compassos com a letra. Tempo vem do código, sem LLM.
- Etapas rodam em sequência (VRAM).

## Formato de `cifra.md`

```
# <id> | BPM 120 | 4/4
[Compasso 1-2]
Primeira linha da letra
[Compasso 3-4]
Segunda linha da letra
```

## Riscos

- Whisper erra letra com voz processada; compassos fora de 4/4 ou com mudança de andamento quebram o beat tracking.
- Beat tracking aqui roda sobre o mix completo (a bateria isolada vem em fase futura).

