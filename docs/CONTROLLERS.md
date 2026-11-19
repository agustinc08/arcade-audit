# Controles

## Panel arcade P1–P4

La identidad persistente se determina por el puerto USB físico (`ID_PATH`/`/dev/input/by-path`) y la identidad del dispositivo (`vendor/product/name`), enlazados al perfil lógico P1–P4. El número `eventXX` y el índice `jsX` son datos de runtime y pueden renumerarse después de un reboot; no son identificadores persistentes.

| Jugador | Puerto USB físico | event histórico | js histórico |
|---|---:|---|---:|
| P1 | USB5 | `/dev/input/event17` | js0 |
| P2 | USB6 | `/dev/input/event18` | js1 |
| P3 | USB8 | `/dev/input/event20` | js3 |
| P4 | USB7 | `/dev/input/event19` | js2 |

Esta tabla conserva el snapshot histórico de esa sesión; no fija los números de evento como identidad absoluta entre boots. En la auditoría post-reboot del 2026-11-18, los mismos puertos físicos aparecen como P1 USB5 `/dev/input/event18`, P2 USB6 `/dev/input/event19`, P3 USB8 `/dev/input/event21` y P4 USB7 `/dev/input/event20`. `udevadm ID_PATH` y los enlaces `by-path` confirmaron puertos físicos 5, 6, 8 y 7 respectivamente; los cuatro dispositivos reportaron VID:PID `0079:0006` y nombre DragonRise. Clasificación: `KERNEL_INPUT_EVENT_RENUMBER_AFTER_REBOOT`; la asignación lógica P1–P4 no cambió.

El safety gate debe validar para cada jugador el puerto físico esperado, `ID_PATH`/`by-path`, identidad del dispositivo y ausencia de faltantes o duplicados. `eventXX` y `jsX` se conservan sólo como datos runtime informativos. Un intercambio de puertos físicos, una identidad inesperada, un dispositivo faltante o duplicado es `P1_P4_MAPPING_CHANGE` y mantiene `PAUSED_SAFETY`. Esta detección prueba identidad/asignación del sistema; no certifica pulsaciones físicas dentro de cada juego.

## Selector y perfiles

`selector_controles` ofrece `BOTONERAS PRIMERO`, `JOYSTICKS PRIMERO` y `CANCELAR`. `controller_dispatcher` recibe la opción, identifica los dispositivos y configura el perfil elegido. No mezclar perfiles para completar puestos insuficientes. El comando activo y los scripts no se modificaron.

## Mandos externos

Hay adaptador Bluetooth USB y adaptador Sony/PSX USB detectados en el inventario del sistema. Los nombres/modelos concretos de gamepads externos pueden variar; no se asume que DualShock 4, DualSense o HyperX estén conectados en todo momento. La auditoría de controladores vivos es `controllers_live.json`; contiene una instantánea, no certificación histórica.

Algunos gamepads pueden presentar dispositivo de audio. La política actual conserva HDMI como salida predeterminada; la reconexión física DS4 y la persistencia tras reboot siguen pendientes.

## Multiplayer

El panel proporciona cuatro identidades de jugador. Sistemas y emuladores pueden admitir más jugadores con mandos externos/multitap, pero metadata o capacidad de runtime no certifica simultaneidad física. `CONTROL_CERTIFIED` requiere una secuencia real observada por una persona.
