# Estado actual del arcade

- UPDATED_AT: 2026-11-17T14:47:32+00:00
- GITHUB_HEAD observado antes de publicar: `c3fd9e54994198c6338b07b6e4bf8367a8b78207`
- BATOCERA_VERSION: 43.1

## Sistema y hardware

- CPU: 12th Gen Intel(R) Core(TM) i5-12400F
- GPU: NVIDIA Corporation GP106 [GeForce GTX 1060 3GB] (rev a1)
- RAM: 15Gi
- DISPLAY: modo configurado `max-1920x1080`; EDID/modo vivo no disponible en la sesión de consulta.
- NETWORK: Ethernet y adaptadores Wi-Fi/Bluetooth detectados históricamente; no se publican SSID, dirección IP ni MAC.

## Configuración arcade

- GLOBAL_MAME_CORE: `mame078plus`
- MAME_OVERRIDES_COUNT: 18
- AUDIO_DEFAULT: `alsa_output.pci-0000_01_00.1.hdmi-stereo`
- HDMI_DEFAULT_STATUS: PASS
- AUDIO_POLICY_STATUS: instalada; reconexión física DS4 y persistencia post-reboot pendientes.

### P1–P4

- Fuente de snapshot: `controllers_live.json`
- P1: USB5 / event17 / js0
- P2: USB6 / event18 / js1
- P3: USB8 / event20 / js3
- P4: USB7 / event19 / js2

- GAMEPADS_CONNECTED: 1
  - USB Gamepad (USB, audio endpoint: no/unknown)

## Certificación

- FULL_CERTIFICATION_PHASE: RUNNING
- TOTAL_INVENTORY: 8426
- INSTALLED: 8400
- HISTORICAL_BOOT_OK: 1200
- AUTO_CERTIFIED: 1024
- GAME_FAIL: 142
- STATIC_FAIL: 44
- FLAKY: 0
- NEEDS_REPAIR: 186
- CONTROL_CERTIFIED: 0
- GUEST_READY: 0
- NEXT_GAME: `fbneo:/userdata/roms/fbneo/gijoe.zip`
- UNIQUE_GAMES_PROCESSED: 1210
- RESULT_RECORDS: 1212
- LAUNCH_TRANSACTIONS: 1168
- RETRY_TRANSACTIONS: 2
- ADAPTERS_READY: 23
- ADAPTERS_PENDING: 25
- REPAIR_QUEUE_PENDING: 22

## Espacio

- FILESYSTEM_STATUS: lectura de capacidad; no es una prueba SMART.
    /dev/sda2        211G   121G   82G  60% /userdata
    /dev/sdc1        3,6T  1012G  2,5T  30% /media/ROMS
    /dev/sdb1        916G   783G   88G  90% /media/BATOCERA_ROMS

## Guest Mode y herramientas

- GUEST_MODE_STATUS: PENDING; no se promueven juegos automáticamente.
- ARCADE_MANAGER_STATUS: script local disponible; servicio/panel persistente no certificado.
- OPEN_ROOT_ISSUES: 9
- MANUAL_TESTS_PENDING: 14 (detalle en `data/manual_physical_test_queue.csv`).
- LAST_MAJOR_CHANGES: Resolved HDMI selection policy at runtime, verified no-game transaction restore, found/version-checked FBNeo DAT, audited publisher changeset; no game launched.

Este documento se deriva de checkpoints, tabla de certificación y consultas locales. Los datos variables deben regenerarse; los reportes históricos no prevalecen sobre estas fuentes.
