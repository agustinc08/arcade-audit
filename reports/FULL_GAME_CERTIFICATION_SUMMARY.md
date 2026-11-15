# Certificación completa de juegos — estado reanudable

- Fecha: 2026-11-15T10:07:42+00:00
- Sistemas con inventario: 51
- Juegos/registros: 8426
- Instalados según fichero/gamelist: 8400
- Evidencia histórica BOOT_OK: 1200
- STATIC_VALIDATED completo: 0 (la mera presencia no verifica dependencias/ROMset)
- AUTO_CERTIFIED: 0; CONTROL_CERTIFIED: 0; GUEST_READY: 0
- NOT_TESTED para auto-certificación: 8426
- FAIL histórico conservado, separado: 197
- FLAKY: 0 nuevos (sin reintentos de runtime en esta fase)
- NEEDS_REPAIR: los fallos históricos están en `arcade_games_audit.csv`; consolidación de causas pendiente.
- MANUAL_REQUIRED: control físico, audio reconnection, salida por sistema/core.

## Lectura correcta

Los BOOT_OK históricos no se elevan a AUTO_CERTIFIED. No hubo lanzamientos nuevos: se creó un baseline separado actual y verificado que conserva el histórico, pero todavía falta integrar una transacción de restore en el runner universal; además el default de audio sigue en el sink del DualShock.

La prueba automática futura deberá pasar por EmulationStation, `controller_dispatcher` y launcher oficial; snapshots transaccionales por juego, duración específica por sistema, evidencia visual/audio y estado limpio serán obligatorios.

## Resumen por sistema

- **atari2600**: total 2, instalado 2, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **c64**: total 4, instalado 4, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **cannonball**: total 1, instalado 0, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **cdogs**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **devilutionx**: total 8, instalado 0, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **dreamcast**: total 775, instalado 775, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **easyrpg**: total 12, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **fbneo**: total 104, instalado 104, BOOT_OK histórico 88, FAIL histórico 1, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **fds**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **flatpak**: total 2, instalado 2, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **gamecube**: total 9, instalado 9, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **gb**: total 410, instalado 410, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **gba**: total 725, instalado 725, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **gbc**: total 406, instalado 406, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **hcl**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **hurrican**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **ikemen**: total 2, instalado 0, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **mame**: total 1324, instalado 1324, BOOT_OK histórico 1112, FAIL histórico 196, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **mastersystem**: total 383, instalado 383, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **megacd**: total 24, instalado 24, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **megadrive**: total 1037, instalado 1037, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **mrboom**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **n64**: total 377, instalado 377, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **naomi**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **nds**: total 2, instalado 2, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **neogeo**: total 105, instalado 105, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **nes**: total 702, instalado 702, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **odcommander**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **openbor**: total 128, instalado 128, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **pcengine**: total 529, instalado 529, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **ports**: total 5, instalado 5, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **prboom**: total 2, instalado 2, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **ps2**: total 196, instalado 196, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **ps3**: total 13, instalado 13, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **ps4**: total 95, instalado 95, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **psp**: total 631, instalado 631, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **psx**: total 78, instalado 78, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **pygame**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **saturn**: total 6, instalado 6, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **scummvm**: total 3, instalado 3, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **sdlpop**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **snes**: total 275, instalado 275, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **solarus**: total 10, instalado 10, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **steam**: total 7, instalado 7, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **superbroswar**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **theforceengine**: total 6, instalado 6, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **tic80**: total 3, instalado 3, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **windows**: total 7, instalado 3, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **xbox**: total 2, instalado 2, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **xbox360**: total 5, instalado 5, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.
- **xrick**: total 1, instalado 1, BOOT_OK histórico 0, FAIL histórico 0, AUTO_CERTIFIED 0, CONTROL_CERTIFIED 0, GUEST_READY 0.


## Gate de lanzamiento actualizado — 2026-11-15

El default HDMI ya está fijado por el servicio existente y fue comprobado con endpoint DS4 presente. El motor transaccional nuevo pasó pruebas sin juego, incluida la restauración real de `batocera.conf` con SHA antes/después idéntico y detección de conflicto concurrente. `AUTO_CERTIFIED` sigue en 0: falta control positivo mediante ES/controller_dispatcher y completar adapters de estado persistente por sistema. El runner histórico queda fuera de uso.


## Reconciliación de bloqueos — 2026-11-15T10:52:13+00:00

Se realizó un control positivo único de `altair` para validar la cadena de lanzamiento y restauración; no cuenta como juego nuevo certificado. Resultado: ROM correcta en ES y cmdfile; core `/usr/lib/libretro/mame_libretro.so`; proceso estable 21,25 s; HDMI default durante el muestreo; cierre con `game_health` exit 0; retorno a ES; restore de 62 file/tree paths `RESTORE_VERIFIED`; SHA de `batocera.conf` antes/después igual (`098c8844…47b52d2`). Hotkeygen anotó `ProcessLookupError` posterior a la salida del PID; se clasifica `CLEANUP_RACE`, no fallo del juego.

El engine ahora soporta snapshots acotados de árboles existentes y ausentes, además de detectar conflictos concurrentes; su self-test pasó. Aun así `AUTO_CERTIFIED=0`: el scaffold no implementa adapters por sistema ni un piloto de 10 juegos, y falta integrar monitorización HDMI/safety gates en el runner. La reconexión física DS4 y reboot validation permanecen pendientes. No se inició certificación masiva; `CONTROL_CERTIFIED=0`, `GUEST_READY=0`.


## Piloto universal actualizado — 2026-11-15

- Juegos únicos `AUTO_CERTIFIED`: **10** (de 10 del piloto).
- Intentos: 11; un `ENGINE_FAIL` inicial fue un core esperado incorrecto del adapter (`pce_fast` frente al core efectivo `pce` definido por el sistema ES); se corrigió y el mismo juego pasó en la reanudación. Los otros ocho PASS no se repitieron.
- `GAME_FAIL`: 0; `WRONG_GAME_DISPATCH`: 0; `AUDIO_ROUTE_CHANGED`: 0; restore fallido: 0.
- HDMI: estable antes/durante/después. `batocera.conf`, core global, 18 overrides y P1-P4 sin cambios.
- `CONTROL_CERTIFIED`: 0; `GUEST_READY`: 0. El piloto no inyectó inputs ni certificó controles físicos.
- Adaptadores: 48 sistemas detectados; 23 READY por familia; 25 standalone en espera de adapter seguro.
- Reporte detallado: `reports/UNIVERSAL_CERTIFIER_PILOT.md`.
- Siguiente juego del lote: se determina por `full_game_certifier.py --batch 50`; el checkpoint registra progreso por juego.
