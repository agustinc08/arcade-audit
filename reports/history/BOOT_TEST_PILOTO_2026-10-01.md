> Snapshot histórico; los valores de red y credenciales se saneaban en esta copia cuando correspondía. No usar como estado vigente; consultar `ARCADE_CURRENT_STATE.md`.

# BOOT TEST PILOTO

Fecha: 2026-10-01
Estado del piloto: `LAUNCH_BLOCKED`

## 1. MÉTODO

Se leyó completo `/userdata/AUDITORIA_JUEGOS_ESTATICA_2026-10-01.md` y se validaron los inventarios estático y funcional.

- `game_static_audit.csv`: 8.142 registros, 19 campos, 8.142 visibles y 0 claves `system + path` duplicadas.
- `game_static_audit.json`: JSON válido, 8.142 registros; mismas claves y mismos `structural_status` que el CSV.
- Estados estáticos: 7.932 `READY_FOR_BOOT`, 1 `READY_FOR_BOOT_WITH_NOTE`, 70 `FORMAT_PROBLEM`, 11 `ROMSET_PROBLEM`, 6 `USER_CONTENT_REQUIRED`, 117 `SPECIAL_MANUAL`, 2 `NEEDS_FUNCTIONAL_TEST`, 2 `NEEDS_REVIEW` y 1 `NOT_GAME_CONTENT`.
- Auditoría funcional: CSV y JSON válidos, 8.142 registros; no fueron modificados. El CSV contiene 8.141 `NEEDS_TEST` y 1 `NEEDS_MANUAL_TEST`.

La definición activa de los siete sistemas piloto usa `/userdata/system/el_gordo_tools/controller_dispatcher` como comando de EmulationStation. El dispatcher llama al selector de controles, asigna dispositivos, coordina el lanzamiento y, en el proceso hijo, invoca `/usr/bin/emulatorlauncher`/configgen. No se ejecutó ninguno de esos componentes para probar un juego.

## 2. SEGURIDAD Y MOTIVO DE BLOQUEO

La sesión actual es SSH (`SSH_TTY` y `SSH_CONNECTION` presentes) y no tiene `DISPLAY` ni `XAUTHORITY`. `XDG_RUNTIME_DIR` apunta a `/var/run`; la presencia de un socket X11 `X0` por sí sola no demuestra que esta sesión pueda usar la autorización y el contexto de la sesión gráfica.

EmulationStation aparece activo (PID 17529, `--windowed`) y `batocera-es-swissknife --espid` devuelve ese PID. La misma herramienta reporta `--emupid` como `0`; no había emulador activo en el momento de la inspección. El entorno del PID de EmulationStation no se pudo leer desde el espacio de procesos de esta sesión, por lo que no se puede copiar ni verificar de forma segura el contexto gráfico real.

El dispatcher no ofrece aquí un canal remoto documentado para pedirle a la instancia activa de EmulationStation que abra una selección. Ejecutarlo directamente por SSH no equivale a seleccionar un juego en el frontend: su ruta normal puede abrir el selector gráfico, usa SDL para enumerar mandos, toma un lock, escribe logs/estado de salud y crea un proceso hijo para el launcher. `--simulate-choice` evita el selector, pero no es una acción originada por EmulationStation y no demuestra que la sesión gráfica se esté reproduciendo fielmente. Invocar el dispatcher o el emulador desde esta sesión sería una ruta alternativa no validada.

**Decisión:** no se lanzó ningún juego. No se intentó cerrar procesos ni enviar señales. El piloto queda `LAUNCH_BLOCKED` antes de la selección de juegos.

## 3. LOTE

Objetivo de diseño: 21 juegos `READY_FOR_BOOT` (3 NES, 3 SNES, 3 Mega Drive, 3 GBA, 3 Dreamcast, 3 PS2 y 3 MAME). No se seleccionó ni ejecutó un lote, porque la verificación del mecanismo real de lanzamiento es un requisito previo y no se pudo satisfacer desde SSH.

## 4. RESULTADOS

Juegos seleccionados: 0  
Juegos ejecutados: 0  
Resultado global del mecanismo: `LAUNCH_BLOCKED`  
Proceso de juego visto: no  
Cleanup: no aplicable (no hubo lanzamiento).

Los archivos de resultados quedan con cabecera/esquema válido y cero registros por juego. Esto evita presentar intentos no realizados como resultados individuales.

## 5. RESUMEN

BOOT_OK: 0  
FAIL_BOOT: 0  
CRASH: 0  
TIMEOUT: 0  
LAUNCH_BLOCKED: 1 piloto completo  
TEST_ERROR: 0

## 6. RESULTADOS POR SISTEMA

No hubo resultados individuales: el piloto se detuvo antes de elegir juegos o lanzar emuladores.

## 7. PROBLEMAS DEL HARNESS

- La sesión SSH no expone `DISPLAY` ni `XAUTHORITY`.
- No se pudo inspeccionar desde esta sesión el entorno del proceso de EmulationStation.
- No se identificó un mecanismo seguro para enviar una selección de juego a la instancia activa del frontend.
- No se verificó una forma de vincular un proceso iniciado desde el frontend con este harness y cerrarlo sin sustituir el flujo real.

