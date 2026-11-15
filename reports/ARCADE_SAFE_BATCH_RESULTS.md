# Resultados — lote seguro de overrides MAME

- Fecha: 2026-11-15 (reconciliación; 2026-11-15T05:42:22Z).
- Estado: **SIN CANDIDATOS ELEGIBLES; no se lanzó ningún juego.**
- Fuente exclusiva: `ARCADE_NEXT_SAFE_BATCH.md` y `arcade_next_safe_batch.csv`.
- El CSV tiene 0 filas de candidatos. El Markdown declara lote principal 0/20 y reserva 0/20.
- Candidatos evaluados en la lista preparada: 0. Contexto: 56 candidatos estáticos `USE_MAME_CORE_X` no tienen piloto con MAME actual, pero todos ya fueron lanzados con `mame078plus`; el análisis fuente los excluye por historial. No se escogieron fuera del lote.

## Resultado de esta tanda

| Métrica | Resultado |
|---|---:|
| Candidatos del lote | 0 |
| Lanzados | 0 |
| Omitidos del lote | 0 |
| BOOT_PASS | 0 |
| BOOT_FAIL | 0 |
| Porcentaje PASS | No aplica (0 candidatos lanzados) |
| Overrides nuevos/eliminados | 0 / 0 |
| Restore verificado | 0/0; N/A porque no hubo lanzamientos |
| 3P/4P recuperados | 0 |
| Fighting recuperados | 0 |
| Controles especiales | 0 |

No hay listas PASS, FAIL o SKIPPED: no existen entradas en el lote preparado. Por la misma razón, la matriz `arcade_core_compatibility.csv` se conserva sin cambios; no hay resultado de esta tanda que añadir y no se altera evidencia histórica.

## Reconciliación del sistema

- Core global: `mame078plus`, **no cambiado**.
- Overrides activos antes y después (nueve): `ffight2b`, `altair`, `apache3`, `blazlaz`, `cubeqst`, `sia2650`, `evosocc`, `hoops95`, `funcube4`. Coinciden con `batocera.conf` y la lista documentada.
- Core moderno disponible: `/usr/lib/libretro/mame_libretro.so`; core `mame078plus` disponible. No se usaron para lanzar juegos.
- EmulationStation: PID 2929 confirmado con `batocera-es-swissknife --espid`.
- Sin procesos RetroArch/MAME ni tester huérfanos detectados en la consulta de procesos.
- `controller_dispatcher --self-test`: `DISPATCHER_SELF_TEST_OK`.
- `controller_dispatcher --diagnose` y `sdl2-jstest --list`: cuatro DragonRise presentes, mapeo sin duplicados: P1 USB5/event17, P2 USB6/event18, P3 USB8/event20, P4 USB7/event19. No se modificó el mapping.
- Estado del sistema: **OK**, sin regresión atribuible a esta tanda. No aplican controles térmicos ni comprobaciones periódicas por cada cinco juegos, pues no hubo lanzamientos.

## Hallazgos de compatibilidad heredados (no son fallos de esta tanda)

- CHD requerido ausente según `ARCADE_CHD_MISSING.md`: `darkhleg`, `dsftkd`, `dstage`, `fbait2bc`, `fbaitbc`, `fbaitmc`, `gauntdl`, `gauntleg`, `gtrfrk2m`, `gtrfrks`, `hyperath`, `hyprdriv`, `jojo`, `nagano98`, `qdrmfgp`, `qdrmfgp2`, `redearth`, `salarymc`, `simpbowl`, `tenthdeg`, `vaportrx`, `weddingr`; Los diez casos históricos adicionales son `area51mx`, `blitz`, `blitz2k`, `blitz99`, `calspeed`, `carnevil`, `cryptklr`, `maxforce`, `sfrush`, `wg3dh`. BATCH 2 confirmó por log `redearth`, `jojo`, `hyperath`.
- Dependencias/ROM: parents/ROMOF no localizados: `aerofgts`→`coh1002v`, `bigdeal`→`bonuscrd`, `bldyror2`→`coh1002e`, `cbaj`, `flamegun`, `glpracr3`, `mfjump`, `shngmtkb`, `tblkkuzu`→`coh1002m`, `hvnsgate`→`coh1001l`. Archivos documentados: `armwar` y `ssf2t` requieren `.key`; `polepos` requiere siete miembros listados en `ARCADE_NEXT_SAFE_BATCH.md`. BATCH 2 registró faltantes para `mvp`, `nbapbp` y miembros de `jojoba`.
- ROMset: quedan clases CRC parcial/no coincidente documentadas en `ARCADE_NEXT_SAFE_BATCH.md`; no se relanzaron ni clasificaron como fallos nuevos.

## Decisiones

1. El override individual sigue siendo una estrategia segura bajo evidencia histórica: nueve overrides individuales siguen activos, los pilotos previos registraron PASS con restore verificado y el core global permanece `mame078plus`. Esta tanda no añade validación nueva.
2. Porcentaje de PASS del lote: no definido; hubo 0 candidatos y 0 lanzamientos.
3. No continuar automáticamente con otro lote. Para habilitar una nueva tanda, primero debe prepararse un lote con candidatos elegibles según las reglas y evidencia actuales.
4. Los casos que requieren CHD son los enumerados arriba; se distinguen de los fallos de ROM/dependencias y ROMset.
5. No hay juegos recuperados en esta tanda para priorizar a prueba física. Prioridad pendiente heredada: fighting de BATCH 1 si se requiere certificación física; `cubeqst` queda sujeto a trackball. No se certificó ningún control aquí.
6. Juegos 3P/4P recuperados: ninguno. Fighting <=6 botones recuperados: ninguno. UMK3 sigue sin resolverse por esta auditoría.
7. No existe evidencia para cambiar el core global: las pruebas previas muestran recuperaciones con override individual y el core global sigue estable como `mame078plus`; no cambiarlo.

## Cambios y validaciones

- Creado `safe_batch_checkpoint.json` con fuentes hashadas, candidatos, contadores, overrides antes/después, estado de restore y estado runtime.
- Creado este informe. No se cambió `arcade_core_compatibility.csv` porque la tanda no produjo resultados por juego.
- No hubo cambios de configuración ni escrituras de juego que requirieran restore.
- No se ejecutaron juegos ni pruebas físicas.
- Exportación filtrada sincronizada a `arcade_audit_git/`: 38 archivos de fuente regular permitidos; escáner de secretos PASS y escáner de payloads PASS. No se hizo commit ni push. El script integral no se ejecutó porque incluye commit y puede intentar push; además, `git` no está instalado en este entorno.
