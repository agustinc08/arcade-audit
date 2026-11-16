# Reconciliación de certificación tras Batch 6

- Resultado: **PASS**
- Fecha: 2026-11-16
- No se lanzó ningún juego durante la reconciliación.

## Evidencia y métricas

| Métrica | Valor |
|---|---:|
| Result records | 511 |
| Juegos únicos procesados | 510 |
| Transacciones de lanzamiento | 509 |
| Retries de identidad | 1 |
| AUTO_CERTIFIED | 499 |
| GAME_FAIL | 9 |
| STATIC_FAIL | 2 |
| FLAKY | 0 |
| NEEDS_REPAIR | 11 |
| Restores verificados | 509 |
| Restore failures | 0 |
| Engine failures activos | 0 |
| ENGINE_FAIL históricos | 1 |
| Latest batch | `priority_batch_6` |

`attempted_new` se conserva por compatibilidad como alias de transacciones de lanzamiento: 509. No significa ni juegos únicos (510) ni records (511). `retry_transactions=1` identifica la identidad repetida de PC Engine cuyo último resultado es AUTO_PASS. El ENGINE_FAIL histórico no es activo.

Batch 6 añadió exactamente 100 records: 98 AUTO_PASS y 2 GAME_FAIL. Los 2 STATIC_FAIL (`hoops95`, `evosocc`) ya existían antes del lote; el reporte inicial se corrigió. La fila CSV de cada resultado coincide con su último resultado válido. No se borró ni alteró ningún resultado, transacción o estado individual.

## Cursor

- Cursor anterior inválido: `mame:/userdata/roms/mame/gundealr.zip` (ya AUTO_CERTIFIED).
- NEXT_GAME reconciliado: `mame:/userdata/roms/mame/machridr.zip`.
- Validación: instalado, `NOT_TESTED`, adapter `MAME078PLUS` READY, sin resultado anterior, preflight PASS.
- Los siguientes 20 candidatos figuran en `runtime/checkpoint_reconciliation_20261116T194825/NEXT_QUEUE_PREVIEW.csv`; los 20 pasan elegibilidad y preflight.

## Invariantes y hashes

- CSV rows estables: 8426; altas/bajas: 0; AUTO_CERTIFIED/GAME_FAIL/STATIC_FAIL degradados o perdidos: 0.
- Transaction IDs duplicados inesperados: 0; restores nuevos fallidos: 0.
- CSV SHA-256 BEFORE: `ed073d1a4fd8ae35439afbca1230d7a8aa5ffc272c7e64ef562e3f942a7cb461`
- CSV SHA-256 AFTER: `ed073d1a4fd8ae35439afbca1230d7a8aa5ffc272c7e64ef562e3f942a7cb461` (idéntico)
- Checkpoint SHA-256 BEFORE: `4017b212e32cd3d30ad9cfb34e1e831bff101f406a5473440983cb4c31e7b3c5`
- Checkpoint SHA-256 AFTER: `8e73a1c229ad3cd5233c26df818979d1743c1e7cc2bd625d80bb0160a0d632d6`
- Master checkpoint SHA-256 BEFORE: `0f8ab9c5a5aa9d0a0a43a4068ed3bdeec2ca0c7319bc35cce397224bd68fe0a7`
- Master checkpoint SHA-256 AFTER: `3cff377986af1201d063ad38ab71962769aadfad08a4f29babfd89d3b7876bd2`

El checkpoint y el resumen maestro cambiaron sólo en metadatos agregados/cursor; los registros individuales no se reescribieron. No se modificaron ROMs, cores, overrides, controles ni configuración arcade.
