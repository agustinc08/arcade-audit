# Certificación universal — lote prioritario 1

- Fecha: 2026-11-15T09:10:17-03:00
- Alcance: 50 juegos de la cola con adapter READY; una transacción secuencial por juego.
- Piloto previo: 10 juegos únicos, 10 AUTO_PASS en 11 intentos; el intento extra fue una discrepancia esperada de core PC Engine, corregida antes de este lote.
- Resultado del lote: **49 AUTO_PASS, 1 GAME_FAIL (SIGSEGV)**.
- Restores: **50/50 RESTORE_VERIFIED**.
- Fallos del motor en este lote: **0**.
- Fallos globales: **0 wrong dispatch, 0 audio route changes, 0 cambios de batocera.conf/mappings, 0 huérfanos**.
- Controles físicos certificados: **0**. AUTO_PASS valida arranque/runtime/identidad/audio/salida/restore, no botones físicos.

## Fallo de juego

- `mvp` — `Mvp`; RetroArch cargó `mame078plus` y el contenido solicitado correctamente, permaneció 1.053 s y game_health registró `exit_code=-11`, `signal=11` (SIGSEGV). HDMI y retorno a ES correctos; restore verificado. No se reintentó.

## AUTO_PASS

| Sistema | ROM | Nombre | Adapter | Segundos estables | Restore |
|---|---|---|---|---:|---|
| mame | `xmen.zip` | X-Men | MAME078PLUS | 20.159 | RESTORE_VERIFIED |
| mame | `umk3.zip` | Ultimate Mortal Kombat 3 | MAME078PLUS | 20.156 | RESTORE_VERIFIED |
| mame | `xmen6p.zip` | X-Men | MAME078PLUS | 20.172 | RESTORE_VERIFIED |
| mame | `simpsons.zip` | The Simpsons | MAME078PLUS | 20.138 | RESTORE_VERIFIED |
| mame | `snowbros.zip` | Snow Bros. : Nick & Tom | MAME078PLUS | 20.148 | RESTORE_VERIFIED |
| mame | `sia2650.zip` | Super Invader Attack | MAME_CURRENT | 20.182 | RESTORE_VERIFIED |
| mame | `snowbro2.zip` | Snow Bros. 2 : With New Elves | MAME078PLUS | 20.177 | RESTORE_VERIFIED |
| mame | `dino.zip` | Cadillacs and Dinosaurs | MAME078PLUS | 20.142 | RESTORE_VERIFIED |
| mame | `ffight2b.zip` | Final Fight 2 | MAME_CURRENT | 20.150 | RESTORE_VERIFIED |
| mame | `mk3.zip` | Mortal Kombat 3 | MAME078PLUS | 20.157 | RESTORE_VERIFIED |
| mame | `punisher.zip` | The Punisher | MAME078PLUS | 20.164 | RESTORE_VERIFIED |
| mame | `warriorb.zip` | Warrior Blade - Rastan Saga Episode III | MAME078PLUS | 20.156 | RESTORE_VERIFIED |
| mame | `deadconx.zip` | Dead Connection | MAME078PLUS | 20.166 | RESTORE_VERIFIED |
| mame | `exvania.zip` | Exvania | MAME078PLUS | 20.161 | RESTORE_VERIFIED |
| mame | `gauntlet.zip` | Gauntlet | MAME078PLUS | 20.131 | RESTORE_VERIFIED |
| mame | `numanath.zip` | Numan Athletics | MAME078PLUS | 20.145 | RESTORE_VERIFIED |
| mame | `tmnt.zip` | Teenage Mutant Ninja Turtles | MAME078PLUS | 20.145 | RESTORE_VERIFIED |
| mame | `tmnt2.zip` | Teenage Mutant Ninja Turtles: Turtles in Time | MAME078PLUS | 20.137 | RESTORE_VERIFIED |
| mame | `alexkidd.zip` | Alex Kidd: The Lost Stars | MAME078PLUS | 20.126 | RESTORE_VERIFIED |
| mame | `asurabld.zip` | Asura Blade - Sword Of Dynasty | MAME078PLUS | 20.143 | RESTORE_VERIFIED |
| mame | `aurail.zip` | Aurail | MAME078PLUS | 20.125 | RESTORE_VERIFIED |
| mame | `avengers.zip` | Avengers | MAME078PLUS | 20.164 | RESTORE_VERIFIED |
| mame | `bonkadv.zip` | B.C. Kid - Arcade Version | MAME078PLUS | 20.170 | RESTORE_VERIFIED |
| mame | `dkong3.zip` | Donkey Kong 3 | MAME078PLUS | 20.164 | RESTORE_VERIFIED |
| mame | `doapp.zip` | Dead Or Alive ++ | MAME078PLUS | 20.157 | RESTORE_VERIFIED |
| mame | `ffight.zip` | Final Fight | MAME078PLUS | 20.154 | RESTORE_VERIFIED |
| mame | `galaga.zip` | Galaga | MAME078PLUS | 20.134 | RESTORE_VERIFIED |
| mame | `chqflag.zip` | Chequered Flag | MAME078PLUS | 20.134 | RESTORE_VERIFIED |
| mame | `harddunk.zip` | Hard Dunk | MAME078PLUS | 20.127 | RESTORE_VERIFIED |
| mame | `88games.zip` | '88 Games | MAME078PLUS | 20.123 | RESTORE_VERIFIED |
| mame | `aafb.zip` | All American Football | MAME078PLUS | 20.106 | RESTORE_VERIFIED |
| mame | `arabianm.zip` | Arabian Magic | MAME078PLUS | 20.138 | RESTORE_VERIFIED |
| mame | `arkretrn.zip` | Arkanoid Returns | MAME078PLUS | 20.155 | RESTORE_VERIFIED |
| mame | `balonfgt.zip` | Vs. Balloon Fight | MAME078PLUS | 20.157 | RESTORE_VERIFIED |
| mame | `bbmanw.zip` | New Dyna Blaster - Global Quest | MAME078PLUS | 20.140 | RESTORE_VERIFIED |
| mame | `bubblem.zip` | Bubble Memories: The Story of Bubble Bobble III | MAME078PLUS | 20.157 | RESTORE_VERIFIED |
| mame | `bublbob2.zip` | Bubble Bobble II | MAME078PLUS | 20.143 | RESTORE_VERIFIED |
| mame | `bucky.zip` | Bucky O'Hare | MAME078PLUS | 20.129 | RESTORE_VERIFIED |
| mame | `captaven.zip` | Captain America And The Avengers | MAME078PLUS | 20.147 | RESTORE_VERIFIED |
| mame | `captcomm.zip` | Captain Commando | MAME078PLUS | 20.150 | RESTORE_VERIFIED |
| mame | `cupfinal.zip` | Taito Cup Finals | MAME078PLUS | 20.161 | RESTORE_VERIFIED |
| mame | `cyvern.zip` | Cyvern : The Dragon Weapons | MAME078PLUS | 20.166 | RESTORE_VERIFIED |
| mame | `danceyes.zip` | Dancing Eyes | MAME078PLUS | 20.140 | RESTORE_VERIFIED |
| mame | `dariusg.zip` | Darius Gaiden : Silver Hawk | MAME078PLUS | 20.163 | RESTORE_VERIFIED |
| mame | `dariusgx.zip` | Darius Gaiden - Silver Hawk Extra Version | MAME078PLUS | 20.166 | RESTORE_VERIFIED |
| mame | `dungeonm.zip` | Dungeon Magic | MAME078PLUS | 20.142 | RESTORE_VERIFIED |
| mame | `dynablst.zip` | Dynablaster | MAME078PLUS | 20.119 | RESTORE_VERIFIED |
| mame | `elvactr.zip` | Elevator Action Returns | MAME078PLUS | 20.151 | RESTORE_VERIFIED |
| mame | `embargo.zip` | Embargo | MAME078PLUS | 20.156 | RESTORE_VERIFIED |

## Estado de seguridad al cerrar

- EmulationStation: activo; API idle; sin juego en ejecución.
- Marker: ausente; procesos de lanzamiento/emulación huérfanos: 0.
- HDMI default: `alsa_output.pci-0000_01_00.1.hdmi-stereo`.
- Core MAME global: `mame078plus`.
- Overrides MAME activos: 18; P1–P4 sin cambios.
- Estado: Phase 14 continúa RUNNING; siguiente cola: `mame/espgal.zip` (cola restante aproximada: 6604 entradas READY).
