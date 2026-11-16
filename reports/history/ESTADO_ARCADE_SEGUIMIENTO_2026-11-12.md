> Snapshot histórico; los valores de red y credenciales se saneaban en esta copia cuando correspondía. No usar como estado vigente; consultar `ARCADE_CURRENT_STATE.md`.

# ESTADO DEL ARCADE — SEGUIMIENTO NOVIEMBRE 2026

**Fecha de referencia:** 12/11/2026, 21:05 ART  
**Modalidad:** auditoría de seguimiento read-only. No se modificaron configuraciones, servicios, ROMs, BIOS, saves ni archivos activos. La única escritura de esta etapa es este informe.  
**Límite importante:** el contexto de ejecución permite leer parte de `/userdata`, sysfs y logs del arranque, pero no expone los nodos `/dev/sd*`, `/dev/input`, la sesión DBus ni los procesos gráficos del host. `ps` solo muestra el proceso de esta sesión. Por ello no se pudieron medir SMART actual, EmulationStation en vivo, conexiones de audio/Bluetooth ni tráfico/IP. Los datos ausentes se marcan como **NO DETERMINABLE**, no se infieren.

## 1. Resumen ejecutivo

- La plataforma detectada sigue siendo Batocera 43co.1/43o.1, kernel 6.18.16, i5-12400F, GTX 1060 3 GB, 16 GB RAM y los tres discos conocidos.
- Mejoró respecto al baseline de septiembre: temperatura CPU observada 46 °C vs 53 °C; la media inválida ya no está en las cuatro rutas afectadas y ambos gamelists examinados parsean como XML válido.
- No se confirmó una regresión física de controles: el kernel enumeró cuatro DragonRise, aunque el perfil cambió el orden P1–P3 y no se pudieron abrir los dispositivos de entrada.
- La pantalla tiene evidencia mixta: `display.log` eligió HDMI-0, 1920×1080 y lanzó ES; DRM/NVIDIA en el arranque registraron conectores desconectados y `Cannot find any crtc or sizes`. Se clasifica **POSIBLE REGRESIÓN / ESTADO CONTRADICTORIO**, sin intervención.
- El fix VSync no puede confirmarse: `es_settings.cfg` ya no tiene una clave `VSync` explícita y ES no es visible para medirlo. No afirmar que falló ni que sigue aplicado.
- El Seagate sigue al 90% de uso; SMART actual no se pudo leer. No hay base para afirmar si sus contadores empeoraron desde septiembre.
- `custom_service` y el generador Xenia persistente coinciden por SHA-256; `hdmi_recovery` y Zaparoo ya no están declarados en `system.services`.
- Se observaron temperaturas normales en reposo. No se hizo carga ni prueba de juegos.
- El baseline/archivo tar de septiembre y backups puntuales siguen presentes; el directorio extraído y el tar suman unos 35,4 GB aparentes.
- Próximos pasos: medir SMART sin self-test, recuperar una observación desde la consola Batocera para VSync/HDMI/controles y decidir una política para el duplicado del backup.
- Durante esta inspección se imprimieron accidentalmente campos de credenciales desde la configuración en la salida de la herramienta. Los valores se omiten de este informe y no se repiten aquí; se recomienda rotarlos fuera de esta auditoría.

## 2. Score general

**66/100 — provisional, con evidencia incompleta del runtime vivo.** La puntuación es de estado observado; parte de la reducción corresponde a telemetría inaccesible, no a fallos demostrados.

| Área | Puntaje | Motivo de la reducción |
|---|---:|---|
| Hardware | 9/10 | Componentes principales coinciden con el baseline; solo fotografía de hardware, no inspección física. |
| Almacenamiento | 7/15 | Seagate al 90%, envejecido con errores históricos; SMART actual inaccesible. |
| Temperaturas | 9/10 | CPU 46 °C y placa 17/28 °C observados; sin GPU/SSD/HDD y sin carga. |
| GPU | 7/10 | Módulo propietario cargado; faltan telemetría y estado gráfico inequívoco. |
| Batocera | 9/10 | Versión y kernel identificados; varias comprobaciones de runtime no visibles. |
| EmulationStation | 4/10 | Configuración y logs consultables, pero no PID/CPU/RSS/renderer actual. |
| Controles | 5/10 | Cuatro unidades USB enumeradas; perfil difiere del baseline y asignación física no validable en este contexto. |
| Estabilidad | 6/10 | Sin Xid/oom/errores críticos visibles en el boot consultado; hay recovery ext4 y avisos gráficos/USB. |
| Backups | 3/5 | Baseline verificado históricamente y presente, pero copia extraída + tar ocupan ~35,4 GB; último baseline es septiembre. |
| Mantenimiento | 3/5 | Servicios fantasma ya no declarados; quedan datos SMART, VSync, HDMI y controles por confirmar. |
| Experiencia de usuario | 4/5 | Resolución configurada a 1080p y arranque de ES registrado; no fue posible ver interacción real. |

## 3. Hardware actual

