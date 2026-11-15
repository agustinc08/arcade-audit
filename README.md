# Arcade Audit

Repositorio aislado para conservar la evolución de la auditoría arcade. La carpeta fuente de trabajo continúa siendo `/userdata/system/state/arcade_audit/`; el repositorio copia sólo informes, datos y scripts seleccionados. No se versiona `/userdata` completo.

## Hardware base

- Batocera personalizado, x86_64.
- Intel Core i5-12400F, 16 GB RAM.
- NVIDIA GeForce GTX 1060 3 GB.
- Cuatro botoneras DragonRise USB para P1-P4.

## Objetivo

Conservar informes, CSV/JSON de auditoría, checkpoints, documentación y scripts propios para comparar la evolución del arcade y continuar el trabajo sin repetir pruebas.

## Estructura

- `reports/`: informes markdown y notas `.txt` seleccionadas.
- `data/`: inventarios, compatibilidad, resultados estructurados y checkpoints CSV/JSON.
- `scripts/`: scripts Python/shell propios de auditoría.

La sincronización se prepara con `/userdata/system/el_gordo_tools/sync_arcade_audit_git.sh`. Ejecutarlo sólo después de que una auditoría termine correctamente y sus reportes estén íntegros. Ante un resultado FALLIDO o PARCIAL, revisar primero la integridad; el script no ejecuta juegos ni modifica el árbol fuente.

## Estado de referencia

Estado extraído de los informes existentes al 2026-11-15; no se relanzaron juegos para crear esta referencia.

- Inventario: 1.397 juegos arcade.
- BOOT_OK_DEFAULT_CORE (`mame078plus`): 1094.
- BOOT_OK_MAME_CURRENT: 18.
- BOOT_OK_FBNEO: 88.
- TOTAL_UNIQUE_BOOT_OK: 1200 (unión por sistema/ROM; sin doble conteo).
- Juegos del inventario sin BOOT_OK en ninguna de esas categorías: 197.
- Core MAME global: `mame078plus`.
- Overrides individuales conocidos: `ffight2b`, `altair`, `apache3`, `blazlaz`, `cubeqst`, `sia2650`, `evosocc`, `hoops95`, `funcube4`, `lbgrande`, `sws98`, `tenkomor`, `multigam`, `multigm3`, `nratechu`, `ertictac`, `kov2p`, `martmast`.
- BATCH 4 real (2026-11-15): control `altair` PASS y 7/7 candidatos normales BOOT_PASS con overrides individuales; 0 fallos de juego. Ver `reports/ARCADE_MAME_BATCH4_RESULTS.md`.
- BATCH 5 real (2026-11-15): `kov2p` y `martmast` BOOT_PASS con MAME actual; 2/2 preflight PASS seleccionados, 43 SKIP_PREFLIGHT. Ver `reports/ARCADE_MAME_BATCH5_RESULTS.md`.
- Estado de controles y conteo reconciliado: consultar los informes bajo `reports/`.

## Cómo interpretar los estados

- `BOOT_OK`: el proceso/emulador alcanzó el criterio documentado de arranque estable. No garantiza controles físicos correctos ni una partida completa.
- `FAIL`: intento registrado que no alcanzó el criterio de arranque; revisar la causa (core, CHD, contenido, ROMSET, crash u otra) antes de concluir.
- `CURRENT_CORE_REJECTED`: el core configurado por defecto rechazó el driver/contenido. No implica automáticamente ROM corrupta ni que otro core vaya a funcionar.
- `INPUT_REVIEW`: controles no comprobados suficientemente; requiere validación de bindings y respuesta física.
- `SPECIAL_CONTROL`: el juego necesita periférico/entrada especial o mapeo fuera de la botonera digital estándar.
- `MANUAL_TEST`: requiere revisión manual; no equivale a PASS ni a fallo confirmado.

## Privacidad y contenido

Este repositorio NO contiene ROMs, BIOS, CHDs, saves ni credenciales. No guardar tokens, contraseñas, claves privadas, archivos `.env`, media scrapeada o backups en este repositorio. El remoto, cuando se configure, debe ser privado.
