# Próximo lote seguro de MAME: sin candidatos elegibles

Fecha de reconciliación: 2026-11-15.
Modo: análisis solamente. No se lanzaron juegos ni se modificaron configuraciones, cores, ROMs, mappings, saves o BIOS.

## Resultado

**Lote principal: 0/20. Lote de reserva: 0/20.** No hay juegos que cumplan simultáneamente los criterios y, en particular, la exclusión de todo juego ya lanzado. No rellené las listas con juegos repetidos.

El inventario `arcade_games_audit.csv` tiene 1.397 filas y las 1.397 registran un estado/fecha de intento. El smoke/checkpoint contiene 239 resultados (239 ROMs únicas). El inventario base registra 1.147 BOOT_OK históricos y 11 fallos históricos; los 239 restantes se intentaron en el smoke. Los 61 juegos con `recommended_action=USE_MAME_CORE_X` en `arcade_core_compatibility.csv` fueron todos lanzados anteriormente con el core default (`GAME_DRIVER_NOT_FOUND`). De esos 61, cinco tienen PASS en BATCH 1; los otros 56 no tienen piloto MAME actual, pero ya fueron lanzados con `mame078plus` y por tu regla también quedan excluidos. Los juegos de BATCH 2 y los nueve overrides actuales también quedan excluidos por historial y/o PASS.

Esto hace incompatible pedir un lote de 20 que sean rechazos exclusivos de `mame078plus` y, a la vez, excluir cualquier juego lanzado antes. La resolución segura bajo las reglas actuales es no recomendar repeticiones. Para que exista un siguiente lote habrá que levantar explícitamente la exclusión de intentos previos para un subconjunto de los 56 estáticos sin piloto, o incorporar nuevos juegos que todavía no estén en el inventario auditado.

## Resumen de elegibilidad y confianza

| Medida | Cantidad |
|---|---:|
| VERY_HIGH_CONFIDENCE elegibles | 0 |
| HIGH_CONFIDENCE elegibles | 0 |
| MEDIUM_CONFIDENCE elegibles | 0 |
| Principal | 0 de 20 |
| Reserva | 0 de 20 |
| Juegos con `USE_MAME_CORE_X` estático | 61 |
| De esos, no probados aún con MAME actual | 56 |
| De esos, ya intentados con core default y por tanto excluidos | 61 |
| Filas del inventario con intento/estado previo | 1397 de 1397 |
| Intentos únicos del checkpoint de smoke | 239 |

Las etiquetas `HIGH_STATIC` del CSV son una recomendación estática, no una categoría de elegibilidad actual ni un PASS. No se convierten en candidatos mientras rija la exclusión de juegos ya lanzados. Además, `BIOS UNKNOWN_STATIC` significa que la auditoría no verificó BIOS exhaustivamente; no equivale a “BIOS confirmada presente”.

## Lote principal (20)

Sin filas elegibles. No se propone ningún juego.

## Lote de reserva (20)

Sin filas elegibles. No se propone ningún juego.

## Controles y prioridades para un lote elegible

- Principal compatible con gabinete: 0; reserva compatible: 0.
- DIRECT_COMPATIBLE en el lote: 0.
- MANUAL_VALIDATE en el lote: 0.
- SPECIAL_CONTROL en el lote: 0.
- Juegos 3P/4P elegibles: 0. No hay candidatos seguros nuevos para validar P1-P4.
- Fighting elegibles con hasta seis botones: 0. `kinstb` (Killer Instinct, 2P/6B) aparece en el pool estático de compatibilidad, pero ya fue lanzado bajo el core default y se excluye.
- No se priorizaron juegos de trackball, spinner, lightgun, pedales, volante, dual-stick o analógico especial.

## Grupos aparte excluidos

Estas listas conservan los casos conocidos para una etapa posterior; no son un lote y no implican reparación ni relanzamiento.

### A. CHD faltante o requerido ausente

Conteo fuente: 22 sets de la tabla de CHD requerido ausente + 10 casos históricos confirmados en logs; 32 nombres únicos entre ambos apartados.

**Metadata actual (`ARCADE_CHD_MISSING.md`, 22):** darkhleg, dsftkd, dstage, fbait2bc, fbaitbc, fbaitmc, gauntdl, gauntleg, gtrfrk2m, gtrfrks, hyperath, hyprdriv, jojo, nagano98, qdrmfgp, qdrmfgp2, redearth, salarymc, simpbowl, tenthdeg, vaportrx, weddingr.

**Históricos en logs (10):** area51mx, blitz, blitz2k, blitz99, calspeed, carnevil, cryptklr, maxforce, sfrush, wg3dh.

La tabla base es estática y no demuestra por sí sola el fallo de boot; BATCH 2 confirma por log `redearth`, `jojo` y `hyperath`. `jojo` también tiene un archivo de ROM requerido ausente.

### B. Dependencia, BIOS o archivos requeridos ausentes/no localizados

**ROMOF/parent no localizado (10):**

