# Auditoría post-reboot de identidad y configuración

Fecha: 2026-11-18. Evidencia leída de sysfs, `udevadm`, el perfil técnico activo, el diagnóstico del dispatcher, el manifest de la transacción FDS y `batocera.conf`.

## Controles P1–P4

La identidad lógica esperada es P1=USB5, P2=USB6, P3=USB8 y P4=USB7. Los cuatro dispositivos presentes tienen VID:PID `0079:0006`, nombre DragonRise, y no exponen número de serie (`uniq` vacío). `ID_PATH`, `by-path`, `DEVPATH` y `phys` distinguen los puertos.

| Jugador | Puerto esperado | Puerto físico actual | `ID_PATH` / `by-path` | Evento actual | `js` actual | Identidad |
|---|---:|---:|---|---|---|---|
| P1 | USB5 | USB5 | `pci-0000:00:14.0-usb-0:5:1.0` | `/dev/input/event18` | `/dev/input/js1` | DragonRise `0079:0006` |
| P2 | USB6 | USB6 | `pci-0000:00:14.0-usb-0:6:1.0` | `/dev/input/event19` | `/dev/input/js2` | DragonRise `0079:0006` |
| P3 | USB8 | USB8 | `pci-0000:00:14.0-usb-0:8:1.0` | `/dev/input/event21` | `/dev/input/js4` | DragonRise `0079:0006` |
| P4 | USB7 | USB7 | `pci-0000:00:14.0-usb-0:7:1.0` | `/dev/input/event20` | `/dev/input/js3` | DragonRise `0079:0006` |

`/dev/input/by-id` no identifica de forma única estas botoneras porque sus seriales son iguales; `by-path` sí distingue sus puertos. En esta ejecución los nodos `/dev/input` no están montados en el namespace de diagnóstico, pero udev conserva los enlaces `DEVLINKS`, y sysfs confirma los cuatro eventos y sus rutas físicas. El mapa leído directamente del dispatcher y `controller_technical.json` coincide con las rutas configuradas.

El snapshot de la sesión anterior era P1 `event17`, P2 `event18`, P3 `event20`, P4 `event19`. El nuevo snapshot es P1 `event18`, P2 `event19`, P3 `event21`, P4 `event20`. Los puertos físicos y jugadores lógicos coinciden; por tanto la clasificación es `KERNEL_INPUT_EVENT_RENUMBER_AFTER_REBOOT`, no `P1_P4_MAPPING_CHANGE`. Los índices `jsX` también cambiaron y no se usan como identidad.

## `batocera.conf`

El baseline se recuperó de `certification_runtime/batocera.conf.current`; su SHA coincide con el `before.sha256` del manifest `20261118T161913_0b1c456071` de la transacción FDS. El snapshot temporal de la transacción fue podado tras verificar restore, pero esta copia exacta conserva el mismo SHA.

| KEY | OLD | NEW | SOURCE PROBABLE | SAFETY RELEVANCE |
|---|---|---|---|---|
| `audio.volume` | `40` | `45` | No atribuible con la evidencia disponible. El log registra `HDMI_DEFAULT_POLICY_APPLIED` a las 20:43:00; el archivo fue modificado a las 20:43:18, pero no hay evidencia de que esa policy escribiera el volumen. | `AUDIO_SETTING`; cambio de nivel, no de ruta. Se trata como no protegido semánticamente. |

No se cambiaron `global.videooutput` (`HDMI-0`), `global.videomode` (`max-1920x1080`), `audio.device` (`alsa_output.pci-0000_01_00.1.hdmi-surround`), el core global MAME (`mame078plus`), sus 18 overrides ni claves de control/integración. El default sink HDMI estéreo posterior al reboot está registrado como PASS por la evidencia runtime entregada para esta sesión; la policy HDMI también dejó `HDMI_DEFAULT_POLICY_APPLIED`. La configuración persistida `audio.device` y el sink runtime difieren de perfil (surround frente a estéreo); se conserva esa distinción sin cambiar configuración.

| Medida | Valor |
|---|---|
| SHA baseline | `098c88444322bacaac5f2f2383e5bf6e5fa42623353fe8c49d307fffc47b52d2` |
| SHA live | `bb8579bd3cb91c2ad8606ff04fe2b7ed238ed0264018a418acbe0943c3762426` |
| Fingerprint semántico protegido (baseline y live; incluye core global MAME y cantidad de overrides) | `0f90f4ed876ddf259cb6b613f09e0f7d9ed21aacd103ef87da0d93c56bca5d45` |
| Resultado semántico | PASS; SHA completo cambió sólo por `audio.volume`; claves protegidas iguales; claves críticas desconocidas cambiadas: ninguna |
| Mtime de `batocera.conf` live | `2026-11-18 20:43:18.197725105 -0300` |
| Integración MAME | `mame078plus`; 18 overrides |
| Dispatcher SHA | `92d7bb43101a72eaaaa844b51b961170c5276a3728e88c2c4240f320d162829c` |
| `controller_technical.json` SHA | `11431873bed4f024d71707b71ad1b2e6848c2f79fafda485b086cad0a548af15` |
| `multiplayer.json` SHA | `f6a72b297f1e587de9e6b3e5ccb885deda22975e444a6e4f1398b2a51928ed0f` |

## Gate y continuidad de Batch 59

El código de safety ahora compara `ID_PATH`/`by-path`, identidad USB y jugador lógico; `eventXX` y `jsX` son informativos. El fingerprint semántico excluye `audio.volume`, conserva video, ruta/audio, MAME overrides y controles, y falla cerrado ante cambios críticos desconocidos.

Batch 59 permanece preservado con 1 lanzamiento, 1 `AUTO_PASS`, 1 `RESTORE_VERIFIED` y cursor exacto en `megacd:/userdata/roms/megacd/Final Fight CD (USA).chd`. FDS no se relanzó.

La primera consulta de estado conservaba el blocker histórico `ES_NOT_IDLE`, aunque Autopilot podía volver a comprobar los gates completos. `reconcile-recovered-safety` pasó: ES idle, `runningGame=NONE`, procesos de lanzamiento/selector/dispatcher/emulador ausentes, marker ausente, `engine_fail_active=0`, identidad P1–P4 estable, fingerprint protegido igual, cola reconciliada y transacción FDS `RESTORE_VERIFIED`. La recuperación guardó backup puntual del checkpoint y preservó todos los contadores y el cursor.

`arcade_autopilot start --dry-run` pasó `HEALTH` y `CHECKPOINT`; el juego inicial fue `megacd:/userdata/roms/megacd/Final Fight CD (USA).chd`. `arcade_autopilot resume` inició Autopilot y `CERT-BATCH-0059` quedó `RUNNING`. La primera transacción nueva terminó `AUTO_PASS` + `RESTORE_VERIFIED` para Final Fight CD con ID `20261118T232842_2d2bb932e1`; luego el runner avanzó a `Lords of Thunder (Europe).chd`. `ARCADE_SAFETY: PASS`. Se dejó Autopilot ejecutándose sin intervención adicional.

La shell aislada no permite consultar directamente PulseAudio (`pactl` devuelve conexión rechazada) y no monta `/dev/input`; los gates de recuperación se comprobaron mediante el proceso Autopilot y la evidencia de udev/sysfs. El HDMI post-reboot queda PASS según la comprobación runtime entregada para la sesión y el log `HDMI_DEFAULT_POLICY_APPLIED`.
