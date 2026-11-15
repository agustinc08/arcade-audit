# ARCADE MAME BATCH 5 — RESULTADOS

- Fecha: 2026-11-15 (America/Argentina/Buenos_Aires).
- Estado: TERMINADO; se ejecutaron únicamente los dos candidatos que pasaron el preflight actual. No se inició BATCH 6 ni pruebas físicas.
- MAME actual: 0.285 (`/usr/bin/mame/mame`), core libretro `/usr/lib/libretro/mame_libretro.so`.

## Estado inicial y pool

- Core global del sistema `mame`: `mame078plus`; permaneció sin cambios.
- Overrides funcionales al inicio: 16. Al final: 18 (los 16 previos más `kov2p` y `martmast`).
- Dispatcher SHA-256 antes/después: `a60be89fb45ea27ec4f7c3f546e088c7ff3da140bccfe1c6a37e5b14ec581c45`.
- Pool matrix no probado con MAME actual: 161 filas; 145 con juego/driver MAME actual soportado y rechazo del core default; filtro normal directo (joystick, 1–4 jugadores, <=6 botones, excluidas reservas/no-juegos): 45 candidatos para preflight.
- Se verificaron 45; `-verifyroms` PASS: 2; SKIP_PREFLIGHT: 43. Se eligieron y lanzaron sólo `kov2p`, `martmast`.
- La clasificación estática CRC era `PARTIAL_CRC_MATCH_UNRESOLVED` para ambos; prevaleció el preflight MAME 0.285 real: driver runnable, `romof=pgm`, dependencias PGM resueltas y `-verifyroms` informó `romset ... [pgm] is good`. Driver status `imperfect`, runnable `yes`. No CHD requerido.
- Los 43 SKIP son candidatos no seguros con el contenido/dependencias actuales; sus categorías y miembros faltantes están listados abajo. No se repararon ni modificaron ROMs.

## Resultados reales

| Juego | Nombre | Jugadores / botones | Tipo | Core y ventana | game_health | Restore | Override |
|---|---|---:|---|---|---|---|---|
| `kov2p` | Knights of Valour 2 Plus - Nine Dragons | 4 / 4 | joystick digital; beat ’em up | MAME actual, 20.540 s | id 8170, exit 0, señal None | VERIFIED | KEEP individual |
| `martmast` | Martial Masters | 4 / 4 | joystick digital; fighting | MAME actual, 20.568 s | id 8171, exit 0, señal None | VERIFIED | KEEP individual |

- `BOOT_PASS`: 2/2; `BOOT_FAIL`: 0; PASS rate: 100.0%.
- En ambos, ROM solicitada = `/runningGame` = argumento `-rom` del dispatcher = nombre cmdfile = contenido RetroArch; marker consumido y eventos dispatcher, emulatorlauncher, cmdfile, core y game_health presentes. RetroArch cargó exactamente `/usr/lib/libretro/mame_libretro.so`, permaneció estable >=20 s, se cerró mediante SIGTERM al PID exacto y `game_health` reportó `exit_code=0`, sin señal.
- `ProcessLookupError` de hotkeygen aparece en `game_health.relevant_error` después del cierre. Se trata de `CLEANUP_RACE`; el juego tuvo exit 0 y duración >20 s. No es fallo MAME.
- Fallos reales de juego: ninguno. Wrong-game dispatch: ninguno.
- `kov2p` es beat ’em up cooperativo; metadata reporta hasta 4 jugadores. `martmast` es fighting, hasta 4 jugadores. Ambos reportan 4 botones y joystick digital. La metadata no certifica simultaneidad ni mapeo dentro del juego.
- `FIGHTING PASS`: 1 (`martmast`). `BEAT’EM UP PASS`: 1 (`kov2p`). `MULTIPLAYER PASS`: 2 con metadata de 4 jugadores; `MULTIPLAYER_PHYSICAL_TEST=REQUIRED`. `DIRECT_COMPATIBLE PASS`: 2. Controles especiales: 0. No se inyectó input ni se realizaron pruebas físicas.

## Reconciliación del guard del runner

- Después de `martmast`, el runner se detuvo por `safety_gate=FAIL`. La causa fue un error de contabilidad del runner: esperaba la lista base + `martmast`, omitiendo el override `kov2p` que debía permanecer activo por su PASS previo.
- Se mantuvo el alto de seguridad y no se lanzó ningún otro título. Una auditoría independiente comprobó que la configuración actual equivale byte por byte a la copia previa a BATCH 5 más exactamente `mame["kov2p.zip"].core=mame` y `mame["martmast.zip"].core=mame`; el conjunto activo son exactamente los 16 overrides iniciales + esos dos. Se corrigió el guard del script.
- Se verificó cada restore, estado persistente contra baseline (sin drift fuera de `batocera.conf` autorizado), ROMs intactas, marker ausente, ES/API idle, ningún proceso residual, P1-P4 intactos y dispatcher intacto. La reconciliación independiente da safety PASS para `martmast`; el indicador crudo original del runner se conserva en checkpoint como evidencia. No se repitieron juegos.