| Componente | Baseline anterior | Actual observado | Cambio |
|---|---|---|---|
| Hostname | BATOCERA | BATOCERA | Igual |
| Sistema | Batocera 43.1 | `43co.1 2026/05/29 04:36` (OS reporta `43o.1`) | Misma base; etiqueta personalizada |
| Kernel / arquitectura | 6.18.16 / x86_64 | 6.18.16 / x86_64 | Igual |
| Motherboard | Gigabyte H610M K DDR4 | Gigabyte H610M K DDR4 | Igual |
| BIOS | FH, 12/02/2025 | FH, 12/02/2025 | Igual |
| CPU | Intel i5-12400F, 6C/12T | Intel i5-12400F, 6C/12T; governor `performance` | Igual |
| RAM | 16 GB | 15 GiB visibles, 2,4 GiB usados, 13 GiB disponibles; swap 0 | Igual capacidad; presión no observada |
| GPU | NVIDIA GTX 1060 3 GB | GP106 GTX 1060 3 GB, PCI `01:00.0`; driver módulo 580.126.09 | Igual |
| PCIe GPU | 8 GT/s ×16 en septiembre | No medible con evidencia disponible | Sin comparación actual |
| SSD | Crucial BX500 240 GB | CT240BX500SSD1, 223,6 GiB, UUID `ae45e54a-04b4-4a20-9f70-ddf57c580413`, `/userdata`, ext4, 60% usado | Mismo dispositivo; SMART inaccesible |
| HDD Seagate | ST1000DM010, 1 TB | ST1000DM010-2EP102, 931,5 GiB, UUID `2c6876be-3640-4aa1-b3cf-d5f7b4e01621`, `/media/BATOCERA_ROMS`, ext4, 90% usado | Mismo modelo; uso sigue alto |
| Toshiba USB | MQ04UBB400, 4 TB | MQ04UBF100 reportado como “External USB 3.0”, 3,6 TiB, UUID `6d235267-5a41-462d-8a02-68b6c952068c`, `/media/ROMS`, ext4, 30% usado | Capacidad/rol igual; modelo informado varía en sufijo, validar solo si importa |
| Wi-Fi | TP-Link RTL8188EU | TP-Link TL-WN722N v2/v3, RTL8188EU; el kernel registró asociación Wi-Fi | Igual tecnología; IP no visible |
| Bluetooth | TP-Link UB500 | TP-Link UB500 `2357:0604`, driver `btusb` cargado | Igual; estado de BlueZ no consultable |
| Ethernet | Realtek RTL8111/8168 | Realtek `10ec:8168`, `r8169`; enlace reportó Down al boot | Sin cable/enlace en ese momento |
| USB | Intel xHCI | Controlador Intel xHCI; hubs, 4 DragonRise, UB500, Wi-Fi y WCH detectados | Inventario consistente |
| Audio | NVIDIA HDMI + HDA | NVIDIA HDA enumerado; `audio.device` configurado a HDMI-surround, volumen 40 | Configuración coincide; stream activo no validable |

**Uptime observado:** aproximadamente 5 minutos al comenzar la consulta (boot cerca de 20:56 ART). No se atribuye el reinicio a una causa; en el arranque se registró recovery ext4.

## 4. Cambios desde septiembre

| Área | Septiembre | Noviembre | Tendencia |
|---|---|---|---|
| CPU EmulationStation | Antes del fix, alrededor de 100% de un hilo; después del fix 30,24% | Sin PID ni muestreo del host; no medible durante 60 s | ⚠ NO DETERMINABLE |
| Media | Cuatro archivos inválidos retirados; fix verificado en septiembre | Las cuatro rutas respaldadas siguen ausentes; no hay errores nuevos equivalentes en los logs consultados; XML de PS2/GBA válido | ✅ RESUELTO / SIN REGRESIÓN OBSERVADA |
| HDMI | Usuario luego lo declaró resuelto; snapshot de septiembre aún tenía discrepancia DRM/Xorg | `display.log` aplicó HDMI-0/1920×1080; DRM/NVIDIA muestran desconexiones y falta de CRTC | ⚠ POSIBLE REGRESIÓN / ESTADO CONTRADICTORIO |
| Temperaturas | CPU package 53 °C, máximo 55 °C | Package 46 °C; placa 17/28 °C | ⬆ MEJORÓ en esta fotografía |
| HDD Seagate | 90%, 21.552 h, 16.941 ciclos, 8 reasignados, 14 `Reported_Uncorrect`, 14 errores ATA, pending/offline 0 | Uso 90%; SMART inaccesible | ➡ Uso igual; salud SMART no comparable |
| SSD | 407 `Unexpected_Power_Loss_Ct` históricos | SMART inaccesible; hubo recovery ext4 en boot actual | ⚠ Sin comparación SMART; observación continúa |
| Toshiba | 4 TB; recovery ext4 en septiembre | 3,6 TiB; 30% usado; recovery ext4 en boot actual | ➡ Capacidad/rol igual; uso previo no comparable |
| Controles | P1/P2/P3/P4 = USB 8/5/6/7 | Perfil actual = USB 5/6/8/7; cuatro DragonRise enumerados | ⚠ CAMBIÓ la asociación documentada; validar en host |
| USB | Sin resets; warning descriptor WCH ya presente | No se vio reset/desconexión; vuelve a aparecer descriptor inválido WCH | ➡ Warning recurrente, no nuevo |
| GPU | GTX 1060/580.126.09, sin Xid en el boot auditado | Mismo modelo/driver; sin Xid visible; estado DRM ambiguo | ➡ Driver/modelo igual; HDMI pendiente de confirmar |
| Xorg | Activo en septiembre | Log de boot configura salida y lanza ES; proceso no visible desde esta sesión | ⚠ No verificado en vivo |
| Backups | Se creó baseline principal y backups puntuales en septiembre | Los mismos archivos siguen presentes; 18,85 GB carpeta + 16,58 GB tar | ➡ Integridad histórica disponible; duplicación de espacio |
| Servicios | `zaparoo_service` y `hdmi_recovery` estaban declarados pero sin destino operativo | Solo `ssh custom_service` declarado; servicios HDMI/Zaparoo ausentes | ✅ LIMPIADO en configuración actual |
| Espacio | HDD 90% | HDD 90%, SSD 60%, Toshiba 30%, pool 43% | ➡ HDD igual; restante sin comparación homogénea |
| Errores | WCH descriptor inválido; sin Xid/USB resets/OOM en boot de septiembre | WCH descriptor inválido; warning `nvidia-drm Cannot find any crtc or sizes`; sin Xid/OOM visibles | ⚠ Avisos recurrentes/estado gráfico ambiguo |

