# Piloto controlado — MAME actual

Inicio: 2026-11-13T10:08:04-03:00

Core objetivo: libretro mame, /usr/lib/libretro/mame_libretro.so. Core global mame078plus sin cambios.
Metadata libretro mame: display_version Git; MAME standalone consultado en la auditoría: v0.285. Driver del target core se confirma además por el argv real en cada PASS.
Backup config: /media/ROMS/ARCADE_BACKUPS/ARCADE_CORE_PILOT_2026-11-13_093236; saves/NVRAM: baseline verificado anterior.
Ruta: EmulationStation → controller_dispatcher → launcher oficial → RetroArch; no se inyectó input.
El override individual esperado es una sola línea mame["<rom>.zip"].core=mame; se preserva el default libretro/mame078plus.

| Juego | ROM | Core previo → nuevo | CRC/dependencias | P/B/control | Boot | Input | Diff | Override | s | Exit | Restore | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| ffight2b | /userdata/roms/mame/ffight2b.zip | mame078plus → mame libretro current | CRC FULL_CRC_MATCH_MAME_CURRENT; CHD NO; BIOS UNKNOWN_STATIC; missing no | 2P/6B/joy | BOOT_OK | DIRECT_COMPATIBLE; input físico no probado | +mame["ffight2b.zip"].core=mame | KEPT | 26.25 | 0 | VERIFIED | diff +mame["ffight2b.zip"].core=mame; PID 29507; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 7/1/0; temp m |
| altair | /userdata/roms/mame/altair.zip | mame078plus → mame libretro current | CRC FULL_CRC_MATCH_MAME_CURRENT; CHD NO; BIOS UNKNOWN_STATIC; missing no | 1P/2B/joy | BOOT_OK | DIRECT_COMPATIBLE; input físico no probado | +mame["altair.zip"].core=mame | KEPT | 26.23 | 0 | VERIFIED | diff +mame["altair.zip"].core=mame; PID 29768; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 11/1/0; temp má |
| apache3 | /userdata/roms/mame/apache3.zip | mame078plus → mame libretro current | CRC FULL_CRC_MATCH_MAME_CURRENT; CHD NO; BIOS UNKNOWN_STATIC; missing no | 1P/3B/stick | BOOT_OK | MANUAL_VALIDATE | +mame["apache3.zip"].core=mame | KEPT | 26.01 | 0 | VERIFIED | diff +mame["apache3.zip"].core=mame; PID 30018; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 10/1/0; temp m |
| blazlaz | /userdata/roms/mame/blazlaz.zip | mame078plus → mame libretro current | CRC FULL_CRC_MATCH_MAME_CURRENT; CHD NO; BIOS UNKNOWN_STATIC; missing no | 1P/3B/joy | BOOT_OK | DIRECT_COMPATIBLE; input físico no probado | +mame["blazlaz.zip"].core=mame | KEPT | 26.25 | 0 | VERIFIED | diff +mame["blazlaz.zip"].core=mame; PID 30268; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 7/1/0; temp má |
| cubeqst | /userdata/roms/mame/cubeqst.zip | mame078plus → mame libretro current | CRC FULL_CRC_MATCH_MAME_CURRENT; CHD NO; BIOS UNKNOWN_STATIC; missing no | 1P/3B/trackball | BOOT_OK | SPECIAL_CONTROL_TRACKBALL | +mame["cubeqst.zip"].core=mame | KEPT | 26.24 | 0 | VERIFIED | diff +mame["cubeqst.zip"].core=mame; PID 30529; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 10/1/0; temp m |

## Estado

- Progreso: 5/5; siguiente: ninguno
- Fase: COMPLETE
- Restore: VERIFIED
- Overrides mantenidos: ffight2b, altair, apache3, blazlaz, cubeqst
- Overrides revertidos: ninguno
- Regresión global: NO GLOBAL REGRESSION; solo overrides de juegos piloto pasados; global mame078plus.
- Error: ninguno
- Mapping técnico usado: P1=USB5, P2=USB6, P3=USB8, P4=USB7; dispositivos y respuesta física no se vuelven a certificar por este smoke test.
- No se encontraron CFG/remaps por juego para los cinco; solo existe configs/mame/cfg/default.cfg.
- Intento inicial ffight2b: game_health registró libretro/mame, PID 28272, 86,72 s, exit 0 e INICIO_SOSTENIDO. No se contabilizó porque el matcher buscaba el ZIP en argv; Batocera usa /var/run/cmdfiles/ffight2b.cmd. El proceso se cerró con SIGTERM y el restore del baseline pasó. Se repite con matcher corregido.

