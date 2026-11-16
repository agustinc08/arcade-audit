# Índice documental del arcade

Este repositorio reúne documentación, datos saneados, checkpoints y herramientas. La fuente activa permanece en `/userdata/system/state/arcade_audit/`; el repo es una exportación filtrada. No contiene ROMs, BIOS, CHD, saves, NVRAM, credenciales ni media pesada.

## Leer primero

- [Estado actual](ARCADE_CURRENT_STATE.md): hardware, configuración y avance derivados de fuentes canónicas.
- [Arquitectura del arcade](docs/ARCADE_ARCHITECTURE.md): ruta de arranque, selección, dispatcher, launcher y cierre.
- [Modelo de datos](docs/DATA_MODEL.md): fuentes de verdad y relación entre CSV, checkpoints e informes.
- [Sistemas detectados](docs/SYSTEMS.md): inventario de sistemas y adapters observados.
- [Configuración Batocera saneada](reports/CURRENT_BATOCERA_CONFIG.md): parámetros permitidos y hashes, nunca el archivo íntegro.

## Certificación de juegos

- [Resumen completo](reports/FULL_GAME_CERTIFICATION_SUMMARY.md): resumen regenerado desde CSV y checkpoints.
- [Batch 6](reports/PRIORITY_CERTIFICATION_BATCH_6.md) y [bloqueo de reconciliación](reports/CERTIFICATION_RECONCILIATION_BLOCKER.md).
- [Lotes prioritarios](reports/): buscar `PRIORITY_CERTIFICATION_BATCH_*.md`.
- [Juegos de 5–8 jugadores](reports/GAMES_5_TO_8_PLAYERS.md).
- [Top party games](reports/TOP_PARTY_GAMES.md).
- [Cola de pruebas físicas](data/manual_physical_test_queue.csv).
- [Certificación por juego](data/full_game_certification.csv).

`AUTO_CERTIFIED` prueba señales automáticas del lanzamiento. No equivale a `CONTROL_CERTIFIED`; `GUEST_READY` requiere controles físicos, salida y experiencia adecuados.

## Problemas y reparaciones

- [Causas raíz](reports/ROOT_CAUSES.md).
- [Issues](data/arcade_issues.csv).
- [Cola de reparación](data/game_repair_queue.csv).
- [Incidentes arquitectónicos](docs/KNOWN_INCIDENTS.md).

## Controles, audio y operación

- [Hardware](docs/HARDWARE.md).
- [Controles y P1–P4](docs/CONTROLLERS.md).
- [Política de audio HDMI](reports/ARCADE_AUDIO_POLICY.md).
- [Modelo de certificación de controles](reports/ARCADE_CONTROL_CERTIFICATION.md).
- [Estado del Arcade Manager](reports/ARCADE_MANAGER_SETUP.md).

## Arcade, MAME y FBNeo

- [Auditoría MAME](reports/ARCADE_AUDIT_REPORT.md).
- [Compatibilidad de cores](reports/ARCADE_CORE_COMPATIBILITY.md).
- [MAME Batch 3](reports/ARCADE_MAME_BATCH3_RESULTS.md), [reanudación](reports/ARCADE_MAME_BATCH3_RESUME_RESULTS.md), [Batch 4](reports/ARCADE_MAME_BATCH4_RESULTS.md) y [Batch 5](reports/ARCADE_MAME_BATCH5_RESULTS.md).
- [Auditoría FBNeo](reports/ARCADE_FBNEO_AUDIT.md).
- [Plan de reparación de contenido MAME](data/mame_content_repair_plan.csv).

## Otras auditorías

- [Auditoría de filesystem](reports/FILESYSTEM_MASTER_AUDIT.md).
- [Inventario de backups](reports/BACKUP_INVENTORY.md) y [datos detallados](data/backups_inventory.csv).
- [Auditoría de cobertura GitHub](reports/GITHUB_COMPLETENESS_AUDIT.md).
- [Auditoría visual/media](reports/ARCADE_VISUAL_MEDIA_AUDIT.md) y [datos por juego](data/media_audit.csv).
- [Investigación de curación](reports/ARCADE_CURATION_RESEARCH.md).

## Historia

Los snapshots de `reports/history/` son evidencia fechada, no el estado vigente. Consultar [índice del archivo](reports/history/README.md). Si un snapshot contradice checkpoints actuales, prevalece [ARCADE_CURRENT_STATE.md](ARCADE_CURRENT_STATE.md) y la fuente canónica indicada en [DATA_MODEL.md](docs/DATA_MODEL.md). El backup completo de septiembre permanece fuera de GitHub.

## Herramientas

- [`scripts/active/`](scripts/active/): snapshots de las herramientas activas y scripts de operación revisados para exportación.
- [`scripts/universal_certifier/`](scripts/universal_certifier/): implementación del certificador y adapters.
- [`scripts/`](scripts/): utilidades históricas/audit por lote. El inventario con SHA está en [custom_scripts_inventory.csv](data/custom_scripts_inventory.csv).

## Historia técnica y decisiones

- [Decisiones técnicas](docs/TECHNICAL_DECISIONS.md).
- [Completitud del archivo documental](reports/GITHUB_COMPLETENESS_AUDIT.md).
- [Inventario de documentación](data/documentation_inventory.csv).
- [Inventario de backups](data/backups_inventory.csv).
