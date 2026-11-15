# Auditoría de escrituras de smoke tests

## Rutas de escritura identificadas antes de probar

- MAME: `/userdata/saves/mame` (NVRAM `.nv`, high scores `.hi`, CFG por juego `.cfg`, diffs); RetroArch declara `/userdata/saves/mame` como save/state directory. MAME 2003 Plus tiene NVRAM bootstraps activos y autosave de high score en `default`.
- FBNeo: `/userdata/saves/fbneo` (save RAM `.fs`, NVRAM `.nv`, high scores `.hi`, memory cards `.memcard`, CFG); core options indican hiscores habilitados, memory card por juego y modo writable.
- RetroArch: `/userdata/system/configs/retroarch` contiene core options, input/remap/config y subcarpeta `saves`; `remap_save_on_exit=true`. Se respalda y restaura archivo por archivo.
- Config MAME: `/userdata/system/configs/mame`; se preserva junto a los datos de core. Configuración general Batocera, definición ES y perfiles P1-P4 se incluyen como archivos guardados puntuales.
- `/userdata/cheats/saves` no existía al inspeccionar; `/userdata/screenshots` existía vacío. Se monitorean para eliminar sólo archivos nuevos de prueba.
- `/userdata/system/logs` y `game_health.sqlite` pueden recibir logs/eventos permitidos; se conservan como evidencia y se reportan, no se revierten. No se toman screenshots ni se envía input.

## Preparación de backup — 2026-11-13T01:10:46-03:00

- Destino: `/media/ROMS/ARCADE_BACKUPS/ARCADE_SMOKE_TEST_SAVES_2026-11-13_011039`
- Archivos fuente monitorizados: 2334
- Archivos copiados y verificados por SHA-256: 2334
- Fuente sin cambios durante copia: sí
- SHA-256 verificado antes de smoke tests: sí


### Lote 1 — fbneo/20pacgalr4.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/20pacgalr4.nv` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **FAILED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Recuperación de restauración — 20pacgalr4.zip

- Hallazgo: el runner generó `/userdata/saves/fbneo/fbneo/20pacgalr4.nv`; el directorio preexistente `/userdata/saves/fbneo/fbneo` sólo cambió su metadata de modificación.
- Causa de pausa: el restaurador anterior rechazó erróneamente un directorio existente al restaurar su metadata. No se lanzó ningún otro juego.
- Acción: eliminado únicamente el archivo nuevo del smoke test y restaurada metadata desde el baseline verificado.
- Verificación: snapshot protegido coincide exactamente con `protected_baseline.json`: **VERIFIED**.

### Lote 2 — fbneo/bbredux.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/bbredux.hi` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/bublboblr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/ckongg.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/ckongg.hi` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/dino.zip

| Tipo | Ruta |
| --- | --- |
| MODIFIED | `/userdata/saves/fbneo/fbneo/dino.hi` |
| MODIFIED | `/userdata/saves/fbneo/fbneo/dino.nv` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/firehawk.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/kod.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/kod.hi` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/mystwarru.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/mystwarru.nv` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/punisher.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/punisher.hi` |
| CREATED | `/userdata/saves/fbneo/fbneo/punisher.nv` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/searcheya.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/spec2kh.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/strkfgtrj.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/strkfgtrj.fs` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/taitotz.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 2 — fbneo/usg182.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/usg182.fs` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/vendetta.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/vendetta.hi` |
| CREATED | `/userdata/saves/fbneo/fbneo/vendetta.nv` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/wcbowldx.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/wcbowldx.fs` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — fbneo/wyvernwg.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/fbneo/fbneo/wyvernwg.nv` |
| MODIFIED | `/userdata/saves/fbneo/fbneo` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — mame/act2000.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — mame/aerofgts.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — mame/aleck64.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 2 — mame/alexkidd.zip

