> Snapshot histórico; los valores de red y credenciales se saneaban en esta copia cuando correspondía. No usar como estado vigente; consultar `ARCADE_CURRENT_STATE.md`.

# ESTADO ACTUAL DEL ARCADE

Fecha de verificación: 2026-11-15 (America/Argentina/Buenos_Aires)
Alcance: lectura de informes, configuración efectiva y estado runtime. No se lanzaron juegos ni se ejecutaron pruebas SMART. No se modificaron configuraciones, ROMs, cores, mappings, saves, BIOS o EmulationStation. Se creó únicamente este informe.

## Resumen

- Inventario auditado: **1.397 juegos arcade reales** (MAME 1.308 + FBNeo 89; soporte excluido según `ARCADE_AUDIT_REPORT.md`).
- **1.191 BOOT_OK acumulados**: 1.147 históricos + 35 del smoke de noviembre + 9 resultados PASS del piloto MAME. BOOT_OK demuestra arranque sostenido según el criterio del piloto; no certifica controles físicos ni juego completo.
- Pendientes de resolución: **206** (1.397 menos 1.191). Los reportes antiguos, el smoke y los pilotos no mantienen una sola clasificación acumulada reconciliada; se detallan abajo las cifras de fuente y sus límites para no presentar categorías solapadas como una suma exacta.
- Overrides individuales activos hacia MAME actual: **9**. Default global continúa siendo `mame078plus`.
- Última tanda: BATCH 2, 2026-11-13. Se lanzaron 10 juegos MAME: 4 PASS y 6 fallaron por contenido requerido ausente/incompleto. Otros 5 casos se omitieron por estrategia de core; no se lanzaron.
- No consta una tanda posterior. **SIGUIENTE ETAPA = nuevo lote pendiente**, elegido con filtro de CRC/dependencias y sin repetir los 20 casos del piloto.
- Botoneras P1-P4 enumeradas actualmente en USB 5/6/8/7 con enlaces `event` y `js` presentes. Esto acredita detección del kernel, no respuesta física dentro del juego.
- No aparece problema crítico nuevo. Los dos segfault recientes de `mame078plus` corresponden al smoke del 13-11 y están registrados; no son nuevos al 15-11.

## Recuperación del trabajo anterior

Directorio revisado: `/userdata/system/state/arcade_audit/`.

Archivos presentes actualmente:

```text
ARCADE_4P_REPORT.md
ARCADE_AUDIT_REPORT.md
ARCADE_CHD_MISSING.md
ARCADE_CORE_COMPATIBILITY.md
ARCADE_CORE_FIX_GROUPS.md
ARCADE_CORE_PILOT_BATCH2_RESULTS.md
ARCADE_CORE_PILOT_RESULTS.md
ARCADE_CRASH_CASES.md
ARCADE_DUPLICATES_MAME_FBNEO.md
ARCADE_FAILURES.md
ARCADE_FAILURES.md.pre_failure_analysis
ARCADE_FIGHTING_CONTROLS.md
ARCADE_MANUAL_TESTS.md
ARCADE_MISSING_DEPENDENCIES.md
ARCADE_PILOT_RETEST.md
ARCADE_SMOKE_TEST_DIAGNOSIS.md
ARCADE_SMOKE_WRITE_AUDIT.md
ARCADE_SPECIAL_CONTROLS.md
arcade_core_compatibility.csv
arcade_games_audit.csv
arcade_games_audit.csv.pre_failure_analysis
arcade_games_audit.json
arcade_games_audit.json.pre_failure_analysis
arcade_support_assets.csv
build_inventory.py
checkpoint.json
checkpoint.json.pre_failure_analysis
classify_batch2_failures.py
create_batch2_backup.py
finalize_batch2_reports.py
pilot_batch2_backup_path.txt
pilot_batch2_checkpoint.json
pilot_checkpoint.json
reconcile_batch2_redearth.py
recover_batch2_mvp.py
smoke_pilot_batch2.py
smoke_pilot_runner.py
smoke_runner.py
```

También existen `pilot_runtime/`, `pilot_batch2_runtime/` y `__pycache__/`. No se usaron backups para restaurar ni se repitió ninguna prueba.

Documentación permanente consultada: `el_gordo_docs/INDICE.md`, `ESTADO.md`, `PENDIENTES.md` no existe; se consultaron los documentos específicos `CONTROLES.md`, `RUNTIME.md`, `SISTEMAS.md`, `HARDWARE.md` y `BACKUPS.md` disponibles. `INDICE.md`/`ESTADO.md` tienen fecha agosto y no reflejan esta auditoría reciente, por lo que prevalecen los informes/runtime de noviembre.