Esto no demuestra que los juegos fallen; demuestra que el método de prueba automatizada desde esta sesión no está habilitado de manera segura.

## 8. CAMBIOS COLATERALES

No se lanzaron juegos y no se modificaron `gamelist.xml`, `es_systems_el_gordo.cfg`, `controller_dispatcher`, `batocera.conf`, ROMs, cores ni configuraciones. Los archivos funcionales y estáticos existentes se conservaron. Las únicas escrituras de esta etapa son este informe y los dos archivos nuevos de resultados, vacíos de registros individuales.

## 9. CONCLUSIÓN

**¿ES SEGURO ESCALAR EL BOOT TEST? NO.** Primero hace falta un mecanismo que opere desde la instancia activa de EmulationStation o una herramienta de prueba integrada y validada que conserve exactamente su contexto de sesión, el dispatcher y una salida controlable. No se debe sustituir por una ejecución directa del emulador desde SSH.

## 10. SIGUIENTE ESCALA RECOMENDADA

No escalar todavía. Diseñar y validar primero un disparador dentro de la sesión del frontend, con selección individual visible, registro del proceso hijo y cierre controlado asociado únicamente a ese lanzamiento. Después se podrá repetir este piloto de 21; los tamaños mayores se decidirán sólo si el piloto termina sin procesos huérfanos ni cambios colaterales.

## INVESTIGACIÓN DEL BLOQUEO DE LANZAMIENTO

Esta sección actualiza el diagnóstico inicial: sí existe un IPC nativo de lanzamiento. El piloto anterior sigue siendo `LAUNCH_BLOCKED` y sus resultados no cambian; no se envió ningún `POST /launch`.

### Sesión real de EmulationStation

- **EmulationStation PID:** `17529`; PPID `17521`; propietario `root` (UID 0); sin TTY de control (`?`); CWD `/userdata`.
- **DISPLAY real:** `:0`.
- **XAUTHORITY real:** no definida en el entorno de EmulationStation, Openbox ni X. `/usr/bin/startx` tiene `enable_xauth=0`; la invocación real de X es `/usr/bin/X :0` sin argumento `-auth`. No se ejecutó `xhost`, así que no se consultó ni alteró la ACL del servidor X.
- **XDG_RUNTIME_DIR:** `/var/run`.
- **DBUS_SESSION_BUS_ADDRESS:** EmulationStation usa un bus de sesión privado iniciado por `dbus-run-session` (la ruta/ID de sesión se omite); el wrapper de arranque tiene el bus de sistema.
- **HOME:** `/userdata/system` en EmulationStation. `USER` y `LOGNAME` no están definidos en su entorno; el propietario efectivo es `root`.
- **PATH:** `/sbin:/usr/sbin:/bin:/usr/bin`.
- **WAYLAND_DISPLAY y variables SDL consultadas:** ausentes.
- **FD relevantes de EmulationStation:** `es_log.txt`, dispositivos NVIDIA/DRM, dispositivos `/dev/input/event*` y un memfd de PulseAudio. Esto confirma que el proceso está integrado a la sesión gráfica y a los dispositivos locales.

Árbol observado:

```text
PID 1 init
└─ PID 2403 startx
   └─ PID 2412 xinit /etc/X11/xinit/xinitrc -- /usr/bin/X :0
      ├─ PID 2414 X (:0)
      └─ xinitrc → Openbox PID 2575
         └─ emulationstation-standalone PID 2644
            └─ dbus-run-session PID 17521
               ├─ dbus-daemon PID 17526 (sesión privada)
               └─ EmulationStation PID 17529
```

`/etc/init.d/S31emulationstation` prepara `XDG_RUNTIME_DIR`/DBus y llama `startx`. `/etc/X11/xinit/xinitrc` inicia Openbox con `emulationstation-standalone`; ese wrapper cambia a `/userdata` e inicia EmulationStation dentro de `dbus-run-session`. La sesión SSH no comparte ese DISPLAY ni el bus privado.

### IPC nativo de lanzamiento

- **IPC nativo:** **SÍ**, API HTTP del propio EmulationStation en `localhost:1234`.
- La interfaz local `/usr/share/emulationstation/resources/services/index.html` implementa `POST /launch` con el path del juego en el cuerpo.
- La utilidad Batocera `/usr/bin/batocera-test` usa el mismo endpoint (`requests.post("http://localhost:1234/launch", data=game)`) y después consulta `GET /runningGame`. No se ejecutó `batocera-test`: selecciona sistemas/juegos aleatoriamente, crea reportes/capturas y envía una acción de salida.
- Verificación inocua de runtime: `GET /isIdle` respondió HTTP 200 con `[ true ]`; `GET /runningGame` respondió HTTP 201 con `{"msg":"NO GAME RUNNING"}`. No se probó el endpoint POST.
- Los clientes locales examinados no envían token, cookie ni otra credencial de aplicación. La petición es HTTP local. El alcance de escucha más allá de `localhost` no se pudo certificar; no se usará el endpoint desde otra máquina.
- **Swissknife puede lanzar juego:** **NO**. Su fuente ofrece consulta de PID, reinicio/cierre de ES o del emulador y otras operaciones; no contiene acción de lanzamiento. `--restart` termina ES con `SIGKILL`; no se ejecutó ninguna acción mutante.

