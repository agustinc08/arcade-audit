# Dependencias faltantes

| Juego | Requerido | Evidencia | Implicación |
| --- | --- | --- | --- |
| armwar | armwar.key, 20 bytes, CRC fe979382 | MAME current y FBNeo DAT; log previo NOT FOUND | Core switch no basta |
| ssf2t | ssf2t.key, 20 bytes, CRC 524d608e | MAME current y FBNeo DAT; log previo NOT FOUND | Core switch no basta |
| polepos | pp3_6.4l, pp3_28.1f, pp3_25.1n, pp3_26.1m, pp3-6.6m, pp2_11.2e, pp2_12.2f, pp2_13.1e | Log NOT FOUND / Required files missing / readroms failed | ZIP incompleto; no modificado |
BIOS/platform rows preservados, excluidos de juegos. Parent, clone y metadata de cada set están en CSV.

## ROMOF/support parent no localizado

| Juego | romof |
| --- | --- |
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

Estos archivos no aparecieron en los ZIP de MAME/FBNeo ni en las rutas BIOS revisadas. Se marca como ROMOF no localizado, no como corrupción del juego.
