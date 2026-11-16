> Snapshot histórico; los valores de red y credenciales se saneaban en esta copia cuando correspondía. No usar como estado vigente; consultar `ARCADE_CURRENT_STATE.md`.

# AUDITORÍA BATOCERA

Fecha de lectura: 2026-09-30. Alcance: inspección estática y de solo lectura. No se modificaron archivos, ROMs, gamelists, media ni configuraciones; no se ejecutaron scripts de auditoría, juegos o emuladores, y no se reiniciaron servicios.

Sistemas encontrados: 51 con gamelist y catálogo; 253 definiciones en la configuración activa de EmulationStation (las 253 rutas configuradas existen).
Gamelists: 51
Entradas gamelist visibles: 8.146
Entradas gamelist totales: 8.433 (287 ocultas)
ROMs físicas: 9.030 archivos dentro de las rutas de sistemas cuyo sufijo coincide con alguna extensión declarada; 8.296 están directamente en carpetas de sistema y 734 dentro de subdirectorios. Es un recuento mecánico de archivos elegibles, no de juegos independientes: incluye formatos auxiliares, paquetes por carpeta, ejecutables internos y medios multidisco. /userdata/roms es un montaje mergerfs; el inventario refleja lo que el montaje presenta, no cada copia que pudiera quedar oculta en sus fuentes.

OK estructural: 8.417 de 8.433 registros gamelist sin referencias ausentes, nombres vacíos ni referencias de media con path roto. Los 16 registros afectados se cuentan una sola vez aunque puedan tener más de un defecto. Los grupos con títulos repetidos, que no demuestran duplicación, se excluyen de este conteo.

Problemas confirmados:
- ROM inexistente en <path>: 9 (1 Cannonball, 8 DevilutionX)
- referencias rotas: 19 instancias (9 paths principales, 2 referencias multidisk ausentes, 7 referencias de media ausentes y 1 imagen con diferencia de mayúsculas/minúsculas)
- imágenes faltantes: 4 archivos físicamente ausentes; hay además 1 referencia a imagen con mayúsculas incorrectas cuyo archivo existe en minúsculas
- videos faltantes: 0
- media faltante distinta de imagen/video: 3 (2 marquees y 1 thumbnail)
- XML inválidos o truncados: 0 de 51
- duplicados confirmados por path de gamelist: 0; no se calcularon hashes
- launchers rotos confirmados: 1 (Zaparoo apunta a un ejecutable local inexistente)
- BIOS faltantes confirmadas: 0
- archivos vacíos: 30
- symlinks rotos: 64 (32 en cada uno de dos prefijos Wine)

Elementos sospechosos: 705 grupos de títulos repetidos entre paths distintos (812 registros adicionales dentro de esos grupos; pueden ser discos, regiones, revisiones o clones); 1 launcher sin permiso de ejecución; 2 referencias BIN de multidisco PSX ausentes; 1 archivo .disabled de Cannonball y 1 acceso directo .lnk fuera de un sistema.
Revisión manual: 3.571 archivos de media sin referencia en campos de gamelist conocidos, 826 directorios vacíos, los 64 symlinks Wine, los grupos de títulos coincidentes, el catálogo de BIOS completo y los ports que requieren validación funcional.

## Alcance, método y límites

- Versión comprobada: Batocera `43cou.1 2026/05/29 04:36`; `/etc/os-release` declara Batocera 43.1, kernel `Linux 6.18.16`, arquitectura x86_64.
- `/userdata/roms` se sirve mediante mergerfs y agrega `/userdata/.roms_base` y dos árboles de medios montados. La auditoría cuenta la vista del montaje.
- La configuración de `/userdata/system/configs/emulationstation/es_systems_el_gordo.cfg` tiene los mismos 253 nombres de sistema que `/usr/share/emulationstation/es_systems.cfg`, aunque los archivos no son idénticos. Los paths declarados existen. Hay 51 gamelists; 48 sistemas tienen al menos un archivo con extensión aceptada y Cannonball, DevilutionX e Ikemen son sistemas de contenido basado en carpetas/entradas especiales.
- Gamelists: se analizaron los 51 XML con parser; se revisaron `<game>`, `<folder>`, `<path>`, `<image>`, `<video>`, `<thumbnail>`, `<marquee>`, `<manual>`, `<fanart>` y paths en `<multidisk>`. Ningún XML dio error. Se encontraron 0 paths vacíos, 0 paths absolutos y 0 paths con `../`.
- Media: hay 33.811 archivos bajo carpetas convencionales de imágenes, videos, marquees, thumbnails, manuals y media. 3.571 no están referenciados por los campos de gamelist enumerados; esta categoría significa “sin referencia de gamelist”, no que otro componente no los use.
- No se hicieron hashes de ROMs. Por eso no se afirma que archivos con nombres parecidos o extensiones diferentes sean copias idénticas. Los grupos de títulos repetidos quedan como sospecha/revisión manual.
- No se procesaron todos los videos ni se hizo una nueva lectura completa de firmas de imagen. El informe del 2026-09-26 registra un análisis previo de 25.697 imágenes: detectó cuatro archivos HTML/texto con extensión de imagen, que fueron retirados entonces; detectó también 444 imágenes válidas cuyo formato no coincidía con la extensión. En el estado actual las cuatro referencias de imagen asociadas siguen sin archivo. La validez binaria actual de cada video/media restante no se determinó.
- La herramienta de Batocera consultada (`batocera-es-swissknife --help`) no ofrece consulta de BIOS; no se encontró un comando independiente de comprobación BIOS. No se lanzó ningún juego.

