# MAME BATCH 3 — reanudación PAUSED_SAFETY

- Fecha: 2026-11-15.
- Checkpoint original preservado sin cambios: `mame_batch3_checkpoint.json` (fase `PAUSED_SAFETY`).
- Checkpoint de esta continuación: `mame_batch3_resume_checkpoint.json`.
- No se inició BATCH 4.

## Diagnóstico

El primer intento de BATCH 3 con `kinstb` sigue fuera de los conteos de MAME actual: `tested_mame_current=NO`, `not_tested_target_core=YES`.

En el único control autorizado, se creó un marker para `system=mame`, `rom=/userdata/roms/mame/altair.zip`, `choice=BOTONERA`. El POST a `http://127.0.0.1:1234/launch` envió exactamente `/userdata/roms/mame/altair.zip` con `Content-Type: application/x-www-form-urlencoded`. EmulationStation respondió **HTTP 200**, headers `Content-Length: 0`, body vacío. Después, `/runningGame` reportó `kinstb`, y los argumentos reales de `controller_dispatcher` fueron `-system mame -rom /userdata/roms/mame/kinstb.zip`.

La divergencia comprobada está entre el juego pedido (`altair`) y la identidad que ES entregó al dispatcher (`kinstb`). El marker quedó sin consumir porque el dispatcher compara `system` y ruta ROM exactos. `selector_controles` se inició; no hubo `emulatorlauncher`, RetroArch, MAME actual, `/var/run/cmdfiles/altair.cmd` ni evento nuevo en `game_health.sqlite`. Se terminó con `SIGTERM` únicamente el PID exacto del selector de esta ejecución, después de verificar su padre dispatcher y los argumentos kinstb, para impedir ese lanzamiento no autorizado.

**Causa inmediata del marker no consumido:** mismatch `altair.zip` vs `kinstb.zip` al entrar al dispatcher. **Causa del desvío dentro de ES/API:** no determinada; no hay evidencia para distinguir una entrada/UI concurrente, una divergencia de estado interno de ES o la resolución de la solicitud. La entrada `altair` sí existe en `/systems/mame/games` con la ruta exacta. El HTML local de servicios envía `game.path` como body. No se puede concluir que `controller_dispatcher` esté roto: conserva el SHA de BATCH 2 y recibió `kinstb`, no `altair`.

La comparación de fuentes no mostró diferencias entre BATCH 2 y BATCH 3 en `post_launch`, body, marker, ruta, timeout, polling, detector de core o consulta `game_health`: BATCH 3 delega el lanzamiento en `smoke_pilot_batch2.run_game`. El control actual no validó la cadena para `altair`, por lo que la tanda se detuvo.

## Identidad de kinstb

MAME actual `-listfull` y `-listxml` devuelve el nombre canónico **`Killer Instinct (SNES bootleg)`** para `kinstb` (máquina runnable, 2 players). No es la máquina arcade Killer Instinct. No se reintentó.

## Resultado del control altair

- `ALTair CONTROL: FAIL — LAUNCH_CHAIN_RUNTIME_FAILURE`.
- T0 marker creado; T1 POST enviado; HTTP 200/body vacío.
- T2 `/isIdle` cambió a false; T3 `/runningGame` cambió a kinstb; T5 dispatcher visto con argumentos kinstb.
- T4 no ocurrió: marker no consumido. T6 no observado. T7 no observado. T8 no ocurrió. T9 no ocurrió.
- RetroArch/MAME actual no arrancaron; esto no es un resultado nuevo de MAME para `altair` ni cuenta como prueba target-core.
- Marker temporal propio retirado; no queda marker residual.
- `kinstb` retry: `NOT RUN`. Candidatos normales y especiales: `NOT RUN`.

## Restore y salud

- Snapshot protegido de 2.434 entradas verificado igual al pretest; no cambiaron `batocera.conf`, cfgs, remaps, saves, NVRAM monitorizado ni ROM. `RESTORE_VERIFIED=YES` para el estado persistente de juego monitorizado.
- **Incidente de preservación de logs:** el shell oficial abrió `es_launch_stderr.log` y `es_launch_stdout.log` con redirección y los truncó. El stderr tenía 3.561 bytes antes del control; no se encontró copia exacta en `/userdata/system`. El contenido anterior no se puede restaurar/verificar. Las versiones posteriores se copiaron al directorio runtime del checkpoint. Esto no afectó saves/configuración, pero limita la preservación de logs.
- ES PID 2929 activo; `/isIdle=[ true ]`, `/runningGame=NO GAME RUNNING`; procesos RetroArch/dispatcher/selector/emulatorlauncher huérfanos: 0; marker ausente.
- Core global `mame078plus`; overrides sin cambios: `ffight2b`, `altair`, `apache3`, `blazlaz`, `cubeqst`, `sia2650`, `evosocc`, `hoops95`, `funcube4`.
- P1-P4 sin cambios: P1 USB5/event17/js0; P2 USB6/event18/js1; P3 USB8/event20/js3; P4 USB7/event19/js2. `controller_dispatcher --diagnose` y `sdl2-jstest --list`: PASS.
- No hay nuevo evento de juego en `game_health.sqlite` (max ID sin cambio desde precontrol); temperatura observada 16.8 °C; memoria disponible 14.46 GiB.

## Clasificación resumida

**PASS**

- Ninguno en esta reanudación.

**FAIL**

- `altair` control → `LAUNCH_CHAIN_RUNTIME_FAILURE`: POST para altair; ES informó y despachó kinstb; marker exacto no consumido; no llegó a MAME. No atribuir al core/ROM.

**NOT RUN**

- `kinstb` retry → no ejecutado porque el control no pasó.
- `lbgrande`, `sws98`, `tenkomor`, `multigam`, `multigm3`, `nratechu`, `ertictac` → no ejecutados.
- Especiales `pacapp2`, `pacappsp`, `ghlpanic`, `midnrun`, `cclownz`, `qb3` → no ejecutados.

## Decisión de seguridad

No continuar la tanda ni usar `kinstb` hasta esclarecer por qué un POST con ruta de `altair` fue seguido por `runningGame` y argv de `kinstb`. No cambiar core global, dispatcher, XML activo, mappings, ROMs, BIOS ni configuración de lanzamiento. No iniciar otra tanda ni pruebas físicas.

## Exportación

Sincronización filtrada de 47 archivos regulares completada a `arcade_audit_git/` mediante copia de archivos; no se ejecutó el script de sync porque realiza operaciones Git. `SECRET SCAN: PASS`. `PAYLOAD SCAN: PASS`; sin ROMs, BIOS, CHD, saves, NVRAM ni media en los archivos exportados. No se ejecutaron comandos Git, commit ni push.
