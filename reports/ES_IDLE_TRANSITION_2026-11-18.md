# Incidente de transición de EmulationStation — 2026-11-18

Estado: EN INVESTIGACIÓN

## Evidencia observada

- `CERT-BATCH-0059` conservó un resultado nuevo válido: `fds:/userdata/roms/fds/Super Mario Brothers (ESP).fds`, `AUTO_PASS`, transacción `20261118T161913_0b1c456071`, `RESTORE_VERIFIED`.
- El manifest de esa transacción registra `RESTORE_VERIFIED` para los siete paths incluidos. `PRE_STATE` y `POST_STATE` de `/userdata/system/batocera.conf` tienen SHA-256 `098c88444322bacaac5f2f2383e5bf6e5fa42623353fe8c49d307fffc47b52d2`.
- Al observar el sistema, la API devolvió `/isIdle = [false]` y `/runningGame.path = /userdata/roms/fds/Super Mario Brothers (ESP).fds`.
- No había proceso `retroarch`, `flycast` ni `genesisplusgx`. Sí seguía activo `/usr/bin/python3 /userdata/system/el_gordo_tools/selector_controles --timeout 0`, PID `22558`, bajo `controller_dispatcher` PID `22557` y la cadena de shell de EmulationStation con los argumentos de FDS. El selector no tiene timeout y no fue cerrado ni eliminado durante esta investigación.
- Los logs registran `boot_audit_auto_choice` y `launch_health` exitoso para FDS entre `16:19:14` y `16:19:34 -0300`. El proceso del selector pendiente comenzó a las `16:19:34 -0300`. No hay evidencia que permita atribuir el nuevo selector a una acción de usuario, repetición de entrada u otra causa externa.
- `/userdata/system/state/boot_audit_once.json` no existe. El archivo `boot_audit_once.lock` sí existe, pero no es el marker de lanzamiento.
- El certifier comprobó el gate inmediatamente después del restore. La implementación anterior consultaba la API una sola vez y elevaba `ES_NOT_IDLE` sin ventana de transición.

## Clasificación

`SELECTOR_NOT_CLOSED` describe el estado runtime demostrado. La causa que inició esa segunda cadena de selector queda sin determinar. No se clasifica como fallo de Final Fight CD ni del juego FDS.

## Cambios preparados

- `full_game_certifier.py` ahora espera hasta 20 segundos, consultando cada segundo y exigiendo dos observaciones consecutivas limpias. Sólo continúa con API idle, `NO GAME RUNNING`, sin procesos de lanzamiento/emulador y sin marker.
- Un selector, dispatcher, launcher, emulador o marker presente bloquea inmediatamente. El timeout produce `ES_IDLE_TIMEOUT` y conserva evidencia JSON; no intenta reiniciar EmulationStation.
- Los bloqueos del gate se clasifican como `PAUSED_SYSTEM_SAFETY_FAILURE`; no se convierten en `GAME_FAIL`.
- Se agregaron siete pruebas focalizadas con reloj falso, mocks y markers/evidencia en directorios temporales.

## Validación y estado

- `py_compile`: PASS.
- Pruebas focalizadas: 7 PASS.
- La comprobación live sigue bloqueada: selector activo, API non-idle y checkpoint en `PAUSED_SYSTEM_SAFETY_FAILURE`. El dry run no autoriza lanzamiento.
- No se reinició EmulationStation, no se terminó ningún proceso, no se alteró el marker, no se modificó el checkpoint y no se lanzó Final Fight CD.
- El siguiente juego permanece `megacd:/userdata/roms/megacd/Final Fight CD (USA).chd`, sin clasificación terminal.

## Próximo paso

Resolver manualmente la pantalla del selector activo y volver a comprobar API, procesos, marker y configuración protegida. Reanudar sólo cuando el dry run reporte `HEALTH PASS`, `ARCADE_SAFETY PASS` y el siguiente juego exacto. El gate implementado debe seguir fallando cerrado si vuelve a aparecer un selector o launcher activo.

## Reconciliación post-reboot (2026-11-18)

La evidencia previa de `SELECTOR_NOT_CLOSED` y el job `20261118T161901_df534fc7`
`FAILED` se conservan sin modificaciones. El runtime limpio después del reboot
no convierte el incidente histórico en inexistente.

Se agregó `arcade_autopilot reconcile-recovered-safety`, que sólo acepta
`PAUSED_SYSTEM_SAFETY_FAILURE` con una causa identificada como `ES_NOT_IDLE`,
`ES_IDLE_TIMEOUT` o `SELECTOR_NOT_CLOSED`. Antes de cambiar el estado exige:

- ausencia de marker, launcher, selector, dispatcher, emulador y certifier;
- dos observaciones limpias de ES API, con `isIdle=true` y sin juego corriendo;
- cero `engine_fail_active`;
- resultado y manifest de `20261118T161913_0b1c456071` en `RESTORE_VERIFIED`;
- hashes/configuración protegida coincidentes con el baseline de esa transacción;
- cola y checkpoint reconciliados, y cursor exacto en Final Fight CD.

La única transición permitida conserva el lote y cursor, y cambia el checkpoint
a `STOPPED_SAFE`, con `blocked_reason=null` y un registro `safety_recovery`.
También crea una copia previa del checkpoint y un evento de auditoría. No
completa Batch 59 ni reejecuta FDS. Los demás blockers, incluidos restore,
corrupción, cambios de configuración/mapeo, disco y marker desconocido, siguen
sin ruta de limpieza.

La metadata nueva de jobs incluye `boot_id`; status contrasta esa identidad y
la identidad de proceso antes de considerar vivo un PID almacenado. El PID
histórico `21930` no existe en `/proc` en esta sesión de herramientas.

Validación de código: `py_compile` PASS. Los siete tests nuevos focalizados
PASS. La suite completa actual reportó además cuatro fallos en pruebas de
consumo/publicación de jobs (`PUBLISH_TASK_NOT_COMPLETE`,
`PUBLICATION_RECEIPT_INVALID` y expectativa `STOP_TEST_LOOP`); no se alteraron
los jobs/history/markers para hacerlos pasar.

La consulta live posterior sí confirma ES idle (`[ true ]`),
`NO GAME RUNNING`, HDMI `alsa_output.pci-0000_01_00.1.hdmi-stereo`, cero procesos
de lanzamiento y marker ausente. El PID `21930` no existe en `/proc` y se
clasifica `STALE`.

La reconciliación se detuvo por una discrepancia nueva: `controller_dispatcher
--diagnose` asigna actualmente P1–P4 a `event18`, `event19`, `event21`,
`event20`, mientras el baseline transaccional conserva `event17`, `event18`,
`event20`, `event19`. Además, el SHA live de `batocera.conf` es
`bb8579bd3cb91c2ad8606ff04fe2b7ed238ed0264018a418acbe0943c3762426`, distinto
del SHA previo/post transacción `098c88444322bacaac5f2f2383e5bf6e5fa42623353fe8c49d307fffc47b52d2`.
Los hashes de `controller_dispatcher`, `controller_technical.json` y
`multiplayer.json` sí coinciden con el baseline. No se modificaron
configuraciones para resolver estas diferencias.

Por esos gates, no se reconcilió el checkpoint, no se ejecutó el dry run ni se
reanuda Autopilot. Batch 59 permanece en su estado original. La suite
focalizada de recovery pasa; la suite completa conserva cuatro fallos en
pruebas previas de consumo/publicación ya registrados arriba.