| Tipo | Ruta |
| --- | --- |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/alexkidd.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi/alexkidd.hi` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — mame/alg_bios.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 2 — mame/alpinesa.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — mame/alpinr2b.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — mame/altair.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 2 — mame/apache3.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/ar_bios.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 3 — mame/ar_ldrb.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/ar_ninj.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/ar_sprg.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/armwar.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log

### Elemento no iniciado — lote 3

- `mame/atarisy1.zip` no llegó a lanzarse: el precheck detectó que EmulationStation aún reportaba el juego anterior. Se mantuvo en cola.
- Antes de limpiar `in_flight`: ES idle, sin juego ni procesos de lanzamiento; árbol protegido coincide con baseline.

### Lote 3 — mame/atarisy1.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 3 — mame/atluspsx.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 3 — mame/atpsx.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 3 — mame/bctvidbs.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 3 — mame/big10.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/bigappg.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/bigdeal.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/bigfight.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/bigfight.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/blazlaz.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/bldyror2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/buggyboy.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/casino5.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/cbaj.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/cball.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/cclownz.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/cd32.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/chplftb.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/chplftb.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/cmast91.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/cmaster.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/cmv4.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/comg076.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/comg128.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/connect4.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/coronatn.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 3 — mame/crysbios.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 4 — mame/cubeqst.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/dacholer.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/darkhleg.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/ddux.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/dealem.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/deroon.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/deroon.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/deroon.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/doapp.zip

| Tipo | Ruta |
| --- | --- |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/doapp.cfg` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/dragoona.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/dragoona.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/dragoona.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/dsftkd.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/dstage.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/dynwar.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/ertictac.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/evosocc.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/fbait2bc.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/fbaitbc.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/fbaitmc.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/feversos.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/feversos.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/feversos.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/ffight2b.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/finalapr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/fishfren.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/fitegolf.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/fitegolf.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/hi/fitegolf.hi` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/fiveside.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/flamegun.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/fredmem.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 4 — mame/freezeat.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/funcube4.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/galastrm.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/galgbios.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 5 — mame/gauntdl.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gauntleg.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gdarius2.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/gdarius2.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gekisou.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gepoker.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/ghlpanic.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gldncrwn.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gloc.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/glpracr3.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/goodejaa.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gprider.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gradius4.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gs4002.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gt103.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gt103a.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gtrfrk2m.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/gtrfrks.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/guab.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/guts.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/guts.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/hi/guts.hi` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/guts.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/heatbrlu.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/heatbrlu.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/hi/heatbrlu.hi` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/hoops95.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/hvnsgate.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/hyperath.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/hyprdriv.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/invasnab.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/jockeygp.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/jojo.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/jojoba.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/jokpoker.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/jolyjokr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/kamikaze.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/kamikaze.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/hi/kamikaze.hi` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/kdynastg.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/kinstb.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/konam80s.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/konamigv.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 5 — mame/kov2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/kov2p.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs, /userdata/system/logs/controller_selector.log, /userdata/system/logs/controller_selector.log.1, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/kviper.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 5 — mame/ladylinr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/lbgrande.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/m_bdrwho.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/martmast.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/maxaflex.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 5 — mame/megat3.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/mf_bdash.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/mfjump.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 5 — mame/midnrun.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/misncrft.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/mk4.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/monopldx.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/monopoly.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/mpu4met0.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/mpu4tst2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/mpu4utst.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/multigam.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/multigm3.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/mvp.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log

### Lote 6 — mame/mvsc.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/mvsc.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/hi/mvsc.hi` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/mvsc.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/nagano98.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/nbapbp.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/ncb3.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/neotris.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/nratechu.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pacapp2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pacappsp.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pacnpal.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/pacnpal.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/paradice.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pasha2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pbball96.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pbballex.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pdrift.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pgear.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/pgear.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/hi/pgear.hi` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/pgear.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pitboss.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pitbossm.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pocketrc.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/poker41.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pokio.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/polepos.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/ppcar.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/psarc95.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 6 — mame/pulltabs.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/puzzli2.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/puzzli2.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/pyramid.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/qb3.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/qdrmfgp.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/qdrmfgp2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/qntoond.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/qos.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/quintoon.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/radikalb.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/rcasino.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/rdft.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/rdft2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/re900.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/redearth.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/rfjet.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 6 — mame/ridgerac.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/salarymc.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/scfinals.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/scfinals.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/scfinals.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/schery97.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/scorpion.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/screenpl.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/senkyu.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sfbonus.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sfiii2n.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sfiii3n.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sfiiin.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sfruitb.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sfzch.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/shngmtkb.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sia2650.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log

### Lote 7 — mame/sidebs.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sidebs2.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sidewndr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/simpbowl.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/skill98.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/slotsnl.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sltblgpo.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sltblgtk.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/smoto20.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/speedrcr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/speedup.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sqix.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/ssf2ghw.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/ssf2t.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log

### Lote 7 — mame/ssf2xjr1.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/ssf2xjr1.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/ssf2xjr1.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/ssipkr24.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/starsldr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/strtdriv.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/superbwl.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/suplup.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/surfplnt.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/svg.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sws98.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/sys573.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 7 — mame/taitogn.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 7 — mame/taitotz.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 7 — mame/tblkkuzu.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/tecmowcm.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/tenkomor.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/tenthdeg.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/terabrst.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/theglad.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/tm4k.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/tm7k.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/trivialp.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 7 — mame/twinbrat.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 8 — mame/tx1.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 8 — mame/vaportrx.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 8 — mame/viprp1.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 8 — mame/vr.zip

| Tipo | Ruta |
| --- | --- |
| CREATED | `/userdata/saves/mame/mame2003-plus/cfg/vr.cfg` |
| CREATED | `/userdata/saves/mame/mame2003-plus/hi/vr.hi` |
| CREATED | `/userdata/saves/mame/mame2003-plus/nvram/vr.nv` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/cfg/default.cfg` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/hi` |
| MODIFIED | `/userdata/saves/mame/mame2003-plus/nvram` |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 8 — mame/vspsx.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: sin cambios detectados

### Lote 8 — mame/weddingr.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 8 — mame/windheat.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite

### Lote 8 — mame/witch.zip

| Tipo | Ruta |
| --- | --- |
| (sin escrituras en árboles protegidos) |

- Restore: **VERIFIED**
- Logs/health database: /userdata/system/logs/controller_selector.log, /userdata/system/logs/display.log, /userdata/system/logs/es_launch_stderr.log, /userdata/system/logs/es_launch_stdout.log, /userdata/system/state/game_health.sqlite