La API es el mecanismo preferido porque el receptor es la instancia activa de EmulationStation. El frontend resuelve el juego y ejecuta su comando configurado, manteniendo el contexto gráfico y los placeholders del sistema. El comando activo contiene:

```text
/userdata/system/el_gordo_tools/controller_dispatcher %CONTROLLERSCONFIG% -system %SYSTEM% -rom %ROM% -gameinfoxml %GAMEINFOXML% -systemname %SYSTEMNAME%
```

EmulationStation sustituye esos tokens al lanzar. `%ROM%` y `%SYSTEM%` se refieren al juego y sistema seleccionados; los datos de control y el XML de juego son valores de ejecución. El binario instalado reconoce `%CONTROLLERSCONFIG%`; el valor concreto depende del lanzamiento y no se puede fijar con seguridad desde una invocación externa estática. El `POST /launch` evita tener que reconstruir esos argumentos: solicita al EmulationStation activo que haga la selección/lanzamiento. El dispatcher escanea SDL y los controles presentes durante el lanzamiento, por lo que una reconstrucción externa puede divergir si cambia la topología de mandos o el perfil.

### Evaluación de métodos

- **Método A — IPC nativo:** **PREFERIDO**. EmulationStation acepta la petición y conserva el comando, el dispatcher y configgen activos. Para detectar el cambio: partir de `/isIdle` y `/runningGame`; tras el POST, esperar que `/runningGame` informe el sistema/juego y contrastar `batocera-es-swissknife --emupid`. Para volver: salir del juego de forma normal y confirmar `/runningGame` HTTP 201, `--emupid` igual a `0` y que siga presente el PID de EmulationStation. Esos pasos de transición/salida aún requieren una prueba piloto controlada; no se hicieron aquí.
- **Método B — copiar el entorno e invocar dispatcher desde SSH:** **UNSAFE**. Aunque se copiara `DISPLAY=:0`, EmulationStation no habría iniciado la acción ni entrado en su ciclo de juego; podría continuar renderizando y leyendo mandos mientras otro emulador usa video/audio/input. También habría que reproducir los valores dinámicos de `%CONTROLLERSCONFIG%`, `%GAMEINFOXML%` y el selector de controles. No se debe usar.
- **Método C — el usuario inicia/sale desde el menú y Codex observa:** **VIABLE**. Codex puede consultar `/runningGame`, `--emupid`, los logs y, una vez que el dispatcher cierre el lanzamiento, la tabla `launch_events` de `/userdata/system/state/game_health.sqlite`. El dispatcher instrumenta comando, core/emulador, PID, duración, exit code, señal y errores pertinentes. El usuario conserva el cierre físico normal; Codex no necesita inyectar teclas ni matar procesos. Las observaciones de imagen/audio/controles/rendimiento siguen siendo humanas.

### Riesgos y recomendación

- El POST sí es una acción de lanzamiento; no ejecutarlo hasta acordar/empezar la prueba controlada.
- El endpoint oficial `batocera-test` usa `hotkeygen --send exit`; no se recomienda reutilizar ese cierre automático en el primer caso. Para la primera comprobación se debe cerrar físicamente desde el juego y confirmar estado idle antes de seguir.
- Si `POST /launch` responde pero no aparece el juego esperado en `/runningGame`, detener el piloto y no repetir POST.
- No se usaron `xdotool`, `xhost`, teclas artificiales, joystick virtual, `uinput`, señales ni reinicios.

**BOOT TEST automático:** `REQUIERE PRUEBA CONTROLADA` (el transporte nativo ya está identificado y sus GET de estado funcionan; falta probar un único POST y validar la transición/cierre).  
**BOOT TEST manual asistido:** `POSIBLE`.  
**Método recomendado:** **A**, comenzando con un único juego y salida física normal; **C** queda como alternativa si no se desea que Codex solicite el lanzamiento.

**Comando de prueba propuesto — NO EJECUTADO:**

```sh
python3 -c 'import requests; requests.post("http://localhost:1234/launch", data="/userdata/roms/<sistema>/<archivo>", timeout=5).raise_for_status()'
```

La ruta debe ser la ruta absoluta exacta de una entrada `READY_FOR_BOOT`. El comando abriría ese juego a través de EmulationStation; no forma parte de una prueba realizada en esta investigación.


## PRUEBA CONTROLADA POST /launch

- **Juego:** Super Mario Bros.
- **Path:** `/userdata/roms/nes/Super Mario Bros. (ESP-Her-Saki).nes`
- **Sistema:** `nes`
- **Core esperado:** `fceumm` (`libretro`)
- **HTTP launch:** `200`, respuesta vacía, 2026-10-01 16:48:56.789274 -03:00. Se envió un solo POST.
- **runningGame:** informó el path/nombre/sistema exactos; `/isIdle=false`.
- **PID:** no hubo PID de emulador (`--emupid` devolvió `0`). EmulationStation siguió activo con PID `17529`; `controller_dispatcher` PID `27450` y `selector_controles` PID `27451` permanecían esperando.
- **Duración:** no se pudo medir runtime de emulador; no se observó proceso de emulador.
- **Salida:** no confirmada; no se envió ninguna acción de salida.
- **Health event:** ninguno nuevo; `launch_events` continuó en count/max id `100`. La base fue consultada en modo read-only.
- **Fatal logs:** no detectados en los logs nuevos consultados; `es_launch_stderr.log` permaneció vacío.
- **Cleanup:** no confirmado; EmulationStation aún informaba no-idle y no se confirmó regreso al menú. No se mató ni señaló ningún proceso.
- **Resultado:** `TEST_ERROR`. El API aceptó la petición y registró el juego solicitado, pero el flujo no llegó a un PID de emulador dentro de la observación; el dispatcher quedó en `selector_controles --timeout 0`. No equivale a FAIL_BOOT del juego ni a BOOT_OK.

