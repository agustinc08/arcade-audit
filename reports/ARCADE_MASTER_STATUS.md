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

El publisher detuvo el primer intento por `LARGE_CHANGESET`; no se bajó ningún umbral. El changeset se revisó ruta por ruta, el test JSON remoto previamente autorizado fue recuperado en el source activo y el inventario final no debe contener borrados. Se publicará sólo si los scans vuelven a pasar y el one-time manifest coincide exactamente con el HEAD y los hashes del changeset.

## Persistencia y salud

Audio: `AUDIO_POLICY_INSTALLED`, reconexión física/reboot pendientes. Restore: positive control PASS. FBNeo DAT: VERIFIED. Global MAME y 18 overrides sin cambios. P1–P4 sin cambios. No iniciar un batch masivo hasta completar adapters y un piloto de infraestructura; después mantener HDMI monitorizado en cada test.
