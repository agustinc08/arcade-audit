# Arquitectura del arcade Batocera

Estado observado/documentado: 2026-11-16. Documento descriptivo; no cambia el runtime.

## Arranque y selección

```text
Encendido
  → Batocera Linux
  → servicios persistentes de /userdata/system/services
  → EmulationStation
  → selección de sistema/juego
  → comando de es_systems_el_gordo.cfg
  → controller_dispatcher
  → selector_controles (cuando la configuración de ese sistema lo habilita)
  → launcher oficial de Batocera
  → emulador/core
  → salida/controlada y game health
  → EmulationStation
```

La configuración activa de EmulationStation es `/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg`. Sus comandos arcade invocan `/userdata/system/el_gordo_tools/controller_dispatcher` con los argumentos de sistema, ROM y metadata de EmulationStation. El dispatcher conserva el flujo oficial de Batocera y prepara la selección de perfil antes de entregar el lanzamiento.

`selector_controles` muestra `BOTONERAS PRIMERO`, `JOYSTICKS PRIMERO` y `CANCELAR`. La elección se devuelve al dispatcher; luego el dispatcher clasifica los dispositivos, aplica el perfil y no mezcla perfiles si faltan controles requeridos. La disponibilidad de opciones no certifica que los botones físicos funcionen dentro de cada juego.

## Proceso de certificación

`/userdata/system/el_gordo_tools/full_game_certifier.py` usa la misma API local de EmulationStation y el mismo comando configurado que el jugador. Un adapter seguro realiza preflight, verificación de identidad, audio y procesos. Cada transacción mantiene snapshots mínimos, registra POST_STATE, restaura contra hashes esperados y verifica el estado final. Una falla individual de juego no implica falla del motor; una discrepancia de identidad, restore o estado global pausa nuevos lanzamientos.

El marcador `boot_audit_once.json` es temporal y de un solo uso para la selección automática de perfil durante pruebas autorizadas. No es parte del uso normal del invitado.

El control y la observación se separan de la ejecución larga mediante `/userdata/system/el_gordo_tools/arcade_certifier_job.sh`. Codex/SSH inicia o consulta el job; el helper crea un supervisor en sesión nueva (`start_new_session=True`/`setsid(2)`); el supervisor ejecuta el certifier con límite `--batch N`, guarda metadata/log persistentes y el certifier mantiene checkpoint transaccional por juego. No hay autoarranque al boot, cron ni servicio de certificación.

```text
Codex / SSH
    ↓ start / status / log / stop-safe
arcade_certifier_job.sh
    ↓ supervisor desacoplado de terminal (sesión nueva)
full_game_certifier.py --batch N
    ↓ gates + transacción + restore verificado
checkpoint por juego
```

La operación y recuperación se describen en `CERTIFIER_JOB_RUNNER.md`. El helper rechaza estados no reconciliados, fallos de motor activos o un segundo certifier; la desconexión SSH/Codex no es una señal de parada.

## Core MAME y overrides

El core predeterminado se mantiene `mame078plus`. Algunas ROMs tienen override individual a `mame` (MAME actual); nunca se cambia el core global como atajo. El número y shortnames vigentes se leen de `batocera.conf` y el registro de sistemas, no de esta descripción.

## Servicios personalizados

`/userdata/system/services/custom_service` verifica una modificación persistente de Xenia mediante hashes exactos y, al recibir `start`, inicia la política de audio arcade. Esta auditoría no cambió el servicio. No se encontró `/userdata/system/custom.sh` activo en la inspección inicial.

En los puntos de entrada inspeccionados (`/userdata/system/services`, `el_gordo_tools` y configuración de EmulationStation) no se localizaron hooks personalizados `gameStart`, `gameStop` ni de conexión/desconexión de mandos. No se infiere que Batocera no tenga hooks internos. La captura de controles vivos se realiza mediante herramienta invocada explícitamente y su JSON es una instantánea, no un daemon.

## Cierre

La salida normal de un juego vuelve a EmulationStation por la ruta de Batocera. El watcher de salida del dispatcher conserva el combo existente del P1; no se modificó durante esta auditoría. `AUTO_CERTIFIED` verifica señales de arranque/runtime/restore, pero no reemplaza la certificación física de controles ni habilita por sí solo Guest Mode.