La anotación histórica `LAUNCH_BLOCKED` se conserva como resultado de la investigación anterior. Esta sección documenta la única tentativa posterior; no se lanzó otro juego. Los archivos funcionales y estáticos permanecen separados y sin cambios.


## RESOLUCIÓN SELECTOR_CONTROLES

**Estado de recuperación (2026-10-02):** EmulationStation PID `17529` continúa activo. `/isIdle` respondió `false`; `/runningGame` sigue identificando Super Mario Bros. El `controller_dispatcher` PID `27450` tiene como hijo al `selector_controles` PID `27451` (`--timeout 0`). `batocera-es-swissknife --emupid` devuelve `0`; no se observó RetroArch ni `emulatorlauncher`. El selector sigue vinculado al lanzamiento anterior. No es posible determinar desde SSH qué imagen ve la TV. No se envió otra petición ni se terminaron procesos.

**Semántica del timeout:** `controller_technical.json` establece `selector.timeout_seconds=0`. En `selector_controles`, el límite sólo se comprueba cuando `timeout > 0`; por ello `0` significa que no vence automáticamente y la espera depende de una selección humana. El dispatcher llama al selector en cada lanzamiento normal, antes de escanear y ordenar los dispositivos para el launcher. El selector no usa el número de jugadores de metadata para decidir su pantalla, ni conserva una selección predeterminada/cacheada en este código.

**Opción existente `--simulate-choice`:** la acepta `/userdata/system/el_gordo_tools/controller_dispatcher`, con `arcade`, `external` o `cancel`. Para `arcade`/`external`, `parent_launch` no inicia `selector_controles`: usa esa elección como orden de prioridad, vuelve a escanear los joysticks SDL reales, valida/ordena los dispositivos y pasa los argumentos de jugadores al mismo `run_official_launcher` y a `emulatorlauncher.launch()`/configgen. El `selected_profile` se asigna sólo al objeto de configuración en memoria. El namespace de dispositivos y el overlay de `/userdata/system/configs` se crean en el proceso hijo para la sesión. No cambia el JSON técnico del perfil. `cancel` detiene el lanzamiento.

**Clasificación:** `POSSIBLY_SAFE` para esta prueba por la ruta disponible. La opción del dispatcher omite sólo la selección visual a nivel de código, pero el `POST /launch` de EmulationStation no permite pasarla: el comando activo invoca el dispatcher con los argumentos de sistema/ROM/mandos generados por ES. La opción `selector_controles --simulate` sólo imprime una elección y no está conectada al comando que el dispatcher construye. No se implementó un marcador/variable de bypass porque no se puede demostrar ahora una activación aislada mientras el lanzamiento anterior mantiene el selector y el frontend fuera de idle.

**Resultado de esta investigación:** modo de auditoría no implementado; segunda prueba no ejecutada; archivos de runtime sin cambios. El registro existente del intento anterior permanece como `TEST_ERROR DEL HARNESS`; el juego sigue `NO EVALUADO`. No se agregó un segundo registro CSV/JSON. Para retomar, primero hay que devolver físicamente el selector anterior a EmulationStation mediante la interfaz normal y comprobar `/isIdle=true`, `runningGame=NO GAME RUNNING` y `emupid=0`.


## RECUPERACIÓN DE EMULATIONSTATION

**Fecha de comprobación en el host:** 2026-10-03 00:55 (-03:00).

