# Auditoría de filesystem — inventario inicial

Fecha: 2026-11-15 (America/Buenos_Aires)

Estado: `COMPLETE_WITH_ISSUES` — inventario inicial de rutas y artefactos candidatos; no se eliminó ningún archivo, backup ni ROM.

## Topología observada

- `/userdata` está en `/dev/sda2` ext4, 213.6 GiB, 119 GiB usados.
- `/media/ROMS` está en `/dev/sdc1` ext4, disco ROMS de 3.6 TiB, 1,012 GiB usados.
- `/userdata/roms` es `mergerfs`: `userdata/.roms_base`, `/media/BATOCERA_ROMS/roms` y `/media/ROMS/roms`. El espacio lógico informado es 4.7 TiB; el conteo `du` no equivale al espacio físico exclusivo por las ramas fusionadas.
- `/userdata/system` ocupa aproximadamente 31 GiB; `/userdata/system/configs` ~17 GiB; `backups_el_gordo` ~2.5 GiB; `state` ~124 MiB; `el_gordo_tools` ~192 KiB.
- `/media/ROMS/ARCADE_BACKUPS` ocupa ~33 GiB. El baseline `BASELINE_PRE_CAMBIOS_2026-09-25_234721.tar.gz` ocupa 16,575,815,656 bytes; no se borró porque no se demostró redundancia segura.

## Backups y referencias

- `ARCADE_SMOKE_TEST_SAVES_2026-11-13_011039` permanece protegido: aparece en `checkpoint.json`, `protected_baseline.json` y checkpoints Batch 3–5.
- `ARCADE_ES_RESET_PRE_BATCH4_20261115_040813` permanece protegido: Batch 4 checkpoint y diffs de gamelists lo referencian.
- Los snapshots Pilot/BATCH2 conservan reportes/configuración usados como evidencia.
- `FINAL_BATOCERA_CONTROLES_JUEGOS` permanece intacto como backup crítico documentado en `BACKUPS.md`.
- El baseline de 16.6 GB requiere inspección de su manifiesto e historial de creación antes de considerar una eliminación.

## Candidatos encontrados

Se detectaron archivos con nombres `.bak` en `/userdata/system/game_audit`, un `.bak` dentro de datos de Abuse, dos checkpoints de sesión con `staging` en el nombre y un archivo temporal de 0 bytes en una ruta de caché RPCS3. Ninguno se borró: los `.bak` del audit son evidencia, el archivo de Abuse puede ser dato activo, los checkpoints son evidencia y el archivo RPCS3 requiere nueva comprobación de contexto aunque no se detectó proceso RPCS3. La tabla contiene tamaños, mtimes, clasificación y referencias conocidas.

No se inspeccionaron contenidos de ROMs ni se recorrieron sus bytes para esta limpieza. No se borraron archivos; `FILES_DELETED=0`, `BACKUPS_DELETED=0`, `TEMP_DELETED=0`, `ROMS_DELETED_SAFE=0`, `TOTAL_BYTES_RECOVERED=0`.

## Incidente overlay (acción accidental, documentada)

Una consulta con `batocera-save-overlay --help` ejecutó realmente la herramienta: el script no reconoce `--help` y guardó el upperdir actual hacia `/boot/boot/overlay` mediante `rsync -av --delete`. Informó `Success`, dejó `/boot` en sólo lectura y actualizó el mtime del overlay de 2026-08-16 a 2026-11-15 06:22. El upperdir observado ocupaba ~724 KiB. La salida incluyó eliminación del estado persistido `/.local/state/wireplumber/default-routes` y sincronización de archivos live (incluidos `.config/pulse/cookie`, `.local/state/wireplumber/stream-properties`, `etc/hosts`, archivos de timezone/ld config/Bluetooth, librerías NVIDIA/X11). No existe hash pre-acción, por lo que no se puede reconstruir un diff fiable; `overlay.old` data de 2026-05 y no es rollback válido. No se reinició el equipo ni se restauró ningún overlay. `REBOOT_VALIDATION_PENDING`. No hacer más escrituras sobre el root overlay hasta revisar esta discrepancia.
