# AUDITORÍA ARCADE — FASE 1: INVENTARIO Y METADATA

Fecha de extracción: 2026-11-12T22:51:33-03:00

## Estado general

- MAME: 1308 ROM ZIP de juego en el inventario actual.
- FBNeo: 89 ROM ZIP de juego en el inventario actual.
- Total MAME + FBNeo: 1397.
- Soporte excluido del conteo de juegos: MAME 16 ZIP, FBNeo 15 ZIP (BIOS/dispositivos/plataformas u otros sets de soporte; detalle en `arcade_support_assets.csv`).
- Arranques históricos vigentes: 1147 PASS y 11 FAIL; 239 NOT_TESTED, incluyendo harness TEST_ERROR anterior, sin contarlo como fallo.
- Input directo estimado por metadata: 874/1397 (62.6%); no es porcentaje de input validado.
- Más de 6 botones: 2; metadata de control especial/no compatible con esta botonera: 150.
- Sets con `players=4`: 121, de ellos 107 con joystick/botones dentro de capacidad. Simultaneidad no está codificada en el XML; 4P físico confirmado: 0.
- ROMset/BIOS contrastables con static audit previo sin cambios detectables: 1170/1397; estados detallados por juego en CSV.
- Metadata: MAME controls/clone metadata: mame2003-plus.xml (legacy core metadata); FBNeo DAT supplies set/clone names but no control section, so unjoined FBNeo input is UNKNOWN.
- Dispatcher SHA-256: `a60be89fb45ea27ec4f7c3f546e088c7ff3da140bccfe1c6a37e5b14ec581c45`.
- ROMset/BIOS status reutilizado sólo si el ZIP actual coincide en tamaño y mtime no es posterior al baseline estático del 1 de octubre; el resto queda UNKNOWN_OR_STALE.

## Cores y configuración

| Sistema | Emulador | Core | Core presente | Dispatcher |
| --- | --- | --- | --- | --- |
| mame | libretro | mame078plus | True | True |
| fbneo | libretro | fbneo | True | True |


## Boot histórico reutilizable por sistema

| Sistema | Total | PASS | FAIL | Pendiente |
| --- | --- | --- | --- | --- |
| mame | 1308 | 1075 | 11 | 222 |
| fbneo | 89 | 72 | 0 | 17 |

## Asignación actual conocida desde configuración técnica

| Jugador | Puerto | by-path |
| --- | --- | --- |
| P1 | 5 | /dev/input/by-path/pci-0000:00:14.0-usb-0:5:1.0-event-joystick |
| P2 | 6 | /dev/input/by-path/pci-0000:00:14.0-usb-0:6:1.0-event-joystick |
| P3 | 8 | /dev/input/by-path/pci-0000:00:14.0-usb-0:8:1.0-event-joystick |
| P4 | 7 | /dev/input/by-path/pci-0000:00:14.0-usb-0:7:1.0-event-joystick |


La enumeración kernel y el diagnóstico SDL previo coinciden con USB5/USB6/USB8/USB7 para P1-P4 respectivamente. Eso valida entrada al dispatcher, no el orden de jugadores dentro de cada juego/core.

## Compatibilidad por metadata

| Clasificación | Cantidad |
| --- | --- |
| COMPATIBLE_CON_VALIDACION | 19 |
| COMPATIBLE_DIRECTO_METADATA | 874 |
| INPUT_REVIEW_METADATA_INCOMPLETA | 291 |
| NO_COMPATIBLE_CON_BOTONERA | 150 |
| PARCIAL_CONTROL_STICK_ANALOGICO_O_ESPECIAL | 44 |
| PARCIAL_DUAL_STICK | 17 |
| PARCIAL_MAS_DE_4_JUGADORES | 2 |


## Ultimate Mortal Kombat 3

- `mame/umk3.zip`: 2 jugadores, joystick 8-way, 6 botones; core por defecto `mame078plus`; boot histórico `BOOT_OK` el 2026-10-07.
- Existe CFG por juego (`saves/mame/mame2003-plus/cfg/umk3.cfg`); hash igual al CFG de `mk3.cfg`: `True`. Formato binario: no se decodificaron bindings; no hay evidencia para confirmar ni descartar duplicación. Requiere prueba física.

El XML disponible es MAME 2003 Plus; el MAME configurado en EmulationStation es mame078plus. Se usa sólo como referencia de controls/players/clones, con ese desfase explícito. FBNeo no tiene input tags en el DAT suministrado.

## Limitación y continuación

