> Snapshot histórico; los valores de red y credenciales se saneaban en esta copia cuando correspondía. No usar como estado vigente; consultar `ARCADE_CURRENT_STATE.md`.

# COMPLEMENTO DE AUDITORÍA — 12/11/2026

**Alcance:** solo SMART, EmulationStation/VSync, P1–P4 y HDMI/Xorg/NVIDIA. Consultas host de solo lectura autorizadas. No se iniciaron SMART tests, no se tocaron controles, configuración, servicios, TV ni procesos. Se generó únicamente este informe.

## 1. SMART actual

| Métrica | Crucial BX500 240 GB | Seagate ST1000DM010 1 TB | Toshiba MQ04UBB400 4 TB |
|---|---:|---:|---:|
| Serial parcial | `2246****C948` | `ZN1J****` | `Z0II****` |
| Power_On_Hours | 12.159 h | 21.853 h | 1.411 h |
| Power_Cycle_Count | 488 | 16.948 | 10 |
| Unexpected Power Loss / Unsafe Shutdown | 407 | No aplica/atributo no presentado | 0 `Power-Off_Retract_Count` |
| Reallocated | 0 NAND blocks / 0 eventos | 8 | 0 |
| Reported_Uncorrect | 0 | 14 | Atributo no reportado; Error Log sin errores |
| Current_Pending | 0 | 0 | 0 |
| Offline_Uncorrectable | 0 | 0 | 0 |
| UDMA_CRC_Error_Count | 0 | 0 | 0 |
| ATA Error Count | SMART Error Log no soportado | 14 (solo muestra los 5 más recientes) | No Errors Logged |
| Temperatura actual | 35 °C (mín/máx 23/46) | 31 °C (mín/máx indicada 24/31) | 29 °C (mín/máx 11/39) |
| SMART overall-health | PASSED | PASSED | PASSED, basado en atributos |
| Observación | Attribute 202 raw=6, normalized=94; ver nota abajo | Atributos de error estables respecto de septiembre | El bridge USB no entrega el ATA SMART Status completo; smartctl advierte respuesta incompleta |