- **Estado inicial informado:** `localhost:1234` rechazaba conexiones y las consultas no elevadas devolvían `ESPID=0` / `EMUPID=0`. Esa vista no coincidía con el host real.
- **Causa probable de la aparente caída:** no se encontró evidencia de que EmulationStation hubiera terminado. Las consultas realizadas dentro del entorno aislado no veían los procesos ni el loopback del host. La consulta elevada posterior encontró la sesión gráfica activa desde el 2026-10-01. La causa de que el diagnóstico aislado no reflejara el host se atribuye al namespace de ejecución; la causa de la espera del lanzamiento sigue siendo `selector_controles --timeout 0`, según la evidencia de procesos.
- **Xorg:** ACTIVO, PID `2414`, `/usr/bin/X :0`.
- **Openbox:** ACTIVO, PID `2575`.
- **EmulationStation:** ACTIVO, PID `17529` desde 2026-10-01 02:42:59.
- **Método nativo identificado:** `/etc/init.d/S31emulationstation start` prepara FIFO/DBus y llama `startx`; `/etc/X11/xinit/xinitrc` inicia Openbox y `emulationstation-standalone`, que ejecuta ES bajo `dbus-run-session`. No se ejecutó porque la sesión ya estaba activa. No se utilizó `batocera-es-swissknife --restart`, cuyo código termina ES con `SIGKILL`.
- **PID de EmulationStation:** `17529`.
- **API 1234:** LISTEN en `127.0.0.1:1234`; ambas consultas respondieron.
- **`isIdle`:** `[ false ]` (HTTP 201).
- **`runningGame`:** HTTP 200 informó Super Mario Bros., sistema `nes`, ROM `/userdata/roms/nes/Super Mario Bros. (ESP-Her-Saki).nes`. Esto refleja la operación de lanzamiento registrada por ES y no demuestra que el emulador haya iniciado.
- **Procesos del lanzamiento:** `controller_dispatcher` PID `27450` y `selector_controles` PID `27451` (`--timeout 0`) seguían activos bajo EmulationStation. La consulta final no mostró `RetroArch` ni `emulatorlauncher`. `batocera-es-swissknife --emupid` devolvió `13694` y `13702`, pero esos PID no aparecieron en el `ps -p` inmediatamente posterior; queda registrada esa discrepancia y no se afirma que haya emulador activo.
- **Estado final:** ERROR / NO IDLE. La sesión gráfica y EmulationStation ya estaban activos, pero el selector continúa esperando y el lanzamiento anterior no ha regresado al menú.
- **Acciones:** no se envió POST, no se inició ningún juego, no se reinició ES ni Xorg, no se movieron los marcadores stale de X y no se enviaron señales. Se detuvo la intervención al encontrar el selector activo; queda pendiente la salida física normal antes de cualquier otra acción.
- **Backup previo a esta anotación:** `/userdata/ARCADE_BACKUPS/BOOT_TEST_PILOTO_2026-10-01.md.pre_ES_RECOVERY_20261003_0056` (copia exacta del informe previo). Rollback documental: restaurar esa copia sobre el informe si se requiere retirar esta sección.


## INTENTO 2 — BOOT AUDIT AUTO BOTONERA (2026-10-03)

**Estado:** `TEST_ERROR` del harness; Super Mario sigue `NO EVALUADO`.

### Correspondencia de la elección

`BOTONERA = arcade`. En `selector_controles`, la opción interna `arcade`
está etiquetada `BOTONERAS PRIMERO`; `external` está etiquetada
`JOYSTICKS PRIMERO`. `controller_dispatcher.classify_and_order()` ordena
primero los controles arcade para `arcade` y llama a la misma ruta
`run_official_launcher()`/`emulatorlauncher`/configgen. No se fabrican
`CONTROLLERSCONFIG`, GUIDs ni mappings.

### Cambio y prueba estática

Se implementó `BOOT AUDIT — AUTO BOTONERA` únicamente en
`/userdata/system/el_gordo_tools/controller_dispatcher`. El one-shot sólo
se acepta con `enabled=true`, sistema y ROM absoluta exactos, `choice=BOTONERA`
y `created_at`/`expires_at` dentro de un TTL máximo de 60 segundos. Una
coincidencia se consume antes de enumerar controles y devuelve la opción
interna existente `arcade`. Si no coincide o expiró, se ejecuta la rama
normal que abre `selector_controles`.

Prueba estática aislada, sin ejecutar launcher/emulador: sin one-shot,
expirado, ROM diferente y sistema diferente toman la rama normal; el match
exacto devuelve `arcade`, consume el archivo y omite la llamada al selector.
Resultado: `STATIC_BOOT_AUDIT_OK`.

### Prueba real única

- Estado previo del host: `isIdle=true`, `runningGame=NO GAME RUNNING`,
  `emupid=0`; EmulationStation PID `17529` activo.
- Se creó `/userdata/system/state/boot_audit_once.json` a las
  `2026-10-03 11:58:29.825 -03:00`, con TTL de 60 segundos.
- Se envió una sola petición a `POST http://127.0.0.1:1234/launch` con la
  ROM objetivo; respuesta HTTP `200`.
- El dispatcher inició a las `12:11:26 -03:00`, más de 12 minutos después
  de vencer el one-shot (`11:59:29.825`). Por tanto no hubo `ONE-SHOT MATCH`:
  el fallback normal abrió `selector_controles` PID `30783` bajo
  `controller_dispatcher` PID `30782`. El selector apareció como proceso;
  no se observó directamente la pantalla del televisor.
- No se inició emulador ni core (`emupid=0`; `fceumm` era el core esperado,
  pero no llegó a ejecutarse). Runtime de emulador: `0 s`.
- Se envió SIGTERM únicamente al selector PID `30783`; el dispatcher salió.
  Verificación final del host: `isIdle=true`, `runningGame=NO GAME RUNNING`,
  `emupid=0`, EmulationStation PID `17529` activo.
- El one-shot vencido se conservó en el backup como
  `boot_audit_once_expired_before_launch.json`; su ruta activa quedó libre.
- La salida segura para un juego iniciado está identificada: `/usr/bin/batocera-test`
  utiliza `hotkeygen --send exit`. No se aplicó porque no hubo emulador.

### Intento 1 y resultado actual

El INTENTO 1 continúa registrado como `TEST_ERROR` del harness: el selector
quedó esperando una elección humana. El 2026-10-03 se cerró únicamente el
selector antiguo PID `27451` con SIGTERM; el dispatcher PID `27450` salió
por sí solo. Se confirmó retorno a `IDLE_OK`.

