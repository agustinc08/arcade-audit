# Controles

## Panel arcade P1–P4

Identidad técnica verificada por USB path/event y diagnóstico del dispatcher en la sesión previa al lote 6; las pruebas del lote mantienen el baseline.

| Jugador | Puerto USB | event path | js histórico |
|---|---:|---|---:|
| P1 | USB5 | `/dev/input/event17` | js0 |
| P2 | USB6 | `/dev/input/event18` | js1 |
| P3 | USB8 | `/dev/input/event20` | js3 |
| P4 | USB7 | `/dev/input/event19` | js2 |

Para identificar botoneras, USB/event y perfil son preferibles a un índice `js` que puede cambiar entre arranques. Los datos prueban detección/asignación del sistema; no certifican pulsaciones físicas dentro de cada juego.

## Selector y perfiles

`selector_controles` ofrece `BOTONERAS PRIMERO`, `JOYSTICKS PRIMERO` y `CANCELAR`. `controller_dispatcher` recibe la opción, identifica los dispositivos y configura el perfil elegido. No mezclar perfiles para completar puestos insuficientes. El comando activo y los scripts no se modificaron.

## Mandos externos

Hay adaptador Bluetooth USB y adaptador Sony/PSX USB detectados en el inventario del sistema. Los nombres/modelos concretos de gamepads externos pueden variar; no se asume que DualShock 4, DualSense o HyperX estén conectados en todo momento. La auditoría de controladores vivos es `controllers_live.json`; contiene una instantánea, no certificación histórica.

Algunos gamepads pueden presentar dispositivo de audio. La política actual conserva HDMI como salida predeterminada; la reconexión física DS4 y la persistencia tras reboot siguen pendientes.

## Multiplayer

El panel proporciona cuatro identidades de jugador. Sistemas y emuladores pueden admitir más jugadores con mandos externos/multitap, pero metadata o capacidad de runtime no certifica simultaneidad física. `CONTROL_CERTIFIED` requiere una secuencia real observada por una persona.