**Crucial, atributo 202:** `smartctl` lo etiqueta `Percent_Lifetime_Remain`, con raw 6 y valor normalizado 94. La guía de Micron identifica el ID 202 como **Percentage Lifetime Used**; usando esa definición, raw 6 indica 6% utilizado (no 6% restante). Se conserva el raw y no se interpreta como desgaste crítico. La semántica del nombre RAW específico puede variar por firmware. [Guía oficial de SMART de Micron](https://assets.micron.com/adobe/assets/urn%3Aaaid%3Aaem%3Ab6bd6cc5-b485-4f75-a88b-f2e061ef9a91/original/as/storage-executive-cli-user-guide.pdf).

Los tres informes se obtuvieron con `smartctl -a`; no se ejecutó `smartctl -t` ni otra prueba. SMART PASSED no significa que cada disco sea perfecto.

## 2. Seagate — septiembre vs ahora

| Métrica | Septiembre | Ahora | Cambio |
|---|---:|---:|---:|
| Power_On_Hours | 21.552 | 21.853 | +301 h |
| Power cycles | 16.941 | 16.948 | +7 |
| Reallocated | 8 | 8 | Sin cambio |
| Reported_Uncorrect | 14 | 14 | Sin cambio |
| ATA errors | 14 | 14 | Sin cambio |
| Current_Pending | 0 | 0 | Sin cambio |
| Offline_Uncorrectable | 0 | 0 | Sin cambio |
| UDMA CRC | No reseñado en baseline | 0 | Sin contador actual |
| Temperatura | No disponible en baseline consultado | 31 °C | Fotografía actual |
| Uso | ~90% | ~90% | Igual aproximadamente |

**Clasificación: ESTABLE en contadores desde septiembre.** No aumentaron los sectores reasignados, errores reportados/ATA ni sectores pendientes. Los 8 reasignados y 14 errores ATA siguen siendo historial real, y el disco continúa al 90% de uso. No hay evidencia para recomendar reemplazo urgente por degradación reciente; conviene mantener reemplazo preventivo planificado por antigüedad, ocupación y errores persistentes. El resultado PASSED no borra esos antecedentes.

## 3. VSync

- Archivo de configuración activa: `/userdata/system/configs/emulationstation/es_settings.cfg`.
- El archivo, modificado el 10/10, **no contiene una clave explícita `VSync` ni `FpsLimit`**; no se encontró otra copia activa de `es_settings.cfg`.
- Por tanto, **no se puede confirmar el valor efectivo cargado por la instancia**. La entrada explícita `VSync=true` del fix de septiembre no persiste en el archivo actual; esto no demuestra que el comportamiento efectivo sea `false`, porque podría regir el default de EmulationStation.
- No se cambió VSync ni FpsLimit.

**Respuesta:** `VSync=true` efectivo = **NO DETERMINABLE**. La configuración no tiene un valor explícito que permita afirmarlo.

## 4. CPU actual de EmulationStation

- PID real: **2929**, comando `emulationstation --exit-on-reboot-required --windowed`.
- Se tomaron 10 muestras con `top` en intervalos de 6 segundos, de 21:35:13 a 21:36:07 ART (aprox. 54 segundos entre muestras; duración efectiva cercana a un minuto).
- CPU ES: **mínimo 30,0%, promedio ~30,2%, máximo 30,3% de un núcleo**.
- RSS: **369,4 MiB** en las muestras; virtual 2.633 MiB.
- Threads: **23**; estado en reposo `S`, con una muestra `R`.
- Load average observado: aprox. **0,17–0,32 / 0,17–0,20 / 0,20–0,21** (1/5/15 minutos).
- CPU total del sistema, derivada del resumen por CPU lógico de las 10 muestras: aprox. **2,3% promedio del equipo** (rango aproximado 2,0–4,1%); `top` presentó los 12 CPU por separado.
- La sesión X0 respondió y HDMI estaba conectado en el modo de escritorio; el muestreo corresponde a ES activo en esa sesión.

Comparación: antes del fix ~100% de un hilo; después ~30,24%; ahora 30,0–30,3%. **La mejora de consumo se conserva.** No demuestra por sí sola el valor interno de VSync, que sigue sin dato explícito.

**Clasificación CPU: FIX DE RENDIMIENTO CONSERVADO.**

## 5. P1–P4 — configuración, kernel y dispatcher

Todos los DragonRise actuales son VID/PID `0079:0006`. Kernel enumera cuatro unidades; mapping actual por ruta y symlink:

| Jugador | Configuración del perfil (`usb_port`) | USB path | event | js | VID/PID | Dispatcher |
|---|---:|---|---|---|---|---|
| P1 | 5 | `pci-0000:00:14.0-usb-0:5:1.0` | `event17` | `js0` | `0079:0006` | P1 → `/dev/input/event17` |
| P2 | 6 | `pci-0000:00:14.0-usb-0:6:1.0` | `event18` | `js1` | `0079:0006` | P2 → `/dev/input/event18` |
| P3 | 8 | `pci-0000:00:14.0-usb-0:8:1.0` | `event20` | `js3` | `0079:0006` | P3 → `/dev/input/event20` |
| P4 | 7 | `pci-0000:00:14.0-usb-0:7:1.0` | `event19` | `js2` | `0079:0006` | P4 → `/dev/input/event19` |

- **Perfil activo:** P1/P2/P3/P4 = **5/6/8/7**.
- **Enumeración kernel:** puertos 5/6/7/8; 4 DragonRise; paths `event17/18/19/20`, `js0/1/2/3` respectivamente.
- **Dispatcher:** `--diagnose` enumeró 4, produjo arcade identities P1=`event17`, P2=`event18`, P3=`event20`, P4=`event19`, `duplicates=false`.
- Se abrió cada joystick con SDL de forma normal para diagnóstico y se cerró; no se hizo `EVIOCGRAB` ni grab exclusivo.
- El orden `js0...js3` solo es enumeración: P3 usa `js3`, P4 `js2` debido a su path, no a índice de jugador.

**¿Cambió respecto de septiembre? Sí, cambió realmente el perfil:** septiembre tenía P1/P2/P3/P4 = **8/5/6/7**. La configuración actual es **5/6/8/7**. No fue una interpretación errónea de esta auditoría: JSON y diagnóstico del dispatcher confirman el orden actual. La documentación de controles actualizada el 09/10 también registra P1 central izquierda→USB5, P2 central derecha→USB6, P3 lateral izquierda→USB8, P4 lateral derecha→USB7, identificado previamente mediante pulsaciones. Por ello, el cambio parece documentado e intencional. Hoy están presentes los cuatro controles y dispatcher aplica el perfil sin duplicados; no se repitió una prueba de botones dentro de juegos.

**Respuesta funcional:** la asignación actual corresponde a la identificación física documentada más reciente; no corresponde al mapa de septiembre. El funcionamiento de cada botonera en juego no se volvió a probar.

## 6. Controller dispatcher

- Path: `/userdata/system/el_gordo_tools/controller_dispatcher`
- Tamaño: **50.819 bytes**
- SHA-256: `a60be89fb45ea27ec4f7c3f546e088c7ff3da140bccfe1c6a37e5b14ec581c45`
- Sintaxis: parseo Python AST **OK**
- Perfil activo: `/userdata/system/configs/el_gordo_controller_profiles/controller_technical.json`
- Referencias de lanzamiento: `es_systems_el_gordo.cfg`; diagnóstico actual exitoso, cuatro dispositivos, sin duplicados.
- Errores recientes en log (10–11/10, no del boot actual): watcher de salida P1 recibió `Errno 19` para un event desaparecido durante pruebas; intentos FIFA Street 2 + JOYSTICK reportaron 2 controles externos cuando el perfil requería 4. No son fallos de la enumeración actual de las cuatro botoneras DragonRise.
- No hay entrada del dispatcher posterior al 11/10 en los logs consultados.

**Estado: ESTABLE EN CONFIGURACIÓN/SINTAXIS; los errores de octubre son históricos de sesiones de prueba.** No se reemplazó ni editó.

## 7. HDMI / Xorg / NVIDIA

- Socket X: `/tmp/.X11-unix/X0` presente; `xrandr --display :0 --query` respondió correctamente.
- XRandR: **HDMI-0 connected primary**, `1920x1080+0+0`, modo seleccionado **1920×1080 @ 60,00 Hz**.
- EmulationStation PID 2929 activo; Openbox activo. La consulta gráfica funciona. El proceso no aparece con nombre literal `Xorg` en la lista consultada, pero el servidor X0 responde.
- sysfs DRM todavía informa conectores NVIDIA desconectados. Es la contradicción conocida: DRM disconnected frente a XRandR connected. Con ES activo, XRandR mostrando el televisor y sin error Xid/NVRM fatal/segfault nuevo, se clasifica **ESTADO CONOCIDO / SIN REGRESIÓN FUNCIONAL**.
- NVIDIA: módulo **580.126.09** cargado. En el boot aparece su carga normal; no se halló `Xid`, `GPU has fallen off the bus`, NVRM fatal ni segfault de Xorg en los logs consultados.
- `nvidia-smi` no está instalado; temperatura/uso GPU no consultados.
- No hubo hotplug, cambio de salida, ni acción sobre EDID/Xorg/driver.

## 8. Credenciales expuestas anteriormente (sin valores)

| Tipo | Archivo origen | Servicio afectado | ¿Valor completo llegó a salida/log? | Recomendación |
|---|---|---|---|---|
| Contraseña Wi-Fi (`wifi.key`) | `/userdata/system/batocera.conf` | WLAN / acceso a la red Wi-Fi configurada | **Sí**, el campo completo apareció en la salida de herramienta de la conversación al mostrar el archivo. No se escribió a un log local por esta auditoría. | Rotar la contraseña Wi-Fi desde el método habitual cuando el usuario lo autorice. |
| Contraseña de ScreenScraper (`ScreenScraperPass`; también apareció el usuario de cuenta) | `/userdata/system/configs/emulationstation/es_settings.cfg` | Cuenta ScreenScraper / scraping | **Sí**, campo completo y usuario aparecieron en la salida de herramienta de la conversación. No se escribió a un log local por esta auditoría. | Rotar la contraseña de ScreenScraper. El usuario de cuenta no es secreto, pero también quedó expuesto. |

No se repiten los valores aquí. No se rotó ninguna credencial. La salida es parte del historial visible de esta conversación/herramienta; la auditoría no creó un archivo adicional de secretos.

## 9. Score corregido

**Score anterior provisional: 66/100**  
**Score corregido: 84/100** (**+18**)

| Área | Puntaje corregido |
|---|---:|
| Hardware | 9/10 |
| Almacenamiento | 12/15 |
| Temperaturas | 9/10 |
| GPU | 8/10 |
| Batocera | 9/10 |
| EmulationStation | 8/10 |
| Controles | 8/10 |
| Estabilidad | 9/10 |
| Backups | 3/5 |
| Mantenimiento | 4/5 |
| Experiencia de usuario | 5/5 |
| **TOTAL** | **84/100** |

Sube porque se pudo consultar SMART directamente, ES mostró el consumo post-fix, los cuatro mandos están presentes y el dispatcher coincide con el perfil vigente, y HDMI funciona en XRandR con ES activo. No se penalizan media ya corregida, servicios fantasma eliminados, Xenia coincidente ni la contradicción DRM conocida sin regresión funcional. Se conserva una deducción por disco Seagate con ocupación alta y errores históricos, valor VSync/FpsLimit no explícito, límites del SMART Toshiba a través de USB y la exposición de credenciales que requiere gestión posterior.

## 10. Próximos pasos

1. **Rotar contraseña Wi-Fi y ScreenScraper** en una etapa aparte, sin reutilizar la salida anterior.
2. **Planificar el reemplazo/descarga de espacio del Seagate**: no hay degradación SMART desde septiembre ni necesidad de emergencia demostrada, pero está al 90% y conserva 8 reasignados/14 errores ATA históricos.
3. **Confirmar VSync efectivo en la interfaz/configuración de ES** cuando sea posible. El CPU post-fix se conserva, pero la clave explícita está ausente; no cambiarla hasta conocer el valor efectivo.

**Conclusión:** Seagate **ESTABLE en los contadores**; VSync efectivo **NO DETERMINABLE**; reducción de CPU de ES **CONSERVADA**; mapa P1–P4 **cambió realmente** a 5/6/8/7 y está aplicado sin duplicados según dispatcher, coherente con la identificación física documentada en octubre; HDMI/XRandR **sin regresión funcional**; el contraste DRM/XRandR sigue siendo el estado conocido.
