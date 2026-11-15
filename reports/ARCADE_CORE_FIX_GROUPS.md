# Grupos de solución — no aplicados

| Acción | Cantidad | Ejemplos |
| --- | --- | --- |
| KEEP_CURRENT_AND_INVESTIGATE | 72 | act2000, alpinr2b, ar_ldrb, ar_ninj, ar_sprg, buggyboy, casino5, cball, cmast91, dacholer, ddux, dyn |
| USE_MAME_CORE_X | 61 | altair, apache3, big10, bigappg, blazlaz, cclownz, cmaster, cmv4, comg076, comg128, coronatn, cubeqs |
| CHD_REQUIRED | 22 | darkhleg, dsftkd, dstage, fbait2bc, fbaitbc, fbaitmc, gauntdl, gauntleg, gtrfrk2m, gtrfrks, hyperath |
| UNKNOWN | 14 | alpinesa, connect4, dealem, goodejaa, gt103, gt103a, m_bdrwho, mpu4met0, mpu4tst2, mpu4utst, pbball9 |
| MISSING_DEPENDENCY | 10 | aerofgts, bigdeal, bldyror2, cbaj, flamegun, glpracr3, hvnsgate, mfjump, shngmtkb, tblkkuzu |
| NOT_WORTH_FIXING | 1 | cd32 |
| USE_FBNEO | 1 | gprider |

## Impacto estático

| Grupo | Cantidad | Observación |
| --- | --- | --- |
| MAME actual CRC full, CHD/ROMOF no faltante | 61 | Candidatos a piloto; no PASS. |
| FBNeo CRC full sin parent externo | 1: gprider | Se recomienda FBNeo como prueba per-game, sin modificar ROM. |
| CHD obligatorio faltante | 22 | Cinco también tienen CRC full; los otros requieren revisar set. |
| ROMOF/parent no localizado | 10 | Dependencia de plataforma ausente en paths examinados. |
| CRC parcial/no coincidente sin CHD | 82 | No demuestra necesidad de reconstrucción. |
| Sin alternativa runtime MAME | 14; neotris condicionado | MAME2010 XML no es core instalado. |
| Contenido faltante fuera de 181 | 3 | armwar, ssf2t, polepos. |
| Crashes | 2 | mvp, sia2650. |

El conjunto estático con posibilidad de probar sin tocar ROMs es de hasta 62 juegos: 61 con MAME current y gprider con FBNeo. Sigue siendo potencial, no boot confirmado. Probar en lotes protegidos antes de cualquier cambio masivo.