## Desglose por sistema

“Archivos por extensión” cuenta archivos con alguna extensión admitida por la configuración del sistema, incluso en subdirectorios. No equivale a juegos ni a estado funcional. Las anomalías concretas están descritas debajo y en las secciones temáticas.

| Sistema | Entradas visibles | Entradas totales | Archivos por extensión |
|---|---:|---:|---:|
| atari2600 | 2 | 2 | 2 |
| c64 | 4 | 4 | 4 |
| cannonball | 1 | 1 | 0 |
| cdogs | 1 | 1 | 1 |
| devilutionx | 2 | 8 | 0 |
| dreamcast | 775 | 775 | 775 |
| easyrpg | 12 | 12 | 1 |
| fbneo | 79 | 104 | 104 |
| fds | 1 | 1 | 1 |
| flatpak | 2 | 2 | 2 |
| gamecube | 9 | 9 | 9 |
| gb | 403 | 410 | 410 |
| gba | 724 | 725 | 725 |
| gbc | 405 | 406 | 406 |
| hcl | 1 | 1 | 1 |
| hurrican | 1 | 1 | 1 |
| ikemen | 2 | 2 | 0 |
| mame | 1.093 | 1.324 | 1.324 |
| mastersystem | 382 | 383 | 383 |
| megacd | 24 | 24 | 24 |
| megadrive | 1.029 | 1.037 | 1.037 |
| mrboom | 1 | 1 | 1 |
| n64 | 377 | 377 | 377 |
| naomi | 1 | 1 | 1 |
| nds | 2 | 2 | 2 |
| neogeo | 104 | 105 | 105 |
| nes | 702 | 702 | 702 |
| odcommander | 1 | 1 | 1 |
| openbor | 128 | 128 | 128 |
| pcengine | 528 | 529 | 529 |
| ports | 6 | 6 | 10 |
| prboom | 1 | 2 | 2 |
| ps2 | 196 | 196 | 196 |
| ps3 | 13 | 13 | 13 |
| ps4 | 95 | 95 | 95 |
| psp | 634 | 637 | 637 |
| psx | 78 | 78 | 84 |
| pygame | 1 | 1 | 2 |
| saturn | 5 | 6 | 6 |
| scummvm | 3 | 3 | 3 |
| sdlpop | 1 | 1 | 1 |
| snes | 275 | 275 | 275 |
| solarus | 10 | 10 | 10 |
| steam | 7 | 7 | 7 |
| superbroswar | 1 | 1 | 1 |
| theforceengine | 6 | 6 | 6 |
| tic80 | 3 | 3 | 3 |
| windows | 7 | 7 | 615 |
| xbox | 2 | 2 | 2 |
| xbox360 | 5 | 5 | 5 |
| xrick | 1 | 1 | 1 |

Los recuentos por extensión se basan en los sufijos declarados por el sistema. Para PSX hay 84 archivos en la raíz con sufijos aceptados; siete de los CHD no están enlazados por `<path>` individual, pero sí por `<multidisk>`. Estos valores ilustran por qué los archivos de extensión aceptada no deben interpretarse como juegos distintos.

### Hallazgos por sistema