El INTENTO 2 también es `TEST_ERROR` del harness por vencimiento del one-shot
antes de que EmulationStation iniciara el dispatcher. No equivale a
`FAIL_BOOT` ni `BOOT_OK`; Super Mario permanece `NO EVALUADO`. No se envió
un segundo POST ni se lanzó otro juego.

**Estado del cambio:** AUTO BOTONERA implementado y prueba estática aprobada;
la selección automática no quedó validada en una ejecución real. El flujo
normal conserva el selector JOYSTICK/BOTONERA cuando falta un one-shot
vigente y exacto. El piloto de 21 juegos queda `NO` hasta validar un match
real con el marcador creado inmediatamente antes del POST autorizado.

**Backup de esta intervención:**
`/userdata/ARCADE_BACKUPS/BOOT_AUDIT_BOTONERA_2026-10-03_115310/`.


## INTENTO 3 — ONE-SHOT 60S ATÓMICO

Fecha: 2026-10-03. No se modificaron `controller_dispatcher`,
`selector_controles`, cores, mappings ni configuraciones de lanzamiento.

- **Precheck host real:** `ESPID=17529`, `isIdle=true`,
  `runningGame=NO GAME RUNNING`, `emupid=0`; sin dispatcher, selector,
  RetroArch ni emulatorlauncher.
- **One-shot:** creado con `enabled=true`, `system=nes`, ROM absoluta exacta,
  `choice=BOTONERA` (valor requerido por el guard actual; convertido a la
  elección interna `arcade`), `created_at=2026-10-03T21:24:43.424-03:00` y
  `expires_at=created_at+60 s`.
- **POST:** `2026-10-03T21:24:43.426-03:00`, HTTP `200`; delta entre escritura
  final y POST: `0.00000143 s`. Fue la única petición.
- **Match:** el log `controller_selector.log` registró `boot_audit_auto_choice`
  para `nes` y la ROM exacta, `choice=BOTONERA`, `internal_choice=arcade`,
  `one_shot_consumed=true`. El archivo one-shot dejó de existir en su ruta
  activa. `selector_controles` no apareció.
- **Emulador:** RetroArch PID `10087`, core
  `/usr/lib/libretro/fceumm_libretro.so` (`fceumm`). Orden del dispatcher:
  P1/P2 fueron las botoneras DragonRise.
- **Boot window:** PID vivo durante `20.01 s`, core presente y sin fatal en
  los logs consultados: `BOOT_OK`. Esto no implica `PASS`.
- **Game health en la comprobación inicial:** aún no había fila de
  `launch_events` mientras el dispatcher esperaba el cierre. El evento se
  generó tras la salida y queda documentado en la sección de resolución.
- **Salida:** se envió una vez `hotkeygen --send exit`. No cerró RetroArch en
  20 segundos. Después, `/isIdle=false`, `runningGame` aún identificaba Super
  Mario y RetroArch PID `10087` seguía presente. `emupid` reportó `0`, aunque
  el proceso RetroArch se confirmó directamente; se conserva la discrepancia.
- **Cleanup al fallar hotkeygen:** inicialmente `ERROR`; no se aplicó otra
  acción dentro de la prueba de arranque. La resolución posterior y el estado
  final están en `## RESOLUCIÓN DE SALIDA AUTOMÁTICA`.
- **Resultado del juego:** `BOOT_OK`; `PASS=NO EVALUADO`. La selección
  automática BOTONERA quedó validada en una ejecución real. El cierre terminó
  validado por terminación controlada; el cierre graceful sigue pendiente.
- **Piloto de 21:** `NO` hasta acordar o implementar una salida graceful
  compatible con el runtime personalizado. No se lanzó otro juego.

## RESOLUCIÓN DE SALIDA AUTOMÁTICA

No se lanzó otro juego ni se repitió `POST /launch`. Se investigó y cerró únicamente el Super Mario del INTENTO 3.

### Mecanismos y causa

- `/usr/bin/batocera-test` usa exactamente `hotkeygen --send exit`; luego consulta `/runningGame` cada 10 segundos hasta que el sistema deja de informar el juego. No tiene un límite de espera ni otra acción de salida en ese bucle.
- `/usr/bin/hotkeygen` implementa `--send` creando un teclado virtual con `evdev.UInput` sobre `/dev/uinput`; busca la acción en los archivos de mapping y emite el código asociado. El mapping del sistema relaciona `KEY_EXIT` con `exit`. Este flujo no consulta `DISPLAY` ni el contexto de hotkeys activo. `/dev/uinput` existe con permisos `0660 root:input`.
- El comando exacto se ejecutó en el HOST REAL y no cerró el emulador. Por tanto, no fue un problema de `DISPLAY` o de namespace. La acción efectivamente genera `KEY_EXIT`, pero no corresponde a una salida aceptada por la configuración efectiva de RetroArch: el dispatcher deja `input_enable_hotkey_btn/axis` e `input_exit_emulator_btn/axis` en `nul`. La explicación consistente con el código y el resultado es que RetroArch ignoró esa tecla no vinculada.
- RetroArch tiene `network_cmd_enable = "false"`; no hay interfaz de comandos local habilitada para pedirle el cierre. No se modificó la configuración.
- El watcher de salida ya existente en `controller_dispatcher` escucha Select+Start del P1 y llama `terminate()` al proceso del launcher. Se eligió su equivalente directo, una única `SIGTERM` al proceso exacto de RetroArch, después de validar PID, PPID y ROM.
- `/usr/bin/batocera-es-swissknife --emukill` no se ejecutó: intenta primero `hotkeygen --send exit`, espera 5 segundos por un proceso que encuentre como `emulatorlauncher` y después recorre descendientes con `SIGKILL`. No es una ruta segura para este árbol.

