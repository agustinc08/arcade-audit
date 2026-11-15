# Diagnóstico de los resultados del smoke test arcade

Fecha: 2026-11-13. Revisión read-only de los 239 resultados nuevos, los 11 fallos heredados y el inventario/harness existente. No se relanzaron juegos.

## Resumen

- Se preservaron los cuatro archivos de resultados en copias `*.pre_failure_analysis` antes de este análisis.
- De los 239 casos nuevos: 35 `BOOT_OK`, 181 rechazos explícitos del core, 18 casos sin dispatch confirmado, 2 crashes y 3 fallos de contenido (los últimos 5 estaban resumidos originalmente como cuatro RetroArch exits y un ZIP incompleto).
- Los 42 `ProcessLookupError` se superponen con 42 de los 181 rechazos; no son otros 42 juegos.
- No hay evidencia de un identificador de ROM mal pasado al core. El defecto demostrado está en la clasificación del inventario y en cómo el harness etiqueta un intento sin dispatch.
- No se creó ni ejecutó `smoke_test_v2.py`: repetir con el mismo argumento/core no validaría una corrección de tester inexistente.

## Game driver not found

### Muestra y argumento que recibe el core

La configuración activa de ES pasa `%ROM%` a `/userdata/system/el_gordo_tools/controller_dispatcher`. Para `act2000.zip`, el evento de `game_health.sqlite` registró este comando:

```text
/usr/bin/retroarch -L /usr/lib/libretro/mame078plus_libretro.so --config /userdata/system/configs/retroarch/retroarchcustom.cfg --set-shader /userdata/shaders/scalehq/2xScaleHQ-persistent-fixed.slangp --verbose /userdata/roms/mame/act2000.zip
```

Log exacto del core:

```text
Full content path /userdata/roms/mame/act2000.zip
Content lookup name: act2000
Game driver not found for act2000!
```

Para `sfiiin.zip`, la forma es idéntica y el core informa `Content lookup name: sfiiin`. El argumento recibido por RetroArch es el path absoluto; el core quita la extensión y busca el basename. No recibe display name, parent ni un identificador con ruta/extensión.

| Sistema | Display name | Archivo / basename | MAME 2003+ DAT | MAME 2010 metadata | Parent/clone/notas |
|---|---|---|---|---|---|
| MAME | Action 2000 | `act2000.zip` / `act2000` | No | Action 2000, runnable=yes | — |
| MAME | Aero Fighters Special | `aerofgts.zip` / `aerofgts` | No | Aero Fighters Special | `romof=vspsx` |
| MAME | Alpine Surfer | `alpinesa.zip` / `alpinesa` | No | Alpine Surfer (Rev. AF2 Ver.A) | — |
| MAME | Alpine Racer 2 | `alpinr2b.zip` / `alpinr2b` | No | Alpine Racer 2 (Rev. ARS2 Ver.B) | — |
| MAME | Altair | `altair.zip` / `altair` | No | Altair, runnable=yes | — |
| MAME | Apache 3 | `apache3.zip` / `apache3` | No | Apache 3, runnable=yes | — |
| MAME | Leader Board Golf | `ar_ldrb.zip` / `ar_ldrb` | No | Leader Board (Arcadia) | `romof=ar_bios` |
| MAME | Ninja Mission | `ar_ninj.zip` / `ar_ninj` | No | Ninja Mission (Arcadia) | `romof=ar_bios` |
| MAME | Asteroids | `ar_sprg.zip` / `ar_sprg` | No | Space Ranger (Arcadia) | `romof=ar_bios`; gamelist display name difiere |
| MAME | ZZZ(notgame):Big 10 | `big10.zip` / `big10` | No | Big 10, runnable=yes | Gamelist la etiqueta no-juego |
| MAME | ZZZ(notgame):Bonus Card | `bigdeal.zip` / `bigdeal` | No | Big Deal (Hungarian) | Gamelist la etiqueta no-juego |
| MAME | Buggy Boy | `buggyboy.zip` / `buggyboy` | No | Buggy Boy/Speed Buggy | Cabina especial posible |
| MAME | Street Fighter III 2nd Impact | `sfiii2n.zip` / `sfiii2n` | No | Street Fighter III 2nd Impact | `cloneof=sfiii2`, `romof=sfiii2` |
| MAME | Street Fighter III 3rd Strike | `sfiii3n.zip` / `sfiii3n` | No | Street Fighter III 3rd Strike | `cloneof=sfiii3`, `romof=sfiii3` |
| MAME | Street Fighter III New Generation | `sfiiin.zip` / `sfiiin` | No | Street Fighter III New Generation | `cloneof=sfiii`, `romof=sfiii` |

