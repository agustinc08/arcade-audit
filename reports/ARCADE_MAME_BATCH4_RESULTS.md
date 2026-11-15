# ARCADE MAME BATCH 4 — RESULTADOS

- Fecha: 2026-11-15 (America/Argentina/Buenos_Aires).
- Lote real de candidatos: 7; el commit previo de “mame batch 4” se conserva como diagnóstico/reanudación de BATCH 3, no como lote de juegos.
- Estado: COMPLETADO. No se inició BATCH 5 ni se probaron controles especiales.

## Limpieza y control de EmulationStation

- Se verificó marker ausente, API idle y sin juego antes del control. El estado previo incluía `/tmp/game.xml` histórico con `kinstb.zip`; no se borró.
- Se realizó un reinicio controlado de ES mediante `GET /quit` y el wrapper standalone lo relanzó (PID anterior 2929, PID nuevo 29733). API respondió `/isIdle=true`, `/runningGame=NO GAME RUNNING`.
- Los diffs de 6 gamelists contienen sólo `playcount`, `lastplayed`, `gametime` en 50 juegos; 0 rutas añadidas/eliminadas y las 50 filas tienen correspondencia en `game_health.sqlite`. Hubo reordenamientos XML sin cambio de rutas. Quedaron documentados bajo `mame_batch4_runtime/gamelist_diffs/`; no se restauraron.
- El disparador exacto de la discordancia POST `altair` → dispatcher `kinstb` no quedó demostrado. Tras reiniciar ES la identidad de extremo a extremo fue correcta. `kinstb` quedó excluido: “Killer Instinct (SNES bootleg)”, no es el arcade original. Su ROM no se modificó.

## Control positivo `altair`

- Resultado: `BOOT_PASS` (control histórico, no cuenta como recuperación nueva). HTTP 200, cuerpo vacío. POST, `runningGame`, dispatcher, cmdfile y contenido de RetroArch fueron `altair.zip`. Marker consumido.
- Core cargado: `/usr/lib/libretro/mame_libretro.so`. `game_health.sqlite` registró 58,112 s, core `mame`, exit 0, sin señal; cierre controlado exacto por `SIGTERM`, retorno a ES y restore verificado.
- El runner tuvo un `TypeError` por sombreado de una variable y no finalizó su checkpoint en caliente. El proceso exacto permaneció ejecutándose; se capturó su argv/logs, se cerró limpiamente y se reconstruyó el resultado con game_health, logs y restore. El runner quedó corregido antes de probar candidatos.

## Candidatos

| Shortname | Nombre | Core | game_health | Duración | Exit | Restore | Override |
|---|---|---|---:|---:|---:|---|---|
| `lbgrande` | Libero Grande | `mame` | 8163 | 20.560 s | 0 | VERIFIED | KEEP |
| `sws98` | Super World Stadium '98 | `mame` | 8164 | 20.602 s | 0 | VERIFIED | KEEP |
| `tenkomor` | Tenkomori Shooting | `mame` | 8165 | 20.582 s | 0 | VERIFIED | KEEP |
| `multigam` | Multi Game | `mame` | 8166 | 20.584 s | 0 | VERIFIED | KEEP |
| `multigm3` | Multi Game III | `mame` | 8167 | 20.584 s | 0 | VERIFIED | KEEP |
| `nratechu` | Neratte Chu | `mame` | 8168 | 20.552 s | 0 | VERIFIED | KEEP |
| `ertictac` | Erotictac/tactic | `mame` | 8169 | 20.613 s | 0 | VERIFIED | KEEP |

## Resumen de ejecución

- Considerados: 7; preflight PASS: 7; `SKIP_PREFLIGHT`: 0; candidatos únicos lanzados: 7; `BOOT_PASS`: 7; `BOOT_FAIL`: 0; `ES_WRONG_GAME_DISPATCH`: 0.
- En los siete runs completos, `requested ROM = ES runningGame = dispatcher -rom = cmdfile/contenido = RetroArch MAME actual`. Los siete permanecieron >20 s, cerraron con exit 0, retornaron a ES y tuvieron `RESTORE_VERIFIED=YES`.
- `game_health` se escribió con una pequeña demora tras la consulta inmediata del runner. Se conciliaron IDs 8163–8169 y el estado `INICIO_SOSTENIDO`; los `ProcessLookupError` de hotkeygen son `CLEANUP_RACE`, no fallos de juego.
- `lbgrande` tuvo un intento incompleto previo: el runner no observó el PID breve de emulatorlauncher y cerró RetroArch a los 0,041 s. No se clasifica como fallo del juego; se repitió una vez y completó PASS. Se conservaron ambos intentos en el checkpoint.
- Restore operaciones: 9/9 VERIFIED (control `altair`, primer intento incompleto de `lbgrande` y siete pruebas completas).

## Overrides y compatibilidad

- Overrides nuevos mantenidos: `lbgrande`, `sws98`, `tenkomor`, `multigam`, `multigm3`, `nratechu`, `ertictac`. Backup previo de `batocera.conf`: `mame_batch4_backups/batocera.conf.pre_batch4_pass_overrides_20261115_043820`.
- Core global: `mame078plus`, sin cambios. Dispatcher intacto, SHA-256 `a60be89fb45ea27ec4f7c3f546e088c7ff3da140bccfe1c6a37e5b14ec581c45`.
- La matriz se actualizó sólo para estos siete porque todos cargaron realmente MAME actual y el restore fue verificado.
- Los siete aparecen con joystick digital y 1–6 botones; ninguno es juego de pelea. Metadata indica 2 jugadores para los siete; no se probaron físicamente P1/P2 ni multiplayer. Juegos de pelea PASS: 0; 3P/4P PASS: 0; controles especiales: 0.
- Sin cambios en `controller_dispatcher`, `selector_controles`, `es_systems_el_gordo.cfg`, perfiles P1-P4, BIOS, ROMs, HDMI o configuración global de RetroArch.

## Estado final

- ES: activo, PID 29733, API idle; sin juego activo ni marker.
- Procesos de lanzamiento huérfanos: 0.
- P1–P4: OK: P1 USB5/event17/js0; P2 USB6/event18/js1; P3 USB8/event20/js3; P4 USB7/event19/js2.
- CPU: 43 °C; memoria disponible: 14.562.964 kB; Xorg activo; sin coincidencias nuevas de error NVIDIA/I/O en la cola reciente de `dmesg`.
- Sistema: OK. Botonera física: pendiente, no certificada.
- No se ejecutaron pruebas físicas, candidatos especiales ni BATCH 5.

## Exportación

- Árbol de exportación actualizado mediante copia filtrada. `SECRET_SCAN: PASS`; `PAYLOAD_SCAN: PASS` (50 archivos regulares revisados). No se ejecutaron comandos Git, commit ni push.