| Set | Parent / ROMOF no localizado |
|---|---|
| aerofgts | coh1002v |
| bigdeal | bonuscrd |
| bldyror2 | coh1002e |
| cbaj | coh1002m |
| flamegun | coh1002m |
| glpracr3 | coh1002m |
| hvnsgate | coh1001l |
| mfjump | coh1002m |
| shngmtkb | coh1002m |
| tblkkuzu | coh1002m |

**Dependencias/ROM documentadas directamente (3):** `armwar` (armwar.key, 20 bytes), `ssf2t` (ssf2t.key, 20 bytes), `polepos` (pp3_6.4l, pp3_28.1f, pp3_25.1n, pp3_26.1m, pp3-6.6m, pp2_11.2e, pp2_12.2f, pp2_13.1e).

**Contenido requerido observado en BATCH 2 (3):** `mvp` (317-0143.key y 315-5298.b9), `nbapbp` (778b01.27p y security_eeprom_uab), `jojoba` (miembros jojoba-simm5.0 a jojoba-simm5.7). Se solapa con “ROMSET dudoso” y CHD cuando corresponda.

No hay una lista de BIOS confirmadas ausentes en los 61 `USE_MAME_CORE_X`; en esos registros figura `UNKNOWN_STATIC`, por lo que no se atribuye confianza de BIOS verificada.

### C. ROMSET dudoso

Conteos del CSV de compatibilidad: 88 `PARTIAL_CRC_MATCH_UNRESOLVED`, 11 `NO_CURRENT_MAME_CRC_MATCH` y 2 `SET_MATCH_CRC_SIZE_METADATA` (101 registros). Esta última clase sólo coincide por metadata/tamaño, no por CRC completo.

**CRC parcial (88):** aerofgts, alpinr2b, ar_ldrb, ar_ninj, ar_sprg, bigdeal, bldyror2, buggyboy, casino5, cbaj, cball, cmast91, dacholer, ddux, dsftkd, dynwar, evosocc, finalapr, fishfren, fiveside, flamegun, freezeat, funcube4, galastrm, gauntdl, gauntleg, gekisou, gloc, glpracr3, gprider, gradius4, gtrfrk2m, hoops95, hvnsgate, hyperath, hyprdriv, invasnab, jockeygp, jolyjokr, kov2, kov2p, martmast, megat3, mf_bdash, mfjump, misncrft, mk4, nagano98, nbapbp, pasha2, pdrift, pitboss, pitbossm, radikalb, rdft, rdft2, rfjet, ridgerac, salarymc, scorpion, senkyu, sfbonus, sfiii2n, sfiii3n, sfruitb, sfzch, shngmtkb, sidebs, sidebs2, simpbowl, speedrcr, speedup, sqix, starsldr, strtdriv, suplup, surfplnt, svg, tblkkuzu, terabrst, theglad, tm4k, tm7k, twinbrat, tx1, viprp1, weddingr, witch.

**Sin CRC coincidente con MAME actual (11):** act2000, darkhleg, dstage, fbait2bc, fbaitbc, fbaitmc, gtrfrks, jojo, jojoba, konam80s, sfiiin.

**Coincidencia sólo por set/tamaño/metadata (2):** mvp, sia2650.

`jojoba` además tuvo fallo de ROMSET confirmado en BATCH 2.

### D. Crashes históricos

Dos casos en `ARCADE_CRASH_CASES.md`: `mvp` y `sia2650` con SIGSEGV en `mame078plus`. Ya no se deben presentar ambos como crashes actuales del target: BATCH 2 clasificó `mvp` como MISSING_CONTENT y `sia2650` como BOOT_OK con override. Ambos siguen excluidos por historial/prueba anterior.

### E. UNKNOWN / dispatch no confirmado

**Soporte/driver desconocido en compatibilidad (14):** alpinesa, connect4, dealem, goodejaa, gt103, gt103a, m_bdrwho, mpu4met0, mpu4tst2, mpu4utst, pbball96, pbballex, ssf2ghw, tecmowcm.

**Smoke con retorno a ES sin dispatch de RetroArch confirmado (18 resultados; 17 shortnames únicos por repetición de `taitotz`):** taitotz, aleck64, alg_bios, ar_bios, atarisy1, atluspsx, atpsx, bctvidbs, crysbios, galgbios, konamigv, kviper, maxaflex, psarc95, sys573, taitogn, taitotz, vspsx.

No se recomienda inferir “core incompatible” ni lanzar override desde estos estados sin evidencia adicional.

### F. Controles especiales

El CSV marca `SPECIAL_CONTROL` en 89 registros: act2000, big10, bigappg, bigdeal, buggyboy, casino5, cball, cclownz, cd32, cmast91, cmaster, cmv4, comg076, comg128, coronatn, cubeqst, fbait2bc, fbaitbc, fbaitmc, finalapr, fiveside, fredmem, funcube4, gepoker, ghlpanic, gldncrwn, gprider, gs4002, gtrfrk2m, gtrfrks, guab, hyprdriv, invasnab, jokpoker, jolyjokr, ladylinr, megat3, mf_bdash, midnrun, monopldx, monopoly, ncb3, pacapp2, pacappsp, paradice, pasha2, pdrift, pitboss, pitbossm, pocketrc, poker41, pokio, pulltabs, pyramid, qdrmfgp, qdrmfgp2, qntoond, quintoon, radikalb, rcasino, re900, ridgerac, salarymc, schery97, screenpl, sfbonus, sfruitb, sidebs, sidebs2, sidewndr, simpbowl, skill98, slotsnl, sltblgpo, sltblgtk, smoto20, speedrcr, speedup, ssipkr24, strtdriv, superbwl, surfplnt, terabrst, tm4k, tm7k, trivialp, tx1, windheat, witch.