## Conteo arcade y clasificación

| Estado | Cantidad actual / dato verificable | Interpretación |
|---|---:|---|
| TOTAL | **1.397** | Inventario de MAME + FBNeo; soporte excluido. |
| BOOT_OK | **1.191** | 1.147 históricos + 35 smoke + 9 PASS MAME. |
| Sin resolver | **206** | Total menos BOOT_OK acumulados. |
| FAIL confirmados | **20** | 11 fallos históricos + 9 fallos actuales de contenido/dependencias (3 del smoke y 6 del piloto; estos últimos redistribuidos abajo). |
| CURRENT_CORE_REJECTED | **168** | Quedan del grupo de 181 rechazos originales tras 8 PASS bajo MAME actual y 5 casos re-clasificados por sus fallos de contenido con MAME actual. |
| MISSING_CHD | **3 confirmados en BATCH 2** | `redearth`, `jojo`, `hyperath`. La lista estática `ARCADE_CHD_MISSING.md` tiene 22 sets requeridos ausentes, que no son todos fallos de boot confirmados. |
| MISSING_CONTENT | **5** | 3 fallos de contenido clasificados en el análisis del smoke + `mvp` y `nbapbp` en BATCH 2. |
| CRASH | **0 crash actual sin resolver confirmado** | Los dos crashes confirmados en `ARCADE_CRASH_CASES.md` (`mvp`, `sia2650`) se revalidaron: `sia2650` BOOT_OK con override y `mvp` falló por contenido requerido bajo MAME actual. El crash de `mame078plus` para `mvp` permanece como antecedente del core default, no como resultado actual del core probado. |
| UNKNOWN | **18** | Casos sin dispatch confirmado en el smoke; no son fallos confirmados del core. |
| ROMSET incompleto | **1** | `jojoba`, ocho miembros SIMM5 ausentes en BATCH 2. Se incluye en los 20 FAIL confirmados. |

Las categorías desglosadas son disjuntas con el último resultado conocido: 20 FAIL + 168 rechazos del core default + 18 UNKNOWN = 206 sin BOOT_OK. En los 20 FAIL, los 9 nuevos casos se desglosan en 3 MISSING_CHD + 5 MISSING_CONTENT + 1 ROMSET; los otros 11 son fallos históricos. Los 9 PASS del piloto salen de los estados previos del smoke (8 rechazos y 1 crash revalidado). Por eso el checkpoint bruto conserva los estados anteriores, pero el total efectivo se obtiene aplicando el resultado posterior del piloto.

El checkpoint bruto tiene 239 resultados de smoke; el análisis posterior corrigió la clasificación de salidas inmediatas/crashes/contenido. No recalcular conteos leyendo sólo `boot_status` de `arcade_games_audit.csv`, porque ese CSV no incorpora la reconciliación de ambos pilotos. El conteo acumulado efectivo se calculó con 1.147 históricos, 35 smoke PASS y 9 pilotos PASS, sin volver a probar juegos. BOOT_OK no certifica controles físicos ni juego completo.

## Core MAME y configuración actual

Fuente activa inspeccionada: `/userdata/system/batocera.conf`; default de sistema en `/usr/share/emulationstation/es_systems.cfg` (`mame078plus`). No hay override global `mame.core`; las 9 líneas actuales son exclusivamente por ROM. El core global **no fue cambiado**.

| GAME | DEFAULT CORE | OVERRIDE CORE | ESTADO | ORIGEN DE VALIDACIÓN |
|---|---|---|---|---|
| ffight2b | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 1, 5/5 PASS |
| altair | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 1, 5/5 PASS |
| apache3 | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 1, 5/5 PASS |
| blazlaz | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 1, 5/5 PASS |
| cubeqst | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 1, 5/5 PASS; requiere trackball |
| sia2650 | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 2; antes crash con default |
| evosocc | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 2; 4P, input físico pendiente |
| hoops95 | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 2; 4P, input físico pendiente |
| funcube4 | mame078plus | mame (MAME current libretro) | PASS; mantenido; restore VERIFIED | BATCH 2; entrada especial gambling/lightgun |

Lista efectiva actual (9): `ffight2b`, `altair`, `apache3`, `blazlaz`, `cubeqst`, `sia2650`, `evosocc`, `hoops95`, `funcube4`.

