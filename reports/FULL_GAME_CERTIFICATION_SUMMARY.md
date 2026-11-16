# Resumen de certificación — RECONCILIATION FAIL

No usar los agregados anteriores como estado actual. El checkpoint superior aún indica `AUTO_CERTIFIED=401`, `ATTEMPTED_NEW=409` y `NEXT_GAME=mame:/userdata/roms/mame/gundealr.zip`, mientras que `full_game_certification.csv` registra `AUTO_CERTIFIED=499` y esa fila ya está certificada. El runner terminó Batch 6 con `next_game=null` y no actualizó `latest_batch` del checkpoint.

No se modificaron checkpoint ni CSV. No hay un `NEXT_GAME` reconciliado; no reanudar automáticamente ni publicar estadísticas como si concordaran. Consultar [bloqueo de reconciliación](CERTIFICATION_RECONCILIATION_BLOCKER.md), [Batch 6](PRIORITY_CERTIFICATION_BATCH_6.md) y las fuentes canónicas.

`CONTROL_CERTIFIED=0`; `GUEST_READY=0`. La reconciliación de agregados/cursor requiere preservar la evidencia transaccional y actualizar únicamente metadata comprobada.
