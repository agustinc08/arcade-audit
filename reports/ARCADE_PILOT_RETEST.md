# Piloto de recuperación — selección y resultados

20 sets únicos seleccionados. El estado inicial de esta tabla era “no lanzado”; la ejecución de BATCH 1 y BATCH 2, sus skips y restores quedan documentados en las secciones de resultados al final. Mantener ES/controller_dispatcher, backup+restore saves/NVRAM y checkpoint por juego.

| Grupo | Set | Core candidato | P | Botones | Input | Condición |
| --- | --- | --- | --- | --- | --- | --- |
| MAME current | ffight2b | mame libretro current | 2 | 6 | joy | CRC full, sin CHD ni ROMOF faltante |
| MAME current | altair | mame libretro current | 1 | 2 | joy | CRC full, sin CHD ni ROMOF faltante |
| MAME current | apache3 | mame libretro current | 1 | 3 | stick | CRC full, sin CHD ni ROMOF faltante |
| MAME current | blazlaz | mame libretro current | 1 | 3 | joy | CRC full, sin CHD ni ROMOF faltante |
| MAME current | cubeqst | mame libretro current | 1 | 3 | trackball | CRC full, sin CHD ni ROMOF faltante |
| FBNeo DAT | gprider | fbneo | 2 | 2 | paddle,pedal | Condicional: CHD, parent/path o CRC |
| FBNeo DAT | sfiii2n | fbneo | 2 | 6 | joy | Condicional: CHD, parent/path o CRC |
| FBNeo DAT | sfiii3n | fbneo | 2 | 6 | joy | Condicional: CHD, parent/path o CRC |
| FBNeo DAT | sfiiin | fbneo | 2 | 6 | joy | Condicional: CHD, parent/path o CRC |
| FBNeo DAT | neotris | fbneo |  |  |  | Condicional: CHD, parent/path o CRC |
| Importantes/históricos | mvp | mame current |  |  |  | Condicional: CHD, parent/path o CRC |
| Importantes/históricos | sia2650 | mame current |  |  |  | Condicional: CHD, parent/path o CRC |
| Importantes/históricos | redearth | mame current | 2 | 6 | joy | Condicional: CHD, parent/path o CRC |
| Importantes/históricos | jojo | mame current | 2 | 6 | joy | Condicional: CHD, parent/path o CRC |
| Importantes/históricos | jojoba | mame current | 2 | 6 | joy | Condicional: CHD, parent/path o CRC |
| Raros/3P-4P/input | evosocc | mame current | 4 | 4 | joy | Condicional: CHD, parent/path o CRC |
| Raros/3P-4P/input | hoops95 | mame current | 4 | 4 | joy | Condicional: CHD, parent/path o CRC |
| Raros/3P-4P/input | nbapbp | mame current | 4 | 3 | joy | Condicional: CHD, parent/path o CRC |
| Raros/3P-4P/input | funcube4 | mame current | 3 | 2 | gambling,joy,lightgun | Condicional: CHD, parent/path o CRC |
| Raros/3P-4P/input | hyperath | mame current | 4 | 3 | joy | Condicional: CHD, parent/path o CRC |

Primero los cinco MAME con CRC full, CHD y parent sin ausencia detectada: ffight2b, altair, apache3, blazlaz, cubeqst. FBNeo: gprider primero (CRC full, sin parent externo); SFIII exige validar parent/path. Casos de crash por separado. Bloquear CHD ausente. P1-P4 requiere prueba física.

## Resultado BATCH 2 — 2026-11-13

Resultados acumulados del piloto. Los cinco primeros son SKIP_WRONG_STRATEGY porque el reporte recomienda FBNeo; no se modificaron ni probaron. Los diez MAME elegibles se ejecutaron secuencialmente.

| Shortname | Display name | Core actual | Core probado/recomendado | CRC | CHD | Control | Resultado | Restore |
|---|---|---|---|---|---|---|---|---|
| gprider | Gp Rider | mame078plus | fbneo | PARTIAL_CRC_MATCH_UNRESOLVED | NO | paddle,pedal | SKIP_WRONG_STRATEGY | VERIFIED_NO_WRITE |
| sfiii2n | Street Fighter III : 2nd Impact - Giant Attack | mame078plus | fbneo | PARTIAL_CRC_MATCH_UNRESOLVED | NO | joy | SKIP_WRONG_STRATEGY | VERIFIED_NO_WRITE |
| sfiii3n | Street Fighter III : 3rd Strike - Fight for the Future | mame078plus | fbneo | PARTIAL_CRC_MATCH_UNRESOLVED | NO | joy | SKIP_WRONG_STRATEGY | VERIFIED_NO_WRITE |
| sfiiin | Street Fighter III : New Generation | mame078plus | fbneo | NO_CURRENT_MAME_CRC_MATCH | NO | joy | SKIP_WRONG_STRATEGY | VERIFIED_NO_WRITE |
| neotris | NeoTRIS | mame078plus | FBNeo path/content unresolved | NO_CURRENT_DRIVER | UNKNOWN |  | SKIP_WRONG_STRATEGY | VERIFIED_NO_WRITE |
| mvp | MVP | mame078plus | mame libretro current | SET_MATCH_CRC_SIZE_METADATA | NO |  | FAIL_MISSING_CONTENT | VERIFIED |
| sia2650 | Super Invader Attack | mame078plus | mame libretro current | SET_MATCH_CRC_SIZE_METADATA | NO | joy4way | BOOT_OK | VERIFIED |
| redearth | Red Earth | mame078plus | mame libretro current | FULL_CRC_MATCH_MAME_CURRENT | YES | joy | FAIL_CHD | VERIFIED |
| jojo | JoJo's Venture | mame078plus | mame libretro current | NO_CURRENT_MAME_CRC_MATCH | YES | joy | FAIL_CHD | VERIFIED |
| jojoba | Jojo's Bizarre Adventure | mame078plus | mame libretro current | NO_CURRENT_MAME_CRC_MATCH | NO | joy | FAIL_ROMSET | VERIFIED |
| evosocc | Evolution Soccer | mame078plus | mame libretro current | PARTIAL_CRC_MATCH_UNRESOLVED | NO | joy | BOOT_OK | VERIFIED |
| hoops95 | Hoops'96 | mame078plus | mame libretro current | PARTIAL_CRC_MATCH_UNRESOLVED | NO | joy | BOOT_OK | VERIFIED |
| nbapbp | Nba Play By Play | mame078plus | mame libretro current | PARTIAL_CRC_MATCH_UNRESOLVED | NO | joy | FAIL_MISSING_CONTENT | VERIFIED |
| funcube4 | Funcube 4 | mame078plus | mame libretro current | PARTIAL_CRC_MATCH_UNRESOLVED | NO | gambling,joy,lightgun | BOOT_OK | VERIFIED |
| hyperath | Hyper Athlete | mame078plus | mame libretro current | PARTIAL_CRC_MATCH_UNRESOLVED | YES | joy | FAIL_CHD | VERIFIED |