## 5. Problemas resueltos

- **Media corrupta:** las cuatro imágenes respaldadas en `EMULATIONSTATION_MEDIA_FIX_2026-09-26_122318` continúan ausentes en sus rutas activas. Los `gamelist.xml` examinados (`ps2`, `gba`) parsean bien. Los hashes de esos XML cambiaron desde la copia del 26/09, pero el contenido actual es XML válido; no se infiere corrupción por la diferencia.
- **Referencia fantasma `hdmi_recovery`:** ya no aparece en `system.services` y no existe archivo de servicio bajo `/userdata/system/services`. Clasificación: **YA LIMPIADO**. Hay una configuración EDID preparada bajo `userdata` comentada como inactiva; no se modificó.
- **Referencia de Zaparoo:** ya no figura en `system.services`, no existe `zaparoo_service` en el directorio de servicios ni target localizado. Clasificación: **YA LIMPIADO / SIN EVIDENCIA DE USO ACTUAL**.
- **Xenia persistente:** fuente y generador activo tienen SHA-256 idéntico `ca0b6b33…98cc188`; corresponde al hash de parche registrado en `custom_service`. Clasificación: **COINCIDE / MANTENER**.
- No se reabren como activos la media histórica ni el HDMI histórico por sí solos; solo se registra la discrepancia gráfica actual para verificación pasiva posterior.

## 6. Problemas que reaparecieron

- **No se confirmó un problema anterior reaparecido.** El único punto con indicios actuales es HDMI: estado DRM/NVIDIA desconectado, contrapuesto al log de configuración exitoso. Se etiqueta posible regresión, no fallo demostrado.
- Recovery ext4 en `sda2`, `sdb1` y `sdc1` ya estaba documentado en septiembre y aparece otra vez en el boot actual. Continúa **EN OBSERVACIÓN**; no es una nueva investigación ni evidencia suficiente por sí sola para afirmar daño.

## 7. Problemas nuevos

1. **Discrepancia actual de mapping P1–P3:** septiembre establecía P1=USB8, P2=USB5, P3=USB6, P4=USB7. El perfil actual establece P1=USB5, P2=USB6, P3=USB8, P4=USB7. La documentación de controles de octubre también recoge el nuevo orden; podría ser intencional, pero no se pudo validar físicamente. **Pendiente de confirmación, no corregir a ciegas.**
2. **VSync no explícito:** `es_settings.cfg` modificado el 10/10 no contiene la clave `VSync`; por tanto el valor efectivo es desconocido. No confirma regresión, pero impide confirmar el fix.
3. **Avisos de arranque actuales:** `nvidia-drm` informó `Cannot find any crtc or sizes`; el kernel también registró un descriptor USB inválido del WCH, `pata_legacy` con `request_irq(14)` ocupado y `NFSD` sin inicializar client recovery tracking (`-110`). Son warnings/error de arranque; no se observó evidencia de impacto de usuario para los últimos tres.
4. **Exposición accidental de credenciales en salida de auditoría:** los campos `wifi.key` y `ScreenScraperPass` quedaron visibles en salida de herramienta al leer archivos completos. No se incluyen en el informe. Recomendar rotación controlada de ambos secretos como acción de seguridad posterior.

No se confirma degradación nueva de discos porque SMART no estuvo accesible.

## 8. EmulationStation