- **c64:** Fix-It Felix Jr. tiene una referencia de marquee ausente: `./fix_it_felix_64-marquee.png` desde `/userdata/roms/c64/gamelist.xml`.
- **cannonball:** el path principal no existe y faltan referencias a thumbnail y marquee; la imagen `./images/Cannonball.png` difiere en mayúsculas del archivo visible `images/cannonball.png`.
- **devilutionx:** 8 paths `.mpq` ausentes; seis pertenecen a registros ocultos sin nombre.
- **gba:** faltan las imágenes de Pokémon: Team Rocket Edition y ESPN Winter X-Games Snowboarding 2.
- **ps2:** faltan las imágenes de Devil May Cry 2, discos 1 y 2.
- **psx:** el metadata multidisc de Dino Crisis y Dino Crisis 2 apunta a dos archivos BIN inexistentes. Los paths principales `.chd` existen. Siete CHD de Final Fantasy VII, Metal Gear Solid y Parasite Eve II no son huérfanos: están mencionados en sus referencias `<multidisk>`.
- **ports:** un launcher con dependencia local ausente (Zaparoo); SuperTuxKart.sh carece del bit ejecutable; los demás detalles están en la sección Ports.
- **windows:** 64 symlinks Wine colgantes bajo los prefijos Diablo II y TMNT Rescue-Palooza.
- **otros sistemas:** no se detectaron paths directos faltantes ni media referenciada ausente fuera de los sistemas enumerados arriba.

## 1. RESUMEN GLOBAL

Los 51 XML son válidos y los paths de juegos no tienen campos vacíos, absolutos ni escapes de directorio. Hay 9 paths principales ausentes: Cannonball y ocho archivos de DevilutionX. Se detectaron también dos paths BIN ausentes dentro del metadata multidisc de PSX.

Las cuatro imágenes conocidas de PS2/GBA siguen ausentes. Cannonball agrega dos media ausentes y una referencia a imagen con case mismatch; C64 agrega un marquee ausente. No faltan videos referenciados.

No se confirmó duplicación por path ni se compararon hashes. Hay 705 grupos de títulos repetidos entre paths distintos. Se contaron 3.571 archivos sin referencia a gamelist en árboles de media y 30 archivos de cero bytes. No se midió el funcionamiento de ningún juego.

## 2. ERRORES CONFIRMADOS QUE CONVIENE CORREGIR

Gravedad media: el catálogo muestra entradas cuyo archivo principal no está en el path indicado.

- **MISSING_ROM — CONFIRMADO — Cannonball:** sistema cannonball, juego “Cannonball”; el gamelist pide `/userdata/roms/cannonball/Cannonball.cannonball`, pero solo existe `Cannonball.cannonball.disabled` (25 bytes). El archivo con sufijo `.disabled` no coincide con la extensión `.cannonball` declarada por el sistema.
- **MISSING_ROM — CONFIRMADO — DevilutionX:** juego “Diablo 1”; falta `/userdata/roms/devilutionx/diabdat.mpq`, señalado por `_info.txt` como los datos base de Diablo 1.
- **MISSING_ROM — CONFIRMADO — DevilutionX:** juego “Diablo 1: Hellfire”; falta `/userdata/roms/devilutionx/hellfire.mpq` (datos de expansión). La ausencia no demuestra nada sobre el arranque, que no se probó.
- **MISSING_ROM / EMPTY_NAME — CONFIRMADO, entradas ocultas:** seis records ocultos en `devilutionx/gamelist.xml` refieren `fonts.mpq`, `hfmonk.mpq`, `hfmusic.mpq`, `hfvoice.mpq`, `pl.mpq` y `ru.mpq`; ninguno existe en ese directorio y los seis carecen de `<name>`. Son recursos condicionales/idioma según `_info.txt`, no seis juegos visibles.
- **BROKEN_REFERENCE — CONFIRMADO — PSX:** los paths de metadata `<multidisk>` para `(PS1) Dino Crisis [PAL] [SLES-02211].bin` y `(PS1) Dino Crisis 2 [PAL] [SLES-03225] (Track 2).bin` no existen. Los paths principales de gamelist apuntan a CHD que sí existen.
- **MISSING_IMAGE — CONFIRMADO:** faltan 4 archivos enlazados por gamelist: dos imágenes de Devil May Cry 2 en PS2 y dos imágenes de Pokémon: Team Rocket Edition / ESPN Winter X-Games Snowboarding 2 en GBA. El informe del 2026-09-26 había confirmado que esos cuatro archivos corruptos se retiraron y que se conservaron las referencias.
- **MISSING_MEDIA — CONFIRMADO:** falta el marquee de Fix-It Felix Jr. en C64; faltan marquee y thumbnail de Cannonball.
- **BROKEN_REFERENCE — CONFIRMADO, diferencia de case:** el gamelist de Cannonball pide `images/Cannonball.png`, pero el archivo presente es `images/cannonball.png`. En Linux esos nombres no son equivalentes.
- **BROKEN_LAUNCHER — CONFIRMADO — Zaparoo:** `/userdata/roms/ports/Zaparoo.sh` existe y es ejecutable, pero llama a `/userdata/system/zaparoo`, que no existe.

