# MAME Batch 3 — pruebas por override individual

- Fecha: 2026-11-15.
- Estado: **PAUSED_SAFETY** antes de iniciar el juego en MAME actual.
- Core global `mame078plus`, sin cambios. Core objetivo disponible: `/usr/lib/libretro/mame_libretro.so`.
- Ruta solicitada: EmulationStation → `controller_dispatcher` → launcher oficial → RetroArch. No se inyectó input.
- Corrección de conteo: un intento sólo con `mame078plus` es `TESTED_DEFAULT_CORE`, no `TESTED_MAME_CURRENT`.

## Pool y preflight

- `USE_MAME_CORE_X`: 61 entradas.
- Excluidos por pruebas MAME actual según reportes reales: BATCH 1 (5) y BATCH 2 (10). BATCH 2 skips FBNeo (`gprider`, `sfiii2n`, `sfiii3n`, `sfiiin`, `neotris`) también excluidos.
- Pool target-core no probado: **56** (recalculado contra BATCH 1/BATCH 2, no inferido de las columnas antiguas).
- MAME standalone 0.285 `-verifyroms`: 56 considerados; 48 PASS y 8 `SKIP_PREFLIGHT`.
- De los candidatos que pasan preflight, se seleccionaron 14: ocho de joystick digital y seis juegos reales con control especial porque no había 20 juegos normales elegibles. Los 14 tienen ZIP legible, driver runnable, `-verifyroms` bueno, y sin disk/BIOS set requerido en el XML comprobado. Cola priorizada: `kinstb`, `lbgrande`, `sws98`, `tenkomor`, `multigam`, `multigm3`, `nratechu`, `ertictac`, `pacapp2`, `pacappsp`, `ghlpanic`, `midnrun`, `cclownz`, `qb3`.

### SKIP_PREFLIGHT

- `fredmem` — falta `bsmt2000.bin` / parent `bsmt2000`; ROMset bad.
- `kdynastg` — falta `kdynastg_pic`; no existe dump bueno conocido.
- `ncb3` — `82s147.u2` necesita redump.
- `pocketrc` — falta `c76.bin` del parent `namcoc76`.
- `ppcar` — `qs1000.bin` sin dump bueno conocido.
- `quintoon` — `95001016.snd` necesita redump.
- `sidewndr` — `2_h09.bin` necesita redump.
- `ssipkr24` — cinco archivos (`tuni-83.u67`, `.u70`, `.u69`, `.u68`, `tunipoker.u28`) necesitan redump.

## Intento de lanzamiento y detención

- `kinstb` / Killer Instinct (SNES bootleg) pasó preflight y recibió un override temporal individual.
- El POST de lanzamiento a EmulationStation devolvió HTTP 200, pero el API volvió a `idle`; el marcador de auditoría no fue consumido. No apareció RetroArch, no se cargó MAME actual y no se creó evento nuevo en `game_health.sqlite`.
- Clasificación: **UNKNOWN — `DISPATCHER_MARKER_NOT_CONSUMED`**. No se atribuye el resultado a ROM, driver ni MAME actual y no cuenta como prueba MAME actual.
- El runner revirtió el override temporal `kinstb`; el restore se verificó y el batch se detuvo antes del siguiente candidato.

| Shortname | Nombre | Lanzamiento real | MAME result | Override temporal | Restore |
|---|---|---|---|---|---|
| kinstb | Killer Instinct (SNES bootleg) | No; RetroArch/MAME no iniciaron | UNKNOWN — DISPATCHER_MARKER_NOT_CONSUMED | Revertido | VERIFIED |

## Estado final

- Launch requests: 1; juegos iniciados en RetroArch/MAME: 0.
- BOOT_PASS: 0. BOOT_FAIL/UNKNOWN en cadena de lanzamiento: 1. Porcentaje PASS entre juegos iniciados: no aplica (0 iniciados).
- Overrides nuevos retenidos: 0. Override temporal probado y revertido: `kinstb`.
- Restore de intento: 1/1 VERIFIED. Árboles protegidos iguales al baseline; `batocera.conf` coincide con BATCH 2 más sólo los nueve overrides conocidos.
- Core global: `mame078plus`, sin cambios.
- EmulationStation: PID 2929, API idle. Sin procesos RetroArch/MAME huérfanos. Dispatcher conserva el SHA-256 de BATCH 2. El API no llegó a consumir el marcador; causa raíz no determinada. El SHA-256 de `controller_dispatcher` coincide con BATCH 2 (`a60be89f…581c45`) y el XML activo sigue llamándolo para MAME.
- P1-P4: OK; `controller_dispatcher --self-test` directo devolvió `DISPATCHER_SELF_TEST_OK`; diagnóstico PASS, sin duplicados: P1 USB5/event17/js0, P2 USB6/event18/js1, P3 USB8/event20/js3, P4 USB7/event19/js2.
- Temperatura observada: 52 °C; memoria disponible: 14.1 GiB; sin errores críticos nuevos en la comprobación final.
- DIRECT_COMPATIBLE PASS: 0; FIGHTING PASS: 0; MULTIPLAYER PASS: 0; SPECIAL CONTROL PASS: 0. No se hizo prueba física. No se inició BATCH 4.

## Reconciliación de estados de prueba

La matriz conserva los campos históricos y añade `tested_default_core`, `tested_mame_current`, `tested_fbneo`, `not_tested_target_core`, `mame_current_result`, `mame_current_tested_at` y `mame_current_restore`. Para `kinstb`, el lanzamiento no llegó al core, por lo que permanece `tested_mame_current=NO` y `not_tested_target_core=YES`.

La revisión del dispatcher no encontró cambio respecto del SHA-256 registrado en BATCH 2, y el XML activo de EmulationStation sigue invocándolo para MAME. Esto no explica por qué el API de lanzamiento quedó idle. No repetir el intento ni avanzar al siguiente juego hasta resolver esa discrepancia mediante diagnóstico del runtime.

## Exportación

- Árbol `arcade_audit_git/` sincronizado con 42 archivos regulares permitidos, incluyendo el informe, checkpoint, matriz, preflight y runner.
- `SECRET_SCAN: PASS`; `PAYLOAD_SCAN: PASS` (sin ROMs, BIOS, CHD, saves ni NVRAM).
- No se ejecutaron comandos Git; sin commit ni push.
