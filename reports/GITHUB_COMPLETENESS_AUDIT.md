# Auditoría de completitud documental de GitHub

- Fecha: 2026-11-16
- Repositorio/rama: `agustinc08/arcade-audit`, `main`
- HEAD remoto consultado: `554e66ddcd0373d629179bfc937879952c2234a3`
- Resultado: el diff fue auditado localmente; esta generación aún no implica publicación.

## Cobertura local

El inventario documental registró 565 candidatos en rutas persistentes acotadas. Es un snapshot creado antes de este informe y de `ROOT_CAUSES.md`; ambos se revisaron después de generarlo.

| Categoría | Archivos |
|---|---:|
| USEFUL_MISSING | 68 |
| ALREADY_IN_GIT | 156 |
| UPDATED_VERSION | 12 |
| OBSOLETE_BUT_HISTORIC | 104 |
| DUPLICATE | 221 |
| TEMPORARY / RUNTIME / OBSOLETE_NO_VALUE / UNKNOWN | 0 |
| SENSITIVE | 2 |
| UNRELATED | 2 |

Inventario de scripts propios: 23 entradas; 4 ACTIVE_PRODUCTION, 11 ACTIVE_AUDIT, 5 LEGACY, 2 UNKNOWN y 1 candidato sensible. El publisher Python activo queda fuera de scripts exportados porque el escáner detecta su patrón interno de asignación de token; no se debilitó el scan. El wrapper sin secretos sí está incluido.

Inventario de backups: 9 entradas. Sólo se exporta metadata; los archivos de respaldo quedan locales. El árbol `BASELINE_PRE_CAMBIOS_2026-09-25_234721.tar.gz` (aprox. 16.6 GB) permanece fuera del repo; se registra metadata/hash disponible.

El documento solicitado `/userdata/ESTADO_ACTUAL_DEL_ARCADE_2026-09-25.md` no existe. No se sobrescribió ni se fabricó. Se exportan snapshots históricos fechados que sí existen bajo `reports/history/`.

## Diff exacto contra el HEAD consultado

- Archivos locales permitidos: 212; archivos remotos: 167.
- ADDED: 45 (44 rutas listadas más este informe, que se omite de su propia lista).
- MODIFIED: 7.
- DELETED: 0.
- UNCHANGED: 160.
- Payload total UTF-8: 16,772,558 bytes; ningún archivo supera 20 MB.
- SECRET_SCAN: PASS.
- PAYLOAD_SCAN: PASS.
- MASS_DELETE_GUARD: PASS; no hay borrados.
- LARGE_CHANGESET: el umbral estándar bloquea esta tanda; se requiere autorización one-time ligada exactamente a HEAD/rutas/tamaños/SHA. El guard permanente no se modifica.

### Altas (salvo este mismo informe)

- `ARCADE_CURRENT_STATE.md`
- `ARCADE_DOCUMENT_INDEX.md`
- `data/backups_inventory.csv`
- `data/custom_scripts_inventory.csv`
- `data/documentation_inventory.csv`
- `docs/ARCADE_ARCHITECTURE.md`
- `docs/CONTROLLERS.md`
- `docs/DATA_MODEL.md`
- `docs/HARDWARE.md`
- `docs/KNOWN_INCIDENTS.md`
- `docs/SYSTEMS.md`
- `docs/TECHNICAL_DECISIONS.md`
- `reports/BACKUP_INVENTORY.md`
- `reports/CERTIFICATION_RECONCILIATION_BLOCKER.md`
- `reports/CURRENT_BATOCERA_CONFIG.md`
- `reports/PRIORITY_CERTIFICATION_BATCH_3.md`
- `reports/PRIORITY_CERTIFICATION_BATCH_4.md`
- `reports/PRIORITY_CERTIFICATION_BATCH_6.md`
- `reports/README.md`
- `reports/ROOT_CAUSES.md`
- `reports/history/ARCADE_MASTER_STATUS_2026-11-15.md`
- `reports/history/AUDITORIA_BATOCERA_FINAL.md`
- `reports/history/AUDITORIA_JUEGOS_ESTATICA_2026-10-01.md`
- `reports/history/BOOT_TEST_PILOTO_2026-10-01.md`
- `reports/history/COMPLEMENTO_AUDITORIA_ARCADE_2026-11-12.md`
- `reports/history/ESTADO_ACTUAL_ARCADE_2026-11-15.md`
- `reports/history/ESTADO_ARCADE_SEGUIMIENTO_2026-11-12.md`
- `reports/history/FULL_GAME_CERTIFICATION_SUMMARY_2026-11-16_PRE_DOCUMENTATION_AUDIT.md`
- `reports/history/README.md`
- `scripts/active/arcade_audio_policy_service.sh`
- `scripts/active/arcade_control_certifier.py`
- `scripts/active/arcade_manager.py`
- `scripts/active/arcade_recover.py`
- `scripts/active/certification_transaction.py`
- `scripts/active/certifier_adapters.py`
- `scripts/active/control_overlay.py`
- `scripts/active/controller_dispatcher.py`
- `scripts/active/custom_service.sh`
- `scripts/active/full_game_certifier.py`
- `scripts/active/publish_arcade_audit.sh`
- `scripts/active/rebuild_arcade_current_state.py`
- `scripts/active/rebuild_certification_summary.py`
- `scripts/active/selector_controles.py`
- `scripts/active/update_controllers_live.py`

### Modificaciones

- `README.md`
- `data/arcade_issues.csv`
- `data/controllers_live.json`
- `data/full_game_certification.csv`
- `data/full_game_certification_checkpoint.json`
- `reports/ARCADE_MASTER_STATUS.md`
- `reports/FULL_GAME_CERTIFICATION_SUMMARY.md`

### Borrados remotos

- Ninguno

Los cinco duplicados byte por byte `reports/certification/PRIORITY_BATCH_1..5.md` se excluyeron de la exportación anidada; los reportes canónicos `reports/PRIORITY_CERTIFICATION_BATCH_1..5.md` conservan su contenido y ruta. Los originales de la carpeta activa siguen intactos.

## Estado de certificación observado

La tabla local contiene 499 AUTO_CERTIFIED, 9 GAME_FAIL, 2 STATIC_FAIL, 0 FLAKY, 11 NEEDS_REPAIR, 0 CONTROL_CERTIFIED y 0 GUEST_READY; el checkpoint superior aún declara 401 AUTO_CERTIFIED y apunta a `gundealr`, ya AUTO_CERTIFIED en el CSV. `ARCADE_CURRENT_STATE.md` conserva ambas fuentes bajo `CURRENT_STATE_RECONCILIATION_FAIL` y no presenta ese cursor como confiable. Esta auditoría no modificó el CSV, checkpoint ni orden/cursor de certificación.

## Límites y exclusiones

No se exportan ROMs, BIOS, CHD, saves, NVRAM, backups completos, secretos, claves, logs efímeros, runtime, cache ni media pesada. Dos candidatos sensibles del inventario quedaron excluidos y el publisher no fue copiado como script activo. `batocera.conf` completo no se publica: sólo parámetros saneados y hashes seleccionados.

## Publicación

Pendiente de manifest de una sola vez para este conjunto exacto, con el HEAD `554e66ddcd0373d629179bfc937879952c2234a3`. Cualquier cambio en rutas o contenido invalida la aprobación y obliga a repetir el audit.