- Log de arranque 12/11: `display.log` indica que se aplicó 1920×1080 a HDMI-0 y se lanzó EmulationStation.
- PID, uptime del proceso, CPU promedio, hilo principal, RSS, threads y renderer actual: **NO DETERMINABLES**; `ps` del contexto no ve los procesos del host.
- No fue posible tomar las muestras durante 60 segundos solicitadas. Comparación: pre-fix ~100% de un hilo; post-fix 30,24%; actual no medido.
- `es_settings.cfg`: ThemeSet `es-theme-carbon`; no contiene `VSync` ni `FpsLimit` explícitos. Resolución se observa en `display.log`, no en el proceso vivo.
- OpenGL vendor/renderer y aceleración: no consultables desde esta sesión. La presencia/carga del driver NVIDIA no demuestra por sí sola qué renderer usa ES.
- Logs actuales específicos de ES no aparecen con timestamp del 12/11; los logs de lanzamiento y selector más recientes son del 11/10. Sin evidencia de epidemia actual de media.
- SQLite `game_health.sqlite`: `PRAGMA quick_check` de solo lectura devuelve `ok`; archivo de 90.435.584 bytes, última modificación 11/10.
- **Clasificación VSync:** **NO DETERMINABLE**. No cambiar VSync/FpsLimit.

## 9. GPU / NVIDIA / Xorg

- GPU: NVIDIA GP106 / GeForce GTX 1060 3 GB en `01:00.0`; driver de kernel `580.126.09`; módulos `nvidia`, `nvidia_modeset`, `nvidia_uvm`, `nvidia_drm` cargados. PCIe actual no consultable.
- `nvidia.log` del boot reconoce la GPU, selecciona `legacy580` y carga módulos sin fatal reportado.
- `nvidia-smi` no está disponible; temperatura, utilización, fan y VRAM: **NO DETERMINABLES**.
- En el boot actual `display.log` detecta HDMI-0, selecciona 1920×1080 y llega a “Launching EmulationStation”. En paralelo, sysfs muestra conectores DRM desconectados y dmesg dice `Cannot find any crtc or sizes`.
- Xorg no se pudo enumerar en `ps`; no se pudo consultar XRandR/OpenGL en vivo.
- No aparece `Xid`, `GPU has fallen off the bus` ni NVRM fatal en el dmesg filtrado de este boot.
- **Estado:** NVIDIA cargada; Xorg/HDMI con evidencia mixta. **POSIBLE REGRESIÓN a confirmar de forma pasiva desde la consola; no tocar NVIDIA, Xorg ni EDID.**

## 10. Temperaturas

| Sensor | Actual observado | Septiembre | Evaluación |
|---|---:|---:|---|
| CPU package | 46 °C | 53 °C (máx observado 55 °C) | NORMAL en reposo; mejora puntual |
| CPU cores | 41–46 °C | No separarado en resumen | NORMAL |
| Motherboard / ACPI | 17 °C y 28 °C | No comparable | NORMAL; nombres corresponden a zonas ACPI |
| SSD | No disponible | SMART anterior con dato de pérdida de energía, temp no reseñada aquí | NO DETERMINABLE |
| HDD Seagate | No disponible | SMART histórico con temperatura reportada en auditoría; sin valor comparable actual | NO DETERMINABLE |
| Toshiba | No disponible | No comparable | NO DETERMINABLE |
| GPU | No disponible | Sin telemetría en septiembre | NO DETERMINABLE |

No se encontró throttling, alarma térmica, thermal shutdown ni OOM en los fragmentos consultados. No hubo carga ni stress test. **Clasificación CPU/placa: NORMAL en la fotografía disponible; salud térmica completa: A VIGILAR por falta de GPU y discos.**

## 11. Almacenamiento

| Unidad | Filesystem / UUID | Mount / modo visible | Uso / libre | SMART |
|---|---|---|---|---|
| Crucial BX500, 240 GB | ext4 / `ae45e54a-04b4-4a20-9f70-ddf57c580413` | `/userdata`, RW en tabla de mounts | 121 GiB usados / 81 GiB libres, 60% | **No disponible**: `/dev/sda` no existe en el namespace de esta ejecución |
| Seagate ST1000DM010, 1 TB | ext4 / `2c6876be-3640-4aa1-b3cf-d5f7b4e01621` | `/media/BATOCERA_ROMS`, RW en tabla de mounts | 783 GiB / 88 GiB libres, 90% | **No disponible** |
| Toshiba externo 4 TB | ext4 / `6d235267-5a41-462d-8a02-68b6c952068c` | `/media/ROMS`, RW en tabla de mounts | 1.012 GiB / 2,5 TiB libres, 30% | **No disponible** |

Los nodos de bloque están ocultos aunque `lsblk` expone inventario; `smartctl -a` sobre los tres `/dev/sdX` respondió “No such device”. No se inició self-test. Los números de serie se omiten parcialmente por privacidad. No puede confirmarse temperatura, horas, sectores ni errores SMART de noviembre.

## 12. Seagate 1 TB — comparación

| Atributo | Septiembre | Noviembre | Resultado |
|---|---:|---:|---|
| Horas | 21.552 | No disponible | No comparar |
| Power cycles | 16.941 | No disponible | No comparar |
| Reallocated | 8 | No disponible | No comparar |
| `Reported_Uncorrect` | 14 | No disponible | No comparar |
| `Current_Pending` | 0 | No disponible | No comparar |
| `Offline_Uncorrectable` | 0 | No disponible | No comparar |
| ATA errors | 14 históricos | No disponible | No comparar |
| Uso | ~90% | 90% (783 GiB usados, 88 GiB libres) | ➡ Igual aproximadamente |
| Temperatura | Dato previo no verificado aquí | No disponible | No comparar |

