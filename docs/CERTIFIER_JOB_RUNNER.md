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
- `/userdata/system/state/arcade_audit/jobs/certifier_job.pid`: PID de certifier/supervisor activo.
- `/userdata/system/state/arcade_audit/jobs/certifier_job.log`: enlace al log del job actual.
- `/userdata/system/state/arcade_audit/jobs/logs/<job_id>.log`: log del job; los logs completos previos se comprimen a `.log.gz` al iniciar el siguiente job. Los logs de jobs fallidos se conservan sin comprimir ni borrar.

Después de reconectar: ejecutar `status`. Si `RUNNING`, no iniciar otro. Si `COMPLETE`, reconciliar CSV/checkpoint/summary/current state y después publicar desde Codex. Si `FAILED`, conservar el log, revisar `exit_code`, checkpoint, transacción y restore antes de cualquier reanudación. El helper nunca publica a GitHub ni contiene tokens.

## Límite actual de validación

El helper y la separación de sesión se implementaron, pero la prueba de certificación desacoplada queda pendiente. El estado real observado el 2026-11-16 avanzó más allá del estado de partida indicado: `priority_batch_11` ya había lanzado 10 juegos (9 AUTO_PASS) con 10 restores verificados y luego quedó pausado por `CERTIFIER_EXCEPTION:FileExistsError` al crear `/userdata/system/state/boot_audit_once.json`. El 2026-11-17 el master/summary/current state quedaron reconciliados con 919 transacciones y `NEXT_GAME=mame:/userdata/roms/mame/xsleena.zip`, pero la fase sigue `BLOCKED`, `engine_fail_active=1` y el checkpoint no está en estado ejecutable. El helper rechaza ese estado. No se debe quitar esa guarda para forzar una prueba.

