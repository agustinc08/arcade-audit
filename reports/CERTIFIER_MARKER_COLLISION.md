# CERTIFIER_MARKER_COLLISION

Estado: CERRADO  
Fecha de auditoría local: 2026-11-17

## Evidencia de CERT-007

- Transacción: `20261116T232721_823ec5e49e` (`full-certifier:mame:xmultipl.zip`).
- `PRE_STATE`: `/userdata/system/state/boot_audit_once.json` ausente.
- `run_one()` recibió `FileExistsError` en la apertura exclusiva antes de `POST /launch`.
- `POST_STATE`: el path aparecía como archivo de 213 bytes, SHA-256 `6b5118a1411beaa1d72139ca1186ae46594178c4fffc1ecc483d3c4f110fb22b`.
- El manifest terminó `RESTORE_VERIFIED`, pero ese resultado sólo demuestra que el estado coincidió con PRE después del restore; no demuestra quién creó el marker ni que la transacción tuviera ownership. El snapshot no conserva el contenido porque PRE era ausente.
- El marker está actualmente ausente. No se lanzó `xmultipl` durante esta recuperación.

## Escritores y consumidores encontrados

| Archivo / función | READ | CREATE | OVERWRITE | DELETE | RESTORE |
|---|---|---|---|---|---|
| `el_gordo_tools/full_game_certifier.py` / `run_one()` | safety baseline y comprobación posterior | `open('x')` anterior; ahora helper exclusivo con ownership | No | antes comparaba `audit_id`; ahora exige owner y `transaction_id` | invoca transaction engine |
| `state/arcade_audit/smoke_runner.py` / `run_one()` | preflight y consumo | `open('x')` anterior; ahora helper exclusivo con ownership | No | antes comparaba `audit_id`; ahora exige owner y transaction id | No usa transaction engine para el marker |
| `scripts/mame_batch3_resume_control.py`, `scripts/mame_batch4_runner.py`, `scripts/mame_batch5_runner.py` / launch helpers | preflight y comprobación de consumo | `open('x')` anterior; ahora helper compartido con owner por runner | No | ahora helper exige owner, transaction id y `audit_id` | No usan el transaction engine para el marker |
| `smoke_pilot_runner.py`, `smoke_pilot_batch2.py` / `one_game()` | preflight y comprobación de consumo | `open('x')` anterior; ahora helper compartido con owner por runner | No | ahora helper exige owner, transaction id y `audit_id` | Su restore de otros recursos permanece independiente |
| `scripts/active/full_game_certifier.py`, `scripts/universal_certifier/full_game_certifier.py` / `run_one()` | como el certifier local | `open('x')` anterior; ahora helper exclusivo con ownership | No | ahora helper exige owner y `transaction_id` | Transaction copies protegidas |
| `el_gordo_tools/controller_dispatcher` / `consume_boot_audit_once()` | Lee formato legacy y actual | No | No | Consume una marca válida para el mismo sistema/ROM; ahora bajo el lock compartido | No |
| `el_gordo_tools/certification_transaction.py` / `state()`, `restore()` | Hash PRE/POST | No | Restauración genérica anterior | Restauración genérica anterior podía borrar cuando PRE era ausente | Ahora el marker usa conflicto salvo ownership del `transaction_id` actual |
| `el_gordo_tools/certifier_adapters.py` / `restore_scope()` | Incluye el path en el scope | No | No | No directamente | Lo entrega a la transacción |
| `el_gordo_tools/arcade_autopilot.py` / `health_check()` | Comprueba presencia y ownership | No | No | No | No; `FOREIGN_UNKNOWN` bloquea |
| `el_gordo_tools/arcade_recover.py` / `diagnose()` | Read-only; informa metadata | No | No | No | No |
| `state/arcade_audit/scripts/full_game_certifier.py` y recovery/certifier históricos | La copia planner lee presencia; recovery inspecciona | Sin creación en planner/recovery | No | No | No |
| `state/arcade_audit/scripts/active/*`, `universal_certifier/*` | Copias históricas/alternativas | Revisadas; no son la ruta principal ejecutada por `el_gordo_tools/full_game_certifier.py` | No observado adicional | No observado adicional | Transaction copies protegidas también |
| `selector_controles`, `es_systems_el_gordo.cfg`, services/hooks revisados | Sin referencia directa al marker | Ninguna referencia de creación encontrada | No | No | No |

La ruta de imports de `full_game_certifier.py` prioriza `el_gordo_tools` al importar `certification_transaction`; las copias `scripts/`, `scripts/active/` y `scripts/universal_certifier/` también quedaron actualizadas para que una invocación alternativa no mantenga el restore inseguro. La búsqueda no encontró una creación desde `selector_controles`, `es_systems_el_gordo.cfg` ni hooks/servicios; esos componentes no compiten como escritores.

## Causa raíz demostrada y límite

La causa a nivel de protocolo está demostrada: hubo escritores independientes para el mismo one-shot, sin ownership común de su ciclo de vida, y el transaction engine genérico interpretó `PRE ausente + POST presente` como un archivo que podía eliminar al restaurar. La exclusión `O_EXCL` impidió overwrite, pero por sí sola no evitó que restore borrara el archivo de otra transacción.

El proceso específico que creó el marker de CERT-007 **no se puede atribuir** con la evidencia preservada. Los dos productores directos comprobados son `full_game_certifier.run_one()` y `smoke_runner.run_one()`; el dispatcher sólo consume una marca compatible. El manifest conservó hash/tamaño, no el payload ni PID del escritor. No se afirma que uno de esos productores concretos haya sido el escritor del incidente.

