# Archivo histórico

Los archivos de esta carpeta son snapshots fechados. Preservan el contexto de una etapa y no prevalecen sobre checkpoints, CSV canónicos ni `ARCADE_CURRENT_STATE.md`.

## Documentos importados desde `/userdata`

- `AUDITORIA_BATOCERA_FINAL.md` — auditoría del sistema de septiembre de 2026.
- `AUDITORIA_JUEGOS_ESTATICA_2026-10-01.md` — análisis estático de contenido.
- `BOOT_TEST_PILOTO_2026-10-01.md` — piloto temprano de arranque.
- `COMPLEMENTO_AUDITORIA_ARCADE_2026-11-12.md` — complemento arcade previo a la certificación universal.
- `ESTADO_ARCADE_SEGUIMIENTO_2026-11-12.md` — estado intermedio.
- `ESTADO_ACTUAL_ARCADE_2026-11-15.md` — snapshot más reciente encontrado en `/userdata` al iniciar esta auditoría.
- `ARCADE_MASTER_STATUS_2026-11-15.md` — snapshot del master audit previo a los lotes masivos.

Las copias se mantuvieron separadas de los originales. Se comprobó riesgo de credenciales y se saneó cualquier identificador de red privada que apareciera. Los archivos exactos `ESTADO_ACTUAL_DEL_ARCADE_2026-09-25.md` no existen en las rutas revisadas; el baseline de esa fecha sí existe como backup local, pero el archivo comprimido de 16.5 GB y el árbol no se exportan.

El resto de reportes históricos repetidos, documentos obsoletos o datos de backup se clasifican en `data/documentation_inventory.csv` y `data/backups_inventory.csv`; no se copiarán automáticamente sólo por existir.
