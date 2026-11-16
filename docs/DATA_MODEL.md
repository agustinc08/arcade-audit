# Modelo de datos y fuentes canónicas

| Tema | Fuente canónica | Uso |
|---|---|---|
| Estado por juego | `full_game_certification.csv` | Una fila por juego instalado; diferencia histórico, auto, controles y Guest Ready. |
| Progreso de certificación | `full_game_certification_checkpoint.json` | Transacciones, resultados, contadores, último lote y `next_untested`. |
| Fases del master audit | `arcade_master_checkpoint.json` | Estado y resumen por fase. |
| Incidentes | `arcade_issues.csv` | Root issues, severidad, estado, evidencia y acción. |
| Reparaciones | `game_repair_queue.csv` | Juegos en NEEDS_REPAIR y acción sugerida. |
| Pruebas humanas | `manual_physical_test_queue.csv` | Cola de certificación física; no equivale a resultados aprobados. |
| Sistemas/adapters | `data/detected_systems.csv`, `data/certifier_adapter_registry.csv` | Inventario dinámico y capacidad actual del adapter. |
| Controladores conectados | `controllers_live.json` | Instantánea de panel/gamepads; no historial ni certificación física. |
| MAME/FBNeo por-lote | `mame_batch*_checkpoint.json`, reportes de lote | Evidencia histórica específica; no reemplaza el modelo universal. |
| Resumen humano | `reports/FULL_GAME_CERTIFICATION_SUMMARY.md` | Derivado; se regenera de tabla/checkpoints y se valida antes de publicar. |
| Estado de fases/documentación | `arcade_master_checkpoint.json` | Fuente de estado del Master Audit. |
| Export GitHub | `arcade_audit_git/` + manifest del publisher | Copia filtrada publicada; no es runtime ni fuente de progreso de juegos. |

## Estados que no se deben confundir

- `HISTORICAL_BOOT_OK`: evidencia previa de arranque, bajo el método/core de su época.
- `AUTO_CERTIFIED`: nuevo recorrido del certificador, con sus gates de identity/audio/runtime/exit/restore.
- `CONTROL_CERTIFIED`: prueba física humana de controles.
- `GUEST_READY`: juego completo con auto, control, salida y UX adecuados.

Retries cuentan como transacciones, no como juegos únicos nuevos. Los reportes Markdown son derivados y nunca prevalecen sobre checkpoint/CSV.