### Discrepancia de `--emupid`

`--emupid` busca el PID más nuevo que coincida con `pgrep -f -n emulatorlauncher`. En este lanzamiento el dispatcher importa `configgen.emulatorlauncher` en el mismo proceso y arranca RetroArch directamente como su hijo; no existe un proceso cuyo argv sea `emulatorlauncher`. La llamada aislada a `--emupid` devolvió `0`, aunque `ps` confirmó RetroArch PID `10087`. Los PIDs distintos que aparecieron al incluir `--emupid` en un comando de diagnóstico fueron falsos positivos: el propio texto del comando incluía `emulatorlauncher` en un filtro `awk`. Para este runtime, el árbol de procesos y `/runningGame` identifican el emulador con fiabilidad; `--emupid` no.

### Cierre y validación

- `2026-10-03T22:15:54-03:00`: se revalidó `/usr/bin/retroarch`, PID `10087`, PPID `9944` y la ROM exacta; se envió una sola `SIGTERM`. RetroArch desapareció aproximadamente 1 segundo después. No se envió otra señal. Tipo: `CONTROLLED_TERMINATION`.
- Estado final del HOST REAL: `/isIdle` = `true`; `/runningGame` = `NO GAME RUNNING`; EmulationStation PID `17529` activo; RetroArch, `controller_dispatcher`, `emulatorlauncher` y `selector_controles` ausentes; one-shot inactivo. `--emupid` aislado devolvió `0`. Cleanup: OK.
- `game_health.sqlite` registró evento `101`: `nes`, ROM exacta, `libretro`, core `fceumm`, PID `10087`, duración `3068.06745283399 s`, `exit_code=0`, `signal=NULL`, `status=INICIO_SOSTENIDO`, `requested_exit=0`, sin `relevant_error`. La DB no se modificó.
- Resultado: `BOOT_OK + CLEANUP_OK`. `PASS=NO EVALUADO`; no se certificaron imagen, audio, controles ni rendimiento. El cierre está validado mediante terminación controlada; el cierre graceful con `hotkeygen --send exit` sigue sin validar. No iniciar el piloto de 21 todavía: requiere acordar o implementar una salida graceful compatible con la configuración personalizada.

## BOOT TEST PILOTO 21 — EJECUCIÓN EN CURSO

Lote secuencial por sistema. Cada fila se guarda tras completar el cleanup. `BOOT_OK` no asigna `PASS`.

| # | Sistema | Juego | Boot | Emulador/Core | PID | Ventana | Exit | game_health | Cleanup | Precheck grace | API idle s | Procesos ausentes s | API→procesos s |
|---:|---|---|---|---|---:|---|---|---|---|---|---:|---:|---:|
| 01/21 | NES | Contra | BOOT_OK | libretro / RetroArch/fceumm | 18310 | 15s OK | SIGTERM 0.40s | 102 INICIO_SOSTENIDO | OK | n/a | n/a | n/a | n/a |
| 02/21 | NES | Mega Man 2 | BOOT_OK | libretro / RetroArch/fceumm | 21134 | 15s OK | SIGTERM 0.60s | 103 INICIO_SOSTENIDO | OK | n/a | n/a | n/a | n/a |


### HISTÓRICO — PRECHECK ABORTADO DEL CASO 03/21