## Mitigación local en prueba

- Creación exclusiva compartida bajo `boot_audit_once.lock`, con metadata aditiva: `schema_version`, `owner`, `transaction_id`, `pid`, `process_start_ticks`, `created_at_utc`, `requested_system`, `requested_rom`; permanecen `enabled/system/rom/choice/created_at/expires_at/audit_id` para compatibilidad.
- El dispatcher consume bajo el mismo lock y conserva su UX normal.
- Restore del marker: sólo elimina una marca post-state si está identificada como creada por el `transaction_id` actual. Si PRE ya contenía una marca modificada, o apareció una marca extranjera después de PRE, devuelve `FOREIGN_STATE_CONFLICT` y conserva los bytes.
- Autopilot bloquea con `MARKER_FOREIGN_UNKNOWN` ante una marca presente.
- `arcade_recover.py` sigue siendo diagnóstico read-only; no existe una limpieza automática de marcas stale.
- Tests aislados A–D y carrera de dos escritores: PASS (incluye SHA BEFORE=AFTER para marcas extranjeras). La clasificación `STALE_PROVEN` exige PID/transaction/runtime/metadata compatibles; sólo clasifica, no borra.
- Suite Autopilot + ownership: 26/26 PASS; `py_compile` de las rutas activas y mirrors modificados: PASS; transaction engine `self-test`: `TRANSACTION_ENGINE_SELF_TEST_PASS`.
- Pruebas de sesión desacoplada y duplicate guard: PASS sin ejecutar certifier ni juego. `arcade_certifier_job.py status`: `NOT_RUNNING`.
- `arcade_autopilot start --dry-run`: bloqueado correctamente por `PAUSED_ENGINE_FAILURE`; no propuso batch ni lanzó juego.
- Gates read-only observados: ES `isIdle=true`, `NO GAME RUNNING`, ES PID 7104, emu PID 0; HDMI `alsa_output.pci-0000_01_00.1.hdmi-stereo`; SHA de `batocera.conf` y JSON de P1–P4 coinciden con el baseline; marker ausente. La consulta runtime de `controller_dispatcher --diagnose` fue intermitente: una ejecución confirmó P1–P4, otras devolvieron `P1 no está conectado`; `sdl2-jstest --list` enumeró event17–20. Por esta discrepancia el gate runtime P1–P4 queda INCONCLUSO y el pause continúa.

## Estado operativo

CERT-007 permanece ABIERTO/EN PRUEBA. El checkpoint sigue `PAUSED_ENGINE_FAILURE`; no se reintenta `xmultipl`, no se inicia otro juego ni batch, y los nueve AUTO_PASS de Batch 11 permanecen intactos. Cerrar el incidente requiere resolver/explicar la discrepancia intermitente del diagnóstico P1, decisión explícita de reconciliación/retry de `xmultipl` y una validación final de runner bajo el flujo autorizado. No publicar Autopilot todavía.


## Cierre y validación final — 2026-11-17

- Causa de protocolo confirmada: `full_game_certifier.run_one()`, `smoke_runner.run_one()` y runners históricos tenían rutas capaces de crear el mismo marker con `open('x')`, sin ownership común; el dispatcher también lo consumía. La evidencia de CERT-007 no conservó el payload ni PID del creador, así que el escritor concreto permanece desconocido.
- Mitigación instalada: helper común con lock y create-exclusive, metadata de owner/transaction, abort `MARKER_ALREADY_EXISTS`/`FOREIGN_UNKNOWN`, y restore que devuelve `FOREIGN_STATE_CONFLICT` ante marker ajeno. Los tests existentes de ownership, foreign marker, carrera y restore pasaron; suite local reportada: 26/26 PASS.
- Discrepancia de controles: las primeras lecturas dentro del sandbox no tenían `/dev/input`; no representan el namespace de Batocera. En el runtime real, cinco snapshots consecutivos vieron USB5/event17, USB6/event18, USB8/event20 y USB7/event19 en `/proc`, by-path, udev y SDL; `controller_dispatcher --diagnose` pasó 5/5. No se modificaron USB mappings ni P1-P4.
- Estado previo al retry: ES `isIdle=true`, `NO GAME RUNNING`; HDMI sink por defecto; `batocera.conf` y `controller_technical.json` conservaron hashes baseline; MAME global `mame078plus`, 18 overrides; marker ausente y sin certifier/autopilot activo.
- Retry autorizado e independiente: `mame:/userdata/roms/mame/xmultipl.zip`, transaction `20261117T023330_2ac933f47e`: adapter/core `MAME078PLUS`, identidad correcta, HDMI PASS, runtime estable 20.08 s, `VISUAL_ACTIVITY`, exit 0, `AUTO_PASS`, `RESTORE_VERIFIED` (10 rutas). `full_game_certification.csv` conserva una sola fila para xmultipl; la transacción aumentó a 920, retries a 2, AUTO_CERTIFIED a 898 y ENGINE_FAIL activo bajó a 0. `ENGINE_FAIL_TOTAL_HISTORICAL=2` se conserva.
- Batch 11 sigue parcial: sus 9 AUTO_PASS originales no se repitieron; las 10 transacciones originales permanecen en `batch_in_progress`; `NEXT_GAME=xsleena`. Ningún otro juego/batch se inició en esta recuperación.
- Resultado: CERT-007 CERRADO como incidente de protocolo mitigado y validado. Se conserva explícitamente la limitación de atribución del escritor original y toda la evidencia histórica.
