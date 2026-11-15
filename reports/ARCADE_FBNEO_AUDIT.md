# Auditoría FBNeo — estado de DAT

`FBNEO_DAT: VERIFIED` para la versión de core instalada.

- Core: `/usr/lib/libretro/fbneo_libretro.so` (SHA-256 `8c23c4120a97a8d8f1abc12122d3daebef0606e3ee170d66ad9aa90bcb43f69e`).
- Info: `/usr/share/libretro/info/fbneo_libretro.info`, `display_version = v1.0.0.03`, database `FBNeo - Arcade Games`.
- DAT: `/usr/share/batocera/datainit/bios/fbneo/FinalBurn Neo (ClrMame Pro XML, Arcade only).dat`, copiado por la instalación a `/userdata/bios/fbneo/FinalBurn Neo (ClrMame Pro XML, Arcade only).dat`.
- Versión DAT: `1.0.0.03`; SHA-256 en ambos paths: `fde84d217c5df17a03ba234c421da084afdfe6cd778cc15b759d1e0c941a5f7d`.
- Fecha del archivo runtime: 2026-01-11; no fue necesario descargarlo. Fuente instalada: Batocera `datainit`.
- Comprobación read-only: CRC/tamaño de todos los miembros del DAT de `sfiii3` y `captcomm` coinciden con sus ZIPs, ambos históricos `BOOT_OK_FBNEO`.

No se lanzó ningún juego FBNeo en esta fase. `gprider`, `sfiii2n`, `sfiii3n`, `sfiiin` y `neotris` siguen reservados y sin nueva prueba. El DAT verificado habilita preflight estático, no certifica esos cinco candidatos.


Estado de bloqueo reconciliado: `FBNEO_DAT=VERIFIED`; `FBN-001=CLOSED`. Esto valida la referencia para preflight, no los cinco candidatos pendientes ni una compatibilidad de ROMset adicional.