Los 15 seleccionados son todos MAME `.zip` y usan el mismo core; no existe un caso FBNeo ni otra extensión/core dentro de este grupo que permita ampliar esas variantes.

### Cruce completo de los 181 casos

- 181/181 no aparecen en `/userdata/bios/mame2003-plus/mame2003-plus.xml`, el metadata utilizado para el core MAME configurado.
- 175 aparecen como `runnable=yes` en el XML MAME 2010 instalado. Esto demuestra presencia de driver en esa metadata más nueva, no que el ROM esté íntegro ni que lo pueda ejecutar `mame078plus`.
- 1 está marcado `isbios=yes` en MAME 2010; 5 no aparecen en ese XML. Esos 6 requieren clasificación adicional.
- Todos los rechazos tienen un basename correcto, pero el driver falta en el core activo. Es un rechazo real de la combinación juego/core configurada, no evidencia de ROM corrupta.

### Comparación PASS/FAIL

Se cotejaron `alexkidd.zip`, `bigfight.zip`, `chplftb.zip`, `deroon.zip` y `doapp.zip` contra la muestra. Usan el mismo launcher, core, configuración y forma de argumento; sólo cambia el ZIP. Los PASS permanecieron ~10,6–10,9 s y cerraron con exit 0 controlado. Los fallidos duraron ~0,02–0,05 s, exit 1, y el log del core identifica el basename que rechazó. No aparece display name ni normalización distinta.

## ProcessLookupError

Diez ejemplos revisados (`sfiii3n`, `sfiiin`, `sfruitb`, `sfzch`, `shngmtkb`, `sidebs`, `sidebs2`, `sidewndr`, `simpbowl` y otros del mismo grupo) repiten esta traza:

```text
File "/usr/bin/hotkeygen", line 334, in do_new_context
    os.kill(pid, signal.SIGHUP)
ProcessLookupError: [Errno 3] No such process
```

El evento ya muestra RetroArch con `mame078plus`, el ROM correcto, exit 1 y `Game driver not found`; el proceso terminó en ~0,02 s. El traceback surge en `hotkeygen` al señalar un PID que ya terminó, al cambiar/restaurar el contexto hotkey. No lo arroja la lógica del smoke runner: su lectura de `/proc` captura explícitamente `ProcessLookupError` como carrera de enumeración.

Conteo: 42/204 (20,6%), todos superpuestos con 42 de los 181 rechazos del core. No hay nuevos casos PLE-only. No son 42 fallos adicionales ni evidencia de seguimiento de PID equivocado.

## Immediate returns

Los 18 nombres son `taitotz` (FBNeo) y, en MAME, `aleck64`, `alg_bios`, `ar_bios`, `atarisy1`, `atluspsx`, `atpsx`, `bctvidbs`, `crysbios`, `galgbios`, `konamigv`, `kviper`, `maxaflex`, `psarc95`, `sys573`, `taitogn`, `taitotz`, `vspsx`.

- No tienen evento `boot_audit_auto_choice` en los logs actuales ni evento correspondiente en `game_health.sqlite`; los otros 221 intentos sí tienen el marcador en los logs disponibles.
- Los 18 aparecen como `isbios=yes` en el XML MAME 2010. Son BIOS/plataformas, no 18 juegos que deban producir PASS.
- El runner tradujo “ES idle y no vi RetroArch” directamente a `FAIL_RETURN_TO_ES`, sin exigir que el marcador one-shot se hubiera consumido. No demuestra retorno de un juego: demuestra que no se confirmó que el lanzamiento se despachara.

Clasificación: `TEST_HARNESS_FAILURE / NOT_LAUNCHED`; boot del juego no aplica. No es `CONFIRMED_GAME_FAILURE`.