No se certificó P1-P4 físicamente. cubeqst conserva clasificación de trackball.

## Incidencias del harness y recuperación

- El primer intento de `ffight2b` se observó activo con libretro `mame` durante 86,72 s y terminó con código 0, pero no se contabilizó porque el monitor buscaba la ruta ZIP literal en argv, mientras Batocera invoca `/var/run/cmdfiles/ffight2b.cmd`.
- En el primer reintento, el matcher del `.cmd` ya encontraba RetroArch, pero una comprobación redundante todavía exigía la ruta ZIP literal en argv. Se pausó antes de completar la ventana y se cerró el proceso exacto con SIGTERM. No se clasificó como fallo del juego.
- Se retiró el override temporal de `ffight2b`, se eliminó únicamente el `default.cfg` creado por esa prueba y sus directorios vacíos, y se restauraron los metadatos de la configuración. Hash de `batocera.conf` volvió a coincidir con su copia previa; los árboles de datos protegidos quedaron idénticos al snapshot.
- Tras corregir la comprobación del harness, `ffight2b` pasó la prueba formal. Los cinco resultados finales tienen `BOOT_OK`, exit 0, cierre limpio, retorno a ES y restore verificado.
- Se vieron trazas `ProcessLookupError` de `hotkeygen` al señalizar un PID ya terminado. No coincidieron con error del core; RetroArch permaneció durante la ventana, descargó core/juego y salió con código 0.
- La comprobación final confirmó que no hay deriva en saves/NVRAM u otros árboles protegidos. `batocera.conf` coincide byte por byte con el original más exactamente cinco overrides individuales de los cinco pilotos. No hubo cambio global ni overrides fuera de la muestra.

## BATCH 2 — 15 GAMES

# Piloto controlado — MAME actual — batch 2

Inicio: 2026-11-13T11:16:16-03:00

Core objetivo: libretro mame, /usr/lib/libretro/mame_libretro.so. Core global mame078plus sin cambios.
El log runtime de libretro identifica MAME 0.285 (unknown); el .info muestra display_version Git. La versión standalone instalada no se usó.
Backup config: /media/ROMS/ARCADE_BACKUPS/ARCADE_CORE_PILOT_BATCH2_2026-11-13_104010; saves/NVRAM: baseline verificado anterior.
Ruta: EmulationStation → controller_dispatcher → launcher oficial → RetroArch; no se inyectó input.
La tanda usa exactamente los 15 candidatos restantes de ARCADE_PILOT_RETEST.md. Cinco se omiten porque el reporte prescribe FBNeo; diez se prueban con MAME actual.
Cada override individual es una sola línea mame["<rom>.zip"].core=mame; se preservan los cinco overrides de BATCH 1 y el default global mame078plus.

