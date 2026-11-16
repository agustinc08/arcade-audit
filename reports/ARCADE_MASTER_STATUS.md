# Arcade Master Audit — índice de estado

El reporte de estado anterior fue archivado en `reports/history/ARCADE_MASTER_STATUS_2026-11-15.md`; sus cifras anteceden la certificación masiva.

El estado más reciente observado está en [`ARCADE_CURRENT_STATE.md`](ARCADE_CURRENT_STATE.md). Actualmente lleva el indicador `CURRENT_STATE_RECONCILIATION_FAIL`: el runner terminó Batch 6 y actualizó CSV/resultados, pero no actualizó varios agregados superiores ni el cursor `NEXT_GAME` del checkpoint. La documentación preservó sin cambios los checkpoints y resultados. No tomar el cursor antiguo como reanudable.

Detalle de los 100 juegos de Batch 6: [`reports/PRIORITY_CERTIFICATION_BATCH_6.md`](reports/PRIORITY_CERTIFICATION_BATCH_6.md). Discrepancia y siguiente paso seguro: [`reports/CERTIFICATION_RECONCILIATION_BLOCKER.md`](reports/CERTIFICATION_RECONCILIATION_BLOCKER.md).

Las fuentes canónicas siguen siendo el CSV de certificación, su checkpoint y el checkpoint master. Los reportes derivados no deben volver a marcarse como reconciliados hasta resolver la inconsistencia sin perder transacciones.