## 3. COSAS SOSPECHOSAS QUE CONVIENE REVISAR

- **DUPLICATE / MANUAL_REVIEW — SOSPECHOSO:** 705 grupos de nombres gamelist repetidos en paths diferentes (812 registros por encima de uno por grupo). Hay muchos casos de discos, regiones, revisiones, variantes de MAME o productos distintos con el mismo nombre mostrado. Ejemplos comprobados: Shenmue por discos en Dreamcast; ChuChu Rocket! en dos dumps/regiones; Teenage Mutant Ninja Turtles con `tmnt.zip` y `pc_tmnt.zip` en MAME; Dino Crisis en variantes española y general en PSX. Esto no confirma ROMs duplicadas byte a byte.
- **MANUAL_REVIEW — SOSPECHOSO:** `SuperTuxKart.sh` figura en el gamelist, existe y contiene un launcher hacia `.data/SuperTuxKart/run_game.sh`; el script no tiene permiso de ejecución (`-rw-r--r--`). Los binarios/assets locales de SuperTuxKart sí están presentes. No se probó si el flujo personalizado lo invoca mediante intérprete.
- **SUSPICIOUS_EXTENSION — MANUAL_REVIEW:** `Cannonball.cannonball.disabled` es un archivo presente que no se acepta como ROM activa por la extensión configurada. `_info.txt` describe expresamente ese nombre como archivo que debe renombrarse cuando se instalen los datos requeridos; aquí no se cambió.
- **MANUAL_REVIEW:** existen cuatro directorios de primer nivel no identificados como nombre de sistema: `Nueva carpeta`, `Nueva carpeta (2)`, `iortcw` y `xbox_interno_backup`. Los dos primeros solo tienen subdirectorios vacíos de media; `iortcw` contiene un directorio `main` pequeño; `xbox_interno_backup` solo contiene `_info.txt` y directorios de media. No se infiere que deban borrarse.
- **SUSPICIOUS_EXTENSION / MANUAL_REVIEW:** `/userdata/roms/Descargas - Acceso directo.lnk` está directamente en la raíz de ROMs, fuera de un sistema. No se abrió.
- **ORPHAN_MEDIA — CONFIRMADO respecto de gamelists, revisar antes de considerar descartable:** 3.571 archivos bajo carpetas estándar de media no son referenciados por los XML. Los mayores grupos son MAME, Dreamcast, N64 y PS2. Muchos son videos/fanart de catálogo; no se borró ninguno.
- **MULTIDISK — SOSPECHOSO:** hay referencias multidisco ausentes para Dino Crisis y Dino Crisis 2 aunque los paths principales `.chd` están presentes. Se desconoce si la metadata antigua afecta a la selección; no se lanzó el juego.

## 4. COSAS QUE PUEDEN IGNORARSE

No se recomienda intervenir por estos hallazgos estructurales aislados:

- Los seis registros DevilutionX sin nombre son entradas ocultas de recursos adicionales; son referencias ausentes confirmadas, pero no juegos visibles ni prueba de fallo del juego base.
- Los siete CHD de PSX que no aparecen como `<path>` individual están referenciados en `<multidisk>` de las entradas M3U de Final Fantasy VII, Metal Gear Solid y Parasite Eve II.
- Los 30 archivos de cero bytes incluyen sentinelas/archivos de lanzamiento habituales como `.game`, `.sdlpop`, `.odc`, `.scummvm`, `.keep` y `__init__.py`. No deben tratarse todos como archivos dañados. Los `.air` vacíos de Ikemen y el `.ps4` vacío de L.A. Noire quedan para revisión del paquete, sin concluir que estén rotos.
- Los 826 directorios vacíos incluyen gran cantidad de carpetas `images`, `videos` y `manuals` preparadas por sistema; también hay directorios de estado como `mame/kinst` y `ps4/DLC`. Su existencia vacía no es un error por sí sola.
- Media huérfana significa no citada en campos/path conocidos de gamelist; no implica que ningún theme, scraper anterior o launcher la use.

