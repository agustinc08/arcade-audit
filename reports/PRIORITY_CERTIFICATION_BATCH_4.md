# Certificación prioritaria — lote 4

- Estado: COMPLETE; certifier `engine_ok=true`.
- Considerados: 100.
- Lanzados: 100.
- AUTO_PASS: 96.
- STATIC_FAIL: 0.
- GAME_FAIL: 4.
- FLAKY: 0.
- ENGINE_FAIL nuevo: 0.
- RESTORE_VERIFIED: 100/100.
- AUDIO_ROUTE_CHANGED: 0.
- WRONG_GAME_DISPATCH: 0.
- NEXT_GAME: `mame:/userdata/roms/mame/docastle.zip`.

## Fallos

- `bbprot` — `GAME_FAIL`, `RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED`; capturas T+5/T+15 negras o persistentemente casi negras; exit 0, runtime estable y restore verificado. Causa aún no confirmada.
- `calibr50` — `GAME_FAIL`, `RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED`; capturas T+5/T+15 negras o persistentemente casi negras; exit 0, runtime estable y restore verificado. Causa aún no confirmada.
- `chplftb` — `GAME_FAIL`, `RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED`; capturas T+5/T+15 negras o persistentemente casi negras; exit 0, runtime estable y restore verificado. Causa aún no confirmada.
- `daraku` — `GAME_FAIL`, `RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED`; capturas T+5/T+15 negras o persistentemente casi negras; exit 0, runtime estable y restore verificado. Causa aún no confirmada.

## Seguridad del lote

Las 100 transacciones terminaron con `RESTORE_VERIFIED`; no hubo cambio de audio, despacho incorrecto ni fallo de motor nuevo. `CONTROL_CERTIFIED` y `GUEST_READY` siguen en 0.