## PREFLIGHT omitidos

| Shortname | Categoría MAME 0.285 | Miembros/dependencias indicados por MAME |
|---|---|---|
| `kdynastg` | NO_GOOD_DUMP_REQUIRED, MISSING_ROM_MEMBER | kdynastg_pic |
| `ppcar` | NO_GOOD_DUMP_REQUIRED, MISSING_ROM_MEMBER | qs1000.bin |
| `theglad` | NO_GOOD_DUMP_REQUIRED, MISSING_ROM_MEMBER | theglad_igs027a_execute_only_area |
| `kov2` | MISSING_PARENT | pgm_a1201.u4, pgm_a1204.u10, v102_u19.u19, v107_u18.u18 |
| `svg` | NO_GOOD_DUMP_REQUIRED, MISSING_ROM_MEMBER | svg_igs027a_execute_only_area |
| `nagano98` | MISSING_PARENT | nagano98 |
| `ddux` | MISSING_ROM_MEMBER | 315-5298.b9 |
| `dynwar` | MISSING_ROM_MEMBER | lwio.11e, tk24b1.1a |
| `mk4` | ROMSET_BAD, MISSING_ROM_MEMBER | 461_mortal_k_4_25_u76.u76, c32boot.bin, mk4_l2.u2 |
| `sfzch` | MISSING_ROM_MEMBER | sfz63b.1a |
| `aerofgts` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 1-8_prog0_usa_aa9e.ic5, 1-8_prog1_usa_0a1e.ic6, 1-8_prog3_usa_e1d8.ic8, 1-8_prog4_usa_9127.ic9, 78081g503.ic655 |
| `rdft` | MISSING_ROM_MEMBER | flash0_blank_region80.u1053, raiden-fi_prg0_121196.u0211, raiden-fi_prg1_121196.u0212, raiden-fi_prg2_121196.u0210, raiden-fi_prg3_121196.u029 |
| `rdft2` | MISSING_ROM_MEMBER | flash0_blank_region80.u1053, rm81.u0529.bin, rm82.u0330.bin, rm83.u0331.bin |
| `rfjet` | MISSING_ROM_MEMBER | flash0_blank_region80.u1053 |
| `gradius4` | ROMSET_BAD, MISSING_ROM_MEMBER | m48t58y-70pc1_jac, security_eeprom_ja |
| `ar_ldrb` | MISSING_BIOS, MISSING_PARENT | gcp_v311_1-hi.u16, gcp_v311_1-lo.u11, gcp_v311_2-hi.u17, gcp_v311_2-lo.u12, gcp_v400_1-hi.u16 |
| `ar_ninj` | MISSING_BIOS, MISSING_PARENT | gcp_v311_1-hi.u16, gcp_v311_1-lo.u11, gcp_v311_2-hi.u17, gcp_v311_2-lo.u12, gcp_v400_1-hi.u16 |
| `ar_sprg` | MISSING_BIOS, MISSING_PARENT | gcp_v311_1-hi.u16, gcp_v311_1-lo.u11, gcp_v311_2-hi.u17, gcp_v311_2-lo.u12, gcp_v400_1-hi.u16 |
| `bldyror2` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT, ROMSET_BAD | 78081g503.ic655, at28c16_world, et01.ic652, et03, flash1.024 |
| `cbaj` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 78081g503.ic655, gal16v8d-15lp.sop-rom1.uo117, gal16v8d-15lp.sop-rom2b.uo4138, gal16v8d-15lp.sop-rom3.uo3125, gal16v8d-15lp.sop-rom4c.uo4131 |
| `dacholer` | MISSING_ROM_MEMBER | af-1.3n, af-2.1h, dc.13d |
| `darkhleg` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT, ROMSET_BAD | 700a01,gchgchmp.22g, 700b01.22g, 706jaa02, gx706ja.u1, h8a01.bin |
| `dsftkd` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT, ROMSET_BAD | 700a01,gchgchmp.22g, 700b01.22g, 884jaa02, gn884ja.u1, gn884ja.u6 |
| `dstage` | DRIVER_NOT_RUNNABLE | romset "dstage" not found! |
| `fishfren` | MISSING_ROM_MEMBER | jagwave.rom |
| `flamegun` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 78081g503.ic655, m534002c-61.ic353, mg01.ic652, mg06 |
| `freezeat` | MISSING_ROM_MEMBER | jagwave.rom |
| `gekisou` | MISSING_ROM_MEMBER | alpha-8505_44801c57.bin |
| `glpracr3` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 1.119, 2.120, 78081g503.ic655, m534002c-61.ic353, mg01.ic652 |
| `hvnsgate` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 78081g503.ic655, at01.ic652, at02, m534002c-17.ic353 |
| `jockeygp` | MISSING_PARENT | sp-j3.sp1, sp1-j3.bin, sp1-u3.bin, sp1-u4.bin |
| `konam80s` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT, ROMSET_BAD | 700a01,gchgchmp.22g, 700b01.22g, 826eaa01, gc826ea.u1, h8a01.bin |
| `mfjump` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 78081g503.ic655, m534002c-61.ic353, mg01.ic652, mg14 |
| `misncrft` | ROMSET_BAD, MISSING_ROM_MEMBER | 93c46-eeprom-misncrft, prg-rom2.bin |
| `scorpion` | MISSING_ROM_MEMBER | igr_scorpion_32_a3.ic25 |
| `senkyu` | MISSING_ROM_MEMBER | flash0_blank_region01.u1053 |
| `shngmtkb` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 78081g503.ic655, m534002c-61.ic353, mg01.ic652, mg04 |
| `sqix` | MISSING_ROM_MEMBER | b03__01-2.ef3, b03__03.l2, taito_sq-iu3__lh231041__sharp_japan__8709_d.p8 |
| `suplup` | MISSING_ROM_MEMBER | eeprom-suplup.bin |
| `tblkkuzu` | NO_GOOD_DUMP_REQUIRED, MISSING_PARENT | 78081g503.ic655, m534002c-61.ic353, mg01.ic652, mg12 |
| `twinbrat` | MISSING_ROM_MEMBER | 12.u105, 13.u104, eeprom-twinbrat.bin |
| `viprp1` | MISSING_ROM_MEMBER | flash0_blank_regionbe.u1053 |
| `weddingr` | MISSING_PARENT | weddingr |