| Juego | ROM | Core previo → nuevo | CRC/dependencias | P/B/control | Boot | Input | Diff | Override | s | Exit | Restore | Evidencia |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |
| gprider | gprider.zip | mame078plus → fbneo | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD NO; BIOS UNKNOWN_STATIC; missing no | 2P/2B/paddle,pedal | SKIP_WRONG_STRATEGY | SPECIAL_CONTROL | sin cambios | NONE | 0 | — | VERIFIED_NO_WRITE | ARCADE_PILOT_RETEST.md asigna este candidato a FBNeo/u otra ruta; no se aplicó override ni se lanzó. |
| sfiii2n | sfiii2n.zip | mame078plus → fbneo | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD NO; BIOS UNKNOWN_STATIC; missing no | 2P/6B/joy | SKIP_WRONG_STRATEGY | DIRECT_COMPATIBLE; input físico no probado | sin cambios | NONE | 0 | — | VERIFIED_NO_WRITE | ARCADE_PILOT_RETEST.md asigna este candidato a FBNeo/u otra ruta; no se aplicó override ni se lanzó. |
| sfiii3n | sfiii3n.zip | mame078plus → fbneo | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD NO; BIOS UNKNOWN_STATIC; missing no | 2P/6B/joy | SKIP_WRONG_STRATEGY | DIRECT_COMPATIBLE; input físico no probado | sin cambios | NONE | 0 | — | VERIFIED_NO_WRITE | ARCADE_PILOT_RETEST.md asigna este candidato a FBNeo/u otra ruta; no se aplicó override ni se lanzó. |
| sfiiin | sfiiin.zip | mame078plus → fbneo | CRC NO_CURRENT_MAME_CRC_MATCH; CHD NO; BIOS UNKNOWN_STATIC; missing no | 2P/6B/joy | SKIP_WRONG_STRATEGY | DIRECT_COMPATIBLE; input físico no probado | sin cambios | NONE | 0 | — | VERIFIED_NO_WRITE | ARCADE_PILOT_RETEST.md asigna este candidato a FBNeo/u otra ruta; no se aplicó override ni se lanzó. |
| neotris | neotris.zip | mame078plus → FBNeo path/content unresolved | CRC NO_CURRENT_DRIVER; CHD UNKNOWN; BIOS UNKNOWN_STATIC; missing no | P/B/ | SKIP_WRONG_STRATEGY | MANUAL_VALIDATE | sin cambios | NONE | 0 | — | VERIFIED_NO_WRITE | ARCADE_PILOT_RETEST.md asigna este candidato a FBNeo/u otra ruta; no se aplicó override ni se lanzó. |
| mvp | /userdata/roms/mame/mvp.zip | mame078plus → mame libretro current | CRC SET_MATCH_CRC_SIZE_METADATA; CHD NO; BIOS PRESENT_PARTIAL; missing 317-0143.key; 315-5298.b9 | 0P/B/ | FAIL_MISSING_CONTENT | MANUAL_VALIDATE | +mame["mvp.zip"].core=mame (revertido) | REVERTED | 1.5 | 1 | VERIFIED | MAME 0.285 abortó con Fatal error: Required files are missing; ambos archivos figuran NOT FOUND. Override revertido; restore VERIFIED. |
| sia2650 | /userdata/roms/mame/sia2650.zip | mame078plus → mame libretro current | CRC SET_MATCH_CRC_SIZE_METADATA; CHD NO; BIOS PRESENT_PARTIAL; missing no | 1P/1B/joy4way | BOOT_OK | DIRECT_COMPATIBLE; input físico no probado | +mame["sia2650.zip"].core=mame | KEPT | 26.25 | 0 | VERIFIED | diff +mame["sia2650.zip"].core=mame; PID 13130; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 7/1/0; temp má |
| redearth | /userdata/roms/mame/redearth.zip | mame078plus → mame libretro current | CRC FULL_CRC_MATCH_MAME_CURRENT; CHD YES; BIOS UNKNOWN_STATIC; missing cap-wzd-5.chd | 2P/6B/joy | FAIL_CHD | DIRECT_COMPATIBLE; input físico no probado | +mame["redearth.zip"].core=mame | REVERTED | 4.76 | 1 | VERIFIED | MAME 0.285 abortó con cap-wzd-5.chd NOT FOUND y Required files are missing. Override revertido; restore VERIFIED. |
| jojo | /userdata/roms/mame/jojo.zip | mame078plus → mame libretro current | CRC NO_CURRENT_MAME_CRC_MATCH; CHD YES; BIOS UNKNOWN_STATIC; missing cap-jjk-3.chd; jojo_euro.29f400.u2 | 2P/6B/joy | FAIL_CHD | DIRECT_COMPATIBLE; input físico no probado | +mame["jojo.zip"].core=mame | REVERTED | 4.75 | 1 | VERIFIED | MAME 0.285 abortó con cap-jjk-3.chd NOT FOUND y jojo_euro.29f400.u2 NOT FOUND. Override revertido; restore VERIFIED. |
| jojoba | /userdata/roms/mame/jojoba.zip | mame078plus → mame libretro current | CRC NO_CURRENT_MAME_CRC_MATCH; CHD NO; BIOS UNKNOWN_STATIC; missing jojoba-simm5.0 a jojoba-simm5.7 | 2P/6B/joy | FAIL_ROMSET | DIRECT_COMPATIBLE; input físico no probado | +mame["jojoba.zip"].core=mame | REVERTED | 4.77 | 1 | VERIFIED | MAME 0.285 reportó los ocho miembros SIMM5 NOT FOUND y Required files are missing; el inventario no halló CRC actual coincidente. Override revertido; restore VERIFIED. |
| evosocc | /userdata/roms/mame/evosocc.zip | mame078plus → mame libretro current | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD NO; BIOS UNKNOWN_STATIC; missing no | 4P/4B/joy | BOOT_OK | DIRECT_COMPATIBLE; input físico no probado | +mame["evosocc.zip"].core=mame | KEPT | 26.58 | 0 | VERIFIED | diff +mame["evosocc.zip"].core=mame; PID 15581; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 11/1/0; temp m |
| hoops95 | /userdata/roms/mame/hoops95.zip | mame078plus → mame libretro current | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD NO; BIOS UNKNOWN_STATIC; missing no | 4P/4B/joy | BOOT_OK | DIRECT_COMPATIBLE; input físico no probado | +mame["hoops95.zip"].core=mame | KEPT | 26.49 | 0 | VERIFIED | diff +mame["hoops95.zip"].core=mame; PID 15833; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 10/1/0; temp m |
| nbapbp | /userdata/roms/mame/nbapbp.zip | mame078plus → mame libretro current | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD NO; BIOS UNKNOWN_STATIC; missing 778b01.27p; security_eeprom_uab | 4P/3B/joy | FAIL_MISSING_CONTENT | DIRECT_COMPATIBLE; input físico no probado | +mame["nbapbp.zip"].core=mame | REVERTED | 5.55 | 1 | VERIFIED | MAME 0.285 reportó 778b01.27p y security_eeprom_uab NOT FOUND; Required files are missing. Override revertido; restore VERIFIED. |
| funcube4 | /userdata/roms/mame/funcube4.zip | mame078plus → mame libretro current | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD NO; BIOS UNKNOWN_STATIC; missing no | 3P/2B/gambling,joy,lightgun | BOOT_OK | SPECIAL_CONTROL | +mame["funcube4.zip"].core=mame | KEPT | 26.37 | 0 | VERIFIED | diff +mame["funcube4.zip"].core=mame; PID 16331; core /usr/lib/libretro/mame_libretro.so; DB core=mame; emulator=libretro; exit=0; status=INICIO_SOSTENIDO; mapping configurado P1=USB5, P2=USB6, P3=USB8, P4=USB7; log paths changed=5; restore delta 10/1/0; temp  |
| hyperath | /userdata/roms/mame/hyperath.zip | mame078plus → mame libretro current | CRC PARTIAL_CRC_MATCH_UNRESOLVED; CHD YES; BIOS UNKNOWN_STATIC; missing gv021-j1.chd | 4P/3B/joy | FAIL_CHD | DIRECT_COMPATIBLE; input físico no probado | +mame["hyperath.zip"].core=mame | REVERTED | 4.75 | 1 | VERIFIED | MAME 0.285 abortó con gv021-j1.chd NOT FOUND (parent konamigv) y Required files are missing. Override revertido; restore VERIFIED. |

