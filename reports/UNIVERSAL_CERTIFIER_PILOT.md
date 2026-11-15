# Universal certifier — piloto real

- Fecha: 2026-11-15T08:38:49-03:00
- Estado: `PILOT_PASS_WITH_ADAPTER_FIX`
- Juegos únicos del piloto: 10
- AUTO_PASS finales: 10/10
- Intentos: 11 (8 PASS iniciales, un fallo de identidad del adapter PC Engine, y dos reanudaciones; PC Engine pasó después de corregir core esperado)
- Fallos de juego confirmados: 0
- Wrong game dispatch: 0
- Audio route changed: 0
- Restores verificados: 11/11 intentos, incluidos los 10 PASS finales
- HDMI: `alsa_output.pci-0000_01_00.1.hdmi-stereo` antes/durante/después de cada PASS
- P1–P4: sin cambios; botonería se seleccionó mediante marker de auditoría, sin inyección de inputs
- `game_health`: salida 0 y retorno a ES en los PASS; `ProcessLookupError` de hotkeygen posterior a salida 0 fue `CLEANUP_RACE`
- `batocera.conf`: SHA sin cambios; core global `mame078plus`; 18 overrides MAME sin cambios

## Casos PASS

| Sistema | Juego | Adapter/core | Duración estable | Visual | Restore |
|---|---|---|---:|---|---|
| `fbneo` | Captain Commando (`captcomm.zip`) | `FBNEO` / `/usr/lib/libretro/fbneo_libretro.so` | 20.14s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `gb` | Bomb Jack (U) (`Bomb Jack (U).gb`) | `RETROARCH_GENERIC` / `/usr/lib/libretro/gambatte_libretro.so` | 16.181s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `gba` | Final Fantasy V Advance (`Final Fantasy V Advance (Europe) (En,Fr,De,Es,It).gba`) | `RETROARCH_GENERIC` / `/usr/lib/libretro/mgba_libretro.so` | 16.192s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `mame` | 1941: Counter Attack (`1941.zip`) | `MAME078PLUS` / `/usr/lib/libretro/mame078plus_libretro.so` | 20.165s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `mame` | Libero Grande (`lbgrande.zip`) | `MAME_CURRENT` / `/usr/lib/libretro/mame_libretro.so` | 20.172s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `mastersystem` | Batman Returns (`Batman Returns (EU).sms`) | `RETROARCH_GENERIC` / `/usr/lib/libretro/genesisplusgx_libretro.so` | 16.207s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `megadrive` | Ultimate Mortal Kombat 3 (`Ultimate Mortal Kombat 3 (E) [!].bin`) | `RETROARCH_GENERIC` / `/usr/lib/libretro/genesisplusgx_libretro.so` | 16.244s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `nes` | Super Mario Bros. (`Super Mario Bros. (ESP-Her-Saki).nes`) | `RETROARCH_GENERIC` / `/usr/lib/libretro/fceumm_libretro.so` | 16.204s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `pcengine` | Bull Fight : Ring no Hasha (`Bull Fight - Ring no Haja (Japan).pce`) | `RETROARCH_GENERIC` / `/usr/lib/libretro/pce_libretro.so` | 16.197s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |
| `snes` | NBA Jam (`NBA Jam (USA).zip`) | `RETROARCH_GENERIC` / `/usr/lib/libretro/snes9x_libretro.so` | 16.226s | `VISUAL_ACTIVITY` | `RESTORE_VERIFIED` |

## Discrepancia y corrección

El runtime de `pcengine` usa el core `pce`, declarado como predeterminado en `es_systems_el_gordo.cfg` y confirmado en `es_launch_stdout.log`/`game_health`. El primer intento esperaba incorrectamente `pce_fast` por priorizar `configgen-defaults.yml`; el contenido correcto llegó a RetroArch y el restore pasó. Se corrigió la precedencia para usar el core predeterminado del sistema ES después de overrides explícitos. PC Engine se reprobó sin repetir los otros PASS y quedó `AUTO_PASS` con `/usr/lib/libretro/pce_libretro.so`.

La segunda vuelta usó únicamente los dos casos que faltaban: PC Engine y Game Boy. Los ocho PASS existentes no se repitieron.

## Límite

Esto certifica arranque, identidad, core, estabilidad breve, salida, estado HDMI y restauración. No certifica botones físicos, audio DS4 tras reconexión o reboot, ni `GUEST_READY`. Standalone adapters siguen pendientes.
