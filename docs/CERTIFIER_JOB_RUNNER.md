# Runner desacoplado del certifier

## Propósito

`/userdata/system/el_gordo_tools/arcade_certifier_job.sh` separa el control por SSH/Codex del proceso que ejecuta `full_game_certifier.py`. El helper inicia jobs explícitamente; no existe autoarranque al boot, cron ni servicio de certificación.

El proceso supervisor se lanza con `subprocess.Popen(start_new_session=True)`. Python crea una sesión nueva mediante `setsid(2)`; el job no conserva la sesión ni el terminal de SSH. `nohup`, `tmux` y `screen` no son requisitos. En este equipo está disponible `nohup` y `tmux`; no se encontró `setsid` ni `screen` en `PATH`. No se instala nada.

## Comandos

```sh
/userdata/system/el_gordo_tools/arcade_certifier_job.sh start 100
/userdata/system/el_gordo_tools/arcade_certifier_job.sh status
/userdata/system/el_gordo_tools/arcade_certifier_job.sh log
/userdata/system/el_gordo_tools/arcade_certifier_job.sh log 100
/userdata/system/el_gordo_tools/arcade_certifier_job.sh stop-safe
```

`start N` admite 1–100 y lanza `full_game_certifier.py --batch N`. Antes de iniciar comprueba que no haya otro certifier; el estado/checkpoint esté `COMPLETE`, reconciliado y sin lote parcial; `NEXT_GAME` sea elegible y `NOT_TESTED`; no haya ENGINE_FAIL activo; y que los gates de seguridad integrados sigan pasando: ES/API idle, marker ausente, procesos de lanzamiento ausentes, EmulationStation activo, HDMI como salida de audio, P1–P4, hashes de configuración global y dispatcher. El certifier mantiene además sus propios gates de identidad, audio, transacción y restore.

Si el checkpoint no está limpio o un proceso ya existe, start se niega; para duplicados devuelve `CERTIFIER_ALREADY_RUNNING`. El job tiene límite natural `--batch N` y termina al completar N juegos.

`status` es de sólo lectura. Presenta estado, PID, tiempo transcurrido, juego actual, conteos de lote, restores, cursor, sesión/proceso y log. `log` muestra 50 líneas por defecto y acepta 1–1000.

`stop-safe` escribe una solicitud para el job actual. El certifier la atiende al llegar al límite entre juegos, después de completar la transacción previa y verificar restore y baseline. No envía señales de terminación y no usa `kill -9`. Si se solicita durante una transacción, esa transacción debe terminar antes de parar. El job queda `COMPLETE` con `completion_reason=SAFE_STOP_AT_GAME_BOUNDARY` y el checkpoint conserva la tanda parcial; `start N` retoma ese lote desde el siguiente juego y limita la ejecución al remanente de la tanda original.

## Archivos y recuperación

- `/userdata/system/state/arcade_audit/jobs/certifier_job.json`: metadata, estado, PID, command, exit code y fechas; no contiene secretos.
- `/userdata/system/state/arcade_audit/jobs/history/<job_id>.json`: copia histórica completa creada al consumir un job del batch anterior ya reconciliado y publicado.
- `/userdata/system/state/arcade_audit/jobs/certifier_job.pid`: PID de certifier/supervisor activo.
- `/userdata/system/state/arcade_audit/jobs/certifier_job.log`: enlace al log del job actual.
- `/userdata/system/state/arcade_audit/jobs/logs/<job_id>.log`: log del job; los logs completos previos se comprimen a `.log.gz` al iniciar el siguiente job. Los logs de jobs fallidos se conservan sin comprimir ni borrar.

Después de reconectar: ejecutar `status`. Si `RUNNING`, no iniciar otro. Si `COMPLETE`, reconciliar CSV/checkpoint/summary/current state y después publicar desde Codex. Si `FAILED`, conservar el log, revisar `exit_code`, checkpoint, transacción y restore antes de cualquier reanudación. El helper nunca publica a GitHub ni contiene tokens.

Después de publicar un batch, Autopilot puede marcar su job `CONSUMED` al preparar
el batch inmediatamente siguiente, pero sólo cuando checkpoint, task CERT,
task de publicación, summary, CSV y SHA remoto estén reconciliados. El estado
`CONSUMED` conserva la metadata activa con `consumed_at`, `consumed_by_task` y
`archive_path`; el JSON original permanece en `jobs/history/`. La comprobación
de `RUNNING` y la guarda de certifier activo ocurren antes, así que consumir un
job anterior no permite abrir dos certifiers.

## Límite actual de validación

El helper y la separación de sesión se implementaron, pero la prueba de certificación desacoplada queda pendiente. El estado real observado el 2026-11-16 avanzó más allá del estado de partida indicado: `priority_batch_11` tiene 10 transacciones/restores verificados, 9 juegos lanzados con AUTO_PASS, y `xmultipl` abortado antes de `/launch` por `CERTIFIER_EXCEPTION:FileExistsError` al crear `/userdata/system/state/boot_audit_once.json`. El 2026-11-17 el master/summary/current state quedaron reconciliados con 919 transacciones y `NEXT_GAME=mame:/userdata/roms/mame/xsleena.zip`, pero la fase sigue `BLOCKED`, `engine_fail_active=1` y el checkpoint no está en estado ejecutable. El helper rechaza ese estado. No se debe quitar esa guarda para forzar una prueba.

### Mitigación local de marker (2026-11-17, EN PRUEBA)

La auditoría confirmó dos creadores directos que comparten el path: `full_game_certifier.run_one()` y `smoke_runner.run_one()`. `controller_dispatcher.consume_boot_audit_once()` lee y consume un marker coincidente; no lo crea. El proceso que escribió el marker de CERT-007 no puede atribuirse porque el manifest conservó SHA/tamaño pero no payload/PID.

Se añadió un lock compartido para create/consume/cleanup y metadata de owner/transaction. El restore transaccional ahora devuelve `FOREIGN_STATE_CONFLICT` si la marca no pertenece a la transacción actual. El marker presente bloquea Autopilot como `MARKER_FOREIGN_UNKNOWN`. Pruebas locales aisladas no lanzan juegos. CERT-007 y `PAUSED_ENGINE_FAILURE` permanecen activos; todavía no iniciar un juego ni Batch 11.

También hay un lock exclusivo del proceso certifier, y el job runner sólo acepta un inicio bajo Autopilot si el token de `run_id`, PID, start ticks y relación padre/hijo coinciden. El Autopilot pasa su token explícitamente; una invocación manual no puede colarse como tarea suya. La suite local confirma guards y detached session, pero el certifier real está `NOT_RUNNING` y no se probó una ejecución que lanzara un juego.

