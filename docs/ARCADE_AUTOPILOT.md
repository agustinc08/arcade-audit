# ARCADE AUTOPILOT

Estado: EN PRUEBA. Es una state machine determinística, no un agente IA.
No se activa en boot y esta versión no invoca Codex.

## Arquitectura

`arcade_autopilot` mantiene tareas en `data/autopilot_tasks.json`, estado en
`autopilot_state.json`, eventos en `data/autopilot_events.jsonl` y log rotado
en `logs/autopilot.log`. PID/lock y logs permanecen locales. Los JSON de estado
usan `fsync` y `replace` atómico.

```text
Codex / SSH (inicio, inspección y recuperación)
    ↓ arcade_autopilot start|status|pause|resume|stop-safe
Autopilot desacoplado (sesión propia, lock flock y PID validado en /proc)
    ↓ arcade_certifier_job.sh start N / status / stop-safe
Certifier desacoplado (--batch N, checkpoint por juego)
    ↓ reconcile → rebuild → publisher REST → siguiente tarea segura
```

No hay cron, servicio ni auto-start. Se conservan identity, ES/API/marker,
HDMI/audio, restore, `batocera.conf`, core/overrides MAME, P1–P4, disco y
transaction gates.

Cada transacción automática autoriza como máximo un inicio de emulador. El
dispatcher reclama el inicio mediante escritura atómica ligada a
`transaction_id`, `boot_id`, identidad PID/start_ticks de EmulationStation,
sistema, ROM canónica e identidad de la invocación. Una segunda ejecución ES
que aún coincida con esa transacción queda registrada y se suprime antes de
`configgen`/`emulatorlauncher`. Contexto ausente, corrupto o con identidad
ambigua bloquea el lanzamiento automático. El camino manual no usa esta
reclamación y conserva el selector normal; no se deduplica por ROM/tiempo.

La reconciliación de Batch 69 distingue el incidente inicial (sin emulador)
del retry que llegó a RetroArch dos veces. Sólo acepta ese par exacto de
transacciones, ambas con restore verificado y resultado no terminal, evidencia
del segundo PID cerrado, runtime limpio, configuración protegida/restaurada,
cursor MrBoom y hash remoto del guard publicado. Conserva resultados y el
conteo `considered=1`, `launched=2`, `RESTORES=2`; no convierte el safety
failure en `GAME_FAIL` ni en certificación.

## Comandos

- `arcade_autopilot start [--batch-size 100] [--max-batches 10]`: health check,
  guard de duplicados y comienzo explícito. Batch máximo: 100.
- `arcade_autopilot start --dry-run`: expone tarea, juego y safety gates sin lanzar.
- `arcade_autopilot status`: estado, PID/sesión, tarea, batch, contadores, cursor y SHA.
- `arcade_autopilot log [50|100]`: últimas líneas; máximo 1000.
- `arcade_autopilot tasks`: resumen por estado; `next`: próxima tarea segura/handoff.
- `arcade_autopilot pause`: no empieza otra tarea; permite terminar transacción/restore.
- `arcade_autopilot stop-safe`: boundary seguro y restore; no usa `kill -9`.
- `arcade_autopilot resume`: adopta job válido o inicia tras nuevos gates.

Tras desconexión, consultar `status`. Si RUNNING no iniciar otra instancia.
Un certifier se adopta sólo si PID/command line, metadata y checkpoint coinciden.
Job COMPLETE se reconcilia antes de reports/publicación. Estado dudoso pausa.

### Consumo seguro de job COMPLETE anterior

Al entrar al batch inmediatamente siguiente, un job `COMPLETE` no se ignora
por su estado solamente. Se consume sólo si su identidad (`job_id`, PID,
worker PID, owner `run_id`/PID/start ticks) es coherente; `latest_batch` es el
anterior inmediato; la task CERT y la task GITHUB-PUBLISH de ese batch están
`COMPLETE`; checkpoint, CSV y summary reconcilian; no hay batch parcial,
`blocked_reason` ni `engine_fail_active`; el cursor es válido; y el SHA remoto
publicado coincide con el estado de publicación.

