# Arcade Audit

Documentación central del arcade Batocera personalizado. La fuente operativa local vive en `/userdata/system/state/arcade_audit/`; este repositorio recibe una exportación filtrada de informes, metadata, checkpoints y herramientas seleccionadas.

## Empezar aquí

1. [Estado actual del arcade](ARCADE_CURRENT_STATE.md)
2. [Índice documental](ARCADE_DOCUMENT_INDEX.md)
3. [Resumen de certificación](reports/FULL_GAME_CERTIFICATION_SUMMARY.md)
4. [Causas raíz](reports/ROOT_CAUSES.md) y [cola de reparaciones](data/game_repair_queue.csv)
5. [Scripts exportados](scripts/)

El estado actual señala una discrepancia abierta entre el CSV de certificación y su checkpoint/cursor después de Batch 6. No reanudar desde el `NEXT_GAME` antiguo hasta reconciliar ese metadata. Los resultados de certificación no se alteraron durante la auditoría documental.

## Contenido

- `docs/`: arquitectura, hardware, controles, modelo de datos, incidentes y decisiones.
- `reports/`: estado y análisis vigentes.
- `reports/history/`: snapshots fechados que explican la evolución; no sustituyen al estado actual.
- `data/`: inventarios, certificación, checkpoints y colas estructuradas.
- `scripts/`: snapshots de herramientas propias revisadas para exportación.

## Alcance y privacidad

El repo no contiene ROMs, BIOS, CHD, saves, NVRAM, credenciales, tokens, claves privadas, backups completos ni media pesada. La exportación pasa controles de secretos y payload antes de publicarse.

`AUTO_CERTIFIED` representa validaciones automáticas documentadas; no equivale a `CONTROL_CERTIFIED`. `GUEST_READY` requiere certificación física suficiente y no se infiere automáticamente desde el arranque.
