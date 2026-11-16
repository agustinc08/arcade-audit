# Estado actual del arcade — CURRENT_STATE_RECONCILIATION_FAIL

- UPDATED_AT: 2026-11-16T21:48:47+00:00
- GITHUB_HEAD observado antes de esta publicación: `554e66ddcd0373d629179bfc937879952c2234a3`
- BATOCERA_VERSION: 43.1

## Hardware observado
- CPU: 12th Gen Intel(R) Core(TM) i5-12400F
- GPU: NVIDIA Corporation GP106 [GeForce GTX 1060 3GB] (rev a1)
- RAM: 15Gi
- DISPLAY: configuración HDMI; EDID/modo vivo no disponible desde la sesión de lectura.
- NETWORK: Ethernet y adaptadores Wi-Fi/Bluetooth; no se publican direcciones, SSID ni credenciales.

## Runtime y configuración
- GLOBAL_MAME_CORE (EmulationStation): `mame078plus`
- MAME_OVERRIDES_COUNT: 18
- AUDIO_DEFAULT: `alsa_output.pci-0000_01_00.1.hdmi-stereo`
- AUDIO_POLICY_STATUS: instalada; reconexión física DS4 y persistencia post-reboot siguen pendientes.
- EmulationStation: API idle; `NO GAME RUNNING`; marker ausente; no hay procesos RetroArch/MAME/dispatcher/selector/emulatorlauncher huérfanos.
- P1: USB5 / event17 / js0; P2: USB6 / event18 / js1; P3: USB8 / event20 / js3; P4: USB7 / event19 / js2. Snapshot actual con `mapping_modified=false`.

## Certificación — fuentes en conflicto
- CSV: total=8426, installed=8400, HISTORICAL_BOOT_OK=1200, AUTO_CERTIFIED=499, GAME_FAIL=9, STATIC_FAIL=2, FLAKY=0, NEEDS_REPAIR=11, CONTROL_CERTIFIED=0, GUEST_READY=0.
- Checkpoint: attempted_new=409, AUTO_CERTIFIED=401, next_untested=`mame:/userdata/roms/mame/gundealr.zip`, latest_batch=`priority_batch_5`, status=COMPLETE.
- Estado de la fila indicada como NEXT_GAME en el checkpoint: `AUTO_CERTIFIED`. El runner informó `next_game=null` al completar Batch 6.
- Resultado: no se presenta un contador unificado ni NEXT_GAME como confiable. No se tocó el progreso.

- NEXT_GAME: UNRECONCILED (el checkpoint apunta a `mame:/userdata/roms/mame/gundealr.zip`, cuya fila CSV ya está `AUTO_CERTIFIED`; el runner terminó con `next_game=null`).

## Sistemas

- Adapters detectados: 48; READY=23; PENDING=25 (captura registrada en `data/detected_systems.csv`).
- GUEST_MODE_STATUS: no activo; GUEST_READY continúa en 0 según CSV.
- Arcade Manager: herramienta local presente; no certificado como servicio persistente.
- Espacio actual:
  - /dev/sda2        211G   120G   83G  60% /userdata
  - /dev/sdc1        3,6T  1012G  2,5T  30% /media/ROMS
  - /dev/sdb1        916G   783G   88G  90% /media/BATOCERA_ROMS

Para resolver la discrepancia consultar `reports/CERTIFICATION_RECONCILIATION_BLOCKER.md`. El resumen derivado está marcado en fallo de reconciliación.