No hay overrides activos para `mvp`, `redearth`, `jojo`, `jojoba`, `nbapbp`, `hyperath`; fueron revertidos después de fallar con MAME actual. Tampoco se aplicó override a `gprider`, `sfiii2n`, `sfiii3n`, `sfiiin`, `neotris`; fueron SKIP_WRONG_STRATEGY, no lanzados.

## Piloto MAME

**BATCH 1 (13-11): 5/5 PASS** con MAME actual: `ffight2b`, `altair`, `apache3`, `blazlaz`, `cubeqst`. Cinco overrides mantenidos, restore verificado, sin cambio global.

**BATCH 2 (13-11): 4/10 PASS entre los lanzados; 4/15 total candidatos.**

- PASS / override mantenido / restore verificado: `sia2650`, `evosocc`, `hoops95`, `funcube4`.
- Fallos / override revertido / restore verificado: `mvp` MISSING_CONTENT; `redearth` MISSING_CHD; `jojo` MISSING_CHD y ROM dependiente; `jojoba` ROMSET incompleto; `nbapbp` MISSING_CONTENT; `hyperath` MISSING_CHD.
- SKIP_WRONG_STRATEGY / no lanzamiento / sin escritura: `gprider`, `sfiii2n`, `sfiii3n`, `sfiiin`, `neotris`.
- Resultado acumulado de selección: 9 PASS de 20 candidatos (5/5 BATCH 1 y 4/15 BATCH 2). Restauraciones: BATCH 1 VERIFIED; BATCH 2 15/15 (10 ejecutados/restaurados, 5 omitidos sin escritura).
- Último lote ejecutado: **BATCH 2, 10 juegos lanzados**. No hubo tanda posterior. Por lo tanto, **SIGUIENTE ETAPA = nuevo lote pendiente**, no repetir las dos tandas previas.

## Botoneras P1-P4

Se cruzaron `/dev/input/by-path`, `controller_technical.json`, el `controller_dispatcher` activo y enumeración USB. Los cuatro son `DragonRise Inc. Generic USB Joystick` (`0079:0006`).

| Jugador | USB | event | js | Detección |
|---|---:|---|---|---|
| P1 | 5 | `/dev/input/event17` | `/dev/input/js0` | Sí |
| P2 | 6 | `/dev/input/event18` | `/dev/input/js1` | Sí |
| P3 | 8 | `/dev/input/event20` | `/dev/input/js3` | Sí |
| P4 | 7 | `/dev/input/event19` | `/dev/input/js2` | Sí |

Asignación técnica coincide con el dispatcher: P1=USB5, P2=USB6, P3=USB8, P4=USB7. Resultado: **detectados correctamente a nivel USB/kernel/configuración**. No hay prueba física actual de direcciones, botones 1-6, orden in-game ni participación simultánea 4P.

## Salud actual breve

- CPU: i5-12400F (según documentación/hardware); procesos normales visibles. EmulationStation en ejecución; Xorg en ejecución.
- Temperatura CPU: paquete `x86_pkg_temp` **40 °C** en lectura actual.
- RAM: **15 GiB total; 1,6 GiB usados; 13 GiB disponibles**.
- GPU: GTX 1060 3 GB detectada por PCI; kernel driver `nvidia`; módulo NVIDIA cargado, versión 580.126.09. `nvidia-smi` no disponible en comprobaciones documentadas del piloto.
- Resolución activa: **1920×1080 a 60 Hz**, HDMI-0 primary (Xrandr en `DISPLAY=:0`).
- USB: hub, adaptadores de red/Bluetooth y cuatro botoneras enumeradas; Toshiba USB conectado. Sin desconexión USB nueva observada en la lectura de `dmesg`.
- Discos: `/userdata` en `/dev/sda2` ext4; `/media/BATOCERA_ROMS` en `/dev/sdb1` ext4; `/media/ROMS` en `/dev/sdc1` ext4; `/userdata/roms` mergerfs sobre las rutas personalizadas. `/media/ROMS`: 3,6T total, 30% usado.
- Logs/kernel: no se identificó CRITICAL nuevo, fallo NVIDIA/Xid o error de I/O reciente. Hay dos mensajes de segfault de `mame078plus` fechados 13-11, correspondientes a la auditoría; están documentados, no son nuevos. Logs recientes del 13-11 muestran el fallo esperado de `hyperath` por CHD ausente. `ProcessLookupError` de limpieza del launcher no implica por sí solo fallo del core y ya fue revisado en el informe del piloto.

