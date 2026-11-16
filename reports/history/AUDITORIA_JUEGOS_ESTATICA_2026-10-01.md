> Snapshot histórico; los valores de red y credenciales se saneaban en esta copia cuando correspondía. No usar como estado vigente; consultar `ARCADE_CURRENT_STATE.md`.

# AUDITORÍA ESTÁTICA JUEGO POR JUEGO

Fecha: 2026-10-01T07:34:28-03:00
Gamelists actuales: 49; entradas visibles: 8142. Estados de sistema según RESOLUCION_SISTEMAS_2026-10-01.md.
game_audit.csv/json funcionales: leídos sólo para asegurar separación; no modificados.

## 1. RESUMEN

Juegos visibles: **8142**
Auditados: **8142**
Sistemas activos: **49**
Sistemas completados: **49**

READY_FOR_BOOT: **7932**
READY_FOR_BOOT_WITH_NOTE: **1**
FORMAT_PROBLEM: **70**
ROMSET_PROBLEM: **11**
MISSING_FILE: **0**
EMPTY_FILE: **0**
MISSING_DEPENDENCY: **0**
USER_CONTENT_REQUIRED: **6**
LAUNCHER_PROBLEM: **0**
SPECIAL_MANUAL: **117**
NEEDS_FUNCTIONAL_TEST: **2**
NEEDS_REVIEW: **2**
NOT_GAME_CONTENT: **1**
Porcentaje listo para BOOT TEST (READY + READY_WITH_NOTE): **97.4%**
READY_FOR_BOOT describe preparación estática, no funcionamiento ni PASS. DAT arcade se comparó por CRC+tamaño en directorios ZIP; los payloads no se descomprimieron.

## 2. RESULTADOS POR SISTEMA

| Sistema | Juegos visibles/auditados | READY | Nota | Formato | Romset | Missing/dependencia | Manual | Funcional | Review/no juego |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| atari2600 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| c64 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cdogs | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dreamcast | 775 | 775 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| easyrpg | 12 | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| fbneo | 79 | 73 | 0 | 0 | 6 | 0 | 0 | 0 | 0 |
| fds | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| flatpak | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| gamecube | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gb | 403 | 403 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gba | 724 | 724 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gbc | 405 | 404 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| hcl | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hurrican | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ikemen | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| mame | 1093 | 1088 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| mastersystem | 382 | 382 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| megacd | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| megadrive | 1029 | 1029 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mrboom | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| n64 | 377 | 311 | 0 | 66 | 0 | 0 | 0 | 0 | 0 |
| naomi | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nds | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| neogeo | 104 | 104 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nes | 702 | 702 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| odcommander | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| openbor | 128 | 127 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| pcengine | 528 | 528 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ports | 5 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 |
| prboom | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ps2 | 196 | 196 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ps3 | 13 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ps4 | 95 | 0 | 0 | 0 | 0 | 0 | 95 | 0 | 0 |
| psp | 634 | 634 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| psx | 78 | 77 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| pygame | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| saturn | 5 | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 1 |
| scummvm | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| sdlpop | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| snes | 275 | 275 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| solarus | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| steam | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 |
| superbroswar | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| theforceengine | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| tic80 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| windows | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 |
| xbox | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| xbox360 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| xrick | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |


## 3. JUEGOS CON PROBLEMAS CONFIRMADOS

### FORMAT_PROBLEM — 70

