# Causas raíz y grupos de fallos

Actualizado: 2026-11-16. Este informe agrupa problemas de sistema y contenido; los resultados por juego siguen en `full_game_certification.csv` y los issues detallados en `arcade_issues.csv`.

## Grupos vigentes

| Grupo | Afectados conocidos | Estado | Evidencia / acción |
|---|---:|---|---|
| `MAME078PLUS_SIGSEGV` | 1 (`mvp`) | ABIERTO | SIGSEGV de RetroArch, exit -11. Mantener en reparación y analizar core/driver por separado; no reintentar en la cola normal. |
| `MAME_ROMSET_CRC_MISMATCH` | 1 (`hoops95`) | ABIERTO | `hoops.b2`: CRC esperado `a1dc3519`, actual `b54c63d1`; preflight falló antes de lanzar. No alterar el ZIP. |
| `MAME_BIOS_MEMBER_MISSING` | 1 (`evosocc`) | ABIERTO | Falta `mx27l1000-alt.u14` de `crysbios`, CRC `1e8175c8`; no llegó a lanzamiento. |
| `VISUAL_BLACK_CAPTURE_SUSPECT` | 8 (`stonebal`, `bbprot`, `calibr50`, `chplftb`, `daraku`, `gunbird2`, `heberpop`, `hvymetal`) | REVISIÓN PENDIENTE | Capturas T+5/T+15 negras con proceso estable, salida 0 y restore correcto. No confirma pantalla negra real ni fallo de ROM/core. Comparar backend de captura, renderer, logs y actividad visual alternativa antes de clasificarlos como rotos. |
| `AUDIO_DEFAULT_GAMEPAD` | sistema; DS4 presente durante prueba | MITIGADO | Política activa y HDMI se mantuvo default durante Altair. Reconnect físico DS4 y persistencia post-reboot aún pendientes. |
| `HISTORICAL_RESTORE_RUNNER` | runner histórico | MITIGADO | Certificador actual usa transacciones con snapshot previo por prueba; no usar el runner antiguo que podía restaurar configuración vieja. |
| `FBNEO_DAT_REFERENCE` | preflight FBNeo | CERRADO | DAT runtime v1.0.0.03 coincide con core; esto no certifica los juegos FBNeo aún reservados. |
| `CERTIFICATION_CURSOR_STALE` | cursor de certificación | ABIERTO | Batch 6 está presente en CSV/resultados, pero agregados/cursor superior permanecen en Batch 5. `gundealr` ya está AUTO_CERTIFIED en CSV. No reanudar hasta reconciliar metadata, sin editar resultados históricos. |

## Fallos técnicos separados de sospechas visuales

La tabla de certificación muestra 9 filas `GAME_FAIL`: una SIGSEGV (`mvp`) y ocho `BLACK_SCREEN_SUSPECT` pendientes de revisión visual. Muestra 2 `STATIC_FAIL`: contenido/CRC de `hoops95` y miembro BIOS de `evosocc`. Estos conteos proceden del CSV; el checkpoint superior todavía no reconcilia con el CSV y por eso no deben sustituirse por un único contador canónico hasta corregir ese metadata.

Los sospechosos visuales no deben provocar un fallo masivo automático: el método de captura puede ser incompatible con el renderer o capturar una pantalla legítimamente oscura. No elevarlos a `GAME_FAIL_BLACK_SCREEN` sin evidencia adicional.

## Incidentes históricos mitigados

- La discrepancia `altair` solicitado → `kinstb` despachado fue explicada por estado inconsistente de EmulationStation; el control Altair posterior pasó con identidad completa. No indica fallo de MAME ni de Altair.
- `ProcessLookupError` posterior a un proceso ya terminado se trata como carrera de cleanup si exit, ES y restore están verificados.
- El publisher rechazó cambios grandes por guard. La solución es revisar y aprobar manifest one-time exacto por contenido/HEAD; el límite permanente no se reduce.

## Fuente y mantenimiento

Los estados individuales viven en `arcade_issues.csv`; resultados de juegos en `full_game_certification.csv`; cursor y transacciones en `full_game_certification_checkpoint.json`. Este resumen es derivado y debe regenerarse cuando esas fuentes cambien.
