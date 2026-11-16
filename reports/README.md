# Arcade Audit

Auditoría reproducible del arcade Batocera personalizado: configuración documentada, compatibilidad, resultados de lanzamiento, controles, incidentes y herramientas propias. La publicación usa GitHub REST API desde Batocera; Git no forma parte del runtime.

## Empezar aquí

1. [ARCADE_CURRENT_STATE.md](ARCADE_CURRENT_STATE.md): snapshot generado del estado observado.
2. [ARCADE_DOCUMENT_INDEX.md](ARCADE_DOCUMENT_INDEX.md): guía para navegar documentación y datos.
3. [Resumen de certificación](reports/FULL_GAME_CERTIFICATION_SUMMARY.md): resultados derivados de las fuentes canónicas.
4. [Causas raíz](reports/ROOT_CAUSES.md), [issues](data/arcade_issues.csv) y [cola de reparación](data/game_repair_queue.csv).
5. [Scripts](scripts/): snapshots de herramientas y código de auditoría.

## Fuentes y alcance

El árbol activo de auditoría es `/userdata/system/state/arcade_audit/`; el repo contiene una exportación filtrada y saneada. Las fuentes canónicas de certificación son `data/full_game_certification.csv`, `data/full_game_certification_checkpoint.json` y `data/arcade_master_checkpoint.json`. Los Markdown de estado y resumen se regeneran desde esos datos.

El repo conserva documentación, metadata, decisiones, historial útil y scripts. No contiene ROMs, BIOS, CHD, saves, NVRAM, credenciales, tokens, claves privadas, Wi-Fi ni media pesada. La exportación valida una allowlist y ejecuta secret/payload scans.

La certificación puede quedar marcada `CURRENT_STATE_RECONCILIATION_FAIL` si el CSV y checkpoint discrepan. En ese estado, revisar `reports/CERTIFICATION_RECONCILIATION_BLOCKER.md`; no reanudar usando un cursor que señale un juego ya probado.

## Interpretación

`HISTORICAL_BOOT_OK`, `AUTO_CERTIFIED`, `CONTROL_CERTIFIED` y `GUEST_READY` son estados distintos. Un juego que pasó una prueba automática no tiene necesariamente controles físicos certificados y no se incorpora automáticamente a Guest Mode.

La secuencia real de lanzamiento y las decisiones persistentes están documentadas en [la arquitectura](docs/ARCADE_ARCHITECTURE.md). Los snapshots fechados están en [reports/history/](reports/history/) y no deben tratarse como estado actual.