**Conclusión: NO DETERMINABLE respecto de degradación desde septiembre.** Los atributos antiguos y el 90% de ocupación justifican mantenerlo como riesgo y preparar una sustitución planificada con copia verificada; no hay evidencia actual suficiente para declarar “reemplazo recomendado urgente”. SMART PASSED, si existiera, tampoco equivaldría a disco perfecto.

## 13. Controles / USB

- El kernel enumeró cuatro DragonRise `0079:0006` en los puertos raíz 5, 6, 7 y 8. También detectó WCH `1a86:e30a`, TP-Link UB500 y Wi-Fi USB.
- Perfil actual `controller_technical.json`: **P1→5, P2→6, P3→8, P4→7**. Baseline septiembre: **P1→8, P2→5, P3→6, P4→7**. La documentación de controles editada en octubre recoge las asociaciones actuales central/lateral, lo que sugiere cambio documentado, no necesariamente regresión.
- El diagnóstico del dispatcher reportó P1 ausente en USB5, pero `/dev/input/by-path` no existe en este contexto aislado. No se interpreta como control físicamente desconectado.
- `event`/`js`, VID/PID por rol y duplicados: no verificables; el log de kernel sí confirma cuatro DragonRise enumerados.
- USB reset/disconnect no aparece en el dmesg filtrado. Persiste el warning de descriptor inválido del WCH, ya observado en septiembre.
- `controller_dispatcher`: `/userdata/system/el_gordo_tools/controller_dispatcher`, 50.819 bytes, SHA-256 `a60be89fb45ea27ec4f7c3f546e088c7ff3da140bccfe1c6a37e5b14ec581c45`; sintaxis Python AST válida. Referenciado en `es_systems_el_gordo.cfg`. Cambió frente a septiembre (42.275 bytes, SHA antiguo `2d619f75…d5780f89`); no se comparó diff funcional. **CAMBIÓ, sintaxis OK; uso vivo no determinable.**

## 14. Red / Bluetooth / audio

- Wi-Fi: configuración habilitada; el boot registró autenticación y asociación de `wlan0` y mensaje de conexión exitosa. IP, gateway, DNS reachability, señal y pérdida no se pudieron consultar por restricciones netlink. No se registran claves.
- Ethernet `r8169`: enlace Down en el boot. Sin evidencia de error fatal.
- Bluetooth: UB500 reconocido en USB y `btusb` aparece; `bluetoothctl` aborta al no tener DBus accesible en este contexto. Emparejados/activos/desconexiones actuales: **NO DETERMINABLE**.
- Audio: configuración apunta a salida HDMI NVIDIA-surround, volumen 40; NVIDIA HDA está enumerado. `pactl` no logra conectar al servidor de audio de este contexto, por lo que no se confirma stream activo/volumen efectivo.

## 15. Servicios personalizados

| Servicio | Declarado ahora | Archivo / target | Proceso / último uso | Evaluación |
|---|---|---|---|---|
| `ssh` | Sí (`system.services=ssh custom_service`) | Servicio estándar Batocera/dropbear disponible | Proceso no visible | **MANTENER**, según esperado; no se modificó |
| `custom_service` | Sí | `/userdata/system/services/custom_service` existe; instala/valida generador Xenia persistente | Log último registro 28/07; proceso de servicio no visible | **MANTENER**; fuente/activo coinciden |
| `hdmi_recovery` | No | No existe archivo de servicio ni referencia actual en `system.services` | Logs históricos hasta agosto; ningún uso actual demostrado | **YA LIMPIADO**; la referencia fantasma no sigue declarada |
| `zaparoo_service` | No | Archivo de servicio/target no localizado | Sin uso reciente visible | **NO USADO / YA LIMPIADO** en el estado actual |

No se inició Zaparoo ni ningún servicio. `system.services` actual no incluye Zaparoo ni `hdmi_recovery`.

## 16. Xenia

- Configuración global usa `xenia-canary`, API Vulkan y VSync de Xenia activado; no se lanzó juego.
- `custom_service` conserva source y destination en hash de parche `ca0b6b33…98cc188`, idénticos entre `/userdata/system/configgen_persistent/xenia/xeniaGenerator.py` y `/usr/lib/python3.12/site-packages/configgen/generators/xenia/xeniaGenerator.py`.
- Log persistente registra instalación en julio, sin warnings recientes consultables.
- Estado: **PERSISTENTE Y COINCIDENTE**. Ejecución de Xenia no comprobada en esta auditoría; no tocar configgen ni generar copia histórica.

## 17. Backups

