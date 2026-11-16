# Certificación prioritaria — Batch 5

- Fecha: 2026-11-16T16:59:54-03:00
- Considerados: 100 entradas de la cola materializada; sin alterar su orden.
- Lanzados: 99; omisión por preflight: 1.
- AUTO_PASS: 98.
- STATIC_FAIL: 1.
- GAME_FAIL: 1.
- FLAKY: 0.
- ENGINE_FAIL: 0; fallo de motor activo: 0.
- Restores: 99/99 VERIFIED; fallos: 0.
- AUDIO_ROUTE_CHANGED: 0.
- WRONG_GAME_DISPATCH: 0.
- Rango del lote: `docastle.zip` a `gunbird2.zip`.
- NEXT_GAME: `mame:/userdata/roms/mame/gundealr.zip`.

## STATIC_FAIL

- `evosocc` — `MAME_VERIFYROMS_FAILED`; preflight read-only MAME 0.285 exit 2. Falta el miembro de BIOS `mx27l1000-alt.u14`, 131072 bytes, CRC esperado `1e8175c8` en `crysbios`. El ZIP `crysbios.zip` existe, pero sólo contiene `mx27l1000.u14` CRC `beff39a9`. El juego no fue lanzado. No se modificó el contenido.

## GAME_FAIL

- `gunbird2` — `RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED`. Las capturas T+5.24s y T+15.05s dieron `BLACK_SCREEN_SUSPECT`, black pixel ratio 1.0 y mean luma 0; el proceso permaneció estable 20.59s, cerró con código 0, HDMI siguió en PASS y restore fue VERIFIED. Es un caso para revisión manual dentro de `CERT-004`; sin retry automático.

## Evidencia de seguridad

- Las 99 transacciones lanzadas restauraron los 10 ámbitos protegidos (`RESTORE_VERIFIED`). La entrada de preflight fallida no hizo escrituras (`NOT_REQUIRED_NO_WRITE`).
- El runner terminó `batch_status=COMPLETE`, `engine_ok=true`; sin fallos nuevos de restore, audio, identity dispatch ni configuración global.
- No se repitieron PASS anteriores; `mvp` y `hoops95` no se relanzaron.
- `AUTO_CERTIFIED` acumulados: 401; transacciones registradas: 409; `CONTROL_CERTIFIED=0`, `GUEST_READY=0`.