## 5. ROMS HUÉRFANAS

- **ORPHAN_ROM confirmadas: 0** después de considerar paths principales, directorios de juego y referencias `<multidisk>`.
- La comparación inicial de archivos elegibles contra `<path>` directo produjo siete candidatos PSX sin entrada individual. La inspección del XML mostró que los siete están explícitamente mencionados por `<multidisk>` de tres M3U; por eso no se clasifican como huérfanos.
- Dos referencias multidisc (Dino Crisis y Dino Crisis 2) apuntan a BIN ausentes, detalladas en referencias rotas.
- Recuento físico mecánico: 9.030 archivos de sufijos aceptados por la configuración de sistema; 734 están en subdirectorios y pueden ser archivos internos de paquetes. No se calcularon hashes ni se comprobó integridad interna de ZIP/ISO/CHD.

## 6. MEDIA HUÉRFANA

Total actual sin referencia en los campos de gamelist revisados: **3.571 de 33.811 archivos** bajo carpetas estándar de media. No se borró ni movió nada. La tabla da cantidad por sistema y ejemplos abreviados; “huérfana” aquí solo describe ausencia de referencia XML.

| Sistema | Sin referencia | Ejemplos de ruta relativa |
|---|---:|---|
| mame | 1.144 | videos/aceattac-video.mp4; videos/pzloop2-video.mp4 |
| dreamcast | 1.086 | videos/Neo XYX-video.mp4; videos/Leona's Tricky Adventures-video.mp4 |
| n64 | 912 | videos/Super Robot Wars 64-video.mp4; images/Top Gear Hyper-Bike-marquee.png |
| ps2 | 186 | videos/Fatal Frame II Crimson Butterfly-video.mp4; videos/Wacky Races-video.mp4 |
| fbneo | 64 | videos/ddtodr1-video.mp4; videos/avspu-video.mp4 |
| gba | 28 | images/Pokemon Red Chapter-image.png; images/Pokemon Orange Island-image.png |
| megadrive | 22 | images/Uwol_Quest_For_Money.png; images/Golden Axe-fanart.jpg |
| solarus | 13 | videos/osanas-revenge.mp4; manuals/osanas-revenge-manual.pdf |
| windows | 12 | videos/Ri-li.mkv; videos/Evil Dead Redux.mp4 |
| nes | 11 | images/Blade Buster-marquee.png; images/ninja-4-seasons.jpg |
| psx | 8 | videos/Dino Crisis (Spain)-video.mp4; images/Tekken 3 (USA)-image.png |
| openbor | 7 | videos/he-man.mp4; manuals/gudule-manual.pdf |
| theforceengine | 7 | images/Operation Kyber Crystal - 2 Spaceport-image.png |
| gbc | 6 | videos/quartet.mp4; manuals/ucity_manual.pdf |
| saturn | 6 | images/Cubecat-thumb.jpg; images/HELLSLAVE-boxback.png |
| tic80 | 6 | manuals/8bit-panda-manual.pdf; images/SecretAgents.png |
| gb | 5 | manuals/Retroid-manual.pdf; manuals/Into the Blue-manual.pdf |
| ports | 5 | images/NOX-retro-games - Snake-image.png; images/Zaparoo-image.png |
| easyrpg | 4 | videos/Ib.mp4; videos/WitchsHeart.mp4 |
| neogeo | 4 | videos/mosyougi-video.mp4; images/mosyougi-image.png |
| scummvm | 4 | manuals/Beneath_a_Steel_Sky-manual.pdf; images/Beneath_a_Steel_Sky.jpg |
| xbox | 4 | videos/FableThe Lost Chapters-video.mp4; images/FableThe Lost Chapters-image.png |
| c64 | 3 | images/fix_it_felix_64-marquee.png; images/LASEREGL_artwork.png |
| ikemen | 3 | videos/King of Fighters Shining Go.mp4; images/Famicom-Fighters.gif |
| psp | 3 | videos/silveredge.mp4; manuals/silveredge-manual.pdf |
| snes | 3 | videos/Super Boss Gaiden.mp4; manuals/Super Boss Gaiden-manual.pdf |
| atari2600 | 2 | images/Halo2600.jpg; images/Amoeba_jump.png |
| mrboom | 2 | images/MrBoom-marquee.png; images/MrBoom-thumb.png |
| nds | 2 | manuals/MegaETk-manual.pdf; images/MegaETk.png |
| sdlpop | 2 | images/sdlpop-thumb.jpg; images/sdlpop-fanart.jpg |
| xrick | 2 | videos/xrick.mp4; images/xrick.png |
| cannonball | 1 | images/cannonball.png |
| cdogs | 1 | images/cdogs.png |
| hcl | 1 | images/hcl.png |
| hurrican | 1 | images/hurrican.png |
| superbroswar | 1 | images/supermariowar-image.png |