## EmulationStation

- CPU observado por `ps`: **9,4%** en un muestreo instantáneo; `NLWP=27` threads; RSS aproximado 3,4% de RAM. La media acumulada no equivale a una medición sostenida. El baseline posterior al fix (~30% de un hilo) no se reproduce en este instante, pero no afirmo regresión ni mejora sostenida sin muestreo comparable.
- Resolución de X: **1920×1080 @ 60 Hz**.
- VSync efectivo de EmulationStation: **no determinable de forma concluyente en esta lectura SSH**. La configuración de RetroArch tiene `video_vsync=true`, y el launcher registra `SDL_RENDER_VSYNC=1` para juegos; eso no prueba por sí solo el VSync efectivo del proceso de EmulationStation.
- Renderer de EmulationStation: **no expuesto en configuración/log consultado**, queda por verificar si se necesita. Xorg activo.

## SMART Seagate (lectura, sin tests)

Disco `/dev/sdb`, Seagate `ST1000DM010-2EP102`, serial `ZN1J6BJ4`; `SMART overall-health: PASSED`.

| Atributo | Actual | Baseline solicitado | Comparación |
|---|---:|---:|---|
| Reallocated_Sector_Ct | 8 | 8 | Igual |
| Reported_Uncorrect | 14 | 14 | Igual |
| Current_Pending_Sector | 0 | 0 | Igual |
| Offline_Uncorrectable | 0 | 0 | Igual |
| Temperatura disco | 33 °C | — | Lectura actual |

No se inició SMART short/long.

## Backups

Existe `/media/ROMS/ARCADE_BACKUPS/`. Presentes los backups principales recientes:

- `ARCADE_CORE_PILOT_2026-11-13_093236`
- `ARCADE_CORE_PILOT_BATCH2_2026-11-13_104010`
- `ARCADE_SMOKE_TEST_SAVES_2026-11-13_011039`
- también `BASELINE_PRE_CAMBIOS_2026-09-25_234721` y `EMULATIONSTATION_VSYNC_FIX_2026-09-26_185430`.

Sólo se confirmó presencia; no se recalcularon hashes de árboles grandes.

## Pendientes (máximo 10)

### JUEGOS

1. Diseñar el próximo lote pequeño de MAME usando candidatos con CRC compatible y sin CHD/ROMOF/dependencias ausentes; excluir los 20 ya pilotados y actualizar/reconciliar sus estados antes de ejecutarlo.
2. Resolver por diagnóstico de archivos los fallos confirmados de CHD/contenido/ROMSET (`redearth`, `jojo`, `jojoba`, `nbapbp`, `hyperath`, `mvp`) antes de considerar nuevos overrides.
3. Revisar los 18 sin dispatch y los casos `UNKNOWN` con evidencia de launcher. No hay crash actual sin resolver confirmado en el último análisis; el crash previo de `mvp` quedó re-clasificado por la prueba de contenido de MAME actual.

### CONTROLES

4. Verificación física por jugador P1-P4: direcciones, Start/Coin y botones 1-6 en juego representativo, confirmando que una pulsación accione una sola función.
5. Prueba física de los juegos 4P que ya pasaron (`evosocc`, `hoops95`) y validación de simultaneidad/orden.
6. Prueba de pelea priorizada desde `ARCADE_FIGHTING_CONTROLS.md`, empezando por casos de seis botones y antecedentes de doble acción; revisar UMK3 como caso manual ya documentado.

### HARDWARE

7. Mantener seguimiento SMART pasivo del Seagate y registrar variaciones frente al baseline; sin pruebas forzadas ni acción por esta lectura estable.

### SOFTWARE

8. Reconciliar CSV/checkpoint e informes del smoke con los resultados de ambos pilotos para que cada juego tenga un único estado vigente; documentar renderer/VSync efectivo de ES con una lectura comparable.

### EXPERIENCIA DE USUARIO

9. Tras juegos y controles, revisar colecciones/catálogo: ocultar o clasificar los estados no-juego y hacer visibles los grupos “listos para jugar”, “requieren validación” y “prueba manual”.
10. Después de estabilizar arcade, continuar revisión de otros sistemas según `PENDIENTES.md`/`SISTEMAS.md` (el primero no existe actualmente).

## Orden recomendado para continuar