- Pruebas históricas reusadas sólo si el ZIP actual no tiene mtime posterior a `tested_at`; no se reejecutan sin necesidad.
- No se envió input dentro de los juegos. No se confirma aún que cada juego permanezca abierto ni que los bindings sean correctos.
- Smoke test nuevo pausado antes del primer lanzamiento: el arranque/cierre puede guardar NVRAM o save data automáticamente y no se demostró un modo que lo impida sin cambiar el runtime.
- Checkpoint: `checkpoint.json`; lote previsto: 10 juegos y continuar sólo desde estado idle confirmado.
- Los archivos de controles por acción no están en la metadata disponible; una CFG por juego no demuestra que los bindings difieran del valor base. Las duplicaciones requieren prueba física.

## MAME

- 1308 sets de juego; core por defecto `mame078plus`, presente; dispatcher configurado.
- Historial vigente: 1075 BOOT_OK, 11 FAIL_BOOT, 222 sin prueba vigente.

## FBNeo

- 89 sets de juego; core `fbneo`, presente; dispatcher configurado.
- Historial vigente: 72 BOOT_OK, 0 FAIL_BOOT, 17 sin prueba vigente.

## Compatibilidad de botonera

- 874 sets son candidatos directos por metadata, con joystick y hasta 6 botones; falta prueba física por jugador.
- 2 sets reportan más de 6 botones; 150 necesitan control especial; 291 entradas no tienen metadata input concluyente.

## 4 jugadores

- 121 sets reportan máximo 4 jugadores; 107 cumplen capacidad estimada de la botonera. El DAT no distingue simultáneo/alternado y no hay 4P físico confirmado.

## Pelea y controles especiales

- 27 entradas clasificadas por nombre como juegos de pelea; UMK3 queda para prueba manual.
- Listado de controles especiales: `ARCADE_SPECIAL_CONTROLS.md`.

## Fallos

- 11 fallos de arranque históricos: CHD requerido ausente confirmado por log: 7, salida inmediata; dependencia/causa sin log concluyente: 4. Ver `ARCADE_FAILURES.md`.

## Duplicados MAME / FBNeo

- 13 sets están en ambos sistemas; `ARCADE_DUPLICATES_MAME_FBNEO.md` indica INDISTINTO sólo cuando el historial de ambos y metadata coinciden.

## Validación manual pendiente

- Muestra priorizada de 20 juegos en `ARCADE_MANUAL_TESTS.md`.

## Recomendaciones

- No cambiar mappings/core por ahora. Confirmar primero si smoke tests pueden ejecutarse sin tocar NVRAM/saves; después priorizar pendientes y validación manual.
## Otros sistemas arcade detectados (fuera del smoke test prioritario)

| Sistema | ZIP | CHD | Acción |
| --- | --- | --- | --- |
| neogeo | 105 | 0 | inventariar después; sin smoke test |
| atomiswave | 0 | 0 | inventariar después; sin smoke test |
| naomi | 1 | 0 | inventariar después; sin smoke test |
| model2 | 0 | 0 | inventariar después; sin smoke test |
| model3 | 0 | 0 | inventariar después; sin smoke test |


No se probaron automáticamente otros sistemas arcade en esta fase.

## Smoke tests — estado acumulado

- Total inventariado: 1397; PASS: 1182; FAIL/TIMEOUT: 215; NOT_TESTED: 0; input manual pendiente: 0.
- No se inyectaron pulsaciones. PASS sólo confirma que el core permaneció abierto en la ventana y volvió a ES.
- Clasificación input por metadata: COMPATIBLE_CON_VALIDACION=19, COMPATIBLE_DIRECTO_METADATA=874, INPUT_REVIEW_METADATA_INCOMPLETA=291, NO_COMPATIBLE_CON_BOTONERA=150, PARCIAL_CONTROL_STICK_ANALOGICO_O_ESPECIAL=44, PARCIAL_DUAL_STICK=17, PARCIAL_MAS_DE_4_JUGADORES=2.


## Reconciliación posterior — MAME BATCH 5 (2026-11-15)

Este apéndice actualiza el conteo global sin alterar las cifras históricas fechadas de la Fase 1. Con las fuentes actuales: `BOOT_OK_DEFAULT_CORE` (mame078plus) = 1094, `BOOT_OK_MAME_CURRENT` = 18, `BOOT_OK_FBNEO` = 88, `TOTAL_UNIQUE_BOOT_OK` = 1200 (unión por sistema/ROM, 0 solapamientos). BATCH 5 añadió `kov2p` y `martmast` con PASS y restore verificado. Ver `ARCADE_MAME_BATCH5_RESULTS.md`.