## 7. REFERENCIAS ROTAS

Los 19 casos son instancias de referencia, no 19 juegos distintos:

- **9 paths principales ausentes:**
  - Cannonball: `./Cannonball.cannonball`.
  - DevilutionX: `./diabdat.mpq`, `./hellfire.mpq`, `./fonts.mpq`, `./hfmonk.mpq`, `./hfmusic.mpq`, `./hfvoice.mpq`, `./pl.mpq`, `./ru.mpq`.
- **2 metadata multidisk ausentes en PSX:** Dino Crisis → `./(PS1) Dino Crisis [PAL] [SLES-02211].bin`; Dino Crisis 2 → `./(PS1) Dino Crisis 2 [PAL] [SLES-03225] (Track 2).bin`.
- **7 referencias de media a archivos ausentes:** 4 imágenes (2 PS2, 2 GBA), 2 marquees (C64 y Cannonball) y 1 thumbnail (Cannonball).
- **1 referencia con case mismatch:** Cannonball pide `images/Cannonball.png`; existe `images/cannonball.png`.
- **0 referencias de video ausentes; 0 referencias de manual ausentes.**
- **0 paths vacíos, absolutos o que contengan `../`; 0 referencias duplicadas al mismo path de juego.**

## 8. ARCHIVOS VACÍOS

Hay **30 archivos regulares de cero bytes**. La lista actual:

- MAME: siete `.keep` en `mame2003/{diff,inp,cfg,memcard,hi,snap,nvram}`.
- ScummVM: `Drascula_The_Vampire_Strikes_Back_ES/drascula.scummvm`, `Beneath_a_Steel_Sky/sky.scummvm`, `Flight_of_the_Amazon_Queen/queen.scummvm`.
- PS4: `CUSA09172/L.A. Noire.ps4`.
- Ikemen: `King of Fighters Shining Go.ikemen/Ikemen.log`, `King of Fighters Shining Go.ikemen/data/common.air`, `King of Fighters Shining Go.ikemen/external/mods/.keep`, cuatro archivos de texto vacíos bajo `chars/Kula`, `chars/Fliz`, `chars/yagamiAKOF`, `chars/kyo_XI`; `Famicom-Fighters.ikemen/data/common.air`, `Famicom-Fighters.ikemen/data/FCF/common.air` y `Famicom-Fighters.ikemen/external/mods/.keep`. Conteo de Ikemen: 10.
- Ports/NOX: `nox-retro-games-snake/game/__init__.py`, `nox-retro-games-snake/game/screens/__init__.py`.
- Lanzadores/markers: `hcl/hcl.game`, `hurrican/hurrican.game`, `cdogs/cdogs.game`, `sdlpop/sdlpop.sdlpop`, `odcommander/od-commander.odc`, `superbroswar/smw.game`, `moonlight/.keep`.

Los nombres `.game`, `.odc`, `.scummvm`, `.sdlpop`, `.ps4` y `.keep` pueden operar como sentinelas. Los `common.air` vacíos de Ikemen y el `.ps4` de L.A. Noire requieren revisión de contenido/convención antes de llamarlos corruptos. Ninguno fue abierto ni cambiado.

## 9. SYMLINKS ROTOS

Se detectaron **64 enlaces colgantes** dentro de perfiles Wine; todos apuntan a dispositivos seriales ausentes `/dev/ttyS0` a `/dev/ttyS31`:

- `/userdata/roms/windows/Diablo II.wine/dosdevices/com1` a `com32`: 32 enlaces.
- `/userdata/roms/windows/TMNT Rescue-Palooza.Wine/dosdevices/com1` a `com32`: 32 enlaces. Incluye los reportados `dosdevices/com31` y `dosdevices/com8`.