1. Reconciliar los datos existentes del smoke y pilotos (trabajo documental/lectura; no volver a lanzar juegos ya probados).
2. Preparar un nuevo lote de candidatos MAME por CRC y dependencias; hacer backup específico y validar restores por juego cuando se autorice la ejecución. El lote BATCH 2 tiene evaluación global “MALO” y no conviene elegir candidatos sólo por metadata.
3. Resolver contenidos ausentes y ajustar estrategia de core caso por caso, manteniendo intacto el core global.
4. Validar físicamente P1-P4 y asignación de seis botones por jugador.
5. Probar los juegos 4P con BOOT_OK y verificar orden/simultaneidad.
6. Probar peleas, primero las de seis botones y los casos históricos de doble acción.
7. Mejorar colecciones y catálogo.
8. Revisar los otros sistemas.

## Respuestas directas

1. **¿Dónde nos quedamos?** BATCH 2 terminó el 13-11; 9/20 candidatos del piloto pasan con MAME actual y mantienen override. El smoke de inventario está completo, pero el estado acumulado no quedó reconciliado tras los pilotos.
2. **Último lote ejecutado:** BATCH 2; 10 juegos lanzados, cuatro PASS y seis fallos por contenido. Cinco casos se omitieron sin lanzar.
3. **¿Cuántos funcionan?** 1.191 han demostrado BOOT_OK; el input y el juego completo no están certificados para todos.
4. **¿Cuántos sin resolver?** 206 sin BOOT_OK acumulado.
5. **Overrides activos:** nueve listados arriba: `ffight2b`, `altair`, `apache3`, `blazlaz`, `cubeqst`, `sia2650`, `evosocc`, `hoops95`, `funcube4`.
6. **¿P1-P4 detectados?** Sí por USB/event/js y coinciden con `controller_technical.json`/dispatcher; funcionamiento físico in-game todavía sin validar.
7. **¿Problema crítico nuevo?** No observado. Los errores vistos son históricos del smoke/piloto y fallos esperados de contenido; no aparece regresión crítica posterior.
8. **¿Qué hacer ahora?** Reconciliar documentalmente los estados existentes y preparar, sin ejecutarlo todavía, un nuevo lote de candidatos filtrados por CRC/dependencias. La siguiente etapa de juegos queda pendiente hasta decisión explícita.
9. **¿Qué hacer después?** Ejecutar un lote pequeño sólo cuando se autorice; luego validar P1-P4, seis botones, 4P, peleas, catálogo y finalmente otros sistemas.
10. **¿Qué no conviene tocar?** Core MAME global, configuraciones/mappings de controles, `controller_dispatcher`, ROMs/CHD/BIOS/saves, EmulationStation, drivers, sistema base y backups históricos. No repetir pilotos ya cerrados ni pruebas SMART.

## Fuentes primarias consultadas

- `/userdata/system/state/arcade_audit/ARCADE_AUDIT_REPORT.md`
- `/userdata/system/state/arcade_audit/ARCADE_CORE_COMPATIBILITY.md`
- `/userdata/system/state/arcade_audit/ARCADE_CORE_FIX_GROUPS.md`
- `/userdata/system/state/arcade_audit/ARCADE_CORE_PILOT_RESULTS.md`
- `/userdata/system/state/arcade_audit/ARCADE_CORE_PILOT_BATCH2_RESULTS.md`
- `/userdata/system/state/arcade_audit/ARCADE_FAILURES.md`
- `/userdata/system/state/arcade_audit/ARCADE_MANUAL_TESTS.md`
- `/userdata/system/state/arcade_audit/ARCADE_4P_REPORT.md`
- `/userdata/system/state/arcade_audit/ARCADE_FIGHTING_CONTROLS.md`
- `/userdata/system/state/arcade_audit/ARCADE_SPECIAL_CONTROLS.md`
- `/userdata/system/state/arcade_audit/ARCADE_SMOKE_WRITE_AUDIT.md`
- `/userdata/system/state/arcade_audit/ARCADE_SMOKE_TEST_DIAGNOSIS.md`
- `/userdata/system/state/arcade_audit/ARCADE_PILOT_RETEST.md`
- `/userdata/system/state/arcade_audit/ARCADE_CHD_MISSING.md`
- `/userdata/system/state/arcade_audit/ARCADE_MISSING_DEPENDENCIES.md`
- `/userdata/system/state/arcade_audit/checkpoint.json`, `pilot_checkpoint.json`, `pilot_batch2_checkpoint.json`
- Runtime: `batocera.conf`, `es_systems.cfg`, `controller_technical.json`, `/dev/input/by-path`, logs/kernel, SMART y presencia de backups.
