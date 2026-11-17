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
- Exportar tasks, estado saneado, handoffs, docs y scripts aprobados; nunca PID,
  lock, log o eventos JSONL.

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