| Backup | Fecha | Tamaño aparente | Estado / propósito |
|---|---|---:|---|
| `BASELINE_PRE_CAMBIOS_2026-09-25_234721/` | 25–26/09 | 18,85 GB | Directorio extraído; manifiesto y verificación registrados como OK, 0 diferencias, críticos presentes, SQLite `ok` |
| `BASELINE_PRE_CAMBIOS_2026-09-25_234721.tar.gz` | 26/09 | 16,58 GB | Archivo comprimido presente; no se recalculó hash por tamaño, sidecar SHA-256 existe |
| `EMULATIONSTATION_MEDIA_FIX_2026-09-26_122318/` | 26/09 | 1,19 MB | Copias puntuales de 4 media y 2 gamelists, manifiesto presente |
| `EMULATIONSTATION_VSYNC_FIX_2026-09-26_185430/` | 26/09 | 3,2 KB | Backup de `es_settings.cfg` y registro del cambio VSync; hash original/copias coincide en el registro |

El baseline contiene manifest SHA-256 de archivos individuales y resumen de verificación, pero no se releyó/verificó el contenido completo. La carpeta extraída más el tar aparentan ocupar **35,43 GB**, no necesariamente “basura”: son dos representaciones del mismo baseline. Conservar hasta decidir una política y validar el tar; no borrar durante esta etapa. Como backup histórico es suficiente, pero no es un snapshot actual de cambios posteriores al 26/09.

## 18. Espacio

- `/userdata`: 60%, 81 GiB libres.
- `/media/BATOCERA_ROMS` (Seagate): 90%, 88 GiB libres; sobre el umbral de atención de 85% solicitado.
- `/media/ROMS` (Toshiba): 30%, ~2,5 TiB libres.
- `/userdata/roms` mergerfs: ramas `/userdata/.roms_base:/media/BATOCERA_ROMS/roms:/media/ROMS/roms`; mount presente, 1,9 TiB usados, 2,6 TiB libres, 43% agregado. Las tres ramas están listadas en el mount. No se hizo auditoría de ROMs.
- Logs: aproximadamente 2,6 MB en `/userdata/system/logs`; no se observó crecimiento grande actual. Hay logs recientes solo de boot y logs de ES antiguos (11/10).
- Mayor duplicación clara: baseline extraído + tar, ~35,4 GB sumados. No se borró nada.
- Comparación exacta de crecimiento desde septiembre no disponible para todos los filesystems; uso del Seagate continúa ~90% según baseline.

## 19. Logs

**Actual (boot 12/11):**

- NVIDIA: módulos cargados; `nvidia-drm Cannot find any crtc or sizes`; no Xid ni “fallen off bus” detectados en la búsqueda de dmesg.
- HDMI: log display selecciona HDMI-0, fija 1920×1080 y llega a lanzar ES; sysfs DRM reporta desconectado. Evidencia contradictoria.
- USB: cuatro DragonRise se inicializan; WCH repite descriptor inválido.
- ext4: `recovery complete` para sda2/sdb1/sdc1; igual fenómeno documentado en septiembre.
- `pata_legacy`: `request_irq(14)` devuelve `-EBUSY`; impacto desconocido.
- NFSD: no inicializa tracking de recuperación (`-110`) y continúa con periodo de gracia; impacto en arcade local no demostrado.

**Recurrencia / histórico:**

- WCH descriptor inválido también constaba en septiembre; no contar como problema nuevo.
- Xenia y HDMI recovery logs son históricos, últimos eventos en julio/agosto.
- Los logs actuales no muestran epidemia nueva de `Not a JPEG`, `failed texture`, errores de textura, Xid, OOM, thermal shutdown ni USB resets.

## 20. Riesgos actuales

1. Seagate al 90%, con 8 reasignados y errores ATA históricos; SMART actual no leído.
2. Estado HDMI con reportes en conflicto; no asumir fallo funcional sin evidencia de la pantalla en uso.
3. VSync efectivo y CPU ES actual sin medición; fix no confirmado en `es_settings.cfg` actual.
4. Perfil P1–P3 cambió frente al baseline; cuatro unidades están enumeradas, pero asociación física actual no verificada.
5. Recovery ext4 repetido en el boot actual, ya observado en septiembre; mantener en observación y vigilar apagado correcto/energía.
6. El Toshiba almacena tanto el directorio extraído como el tar del baseline, ~35,4 GB combinados.
7. Credenciales expuestas accidentalmente en salida de herramienta durante esta auditoría; rotar Wi-Fi y ScreenScraper password fuera de este informe.

No hay evidencia confirmada de P0 ni de disco con pending sectors nuevos.

## 21. Quick wins (propuestas, no ejecutadas)

1. **Rotar los dos secretos que aparecieron en la salida de auditoría** — beneficio alto, riesgo bajo si se actualizan desde el método normal de credenciales; pequeño y acotado.
2. **Tomar fotografía de runtime desde la consola Batocera**: VSync/FpsLimit, PID/CPU/RSS ES, renderer, HDMI activo y P1–P4 con dispositivos presentes — beneficio alto, riesgo bajo, sin cambios de configuración.
3. **Leer SMART actual sin self-test**, desde el host con acceso directo a discos — beneficio alto, riesgo bajo, solo lectura; foco Seagate y Unexpected Power Loss del SSD.
4. **Decidir conservar directorio extraído o tar como copia operativa**, tras verificación independiente del tar — libera potencialmente 16–19 GB; no borrar hasta completar esa validación.
5. **Actualizar una nota de baseline** con que HDMI recovery y Zaparoo ya no están declarados y que el perfil P1–P4 cambió; no editar documentación durante esta etapa.