También hay 23 casos `MANUAL_VALIDATE`: alpinesa, alpinr2b, apache3, connect4, dealem, galastrm, gauntdl, gauntleg, gloc, goodejaa, gt103, gt103a, m_bdrwho, mpu4met0, mpu4tst2, mpu4utst, neotris, pbball96, pbballex, ssf2ghw, starsldr, tecmowcm, vaportrx.

Son información de compatibilidad, no candidatos al lote bajo las exclusiones actuales.

## Qué filtra el aprendizaje de BATCH 1 y BATCH 2

- BATCH 1: los cinco (`ffight2b`, `altair`, `apache3`, `blazlaz`, `cubeqst`) ya pasaron; quedan fuera por PASS/override activo. No se repiten.
- BATCH 2: evita escoger por metadata sin revisar contenido: `redearth`, `jojo`, `hyperath` fallaron por CHD; `mvp` y `nbapbp` por archivos requeridos ausentes; `jojoba` por ROMSET incompleto. Se excluyen los 15 casos del batch, incluso los cinco SKIP sin lanzamiento, por instrucción explícita de no repetir miembros de BATCH 2.
- El resultado global del batch fue 4 PASS de 10 lanzados. Los PASS (`sia2650`, `evosocc`, `hoops95`, `funcube4`) ya tienen override/estado de piloto y también quedan excluidos.
- La recomendación estática `FULL_CRC_MATCH_MAME_CURRENT` no basta para prometer arranque: CHD/parent/keys y contenido del set deben estar resueltos. No se propone cambio de core global.

## Respuestas directas

1. **¿Cuántos candidatos realmente seguros quedan?** Cero elegibles sin repetir lanzamientos; hay 56 filas `USE_MAME_CORE_X` sin piloto MAME actual, pero todas ya fueron lanzadas con `mame078plus` y quedan excluidas por tu regla.
2. **¿Cuántos pueden probarse sin cambiar ROM?** Cero en el lote permitido. El análisis estático de 56 filas no autoriza una nueva prueba ni garantiza que cada set no necesite resolver contenido; no se infiere eso desde una etiqueta CRC.
3. **¿Cuántos son 3P/4P?** Cero en candidatos elegibles. El grupo estático `USE_MAME_CORE_X` tiene 1P/2P solamente; los casos 4P conocidos de BATCH 2 ya fueron probados y se excluyen.
4. **¿Cuántos son de pelea?** Cero elegibles. `kinstb` es el candidato estático notable de 2P/6 botones, ya lanzado con core default, por lo que no se puede incluir.
5. **¿Cuántos directamente compatibles con la botonera?** Cero en el lote elegible. En el pool estático de 61 hay 14 `DIRECT_COMPATIBLE`, pero ya todos tienen intento previo.
6. **Candidato de mayor confianza:** ninguno elegible. La mejor clase estática de CRC/dependencias entre los ya intentados es `FULL_CRC_MATCH_MAME_CURRENT` sin CHD, pero eso no supera la exclusión de repetir.
7. **¿Qué errores de BATCH 2 evita el filtro?** Evita los tres CHD ausentes, los archivos requeridos ausentes de `mvp`/`nbapbp`, el ROMSET incompleto de `jojoba`, los casos de control especial y la confusión entre CRC parcial y boot confirmado.
8. **¿Recomiendo lanzar estos 20?** No hay 20 elegibles y no recomiendo relanzar ningún juego bajo la regla actual. Para preparar una tanda ejecutable, hace falta autorizar expresamente el uso de juegos ya lanzados con `mame078plus` pero nunca probados con MAME actual; después se podrá escoger 20 de los 56 estáticos con una revisión de dependencias y controles.

## Fuentes cruzadas

`ARCADE_CORE_PILOT_RESULTS.md`, `ARCADE_CORE_PILOT_BATCH2_RESULTS.md`, `ARCADE_CORE_COMPATIBILITY.md`, `ARCADE_CORE_FIX_GROUPS.md`, `ARCADE_FAILURES.md`, `ARCADE_CHD_MISSING.md`, `ARCADE_MISSING_DEPENDENCIES.md`, `ARCADE_CRASH_CASES.md`, `ARCADE_PILOT_RETEST.md`, `ARCADE_SMOKE_TEST_DIAGNOSIS.md`, `arcade_core_compatibility.csv`, `arcade_games_audit.csv` y `checkpoint.json`. El core default confirmado por runtime/documentación sigue siendo `mame078plus`; no se cambió.
