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
