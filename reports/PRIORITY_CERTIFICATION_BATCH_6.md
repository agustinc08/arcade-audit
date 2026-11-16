# Certificación prioritaria — Batch 6

- Fuente de comparación: export/checkpoint previo y tabla/checkpoint activos.
- Se reanudó en `mame:/userdata/roms/mame/gundealr.zip`; no se repitió el piloto ni se relanzaron juegos previamente PASS.
- Runner finalizó `batch_status=COMPLETE`, `selected=100`, `next_game=null`, `engine_ok=true`.

- CSV rows newly changed: 100 (AUTO_CERTIFIED=98, GAME_FAIL=2).
- Corrección tras comparar contra el checkpoint previo a Batch 6: los 100 registros nuevos son AUTO_PASS=98 y GAME_FAIL=2. Los 2 registros STATIC_FAIL ya existían antes de Batch 6 (`hoops95`, `evosocc`); no forman parte del delta.
- Restauraciones verificadas para lanzamientos: 100/100.
- Nuevos ENGINE_FAIL: 0; nuevos wrong dispatch/audio/restore: 0/0/0.

## Resultados GAME_FAIL

- `heberpop.zip`: RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED; visual=[('BLACK_SCREEN_SUSPECT', 1.0), ('BLACK_SCREEN_SUSPECT', 0.9951)]; estable=20.163 s; exit=0; audio=HDMI_PASS; restore=RESTORE_VERIFIED. Requiere revisión visual, no demuestra fallo de core/ROM por sí solo.
- `hvymetal.zip`: RUNTIME_HEALTH_OR_VISUAL_CHECK_FAILED; visual=[('BLACK_SCREEN_SUSPECT', 0.99803), ('BLACK_SCREEN_SUSPECT', 0.99803)]; estable=20.156 s; exit=0; audio=HDMI_PASS; restore=RESTORE_VERIFIED. Requiere revisión visual, no demuestra fallo de core/ROM por sí solo.

## Safety y limitación del checkpoint

- ES API idle; `NO GAME RUNNING`; marker ausente; RetroArch/MAME/dispatcher/selector/emulatorlauncher sin procesos residuales.
- HDMI default: `alsa_output.pci-0000_01_00.1.hdmi-stereo`; `batocera.conf` SHA-256 `098c88444322bacaac5f2f2383e5bf6e5fa42623353fe8c49d307fffc47b52d2`.
- `batocera.conf` overrides: 18; core MAME efectivo en ES XML: `mame078plus`.
- El resultado del runner no actualizó los agregados superiores del checkpoint ni el cursor: `attempted_new=409`, `auto_certified=401`, `latest_batch=priority_batch_5`, `next_untested=mame:/userdata/roms/mame/gundealr.zip`. Esta discrepancia se resolvió el 2026-11-16 actualizando únicamente metadatos derivados; véase `CERTIFICATION_RECONCILIATION_RESULT.md`.
- La tabla activa sí contiene `AUTO_CERTIFIED=499`; la fila del propio cursor tiene estado `AUTO_CERTIFIED`. El runner informó `next_game=null` al cerrar.
- El CSV y los resultados individuales se conservaron sin cambios. El cursor se reconstruyó usando la cola real del certifier y quedó en `mame:/userdata/roms/mame/machridr.zip`; el Batch 7 sólo puede comenzar tras pasar el self-check de cola y estado global.
