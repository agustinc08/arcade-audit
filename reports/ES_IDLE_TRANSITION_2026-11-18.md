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