Son mappings `COMn` de Wine. Su ausencia confirma el estado colgante del enlace, pero no demuestra impacto en esos juegos; requieren un juego que use puerto serial para determinar impacto. No se modificó ningún enlace.

## 10. PORTS Y LAUNCHERS

El sistema `ports` tiene seis registros visibles en gamelist. El comando configurado pasa por `controller_dispatcher`; no se ejecutó.

- **Zaparoo:** `Zaparoo.sh` existe y tiene permiso ejecutable. Su dependencia `/userdata/system/zaparoo` falta: **BROKEN_LAUNCHER confirmado**.
- **SuperTuxKart:** `SuperTuxKart.sh` existe pero su modo es `0644` sin bit ejecutable. El árbol `.data/SuperTuxKart`, `run_game.sh`, binario x86_64 y carpeta de assets existen. **SOSPECHOSO**, no probado por el launcher/runtime.
- **N64RecompLauncher:** entrada `N64RecompLauncher/N64RecompLauncher.sh`, script y binario existen y son ejecutables. También existen `libSkiaSharp.so`, `libHarfBuzzSharp.so` y `libSDL2.so`, `games.json` y `settings.json`. `RecompiledGames` está vacío. El script ejecutaría `chmod +x N64RecompLauncher` al iniciarse; no se ejecutó. El launcher está presente, pero no hay juegos recompiled en esa carpeta.
- **Steam:** `Steam Latino.sh` y `Steam Espa?ol.sh` existen y son ejecutables. Flatpak informa instalado `app/com.valvesoftware.Steam/x86_64/stable`. No se abrió Steam.
- **NOX retro games - Snake:** launcher ejecutable presente; el path fijo `/userdata/roms/ports/nox-retro-games-snake` y `main.py` existen; Python 3 está instalado. No se importaron módulos ni se ejecutó el juego, así que la disponibilidad de dependencias Python queda sin determinar.
- No se encontraron otros paths locales ausentes confirmados en las seis entradas de Ports revisadas. La presencia de scripts/binarios no equivale a prueba funcional.

## 11. BIOS

- Archivos en `/userdata/bios`: 454 archivos regulares a profundidad máxima 2 en el conteo realizado; cero archivos vacíos en ese mismo alcance.
- Una tabla local anterior enumera 26 paths BIOS/firmware para un subconjunto de sistemas. **Los 26 paths existen actualmente**. No se revalidaron checksums y la tabla no cubre todos los sistemas.
- No hay un comprobador BIOS local identificado en los comandos del sistema consultados. La ayuda de `batocera-es-swissknife` no incluye esa función.
- **MISSING_BIOS confirmado: 0.** Esto significa que no apareció una ausencia demostrable en el conjunto acotado; no certifica toda la lista de requisitos de todos los cores.
- **BIOS presente:** los 26 paths del subconjunto anterior están presentes como archivos; que sean binarios correctos no se determinó ahora.
- **BIOS sospechosa:** ninguna identificada con evidencia actual suficiente.
- **NO DETERMINABLE SIN EJECUTAR EL JUEGO / SIN MATRIZ AUTORITATIVA:** si todas las BIOS exactas y versiones requeridas por cada sistema/core están presentes y son válidas. No se lanzó ningún juego ni se calcularon hashes BIOS.

## 12. ESTADO ACTUAL DE CANNONBALL

El sistema está definido con extensión `.cannonball` y core `cannonball`. El gamelist muestra una entrada, pero su path principal `Cannonball.cannonball` falta. Solo está `Cannonball.cannonball.disabled` (25 bytes). El `_info.txt` del sistema indica que se requieren los ROMs MAME de OutRun rev. B y que el archivo debe llamarse `.cannonball`. La imagen existente está en minúsculas y no coincide con el case del XML; también faltan marquee y thumbnail. El video referenciado sí existe. **Catálogo estructural: incompleto confirmado. Funcionamiento: no probado.**

## 13. ESTADO ACTUAL DE DEVILUTIONX

La definición usa extensión `.mpq` y core `devilutionx`. El directorio contiene gamelist, `_info.txt` e imagen; no hay archivos MPQ. Faltan los ocho paths listados arriba. El archivo base requerido por `_info.txt`, `diabdat.mpq`, falta, por lo que los datos del juego base no están disponibles en el path esperado. Hellfire y sus recursos son expansión; fonts y packs de voz son condicionales. **Catálogo estructural: contenido de juego ausente confirmado. Funcionamiento: no probado.**