Las categorías se solapan cuando MAME reporta, por ejemplo, a la vez miembro faltante y dependencia parental no resuelta. No son conteos mutuamente excluyentes.

## Overrides, restores y estado

- Nuevos overrides mantenidos: `kov2p`, `martmast`; overrides totales: 18.
- Restores: 2/2 VERIFIED. Los únicos cambios persistentes intencionales son los dos overrides; cfg/NVRAM/save generados durante el arranque se restauraron al baseline.
- Global core: `mame078plus`, sin cambios.
- P1-P4: OK, sin cambios: P1 USB5/event17/js0; P2 USB6/event18/js1; P3 USB8/event20/js3; P4 USB7/event19/js2.
- EmulationStation: PID 29733 activo; API idle; `NO GAME RUNNING`; marker ausente; RetroArch/MAME/dispatcher/selector/emulatorlauncher residuales: 0.
- Sistema: OK; temperatura CPU final 49 °C, memoria disponible 14.532.212 kB; sin nuevas líneas críticas NVIDIA/Xorg/I/O en dmesg.
- ROMs, BIOS, CHD, mappings, dispatcher, EmulationStation, HDMI, VSync, FpsLimit y configuración global RetroArch: no modificados.

## Conteo global reconciliado

| Categoría | Juegos únicos BOOT_OK | Fuente/cálculo |
|---|---:|---|
| BOOT_OK_DEFAULT_CORE (`mame078plus`) | 1094 | `arcade_games_audit.csv`, estado vigente por core |
| BOOT_OK_MAME_CURRENT | 18 | 24 probados con target MAME actual; PASS únicos |
| BOOT_OK_FBNEO | 88 | `arcade_games_audit.csv`, core FBNeo |
| TOTAL_UNIQUE_BOOT_OK | 1200 | Unión por `(system, rom)`; solapamientos entre las tres categorías: 0 |

- Este lote recuperó 2 juegos nuevos; `2/2` lanzamientos PASS. De los 24 juegos probados con MAME actual acumulados, 18 pasan y 6 tienen fallos reales en registros anteriores; no se duplicó ningún juego.
- Candidatos fuertes que quedan con el preflight seguro de este pool normal: 0 adicionales con `-verifyroms PASS`; todos los 45 se evaluaron. Quedan otros 43 con contenido/parent/BIOS/ROMset incompleto, además de juegos excluidos por controles especiales o metadata no directa.
- No existe evidencia para cambiar el core global: los resultados sólo justifican overrides individuales en los juegos probados PASS.

## Evidencia y exportación

- Checkpoint: `mame_batch5_checkpoint.json`; preflight completo y salidas crudas: `mame_batch5_preflight.json`.
- Se actualizaron únicamente las filas `kov2p` y `martmast` de `arcade_core_compatibility.csv` con `tested_mame_current=YES`, `BOOT_PASS` y restore VERIFIED.
- Exportación filtrada a `arcade_audit_git/`: SECRET_SCAN PASS; PAYLOAD_SCAN PASS. No se usó Git, commit ni push.
- No se inició BATCH 6, no se probaron controles especiales y no se hicieron pruebas físicas.
