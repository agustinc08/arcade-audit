# Auditoría multiplayer 2P–8P

La fuente actual aporta metadata de 4.085 filas de 2 o más jugadores. De ellas, 163 declaran máximo de 5 o más; tras separar metadata >8, los rangos 5–8 y >8 están listados por separado en `GAMES_5_TO_8_PLAYERS.md`. Estos valores no indican necesariamente jugadores locales simultáneos.

`players_supported_runtime=NOT_TESTED` y `players_physically_certified=NOT_TESTED` para todos. No se afirma soporte 5–8P a partir del XML/gamelist. No se alteró la asignación USB. Topología de paneles observada: P1 USB5/event17/js0, P2 USB6/event18/js1, P3 USB8/event20/js3, P4 USB7/event19/js2; además se detectaron dos pads externos en la instantánea. El límite de hub/USB, multitap, límites del core y número de entradas simultáneas necesitan validación separada.
