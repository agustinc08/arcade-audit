# Causas raíz y grupos de fallos

Actualizado: 2026-11-16. Este informe agrupa problemas de sistema y contenido; los resultados por juego siguen en `full_game_certification.csv` y los issues detallados en `arcade_issues.csv`.

## Grupos vigentes

| Grupo | Afectados conocidos | Estado | Evidencia / acción |
|---|---:|---|---|
| `MAME078PLUS_SIGSEGV` | 1 (`mvp`) | ABIERTO | SIGSEGV de RetroArch, exit -11. Mantener en reparación y analizar core/driver por separado; no reintentar en la cola normal. |
| `MAME_ROMSET_CRC_MISMATCH` | 1 (`hoops95`) | ABIERTO | `hoops.b2`: CRC esperado `a1dc3519`, actual `b54c63d1`; preflight falló antes de lanzar. No alterar el ZIP. |
| `MAME_BIOS_MEMBER_MISSING` | 1 (`evosocc`) | ABIERTO | Falta `mx27l1000-alt.u14` de `crysbios`, CRC `1e8175c8`; no llegó a lanzamiento. |
| `VISUAL_BLACK_CAPTURE_SUSPECT` | 19 (`stonebal`, `bbprot`, `calibr50`, `chplftb`, `daraku`, `gunbird2`, `heberpop`, `hvymetal`, `metlhawk`, `opaopa`, `passsht`, `pignewt`, `primrag2`, `raveracw`, `ripoff`, `sailormn`, `spacewar`, `tetris`, `vigilant`) | REVISIÓN PENDIENTE | Capturas negras sospechosas. Los casos nuevos de Batches 8–10 muestran runtime estable ~20 s, exit 0, HDMI PASS y RESTORE_VERIFIED. En tetris/vigilant hubo dos capturas negras idénticas. Posible incompatibilidad de captura/renderer; no es causa raíz probada ni confirma pantalla negra real. Revisar backend antes de reclasificar. |
| `AUDIO_DEFAULT_GAMEPAD` | sistema; DS4 presente durante prueba | MITIGADO | Política activa y HDMI se mantuvo default durante Altair. Reconnect físico DS4 y persistencia post-reboot aún pendientes. |
| `HISTORICAL_RESTORE_RUNNER` | runner histórico | MITIGADO | Certificador actual usa transacciones con snapshot previo por prueba; no usar el runner antiguo que podía restaurar configuración vieja. |
| `FBNEO_DAT_REFERENCE` | preflight FBNeo | CERRADO | DAT runtime v1.0.0.03 coincide con core; esto no certifica los juegos FBNeo aún reservados. |
| `CERTIFICATION_CURSOR_STALE` | cursor de certificación | CERRADO / RESUELTO | Agregados/cursor derivados reconciliados desde CSV y 511 records; Batch 6 delta verificado. CSV y resultados individuales no se modificaron. NEXT_GAME=`mame:/userdata/roms/mame/machridr.zip`. Ver `CERTIFICATION_RECONCILIATION_RESULT.md`. |

## Fallos técnicos separados de sospechas visuales

La tabla de certificación muestra 20 filas `GAME_FAIL`: una SIGSEGV (`mvp`) y 19 `BLACK_SCREEN_SUSPECT` pendientes de revisión visual. Muestra 2 `STATIC_FAIL`: contenido/CRC de `hoops95` y miembro BIOS de `evosocc`. Los totales actuales son derivados del CSV/checkpoint tras Batch 9; no se cambiaron resultados individuales al actualizar esta agrupación. Los contadores canónicos actuales están en `full_game_certification_checkpoint.json`; el reporte de reconciliación describe semánticas y hashes.

Los sospechosos visuales no deben provocar un fallo masivo automático: el método de captura puede ser incompatible con el renderer o capturar una pantalla legítimamente oscura. No elevarlos a `GAME_FAIL_BLACK_SCREEN` sin evidencia adicional.

## Incidentes históricos mitigados

- La discrepancia `altair` solicitado → `kinstb` despachado fue explicada por estado inconsistente de EmulationStation; el control Altair posterior pasó con identidad completa. No indica fallo de MAME ni de Altair.
- `ProcessLookupError` posterior a un proceso ya terminado se trata como carrera de cleanup si exit, ES y restore están verificados.
- El publisher rechazó cambios grandes por guard. La solución es revisar y aprobar manifest one-time exacto por contenido/HEAD; el límite permanente no se reduce.

## Fuente y mantenimiento

Los estados individuales viven en `arcade_issues.csv`; resultados de juegos en `full_game_certification.csv`; cursor y transacciones en `full_game_certification_checkpoint.json`. Este resumen es derivado y debe regenerarse cuando esas fuentes cambien.

| `CERTIFIER_MARKER_COLLISION` | 1 (`mame/xmultipl.zip`, pre-launch) | ABIERTO | El manifest muestra marker ausente en PRE_STATE y presente en POST_STATE; `open('x')` falló con `FileExistsError` antes de `/launch`. Restore volvió a PRE_STATE, pero el contenido/escritor concurrente no quedó preservado. No reanudar lanzamientos hasta implementar/verificar exclusión mutua y abort seguro ante marker ajeno. Ver `reports/PRIORITY_CERTIFICATION_BATCH_11.md`. |

## Estado de certificación después de Batch 11 parcial

La tabla y los resultados individuales permanecen intactos. Conteos derivados actuales: 897 `AUTO_CERTIFIED`, 20 `GAME_FAIL`, 2 `STATIC_FAIL`, 22 `NEEDS_REPAIR`, 919 transacciones, 921 records y 1 `ENGINE_FAIL` activo. Batch 11 no está cerrado; sus nueve AUTO_PASS son válidos y `xmultipl` no constituye un fallo de juego.
