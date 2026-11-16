# Bloqueo de reconciliación de certificación

- Estado: `RESUELTO` — 2026-11-16.
- Causa: el runner de Batch 6 actualizó correctamente los estados por juego en CSV y añadió resultados por juego, pero no recalculó agregados/cursor de nivel superior ni `latest_batch`. `gundealr.zip` permaneció como cursor aunque ya estaba procesado. El reporte inicial también atribuyó al delta de Batch 6 dos `STATIC_FAIL` que ya existían en el checkpoint anterior.

## Verificación

- Se comparó el CSV activo contra el export previo a Batch 6: mismas 8426 filas, sin altas/bajas, exactamente 100 filas cambiadas (98 AUTO_CERTIFIED, 2 GAME_FAIL).
- El delta del arreglo `results` es exactamente 100: 98 AUTO_PASS y 2 GAME_FAIL. Los dos STATIC_FAIL (`hoops95`, `evosocc`) son registros previos y no se duplicaron.
- Resultados individuales: 511 records, 510 identidades únicas, 509 transacciones identificadas; 1 retry/duplicado legítimo de identidad, resuelto por el último AUTO_PASS.
- 509/509 transacciones tienen `RESTORE_VERIFIED`; 0 restore failures; 0 engine failures activos. El ENGINE_FAIL histórico de PC Engine está seguido por AUTO_PASS y se considera resuelto.
- La cola del certifier produjo 20 candidatos pendientes válidos. El primero es `mame:/userdata/roms/mame/machridr.zip`; está instalado, NOT_TESTED, adapter READY y preflight PASS.

## Cambio aplicado

Se actualizaron sólo metadatos derivados del checkpoint: agregados inequívocos, alias histórico `attempted_new` (transacciones de lanzamiento), `latest_batch=priority_batch_6` y cursor. `arcade_master_checkpoint.json` se actualizó únicamente en PHASE_14 y `certification_counts`. No se modificó CSV, ningún resultado individual, orden de resultados, ROM, core, override ni mapping.

El generador de certificación ahora debe reconciliar por separado juegos únicos, records, transacciones y retries; el siguiente batch tiene un guard de cursor para impedir relanzar una fila terminal.

Historial del bloqueo conservado. Evidencia detallada: `CERTIFICATION_RECONCILIATION_RESULT.md` y `runtime/checkpoint_reconciliation_20261116T194825/pre_reconciliation_manifest.json`.
