# Inventario de backups relevantes

- Entradas inventariadas: 9.
- Se revisaron nombres, tamaño, fecha, manifiestos y referencias; no se restauró ni borró ningún backup.
- Los archivos de saves y las configuraciones en backups permanecen fuera de GitHub.
- Inventario detallado: `data/backups_inventory.csv`.

| Backup | Fecha | Tamaño bytes | Uso | Conservación | SHA/manifest |
|---|---|---:|---|---|---|
| `/media/ROMS/ARCADE_BACKUPS/ARCADE_CORE_PILOT_2026-11-13_093236` | 2026-11-13 | 18344 | Evidencia y snapshots de pilotos de compatibilidad. | YES | `manifest:MANIFEST_SHA256.txt:bc9f0dc38d30b04e712223482222182ac5252776e42aad6053c30a6e83d7245b` |
| `/media/ROMS/ARCADE_BACKUPS/ARCADE_CORE_PILOT_BATCH2_2026-11-13_104010` | 2026-11-13 | 496509 | Evidencia y snapshots de pilotos de compatibilidad. | YES | `manifest:MANIFEST_SHA256.txt:1c7e0244e815685a6a22abee2059e6da9ffb690d3678aa601408e00e2d6626b1` |
| `/media/ROMS/ARCADE_BACKUPS/ARCADE_ES_RESET_PRE_BATCH4_20261115_040813` | 2026-11-15 | 11784890 | Respaldo mínimo previo al reset controlado de EmulationStation. | YES | `manifest:MANIFEST.json:5942bc0b4dca347a6f6a87ce1b29ac5e1a4f43bb0f56f684c47a42d108fc8219` |
| `/media/ROMS/ARCADE_BACKUPS/ARCADE_SMOKE_TEST_SAVES_2026-11-13_011039` | 2026-11-13 | 10232634 | Snapshot de saves previo a pruebas; contiene datos de usuario, no exportar. | YES | `manifest:MANIFEST_SHA256.txt:21cfdfa7e59615a874e47a2e91805d4e0027c3ec3ead0103ea152c4e2f262daf` |
| `/media/ROMS/ARCADE_BACKUPS/BASELINE_PRE_CAMBIOS_2026-09-25_234721` | 2026-09-25 | 18847224553 | Baseline previo a cambios de septiembre; archivo tar grande y árbol selectivo, conservar como recuperación histórica. | YES | `` |
| `/media/ROMS/ARCADE_BACKUPS/BASELINE_PRE_CAMBIOS_2026-09-25_234721.tar.gz` | 2026-09-26 | 16575815656 | Baseline previo a cambios de septiembre; archivo tar grande y árbol selectivo, conservar como recuperación histórica. | YES | `a8445b9768eca923ccfc1a50170598f77c442800432230c3b46ab25b23b6a4ca` |
| `/media/ROMS/ARCADE_BACKUPS/BASELINE_PRE_CAMBIOS_2026-09-25_234721.tar.gz.sha256` | 2026-09-26 | 112 | Baseline previo a cambios de septiembre; archivo tar grande y árbol selectivo, conservar como recuperación histórica. | YES | `69f3926f01ad5f4a832a05daf21e0ae19c4268a72fa67a06807787c64e455cca` |
| `/media/ROMS/ARCADE_BACKUPS/EMULATIONSTATION_MEDIA_FIX_2026-09-26_122318` | 2026-09-26 | 1188753 | Rollback selectivo de cambios de media/gamelist de septiembre. | YES | `` |
| `/media/ROMS/ARCADE_BACKUPS/EMULATIONSTATION_VSYNC_FIX_2026-09-26_185430` | 2026-09-26 | 3236 | Rollback selectivo de cambio VSync de septiembre. | YES | `` |

## Notas de historia y seguridad

- Está presente `BASELINE_PRE_CAMBIOS_2026-09-25_234721` como árbol de archivos y archivo `tar.gz`; el archivo comprimido mide 16,575,815,656 bytes. Su SHA-256 se tomó del sidecar `.sha256`, sin volver a leer el archivo de 16.5 GB. El snapshot queda local, no se exporta.
- Está presente `ARCADE_SMOKE_TEST_SAVES_2026-11-13_011039`; contiene respaldo de saves y se conserva fuera de GitHub.
- Está presente `ARCADE_ES_RESET_PRE_BATCH4_20261115_040813`, creado antes del reinicio controlado de ES.
- Los backups de piloto, ajuste de media y VSync son evidencia/rollback histórico; no se propone limpieza en esta tarea porque no se confirmó obsolescencia completa.
- No se calculó salud SMART ni se hizo lectura de superficie.