## 22. Mejoras futuras

1. Reemplazo planificado del Seagate si SMART actual confirma degradación/progresión; migrar con verificación y mantener origen hasta validar.
2. Política de energía/apagado controlado o UPS solo si la evidencia de recovery/Unexpected Power Loss continúa en mediciones siguientes.
3. Baseline read-only recurrente de temperaturas, SMART, USB, renderer y CPU ES, sin auto-reparación.
4. Simplificar almacenamiento de backups solo después de comprobar manifiesto y tar sin errores.
5. Evaluar telemetría GPU compatible con el runtime, sin instalar herramientas ni cambiar drivers durante la auditoría.

## 23. Qué NO tocar

**COMPONENTES QUE HOY FUNCIONAN Y NO CONVIENE TOCAR**

- **NVIDIA/driver:** carga correctamente el módulo esperado. **NO TOCAR** por ahora; primero confirmar estado gráfico visible.
- **Xorg/EDID/HDMI:** existe evidencia mixta, pero no autorización de intervención ni prueba de pantalla negra. **NO TOCAR**; no reactivar watchers ni apagar/encender TV.
- **VSync/FpsLimit:** fix anterior redujo CPU de ES; valor actual no determinable. **NO TOCAR** hasta medir desde el runtime.
- **`controller_dispatcher`:** archivo activo referenciado, sintaxis válida, hash cambió pero no hay error de sintaxis. **NO REEMPLAZAR** por copia histórica.
- **Mappings P1–P4:** cambiaron y la documentación de octubre lo refleja. **NO RECONFIGURAR** hasta validar cada botonera físicamente.
- **mergerfs:** pool activo con las tres ramas, espacio total visible y sin error de mount. **NO TOCAR**.
- **Xenia/configgen:** copia persistente y activa coinciden exactamente. **NO TOCAR**.
- No modificar gamelists/media, servicios, red, audio, BIOS/boot ni caches como parte de este seguimiento.

## 24. Plan recomendado

| Etapa | Objetivo | Riesgo | Beneficio | Necesidad real |
|---|---|---|---|---|
| 1 | Rotar credenciales expuestas desde la interfaz habitual, fuera de esta auditoría | Bajo | Alto, reduce exposición | Alta |
| 2 | Leer SMART actual de SSD/HDD/Toshiba sin iniciar self-tests | Bajo | Alto, determina progresión y reemplazo | Alta |
| 3 | Confirmar VSync, FpsLimit y CPU/RSS de ES durante 60 s en la consola real | Bajo | Alto, cierra verificación del fix | Alta |
| 4 | Confirmar HDMI/Xorg/NVIDIA con observación pasiva y estado de salida visible | Bajo | Alto si elimina ambigüedad | Media-alta |
| 5 | Validar P1–P4 por paths y evento reales, respetando el orden documentado más reciente | Bajo | Alto para multijugador | Media-alta |
| 6 | Verificar tar/manifest y decidir política de duplicación de backup | Bajo | Recupera espacio potencial | Media |

No ejecutar estas etapas automáticamente.

## 25. Nuevo baseline

- **Fecha:** 12/11/2026 21:05 ART
- **Batocera:** 43co.1 (OS version 43o.1), 2026/05/29 04:36
- **Kernel:** 6.18.16; x86_64
- **CPU:** Intel Core i5-12400F, 6C/12T; governor `performance`
- **CPU temp:** package 46 °C; núcleos 41–46 °C
- **GPU:** NVIDIA GeForce GTX 1060 3 GB, GP106
- **GPU driver:** NVIDIA 580.126.09, módulo cargado
- **GPU temp:** no disponible
- **RAM:** 15 GiB visibles, 2,4 GiB usados, 13 GiB disponibles; swap 0
- **ES CPU promedio:** no medido; proceso no visible en el contexto
- **ES RAM:** no medido
- **VSync:** no explícito en `es_settings.cfg`; efectivo no determinable
- **FpsLimit:** no explícito; valor efectivo no determinable
- **Resolución:** `display.log` informa HDMI-0, 1920×1080; proceso vivo no consultable
- **Xorg:** estado vivo no consultable; log de boot llegó a lanzamiento de ES
- **HDMI:** evidencia mixta; salida configurada, estado DRM desconectado — posible regresión a confirmar
- **SSD:** Crucial BX500 240 GB, ext4 `/userdata`, 60% usado, 81 GiB libres; SMART no disponible
- **Seagate:** ST1000DM010 1 TB, ext4 `/media/BATOCERA_ROMS`, 90%, 88 GiB libres; SMART actual no disponible
- **Toshiba:** 4 TB USB, ext4 `/media/ROMS`, 30%, ~2,5 TiB libres; SMART no disponible
- **Pool:** mergerfs `/userdata/.roms_base:/media/BATOCERA_ROMS/roms:/media/ROMS/roms` → `/userdata/roms`, 43% usado agregado
- **P1:** perfil actual USB5; no validado físicamente (baseline septiembre USB8)
- **P2:** perfil actual USB6; no validado físicamente (baseline septiembre USB5)
- **P3:** perfil actual USB8; no validado físicamente (baseline septiembre USB6)
- **P4:** perfil actual USB7; no validado físicamente (igual baseline)
- **Bluetooth:** UB500 detectado, `btusb`; BlueZ no consultable
- **Wi-Fi:** RTL8188EU asociado durante el boot; IP/señal no consultables
- **Backups:** baseline septiembre presente (18,85 GB extraído + tar 16,58 GB); backups media y VSync presentes
- **Servicios:** `ssh custom_service`; sin `hdmi_recovery` ni Zaparoo declarados
- **Xenia:** parche persistente y activo coinciden por SHA-256
- **Errores críticos actuales:** ninguno confirmado
- **Warnings actuales:** DRM no encuentra CRTC/tamaños; descriptor WCH inválido; `pata_legacy request_irq(14) -EBUSY`; aviso NFSD `-110`
- **Uptime:** ~5 min al inicio de auditoría; boot alrededor de 20:56 ART