## RetroArch exits

| Juego | Evidencia | Clasificación |
|---|---|---|
| `mvp.zip` | Duración 1,159 s; exit -11, señal 11 | Crash SIGSEGV confirmado |
| `sia2650.zip` | Duración 1,065 s; exit -11, señal 11 | Crash SIGSEGV confirmado |
| `armwar.zip` | Exit 1; `armwar.key NOT FOUND`; required files missing | `MISSING_CONTENT`, no crash |
| `ssf2t.zip` | Exit 1; `ssf2t.key NOT FOUND`; required files missing | `MISSING_CONTENT`, no crash |

## ROM incompleta

`polepos.zip` es un fallo confirmado de contenido: MAME enumera miembros requeridos ausentes, incluyendo `pp3_6.4l`, `pp3_28.1f`, `pp3_25.1n`, `pp3_26.1m`, `pp3-6.6m`, `pp2_11.2e`, `pp2_12.2f` y `pp2_13.1e`; luego informa `Required files are missing` y `readroms failed`. No se descargó ni cambió nada.

## Árbol de procesos y revisión técnica del harness

Cadena observada: EmulationStation → `controller_dispatcher` (fork padre/hijo) → `configgen.emulatorlauncher.launch()` → `runCommand()` con `subprocess.Popen` → RetroArch, con el core libretro cargado en el proceso.

El runner busca RetroArch que contenga simultáneamente el path del ROM y el core esperado. Si el proceso dura menos que el intervalo de sondeo, consulta `game_health.sqlite`, que conserva comando, PID, duración, exit code y logs. En los 181 casos sí existe evidencia directa del proceso/core, así que el sondeo no creó el mensaje `Game driver not found`. En los 18 casos sin evento/marker no se debe inferir que un juego arrancó y volvió.

Defectos confirmados del auditor:

1. `build_inventory.py`: usa sólo MAME 2003+ para obtener `bios_device`; si no hay metadata, una entrada de gamelist hace que se conserve como juego. Así entraron BIOS/sets de soporte y juegos fuera de la cobertura declarada del core.
2. `smoke_runner.py`: el caso sin proceso clasifica ES idle como retorno aunque el one-shot no esté consumido; debería reportar `NOT_LAUNCHED/UNKNOWN`.
3. `FAIL_CRASH` no distingue señal 11 de error explícito de contenido: `armwar` y `ssf2t` deberían ser `MISSING_CONTENT`.
4. `game_health` usa una ventana de 15 s para definir inicio sostenido, mientras el runner controla el juego durante ~10 s. Eso deja un `SALIDA_INMEDIATA_PENDIENTE` en la telemetría aunque el runner marque `BOOT_OK`; es desalineación de métricas, no fallo de esos 35 PASS.

### Diff conceptual propuesto — NO APLICADO

Mantener el inventario de archivos, pero añadir clase y elegibilidad; no descartar ni alterar ROMs:

```diff
- biosset = meta.get('bios_device', False)
- is_game = not biosset and (dat_member or rom.lower() in gl)
+ fallback = mame2010_meta.get(setname, {}) if system == 'mame' else {}
+ is_support_set = (meta.get('bios_device', False)
+                   or fallback.get('isbios') == 'yes'
+                   or fallback.get('isdevice') == 'yes'
+                   or fallback.get('runnable') == 'no')
+ entry_kind = ('BIOS_DEVICE' if is_support_set else
+               'CORE_DAT_MEMBER' if dat_member else
+               'GAMELIST_ONLY_UNSUPPORTED_CORE')
+ # Guardar entry_kind y separar elegibilidad de smoke test de presencia en gamelist.
```

Y al clasificar ausencia de lanzamiento:

```diff
+ if not one_shot_consumed and not dispatcher_launch_event:
+     status = 'NOT_LAUNCHED'
+     # No llamar FAIL_RETURN_TO_ES ni contar como fallo de boot del juego.
```

Es un diff propuesto, no aplicado. La decisión exacta de elegibilidad queda pendiente de revisión del usuario.

## Clasificación provisional de los 215 fallos acumulados