## 14. ESTADO DE STEAM / N64RECOMPLAUNCHER / NOX

- **Steam:** Flatpak instalado y ambos scripts existen con permiso ejecutable; estado de inicio no determinado.
- **N64RecompLauncher:** launcher, binario y bibliotecas locales presentes; `RecompiledGames` vacío. Sin juegos compilados visibles allí. Inicio no probado.
- **NOX retro games - Snake:** shell launcher y `main.py` presentes; ruta local válida y Python 3 presente. Dependencias Python y ejecución no comprobadas.
- **SuperTuxKart:** archivos de juego y ejecutables presentes; launcher sin bit ejecutable, sospechoso pendiente de prueba controlada en una etapa funcional futura.
- **Zaparoo:** dependencia ejecutable local ausente; launcher roto confirmado en inspección estática.

## 15. DIFERENCIAS RESPECTO DE LOS PROBLEMAS CONOCIDOS ANTERIORES

- El reporte del 2026-09-25 registraba 8.432 entradas y nueve paths de juego ausentes. Ahora se midieron 8.433 registros totales (uno más) y siguen faltando exactamente los mismos nueve paths principales: Cannonball y ocho DevilutionX.
- Las cuatro imágenes que el informe del 2026-09-26 identificó como corruptas y retiró siguen ausentes de sus paths activos y todavía están referenciadas en PS2/GBA.
- Se identificaron además dos marquees ausentes (C64 y Cannonball), un thumbnail ausente (Cannonball) y una referencia de imagen Cannonball que difiere solo por mayúsculas del archivo presente.
- El análisis de campos `<multidisk>` encontró dos referencias BIN ausentes en PSX que no estaban incluidas en la cuenta de paths principales. Los siete CHD multidisco antes candidatos a huérfanos sí están referenciados indirectamente.
- El número de huérfanos de media anterior no se reutilizó: el nuevo recuento incluye `fanart` y da 3.571 archivos sin referencia gamelist.
- El material de `/userdata/auditoria_consolas/` es una preparación anterior fechada 2026-07-31 (`PREPARED`, sin juegos lanzados); no es un resultado funcional actual. Se inspeccionó, no se ejecutó.

## 16. ELEMENTOS QUE NECESITAN PRUEBA REAL DEL JUEGO

No se asignó PASS/FAIL a ningún juego. Requieren pruebas futuras desde EmulationStation, conforme al alcance separado:

- Cannonball, DevilutionX, los launchers de Ports y los sistemas con paquetes/archivos de juego en carpeta.
- Los 705 grupos con nombres repetidos para decidir si son revisiones/regiones/discos intencionales o entradas redundantes.
- Dino Crisis y Dino Crisis 2 para determinar si la metadata multidisc ausente afecta el uso del CHD principal.
- Los sistemas cuya BIOS/firmware exacta no puede validarse con una matriz autoritativa local.
- El uso que los juegos hacen de los 64 mappings seriales Wine colgantes.
- No se determinó arranque, sonido, imagen en ejecución, controles ni rendimiento de ningún título.

## 17. SIGUIENTE PASO RECOMENDADO

Conservar este informe como baseline de solo lectura. Para una etapa siguiente, priorizar una revisión manual de los casos visibles con contenido ausente (Cannonball y DevilutionX), luego las referencias de media/case y los dos metadatos multidisc PSX. Revisar el launcher Zaparoo y el permiso de SuperTuxKart por inspección antes de cualquier cambio. Mantener intactos los 3.571 medios sin referencia hasta identificar si otra parte del runtime los usa. Realizar la auditoría funcional por separado y registrar PASS/FAIL/NEEDS_TEST solo después de pruebas reales autorizadas desde EmulationStation.

## Registro de cambios de esta auditoría

- Qué se encontró: estado actual detallado en este informe.
- Qué se cambió en ROMs/gamelists/media/configuración/runtime: nada.
- Qué pruebas se hicieron: consultas de versión/montaje/configuración; parseo estático de 51 XML; lectura de paths/atributos de metadata; conteos de archivos, tamaños, permisos, directorios y symlinks; inspección estática de scripts y dependencias locales.
- Resultado: XML válidos; nueve paths principales de juego ausentes; dos referencias multidisc ausentes; media referenciada ausente o con case mismatch; un launcher con dependencia local ausente; ningún juego ejecutado.
- Estado: diagnóstico estructural completado con límites señalados para BIOS e integridad binaria completa de media.