## Respuestas directas

1. **¿El arcade está mejor que en septiembre?** En algunos puntos sí: la temperatura de reposo observada bajó y media/servicios obsoletos están resueltos. El estado general no puede darse por plenamente mejor hasta leer SMART y confirmar HDMI/VSync/controles en el host.
2. **¿Qué problemas anteriores siguen resueltos?** Media corrupta; referencias `hdmi_recovery` y Zaparoo ya retiradas de servicios; fix persistente de Xenia conserva coincidencia. La reducción de CPU por VSync fue validada en septiembre, pero su persistencia actual no quedó confirmada.
3. **¿Qué problema anterior reapareció?** Ninguno confirmado. HDMI tiene señal contradictoria que justifica verificación, no declarar fallo.
4. **¿Apareció un problema nuevo importante?** El cambio de orden P1–P3 frente al baseline requiere validación. Además, hubo exposición accidental de credenciales en salida de la herramienta; rotarlas es recomendable.
5. **¿VSync=true sigue funcionando correctamente?** No determinable: falta la clave en `es_settings.cfg` actual y no se consultó ES vivo.
6. **¿Cuánto CPU consume ahora EmulationStation?** No medible desde este contexto. Último dato post-fix: 30,24% de un hilo.
7. **¿La media corrupta sigue resuelta?** Sí, sin regresión observada en las cuatro rutas respaldadas; gamelists PS2/GBA válidos.
8. **¿HDMI/Xorg/NVIDIA están estables?** Driver NVIDIA cargado y log de arranque de display llegó a 1080p y lanzamiento de ES; DRM/NVIDIA en paralelo informa desconectado/sin CRTC. Estado mixto, confirmar pasivamente.
9. **¿Cómo evolucionó el Seagate de 1 TB?** Uso permanece ~90%; no se pudieron leer horas, ciclos ni SMART actual, así que degradación no determinable.
10. **¿Hay algún disco que deba reemplazarse?** No se puede recomendar reemplazo inmediato con los datos actuales. El Seagate merece prioridad de SMART y plan preventivo por sus errores históricos y ocupación.
11. **¿Las temperaturas actuales son sanas?** CPU/placa sí en la foto de reposo (46 °C package, placa 17/28 °C). GPU y discos no medidos; no prueba bajo carga.
12. **¿P1–P4 siguen correctamente asignados?** No confirmado. Perfil actual es 5/6/8/7, distinto del baseline 8/5/6/7; kernel detecta las cuatro botoneras.
13. **¿Hay resets USB nuevos?** No observados. Se repite el warning del descriptor WCH, ya histórico.
14. **¿custom_service/Xenia sigue funcionando?** Persistencia y copia activa coinciden; el proceso de servicio/Xenia no se observó en vivo. Estado de archivos: estable.
15. **¿hdmi_recovery sigue siendo una referencia fantasma?** No: ya no está declarado ni hay servicio presente. Queda configuración EDID preparada/inactiva.
16. **¿Zaparoo sigue roto/no usado?** No figura como servicio ni se localizó target; no hay evidencia de uso actual. Estado: limpiado/no usado.
17. **¿Los backups actuales son suficientes?** Sí como baseline histórico, no como fotografía posterior al 26/09. Existe duplicación de 18,85 GB más tar de 16,58 GB.
18. **¿Estamos desperdiciando mucho espacio en backups/logs?** Logs no: ~2,6 MB. Backups: 35,4 GB de carpeta extraída + tar que parecen duplicar el baseline; decidir luego de validar.
19. **¿Qué 3 cosas harías a continuación?** (1) Rotar los secretos expuestos; (2) obtener SMART actual con solo lectura; (3) medir ES/VSync y confirmar HDMI/P1–P4 desde el host real.
20. **¿Qué cosas NO tocarías?** NVIDIA/driver, Xorg/EDID/HDMI, VSync/FpsLimit, `controller_dispatcher`, mappings sin prueba física, mergerfs y el generador Xenia coincidente.

**Estado final de esta etapa:** auditoría de evidencia disponible completada con limitaciones declaradas; no se ejecutó ninguna reparación ni mejora. El único archivo nuevo es este informe.
