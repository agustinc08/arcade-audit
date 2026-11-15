# Arcade Master Audit — estado reanudable

Actualizado: 2026-11-15T10:52:13+00:00

## Estado confirmado

- Batocera 43.1; no se actualizó. Catálogo Arcade histórico: 1.397; BOOT_OK histórico 1.094 default + 18 MAME actual + 88 FBNeo = 1.200 títulos únicos reportados.
- Core global MAME `mame078plus`; 18 overrides individuales, sin cambios. P1 USB5/event17/js0; P2 USB6/event18/js1; P3 USB8/event20/js3; P4 USB7/event19/js2.
- El control `altair` fue un positive control, no una recuperación/certificación nueva: ES API → dispatcher → launcher → RetroArch `/usr/lib/libretro/mame_libretro.so`; game_health id 8174, 21,25 s, exit 0; HDMI default durante la sesión; restore transaccional de 62 rutas VERIFIED.
- Audio HDMI policy instalada en el custom_service existente. DS4 endpoint quedó disponible. Desconexión/reconexión física y reboot validation siguen pendientes.
- FBNeo DAT instalado v1.0.0.03 localizado y verificado por hash/version y CRC/tamaño de `sfiii3` y `captcomm`. No se relanzaron reservados.
- No se borraron ROMs, BIOS, CHD, saves ni NVRAM. Los árboles MAME nuevos creados por el control fueron restaurados después de verificar que estaban ausentes en PRE_STATE.

## Bloqueos y fases

Consultar `arcade_master_checkpoint.json` como fuente de estado. PHASE_03 catalog curation sigue RUNNING; no repetir ni borrar. PHASE_14 sigue BLOCKED para automatización general: falta implementar adapters por sistema y un piloto de 10 casos. Ningún juego nuevo se marca AUTO_CERTIFIED, CONTROL_CERTIFIED o GUEST_READY. La prueba positiva de `altair` sólo valida la cadena/transaction gate.

`CERT-001` está mitigado: el runner histórico no se usa; motor actual pasó self-test (archivos, árboles y conflicto concurrente) y el control `altair` restauró 62 paths con batocera.conf SHA intacto. Los siguientes adapters deben declarar sus directorios/file paths persistentes; no usar restores globales históricos.

## GitHub

El publisher detuvo el primer intento por `LARGE_CHANGESET`; no se bajó ningún umbral. El changeset se revisó ruta por ruta, el test JSON remoto previamente autorizado fue recuperado en el source activo y el inventario final no debe contener borrados. La autorización one-time exacta publicó 96 archivos añadidos y 1 modificado, sin borrados. SECRET_SCAN/PAYLOAD_SCAN PASS; `main` verificado en `71ed4467dc56c349f85657f0ec0268a48adfe80b` (`arcade: master audit infrastructure`). El guard normal permanece intacto.

## Persistencia y salud

Audio: `AUDIO_POLICY_INSTALLED`, reconexión física/reboot pendientes. Restore: positive control PASS. FBNeo DAT: VERIFIED. Global MAME y 18 overrides sin cambios. P1–P4 sin cambios. No iniciar un batch masivo hasta completar adapters y un piloto de infraestructura; después mantener HDMI monitorizado en cada test.

## Universal certifier — piloto real (2026-11-15)

El runner `/userdata/system/el_gordo_tools/full_game_certifier.py` ya ejecuta por la API de EmulationStation y conserva el selector/dispatcher. Se corrigió la precedencia de módulos: carga el motor transaccional actual de `el_gordo_tools`, no la copia histórica de `scripts/`.

El piloto terminó con 10/10 juegos únicos `AUTO_PASS` (11 intentos por una expectativa de core PC Engine corregida y reprobada). Cada PASS verificó identidad de ROM, dispatcher/marker, core, HDMI, estabilidad, actividad visual, `game_health` exit 0, retorno a ES y restore. No hubo wrong dispatch, cambio de audio, fallo de restore ni regresión P1-P4/core global. Los snapshots de transacción se podaron sólo tras restore verificado, conservando manifests/resultados.

Adapters detectados: 48 sistemas; 23 READY por familia y 25 standalone aún pendientes. La pasada masiva opera sólo sistemas READY y cada juego necesita su propio preflight y restore scope. El adapter standalone no se lanza. `AUTO_CERTIFIED=10`; `CONTROL_CERTIFIED=0`; `GUEST_READY=0`. Reconnect/reboot físico de DS4 sigue pendiente.

Detalle: `reports/UNIVERSAL_CERTIFIER_PILOT.md`; registro: `data/certifier_adapter_registry.csv`; progreso y reanudación: `full_game_certification_checkpoint.json`. Siguiente: lote prioritario de hasta 50, con checkpoint por juego.
