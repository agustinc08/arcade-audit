# Bloqueo de reconciliación de certificación

- Estado: `ABIERTO` — generado el 2026-11-16 después de completar el runner de Batch 6.
- La tarea documental no modificó `full_game_certification_checkpoint.json`, `full_game_certification.csv` ni `arcade_master_checkpoint.json`.

## Discrepancia comprobada

- CSV: 8426 juegos; installed=8400; historical_boot_ok=1200; AUTO_CERTIFIED=499; GAME_FAIL=9; STATIC_FAIL=2; FLAKY=0; NEEDS_REPAIR=11.
- Checkpoint superior: attempted_new=409; auto_certified=401; next_untested=`mame:/userdata/roms/mame/gundealr.zip`; latest_batch=`priority_batch_5`; status=COMPLETE.
- Checkpoint counts/result records: AUTO_PASS=499; records=511; `next_game`=None.
- La fila CSV del `next_untested` tiene estado `AUTO_CERTIFIED`. Por tanto ese cursor no puede usarse para reanudar sin repetir un juego ya certificado.
- `arcade_master_checkpoint.json` conserva también el snapshot anterior de agregados (409 attempted / 401 auto).

## Batch 6 verificado por delta

- 100 filas de juego cambiaron desde el export anterior: 98 AUTO_CERTIFIED y 2 GAME_FAIL.
- 102 nuevos registros en `results`: 98 AUTO_PASS, 2 GAME_FAIL y 2 preflight STATIC_FAIL (sin lanzamiento); 100/100 restores de lanzamientos.
- Los dos GAME_FAIL (`heberpop`, `hvymetal`) tienen identidad correcta, HDMI, proceso estable ~20 s, exit 0 y restore; el clasificador fue `BLACK_SCREEN_SUSPECT`, queda revisión visual. No hay nuevo ENGINE_FAIL.
- El contador acumulado `ENGINE_FAIL=1` corresponde al incidente de `update_csv` en hoops95 del 15/11, resuelto/no launch, `resolved_engine_incidents` lo marca verified. No es fallo nuevo de Batch 6.

## Acción segura

- No se editó progreso ni se dedujo un nuevo NEXT_GAME a partir de la cola. El checkpoint superior y el resumen publicado no concuerdan con CSV/resultados.
- El generador `rebuild_certification_summary.py` y el generador de estado estricto deben detenerse con `REPORT_RECONCILIATION_FAIL` / `CURRENT_STATE_RECONCILIATION_FAIL` hasta una reconciliación autorizada de metadatos del checkpoint.
- No publicar un `ARCADE_CURRENT_STATE.md` con cifras únicas ni certificar un cursor reanudable mientras siga esta discrepancia.
- Próximo paso técnico: reconciliar sólo agregados/cursor desde resultados de transacción ya presentes, preservando cada resultado; verificar el cursor siguiente contra queue policy y filas no probadas. Esta tarea no ejecutó ese cambio.
