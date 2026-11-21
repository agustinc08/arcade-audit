# Estado actual del arcade

- UPDATED_AT: 2026-11-21T02:38:32+00:00
- GITHUB_HEAD observado antes de publicar: `9594bd8766741227edea748e166d338af0eccaca`
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

- Fuente de snapshot: `controller_technical.json + live udev/sysfs`
- P1: USB5 / /dev/input/event18 / /dev/input/js1; ID_PATH `pci-0000:00:14.0-usb-0:5:1.0`; by-path `/dev/input/by-path/pci-0000:00:14.0-usb-0:5:1.0-event-joystick`; VID:PID `0079:0006`; name `DragonRise Inc.   Generic   USB  Joystick` (event/js = valores runtime actuales).
- P2: USB6 / /dev/input/event19 / /dev/input/js2; ID_PATH `pci-0000:00:14.0-usb-0:6:1.0`; by-path `/dev/input/by-path/pci-0000:00:14.0-usb-0:6:1.0-event-joystick`; VID:PID `0079:0006`; name `DragonRise Inc.   Generic   USB  Joystick` (event/js = valores runtime actuales).
- P3: USB8 / /dev/input/event21 / /dev/input/js4; ID_PATH `pci-0000:00:14.0-usb-0:8:1.0`; by-path `/dev/input/by-path/pci-0000:00:14.0-usb-0:8:1.0-event-joystick`; VID:PID `0079:0006`; name `DragonRise Inc.   Generic   USB  Joystick` (event/js = valores runtime actuales).
- P4: USB7 / /dev/input/event20 / /dev/input/js3; ID_PATH `pci-0000:00:14.0-usb-0:7:1.0`; by-path `/dev/input/by-path/pci-0000:00:14.0-usb-0:7:1.0-event-joystick`; VID:PID `0079:0006`; name `DragonRise Inc.   Generic   USB  Joystick` (event/js = valores runtime actuales).

- Identidad persistente: jugador lógico + puerto USB físico + `ID_PATH`/`by-path` + VID:PID + nombre. `eventXX` y `jsX` son valores runtime actuales y pueden renumerarse.

- GAMEPADS_CONNECTED: 1
  - USB Gamepad (USB, audio endpoint: no/unknown)

## Certificación

- FULL_CERTIFICATION_PHASE: RUNNING
- TOTAL_INVENTORY: 8426
- INSTALLED: 8400
- HISTORICAL_BOOT_OK: 1200
- AUTO_CERTIFIED: 5512
- GAME_FAIL: 172
- STATIC_FAIL: 194
- FLAKY: 0
- NEEDS_REPAIR: 366
- CONTROL_CERTIFIED: 0
- GUEST_READY: 0
- NEXT_GAME: `mrboom:/userdata/roms/mrboom/MrBoom.libretro`
- UNIQUE_GAMES_PROCESSED: 6644
- RESULT_RECORDS: 6648
- LAUNCH_TRANSACTIONS: 5688
- RETRY_TRANSACTIONS: 4
- ADAPTERS_READY: 23
- ADAPTERS_PENDING: 25
- REPAIR_QUEUE_PENDING: 22

## Espacio

- FILESYSTEM_STATUS: lectura de capacidad; no es una prueba SMART.
    /dev/sda2        211G   122G   80G  61% /userdata
    /dev/sdc1        3,6T  1012G  2,5T  30% /media/ROMS
    /dev/sdb1        916G   783G   88G  90% /media/BATOCERA_ROMS

## Guest Mode y herramientas

- GUEST_MODE_STATUS: PENDING; no se promueven juegos automáticamente.
- ARCADE_MANAGER_STATUS: script local disponible; servicio/panel persistente no certificado.
- OPEN_ROOT_ISSUES: 9
- MANUAL_TESTS_PENDING: 14 (detalle en `data/manual_physical_test_queue.csv`).
- LAST_MAJOR_CHANGES: Resolved HDMI selection policy at runtime, verified no-game transaction restore, found/version-checked FBNeo DAT, audited publisher changeset; no game launched.

Este documento se deriva de checkpoints, tabla de certificación y consultas locales. Los datos variables deben regenerarse; los reportes históricos no prevalecen sobre estas fuentes.