La metadata original queda archivada en `jobs/history/<job_id>.json`. La
metadata corriente pasa a `CONSUMED` con `consumed_at`, `consumed_by_task` y
`archive_path`. Si falta evidencia, el estado queda `PAUSED_SAFETY` con
`COMPLETE_JOB_CHECKPOINT_MISMATCH` y no se inicia el runner. Un job `RUNNING`
sigue usando los guards existentes de PID/command line/checkpoint y no crea un
segundo certifier. Un reintento después del consumo exige validar de nuevo el
archivo histórico y la reconciliación.

Si el proceso Autopilot cae después del consumo y antes del start, la task del
batch siguiente vuelve a `READY` sólo cuando el checkpoint sigue limpio y la
última metadata está `CONSUMED`; luego se vuelven a validar el archivo y el SHA
antes de iniciar exactamente un runner nuevo.

La publicación de un batch genera además `jobs/publications/<batch>.json` con
las identidades CERT/PUBLISH, SHA remoto verificado, fecha y hashes SHA-256 del
checkpoint, summary y report del batch. El consumo vuelve a comparar esos
hashes con los artefactos locales; un SHA remoto aislado no es evidencia
suficiente. La copia `certifier_job` de `autopilot_state.json` es un snapshot:
la metadata de `jobs/certifier_job.json` es la identidad canónica y el snapshot
sólo se usa para detectar que se está hablando de otro `job_id`.

El cursor canónico es `full_game_certification_checkpoint.json.next_untested`
después de completar la reconciliación. Un snapshot previo del job puede tener
un cursor anterior; no invalida el checkpoint reconciliado. Los nombres ROM
pueden contener espacios. `considered` puede exceder `launched` cuando el
preflight produce `STATIC_FAIL`; cada entrada considerada debe quedar clasificada,
pero no debe exigirse `launched == considered`.

El error `COMPLETE_JOB_CHECKPOINT_MISMATCH` siempre conserva el motivo concreto
como `COMPLETE_JOB_CHECKPOINT_MISMATCH:<SUBREASON>` en la task, el evento, el
log y `pause_reason`. La finalización de batch guarda `completed_batch_ids`
antes de marcar la task `COMPLETE`, para no sumar dos veces tras una caída.

Durante un batch activo, `STATUS: RUNNING` y `ARCADE_SAFETY: PASS` son campos
separados: `RUNNING` no representa un fallo de safety. `NEXT_ACTION` se deriva
del certifier vivo cuando éste está procesando.

El arranque de un job bajo Autopilot valida primero el `run_id`, PID y
`process_start_ticks` del worker. El detached runner conserva esa vinculación en
`certifier_job.json`; el certifier la vuelve a verificar junto con su PID y el
PID de su worker. No depende de encontrar al Autopilot como ancestro del
certifier, porque el job crea una sesión propia y el proceso queda reparentado.
Un inicio manual durante un Autopilot activo sigue siendo rechazado.

## Tareas y recuperación

Las tareas se agrupan por batch o root cause, no por cada AUTO_PASS.
`automatic=true` requiere dependencias completas, intentos disponibles y health
gates aprobados. CODEX_REQUIRED/MANUAL_REQUIRED crean handoffs explícitos; tareas
automáticas independientes conservan prioridad. Adapter PENDING se lee del
registry al crear la queue; muestra física se toma de `manual_physical_test_queue.csv`.
No se promociona `GUEST_READY`; repairs sin receta revisada quedan bloqueadas.

