# Autopilot / detached certifier ownership handoff

Estado: EN PRUEBA  
Fecha: 2026-11-17

## Síntoma

Autopilot quedó en `WAITING_CODEX` con `CERT-BATCH-0011` sin iniciar. El runner
rechazó el certifier tres veces con `AUTOPILOT_ALREADY_RUNNING_WITHOUT_OWNER_TOKEN`.
Los tres logs de job contienen únicamente `REFUSED`; el checkpoint permanece
`STOPPED_SAFE` en `mame:/userdata/roms/mame/xsleena.zip`. No hubo POST `/launch`
ni proceso de juego.

## Causa raíz

El runner validaba correctamente que su proceso start tenía como padre directo
al worker Autopilot y que coincidían `run_id`, PID y `process_start_ticks`.
Después creaba un worker en una sesión separada y éste lanzaba
`full_game_certifier.py`. Ese detached handoff reparenta al certifier, así que
la comprobación de ancestros del certifier ya no podía encontrar al Autopilot.
La negativa fue fail-closed, pero inutilizaba el flujo detached.

## Cambio mínimo

`arcade_certifier_job.py` ahora registra en el metadata del job la identidad
validada del Autopilot que delegó el start. El certifier comprueba el owner
registrado contra el estado vivo de Autopilot, el entorno `run_id`, PID y start
ticks, y además verifica su propio PID y el PID de su worker. Arranques manuales
siguen rechazados durante un Autopilot activo. No se usa la mera presencia de
una variable de entorno como autorización.

## Evidencia y validación

- Los tres intentos del 2026-11-17 fueron sólo rechazos previos al launch; sus
  logs están en `jobs/logs/20261117T083*.log*`.
- Backup de los scripts y test previo al cambio:
  `recovery_backups/autopilot_owner_handoff_20261117T1136/`.
- `py_compile` de runner, certifier y test: PASS.
- Tests focalizados de delegación válida, PID de worker incorrecto, owner
  foreign y rechazo de inicio manual: PASS (3/3).
- `arcade_autopilot start --dry-run --batch-size 100 --max-batches 100`:
  `HEALTH: PASS`, `CHECKPOINT: PASS`, próxima tarea `CERT-BATCH-0011`,
  próximo juego `mame:/userdata/roms/mame/xsleena.zip`; no lanzó juego.
- La suite completa 26/26 no se repitió; los cambios se cubrieron con tests
  focalizados.

## Resultado de validación

- Publicación infra con `SECRET_SCAN` y `PAYLOAD_SCAN` PASS. HEAD remoto
  verificado: `f1124def868182422a7eee0be43aeecb7b811cc8`; no force.
- Dry-run final: `HEALTH: PASS`, `CHECKPOINT: PASS`, próxima tarea
  `CERT-BATCH-0011`, cursor `xsleena`.
- Autopilot activo en PID 2061, sesión/grupo 2061; runner PID 2094, sesión/grupo
  2094; certifier PID 2096. Los tres procesos fueron observados vivos bajo
  `/proc` y el job conserva el owner `run_id`/PID/start ticks esperado.
- El checkpoint progresó desde 10/100 hasta 19/100: `AUTO_PASS=18`,
  `GAME_FAIL=0`, `RESTORE_VERIFIED=19`, `RESTORE_FAILURES=0`,
  `AUTO_CERTIFIED=907`; cursor siguiente `mame:/userdata/roms/mame/znpwfv.zip`.
  Ningún resultado terminal original fue relanzado.
- `arcade_autopilot status` imprime `ARCADE_SAFETY: FAIL:RUNNING:None` cuando
  el checkpoint está en RUNNING. Es una limitación de su presentación actual:
  el resumen sólo define PASS para COMPLETE/STOPPED_SAFE; no refleja que el
  launch pasó `HEALTH: PASS`/`CHECKPOINT: PASS` ni que el job RUNNING está
  vinculado a Autopilot. No provocó pausa ni detuvo el worker. Debe corregirse
  como indicador `IN_PROGRESS` en una revisión futura, sin cambiar gates.

Autopilot y certifier siguen detached y el checkpoint progresa; Codex puede
finalizar sin esperar la terminación de Batch 11. Batch 11 sigue RUNNING. No
iniciar Batch 12 ni repetir los nueve `AUTO_PASS` originales.