| Clase | Cantidad | Detalle |
|---|---:|---|
| `CONFIRMED_GAME_FAILURE` del core configurado | 181 | Core rechaza driver; no implica ZIP dañado ni argumento erróneo |
| `TEST_HARNESS_FAILURE / NOT_LAUNCHED` | 18 | Entradas BIOS/plataforma sin dispatch probado |
| `CONFIRMED_GAME_FAILURE` de runtime | 2 | `mvp`, `sia2650`, SIGSEGV |
| `MISSING_CONTENT` nuevo | 3 | `armwar.key`, `ssf2t.key`, miembros de `polepos.zip` |
| `MISSING_CONTENT` heredado | 7 | Logs previos documentan CHD faltante: `area51mx`, `blitz`, `blitz2k`, `blitz99`, `calspeed`, `carnevil`, `cryptklr` |
| `NEEDS_RETEST / UNKNOWN` heredado | 4 | `kinst2`, `maxforce`, `sfrush`, `wg3dh`; salida rápida sin causa suficiente en esta revisión |
| **Total** | **215** | 204 nuevos + 11 anteriores |

Los 42 PLE son una subanotación de 42 rechazos y no se suman. Los 35 `BOOT_OK` nuevos y los 1.147 PASS anteriores quedan fuera de la cuenta de fallos; no se reejecutaron.

## Impacto potencial

| Causa | Casos | % de 204 | Retest/reclasificación potencial |
|---|---:|---:|---|
| Driver ausente en core MAME 2003+ | 181 | 88,7% | 0 recuperables corrigiendo el argumento del tester. Los 175 presentes en metadata MAME 2010 podrían evaluarse en una etapa de decisión de core, sin garantía de resultado. |
| PLE de hotkeygen | 42, superpuestos | 20,6% | 0 casos únicos; el error no cambia el resultado del core. |
| BIOS sin dispatch | 18 | 8,8% | 18 reclasificables como no-juego/no-lanzado; no son 18 boots recuperables. |
| SIGSEGV | 2 | 1,0% | Retest diagnóstico opcional en el futuro; no aparentan falsos negativos del runner. |
| Contenido faltante nuevo | 3 | 1,5% | No se resuelve con el harness. |

La corrección de normalización de driver tendría recuperación demostrada de **0/181**. La corrección de clasificación podría retirar **18/204** de los fallos de juegos, sin convertirlos en PASS.

## Tester v2 propuesto y muestra

No se creó `smoke_test_v2.py` ni se ejecutó la muestra de 13. La hipótesis de driver incorrecto quedó contradicha: el core recibió y normalizó el shortname correcto. Los PLE son de hotkeygen; los 18 inmediatos no llegaron al dispatcher. Por eso los criterios de V2 para corregir driver resolution/process tracking no aplican.

Una v2 futura debería separar `entry_kind`, `core_driver_support`, `dispatch_confirmed`, `boot_status` e `input_status`; emitir `NOT_LAUNCHED` si no se consume el one-shot; y usar log/exit code para distinguir driver ausente, contenido requerido faltante y señal 11. Debe conservar backup/restore de saves/NVRAM, PID exacto y controles de salud, y no reejecutar masivamente sin revisar el inventario corregido.

## Resultado y próximo paso

1. Los 181 errores del driver son rechazos reales del core configurado, no identificadores mal formados. No demuestran por sí solos ROM corrupta.
2. El argumento incorrecto detectado: **ninguno**.
3. Los 42 PLE no son fallos adicionales; el origen es `hotkeygen` intentando enviar SIGHUP a un PID ya terminado.
4. Casos nuevos con fallo confirmado de runtime/contenido: 5 (2 SIGSEGV + 3 contenido). Los otros 181 son incompatibilidad/rechazo del core activo; 18 son entradas de soporte mal contadas como juegos.
5. El caso `polepos.zip` sí es contenido incompleto.
6. La muestra V2 no se ejecutó. No hubo modificaciones ni escrituras nuevas de saves/NVRAM en este análisis.
7. Próxima etapa, tras revisión: preparar copia del inventario/harness con esas distinciones; después decidir si se prueban sólo juegos elegibles y qué core se toma como referencia. No corregir todavía ROMs, cores, mappings ni juegos.