- n64 — 1080 TenEighty Snowboarding (./1080 TenEighty Snowboarding (Europe) (En,Ja,Fr,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Banjo Kazooie Gruntildas Mask (./Banjo Kazooie Gruntildas Mask.zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Banjo-Tooie (./Banjo-Tooie (Europe) (En,Fr,De,Es).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Beetle Adventure Racing! (./Beetle Adventure Racing! (Europe) (En,Fr,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Blast Corps (./Blast Corps (Europe) (En,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Body Harvest (./Body Harvest (Europe) (En,Fr,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Bomberman 64 (./Bomberman 64 (Europe) (1).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Bomberman 64 (./Bomberman 64 (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Bomberman 64 : The Second Attack! (./Bomberman 64 - The Second Attack! (USA).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Bomberman Hero (./Bomberman Hero (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Conker's Bad Fur Day (./Conkers Bad Fur Day (Uncensored).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Cruis'n Exotica (./Cruis'n Exotica (USA).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Cruis'n USA (./Cruis'n USA (USA) (Rev B).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Diddy Kong Racing (./Diddy Kong Racing (Europe) (En,Fr,De) (Rev 1).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Doom 64 Complete Edition (v1.0) (./Doom 64 Complete Edition (v1.0).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Duke Nukem - Zero Hour (./Duke Nukem - Zero Hour (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Duke Nukem 64 (./Duke Nukem 64 (4 Player Co-op Hack).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Excitebike 64 (./Excitebike 64 (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — F-zero X - Expansion Kit (./F-Zero X - Expansion Kit (Japan) (64DD) (Hack by Zoinkity v2) (T-En by LuigiBlood v2).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Goemon's Great Adventure (./Goemon's Great Adventure (USA).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — GoldenEye 007 - Counter-Strike Map Pack (./GoldenEye 007 - Counter-Strike Map Pack.zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Harvest Moon 64 (./Harvest Moon 64 (USA).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Hexen (./Hexen (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Jet Force Gemini Trainer and Co-Op Hack (./Jet Force Gemini Trainer and Co-Op Hack.7z): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Kirby 64 : The Crystal Shards (./Kirby 64 - The Crystal Shards (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mario Golf (./Mario Golf (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mario Kart 64 (./Mario Kart 64 (3-4 players Grand Prix).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mario Party - 48433 (./Mario Party - 48433.zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mario Party 2 (./Mario Party 2 (Europe) (En,Fr,De,Es,It) (Wii Virtual Console).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mario Party 3 (./Mario Party 3 (Europe) (En,Fr,De,Es).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mario Tennis (./Mario Tennis (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mystical Ninja Starring Goemon 2 (./Mystical Ninja 2 Starring Goemon (Europe) (En,Fr,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Mystical Ninja Starring Goemon (./Mystical Ninja Starring Goemon (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Ogre Battle 64 : Person of Lordly Caliber (./Ogre Battle 64 - Person of Lordly Caliber (USA) (Rev 1).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Paper Mario - Star Nova (v1.3.0) (./Paper Mario - Star Nova (v1.3.0).7z): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Perfect Dark (./Perfect Dark (Europe) (En,Fr,De,Es,It).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Pilotwings 64 (./Pilotwings 64 (Europe) (En,Fr,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Pokémon Puzzle League (./Pokemon Puzzle League (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Pokémon Snap (./Pokemon Snap (Spain).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Pokémon Stadium (./Pokemon Stadium (Europe) (Rev 1).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Pokémon Stadium 2 (./Pokemon Stadium 2 (Spain).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Quake (./Quake (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Quake II (./Quake II (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Quake II New Controls (./Quake II New Controls.zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Quest 64 (./Quest 64 (USA).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Resident Evil 2 (./Resident Evil 2 (Europe) (En,Fr).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Ridge Racer 64 (./RR64 - Ridge Racer 64 (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Rush 2 : Extreme Racing USA (./Rush 2 - Extreme Racing USA (Europe) (En,Fr,De,Es,It,Nl).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — San Francisco Rush : Extreme Racing (./San Francisco Rush - Extreme Racing (Europe) (En,Fr,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — San Francisco Rush 2049 (./San Francisco Rush 2049 (Europe) (En,Fr,De,Es,It,Nl).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Snowboard Kids (./Snowboard Kids (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Snowboard Kids 2 (./Snowboard Kids 2 (USA).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Space Station Silicon Valley (./SpaceStation Silicon Valley (Europe) (En,Fr,De,Es,It,Nl,Pt).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Star Fox 64 (./Star Fox 64 (USA) (Rev 1).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Super Mario 64 Remake 2.0 (./Super Mario 64 Remake 2.0.zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Super Smash Bros. (./Super Smash Bros. (Europe) (En,Fr,De) (1).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Super Smash Bros. (./Super Smash Bros. (Europe) (En,Fr,De).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — The Legend of Zelda  Ocarina of Time - 4 Player Edition (./The Legend of Zelda  Ocarina of Time - 4 Player Edition.zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — The Legend of Zelda Majoras Mask Redux (./The Legend of Zelda Majoras Mask Redux.zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Turok : Dinosaur Hunter (./Turok - Dinosaur Hunter (Europe) (Rev 2).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Turok : Rage Wars (./Turok - Rage Wars (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Turok 2 : Seeds Of Evil (./Turok 2 - Seeds of Evil (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Turok 3 : Shadow of Oblivion (./Turok 3 - Shadow of Oblivion (Europe) (Beta) (2000-07-10).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Turok 3 : Shadow of Oblivion (./Turok 3 - Shadow of Oblivion (Europe).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Yoshi's Story (./Yoshi's Story (USA) (En,Ja) (1).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- n64 — Yoshi's Story (./Yoshi's Story (USA) (En,Ja).zip): ZIP/7z incompatible con Mupen64Plus standalone; no hay extracción/selección automática.
- psx — Mortal Kombat Trilogy (E) (./Mortal Kombat Trilogy (E) (v1.1) (Track 01) [SLES-02509].7z): Mortal Kombat Trilogy .7z contiene BIN.ECM y pistas APE; DuckStation recibe .7z directamente, sin extracción activa.
- saturn — Chill (./Chill (Jan 19, 1998 prototype).zip): ZIP incompatible con Beetle Saturn efectivo; miembros: Chill (unreleased) [19-1-98]/chill.bin, Chill (unreleased) [19-1-98]/chill.cue
- saturn — Ferox (./Ferox (Jul 29, 1997 prototype).zip): ZIP incompatible con Beetle Saturn efectivo; miembros: Ferox_Saturn/Ferox.iso, Ferox_Saturn/readme.txt, Ferox_Saturn/swap-trick.txt
- saturn — Sonic X-treme (./Sonic X-treme (Jul 14, 1996 prototype).zip): ZIP incompatible con Beetle Saturn efectivo; miembros: SonicXtreme_POV_07-14-96.iso

### ROMSET_PROBLEM — 11

- fbneo — Bubble Bobble (./bublboblr.zip): bublboblr: faltan 16/18 ROMs por CRC+tamaño en set/parent/BIOS (a78-08.37, a78-07.46, a78-01.17, a78-09.12, a78-10.13, a78-11.14, a78-12.15, a78-13.16); central directory
- fbneo — decocass (./decocass.zip): decocass: faltan 4/45 ROMs por CRC+tamaño en set/parent/BIOS (v0c-.7e, dsp-3_p0-c.m9, v0d-.7e, dsp-3_p0-d.m9); central directory
- fbneo — Cadillacs and Dinosaurs (./dino.zip): dino: faltan 6/28 ROMs por CRC+tamaño en set/parent/BIOS (cd63b.1a, ioc1.ic1, d7l1.7l, d8l1.8l, d9k2.9k, d10f1.10f); central directory
- fbneo — The King of Dragons (./kod.zip): kod: faltan 2/28 ROMs por CRC+tamaño en set/parent/BIOS (kd29b.1a, ioc1.ic7); central directory
- fbneo — The Punisher (./punisher.zip): punisher: faltan 12/34 ROMs por CRC+tamaño en set/parent/BIOS (buf1, ioa1, prg2, rom1, ps63b.1a, iob1.12d, bprg1.11d, ioc1.ic1); central directory
- fbneo — Vendetta (./vendetta.zip): vendetta: faltan 2/12 ROMs por CRC+tamaño en set/parent/BIOS (p1-pal16l8acn.17e, p2-pal16l8acn.14e); central directory
- mame — Alex Kidd: The Lost Stars (./alexkidd.zip): alexkidd: faltan 4/19 ROMs por CRC+tamaño en ZIP propio/parent/BIOS (epr10429.42, epr10427.26, epr10430.43, epr10428.25); comparación central directory
- mame — Deroon Derodero (./deroon.zip): deroon: faltan 1/12 ROMs por CRC+tamaño en ZIP propio/parent/BIOS (t103ubl1.j08); comparación central directory
- mame — Marvel vs. Capcom : Clash of Super Heroes (./mvsc.zip): mvsc: faltan 4/22 ROMs por CRC+tamaño en ZIP propio/parent/BIOS (mvcu.03d, mvcu.04d, mvcux.03d, mvcux.04d); comparación central directory
- mame — Pac & Pal (./pacnpal.zip): pacnpal: faltan 1/10 ROMs por CRC+tamaño en ZIP propio/parent/BIOS (papi3.3m); comparación central directory
- mame — Armored Warriors (./pgear.zip): pgear: faltan 2/22 ROMs por CRC+tamaño en ZIP propio/parent/BIOS (pwgjx.03a, pwgjx.04a); comparación central directory

### MISSING_FILE / EMPTY_FILE / MISSING_DEPENDENCY — 0

Ninguno.

### USER_CONTENT_REQUIRED — 6

- theforceengine — Operation Kyber Crystal - 1 Imperial Mine (./mods/Operation Kyber Crystal - 1 Imperial Mine.tfe): Mod requiere contenido base Dark Forces ausente.
- theforceengine — Operation Kyber Crystal - 2 Spaceport (./mods/Operation Kyber Crystal - 2 Spaceport.tfe): Mod requiere contenido base Dark Forces ausente.
- theforceengine — Operation Kyber Crystal - 3 Distribution Center (./mods/Operation Kyber Crystal - 3 Distribution Center.tfe): Mod requiere contenido base Dark Forces ausente.
- theforceengine — Operation Kyber Crystal - 4 Ice World (./mods/Operation Kyber Crystal - 4 Ice World.tfe): Mod requiere contenido base Dark Forces ausente.
- theforceengine — Operation Kyber Crystal - 5 Hosnian Prime (./mods/Operation Kyber Crystal - 5 Hosnian Prime.tfe): Mod requiere contenido base Dark Forces ausente.
- theforceengine — Operation Kyber Crystal - 6 Reckoning (./mods/Operation Kyber Crystal - 6 Reckoning.tfe): Mod requiere contenido base Dark Forces ausente.

### LAUNCHER_PROBLEM — 0

Ninguno.

### NEEDS_REVIEW / NOT_GAME_CONTENT — 3

- easyrpg — Lavender translation kit (./Lavender/Lavender translation kit.zip): Translation kit con recursos, no proyecto RPG ejecutable.
- gbc — Petris (./petris.zip): petris.zip contiene petris.gbc; extracción no certificada.
- saturn — Cube Cat (./cubecat_sl_elf.iso): ES acepta ISO; metadata Beetle no declara ISO.

### NEEDS_FUNCTIONAL_TEST — 2

- ikemen — Famicom-Fighters (./Famicom-Fighters.ikemen): Joystick físico y mapas P1/P2 requieren prueba funcional.
- ikemen — King of Fighters Shining Go (./King of Fighters Shining Go.ikemen): Joystick físico y mapas P1/P2 requieren prueba funcional.

## 4. CASOS ESPECIALES

- PSX Mortal Kombat Trilogy .7z: contiene BIN.ECM y pistas APE; FORMAT_PROBLEM.
- N64: 64 ZIP + 2 7z incompatibles con Mupen64Plus standalone; no se extrajeron.
- Saturn: tres ZIP listados y FORMAT_PROBLEM; ISO NEEDS_REVIEW.
- GBC petris.zip: NEEDS_REVIEW; contiene petris.gbc.
- EasyRPG Lavender translation kit: NOT_GAME_CONTENT; se conserva.
- IKEMEN: dos títulos NEEDS_FUNCTIONAL_TEST por controles físicos no certificables.
- OpenBOR Final Fight & Cadillacs: READY_FOR_BOOT_WITH_NOTE por log histórico individual.
- The Force Engine: seis USER_CONTENT_REQUIRED por falta del contenido base de Dark Forces.
- PS4: 95 paths de archivos del paquete se vincularon a eboot.bin antecesor y quedaron SPECIAL_MANUAL; no son 95 juegos distintos.

## 5. MAME

Core efectivo: libretro/mame078plus (MAME 2003-Plus), no MAME standalone 0.285. DAT: /userdata/bios/mame2003-plus/mame2003-plus.xml.
ZIP visibles: 1093; CRC+tamaño compatibles: 1088; ROMSET_PROBLEM: 5; revisión DAT: 0. Parents y ZIPs de BIOS en rompaths locales fueron considerados.


## 6. FBNEO

DAT Arcade local v1.0.0.03: /userdata/bios/fbneo/FinalBurn Neo (ClrMame Pro XML, Arcade only).dat.
ZIP visibles: 79; CRC+tamaño compatibles: 73; ROMSET_PROBLEM: 6; revisión DAT: 0; dependencias NeoGeo compartidas y BIOS local consideradas.


## 7. NEOGEO

DAT local FBNeo Neo Geo v1.0.0.03: /userdata/bios/fbneo/FinalBurn Neo (ClrMame Pro XML, Neogeo only).dat.
ZIP visibles: 104; CRC+tamaño compatibles: 104; ROMSET_PROBLEM: 0; revisión DAT: 0. neogeo.zip fue contrastado contra ROMs comunes y BIOS de programa. Variantes merge alternativas no se trataron como requisitos simultáneos.


La comparación usa CRC/tamaño declarados en central directories; no certifica integridad del payload. Sets con dependencia parent/BIOS presente no se marcaron como incompletos por ROMs heredadas.

## 8. READY_FOR_BOOT POR SISTEMA

| Sistema | READY | READY_WITH_NOTE |
|---|---:|---:|
| atari2600 | 2 | 0 |
| c64 | 4 | 0 |
| cdogs | 1 | 0 |
| dreamcast | 775 | 0 |
| easyrpg | 11 | 0 |
| fbneo | 73 | 0 |
| fds | 1 | 0 |
| gamecube | 9 | 0 |
| gb | 403 | 0 |
| gba | 724 | 0 |
| gbc | 404 | 0 |
| hcl | 1 | 0 |
| hurrican | 1 | 0 |
| mame | 1088 | 0 |
| mastersystem | 382 | 0 |
| megacd | 24 | 0 |
| megadrive | 1029 | 0 |
| mrboom | 1 | 0 |
| n64 | 311 | 0 |
| naomi | 1 | 0 |
| nds | 2 | 0 |
| neogeo | 104 | 0 |
| nes | 702 | 0 |
| odcommander | 1 | 0 |
| openbor | 127 | 1 |
| pcengine | 528 | 0 |
| prboom | 1 | 0 |
| ps2 | 196 | 0 |
| ps3 | 13 | 0 |
| psp | 634 | 0 |
| psx | 77 | 0 |
| saturn | 1 | 0 |
| scummvm | 3 | 0 |
| sdlpop | 1 | 0 |
| snes | 275 | 0 |
| solarus | 10 | 0 |
| superbroswar | 1 | 0 |
| tic80 | 3 | 0 |
| xbox | 2 | 0 |
| xbox360 | 5 | 0 |
| xrick | 1 | 0 |


## 9. NEEDS_REVIEW

Casos individuales incluidos en la sección 3 y en CSV/JSON.

## 10. SPECIAL_MANUAL

PS4, Windows, Ports, Flatpak, Pygame y Steam conservan clasificación manual por paquete/aplicación; las rutas y razones están en CSV/JSON.

## 11. SIGUIENTE ETAPA

La siguiente etapa será BOOT TEST, uno por uno y por el flujo real. PASS funcional requerirá confirmación humana de arranque, imagen, audio, controles y rendimiento. Esta auditoría no lanzó juegos.

## CHECKPOINT

Sistemas completados: 49/49. Juegos auditados: 8142/8142.