El precheck de Castlevania detectó RetroArch PID `23336` con API `isIdle=true` y `NO GAME RUNNING`. El harness no creó one-shot ni envió POST. En la consulta posterior el PID ya no existía; la API seguía IDLE y EmulationStation `17529` activo, sin procesos runtime ni marcador. No se envió señal al PID porque no fue posible asociarlo inequívocamente a un lanzamiento. Conforme a la regla de parada por precheck no limpio, la primera ejecución se detuvo: **2 juegos lanzados**, ambos `BOOT_OK + CLEANUP_OK`; caso 03 registrado como `TEST_ERROR_PRECHECK`, sin lanzamiento. El piloto se reanudará desde Castlevania tras aplicar el grace check temporal.
| 03/21 | NES | Castlevania | BOOT_OK | libretro/fceumm | 20716 | 15s OK | SIGTERM no medidos | 104 INICIO_SOSTENIDO | OK | no (—) | NO MEDIDO | NO MEDIDO | NO MEDIDO |
| 04/21 | SNES | The Legend of Zelda: A Link to the Past | BOOT_OK | libretro/snes9x | 21936 | 15s OK | SIGTERM 0.00s | 105 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 05/21 | SNES | Street Fighter II | BOOT_OK | libretro/snes9x | 22690 | 15s OK | SIGTERM 0.00s | 106 INICIO_SOSTENIDO | OK | no (—) | 1.89 | 1.89 | 0 |
| 06/21 | SNES | Contra III: The Alien Wars | BOOT_OK | libretro/snes9x | 23093 | 15s OK | SIGTERM 0.00s | 107 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 07/21 | MEGADRIVE | Streets of Rage 2 | BOOT_OK | libretro/genesisplusgx | 23527 | 15s OK | SIGTERM 0.00s | 108 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 08/21 | MEGADRIVE | Golden Axe | BOOT_OK | libretro/genesisplusgx | 23942 | 15s OK | SIGTERM 0.00s | 109 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 09/21 | MEGADRIVE | Sonic the Hedgehog | BOOT_OK | libretro/genesisplusgx | 24364 | 15s OK | SIGTERM 0.00s | 110 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 10/21 | GBA | Metroid Fusion | BOOT_OK | libretro/mgba | 24779 | 15s OK | SIGTERM 0.00s | 111 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 11/21 | GBA | The Legend of Zelda: The Minish Cap | BOOT_OK | libretro/mgba | 25197 | 15s OK | SIGTERM 0.00s | 112 INICIO_SOSTENIDO | OK | no (—) | 2.15 | 2.15 | 0 |
| 12/21 | GBA | Advance Wars | BOOT_OK | libretro/mgba | 25610 | 15s OK | SIGTERM 0.00s | 113 INICIO_SOSTENIDO | OK | no (—) | 2.15 | 2.15 | 0 |
| 13/21 | DREAMCAST | Crazy Taxi | BOOT_OK | libretro/flycast | 26034 | 25s OK | SIGTERM 0.00s | 114 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 14/21 | DREAMCAST | Soulcalibur | BOOT_OK | libretro/flycast | 26524 | 25s OK | SIGTERM 0.00s | 115 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 15/21 | DREAMCAST | Marvel vs. Capcom 2 | BOOT_OK | libretro/flycast | 27000 | 25s OK | SIGTERM 0.00s | 116 INICIO_SOSTENIDO | OK | no (—) | 1.61 | 1.61 | 0 |
| 16/21 | PS2 | God of War | BOOT_OK | pcsx2/pcsx2 | 27498 | 35s OK | SIGTERM 0.00s | 117 INICIO_SOSTENIDO | OK | no (—) | 1.63 | 1.63 | 0 |
| 17/21 | PS2 | Gran Turismo 3: A-spec | BOOT_OK | pcsx2/pcsx2 | 28062 | 35s OK | SIGTERM 0.00s | 118 INICIO_SOSTENIDO | OK | no (—) | 1.89 | 1.89 | 0 |
| 18/21 | PS2 | Tekken 5 | BOOT_OK | pcsx2/pcsx2 | 28634 | 35s OK | SIGTERM 0.00s | 119 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 19/21 | MAME | Galaga | BOOT_OK | libretro/mame078plus | 29147 | 25s OK | SIGTERM 0.00s | 120 INICIO_SOSTENIDO | OK | no (—) | 2.15 | 2.15 | 0 |
| 20/21 | MAME | Street Fighter II | BOOT_OK | libretro/mame078plus | 29629 | 25s OK | SIGTERM 0.00s | 121 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |
| 21/21 | MAME | Donkey Kong | BOOT_OK | libretro/mame078plus | 30101 | 25s OK | SIGTERM 0.00s | 122 INICIO_SOSTENIDO | OK | no (—) | 1.88 | 1.88 | 0 |

## CIERRE — BOOT TEST PILOTO 21

- Lanzamientos reales: **21/21**; `BOOT_OK`: **21**; `FAIL_BOOT`: **0**; `CRASH`: **0**; `TEST_ERROR` de lanzamiento: **0**.
- Cleanup estable: **21/21**. El host terminó `IDLE_OK`, EmulationStation activo, one-shot inactivo y sin procesos del lanzamiento.
- Por sistema: NES **3/3**, SNES **3/3**, MegaDrive **3/3**, GBA **3/3**, Dreamcast **3/3**, PS2 **3/3**, MAME **3/3**.
- Precheck: transitorios de runtime confirmados **0**; persistentes confirmados **0**. Hubo dos detenciones históricas de precheck para Castlevania, ambas sin POST: PID 23336 desapareció antes de poder identificarse; PID 20038 fue un falso positivo del propio harness. Se corrigió el filtro temporal para clasificar sólo por ejecutable/comm. Castlevania luego arrancó como secuencia 03 y completó cleanup.
- En los 18 cleanups con medición del lote reanudado, API idle y procesos ausentes aparecieron en la misma muestra; la diferencia máxima observada API idle→proceso ausente fue **0,00 s a resolución de sondeo de 250 ms**. Los dos juegos NES previos al cambio del harness tampoco tienen esta métrica. Para Castlevania 03 el helper tuvo un `NameError` tras SIGTERM: la comprobación independiente confirmó IDLE/procesos ausentes, pero sus tiempos exactos quedaron **sin medir**.
- `PASS` asignados: **0**. `BOOT_OK` sólo acredita el arranque sostenido y cleanup; no certifica imagen, audio, controles ni rendimiento.
- El mecanismo es **apto con ajustes** para una escala gradual: mantener el precheck corregido, el retardo de API de arranque y la validación posterior a SIGTERM. No se inició ninguna auditoría masiva.