Los estados de task son `PENDING`, `READY`, `RUNNING`, `COMPLETE`, `FAILED`,
`BLOCKED`, `CODEX_REQUIRED`, `MANUAL_REQUIRED`, `PAUSED_SAFETY` y `SKIPPED`.
El estado global es `STOPPED`, `RUNNING`, `PAUSED`, `PAUSED_SAFETY`,
`WAITING_CODEX`, `WAITING_MANUAL`, `COMPLETE` o `ERROR`. La selección considera
prioridad, dependencias y máximo de intentos; una tarea CODEX/MANUAL no bloquea
otras tareas automáticas independientes.

- No duplica Autopilot/certifier: lock `flock`, PID, start ticks y `/proc`.
- GAME_FAIL/STATIC_FAIL aislados no pausan el motor.
- Marker collision, restore, transaction, config, mapping, audio, disco o ES
  incongruentes bloquean nuevos trabajos.
- Un marker presente sin ownership demostrable se clasifica
  `MARKER_FOREIGN_UNKNOWN` y mantiene `PAUSED_SAFETY`; no se limpia por edad.
- La parada segura conserva checkpoint parcial; no se reintenta identidad terminal.
- GitHub falla sin revertir progreso local; retry acotado con backoff.
- Log máximo 5 MiB y tres rotaciones.
- Cada batch estable genera `reports/AUTOPILOT_STATUS.md` con métricas,
  fallos, handoffs y siguiente cursor.
- Un retry excepcional autorizado para una sola transacción detiene el worker
  tras publicar su propio batch; no puede consumir el límite `max_batches` y
  seguir con el siguiente batch. El estado persistido bloquea otro start hasta
  revisión explícita.
- Exportar tasks, estado saneado, handoffs, docs y scripts aprobados; nunca PID,
  lock, log o eventos JSONL.

### Reconciliación explícita post-reboot de bloqueos ES

`arcade_autopilot reconcile-recovered-safety` es una ruta separada y fail-closed
para un checkpoint `PAUSED_SYSTEM_SAFETY_FAILURE` cuyo motivo contenga
exactamente una causa recuperable (`ES_NOT_IDLE`, `ES_IDLE_TIMEOUT` o
`SELECTOR_NOT_CLOSED`). Exige ES idle y `NO GAME RUNNING`, ausencia de marker y
procesos de lanzamiento/certifier, `engine_fail_active=0`, la última transacción
con resultado y manifest `RESTORE_VERIFIED`, hashes protegidos compatibles con
el baseline transaccional y reconciliación de queue/checkpoint. Sólo entonces
guarda backup, registro de recovery y transforma el estado en `STOPPED_SAFE`;
preserva íntegros el lote parcial, resultados y cursor. No habilita otros
blockers ni marca un batch `COMPLETE`.

Las nuevas metadata de job guardan `/proc/sys/kernel/random/boot_id` y el
estado del PID. Después de reiniciar, un PID persistido sólo se reconoce activo
si coincide el boot y `/proc/<pid>` confirma el comando certifier; el PID no es
una identidad suficiente por sí solo.

La operación real se libera sólo después de pruebas y un test pequeño elegible
con detached survival, checkpoint y restore. Si el checkpoint está bloqueado,
no iniciar juegos ni `start` real.

## Validación del handoff detached — 2026-11-17

El primer arranque real de Autopilot llegó al detached job runner, pero el
certifier rechazó tres veces la ejecución antes de lanzar un juego. La causa
fue que el guard del certifier exigía una cadena de ancestros hasta Autopilot;
la sesión propia del worker rompe esa cadena al reparentar el certifier. Los
tres logs `REFUSED` y el checkpoint `STOPPED_SAFE` se conservan. La corrección
local valida la delegación guardada por el runner contra el Autopilot activo,
su PID/start ticks, el `run_id`, el PID del worker y el PID/command line del
certifier. Pruebas unitarias focalizadas y dry-run pasan. La publicación y el
arranque sólo se consideran listos después de verificar esta revisión en
GitHub; no se atribuye a este rechazo ningún fallo de juego.
