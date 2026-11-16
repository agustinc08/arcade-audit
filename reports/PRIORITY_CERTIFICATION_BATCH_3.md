# Certificación prioritaria — lote 3

- Estado: COMPLETE; certifier `engine_ok=true`.
- Considerados: 100.
- Lanzados: 100.
- AUTO_PASS: 99.
- STATIC_FAIL: 0.
- GAME_FAIL: 1.
- FLAKY: 0.
- ENGINE_FAIL nuevo: 0.
- RESTORE_VERIFIED: 100/100.
- AUDIO_ROUTE_CHANGED: 0.
- WRONG_GAME_DISPATCH: 0.
- NEXT_GAME: `mame:/userdata/roms/mame/battroad.zip`.

## Fallos

- `stonebal` — `GAME_FAIL`, `RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED`: juego estable 20 s, salida 0 y restore correcto; capturas T+5/T+15 negras e idénticas. Se registra como sospecha visual, sin atribuirlo a ROM/core.

## Seguridad del lote

Las 100 transacciones terminaron con `RESTORE_VERIFIED`; HDMI permaneció en el sink esperado. No se repitieron juegos con AUTO_PASS previo. `CONTROL_CERTIFIED` y `GUEST_READY` permanecen en 0.