## Estado

- Progreso: 15/15; siguiente: ninguno
- Juegos ejecutados: 10/10 MAME; omisiones: 5/5 estrategia ajena.
- PASS: 4/15 total candidatos; restores verificados: 10/10 ejecutados.
- Fase: COMPLETE
- Restore: 15/15: 10 ejecutados/restaurados y 5 omitidos sin escrituras, snapshot idéntico
- Overrides mantenidos: sia2650, evosocc, hoops95, funcube4
- Overrides revertidos: mvp, redearth, jojo, jojoba, nbapbp, hyperath
- Regresión global: NO GLOBAL REGRESSION; BATCH 1 intact; only passing BATCH 2 game overrides added.
- Error: 
- Mapping técnico usado: P1=USB5, P2=USB6, P3=USB8, P4=USB7; dispositivos y respuesta física no se vuelven a certificar por este smoke test.
- P1-P4 y dispatcher permanecen sin cambios; el smoke test no certifica respuesta física. Juegos 3P/4P compatibles quedan con prioridad alta de validación manual.
- Los logs runtime confirman CHD ausente en hyperath, jojo y redearth; jojo también carece de jojo_euro.29f400.u2.

No se certificó input físico.

## Cierre de la segunda tanda

- BOOT_OK: 4/10 lanzados; 4/15 candidatos totales al incluir cinco SKIP_WRONG_STRATEGY.
- Fallos por causa: {'CHD': 3, 'MISSING_CONTENT': 2, 'ROMSET': 1, 'DRIVER': 0, 'CRASH_CONFIRMED': 0, 'OTHER': 0}. No hubo FAIL_DRIVER ni crash del core separado de contenido requerido ausente.
- Compatibles directos con metadata y boot PASS: sia2650, evosocc y hoops95. funcube4 pasó boot y requiere control especial (gambling/lightgun).
- 4P con boot PASS: evosocc y hoops95; input físico pendiente. nbapbp y hyperath son 4P, pero faltan archivos/CHD.
- Temperatura final registrada: 54 °C. Máxima conservada entre lecturas reportadas del lote: 54 °C; las comprobaciones térmicas de cada juego no detectaron umbral crítico.
- NVIDIA: módulo cargado, driver 580.126.09; nvidia-smi no está disponible. Xorg activo y sin errores críticos nuevos observados en las comprobaciones por juego.
- ES quedó idle; hashes de controller_dispatcher y perfil técnico coinciden; snapshot protegido sin deriva. batocera.conf coincide con el backup BATCH 2 más sólo los overrides de juegos PASS.
- Recomendación: continuar sólo por lotes y con filtro CRC/dependencias; no se ejecutó otra tanda.
