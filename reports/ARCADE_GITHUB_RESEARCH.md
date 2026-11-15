# Investigación UX, controles, multiplayer y herramientas

## Referencias consultadas

- Batocera, [Configure a Controller](https://wiki.batocera.org/configure_a_controller): documenta perfiles por mando; una identidad lógica puede variar y requiere mapping explícito. Integrar la detección existente; no sustituirla.
- Batocera, [Remapping controls per emulator](https://wiki.batocera.org/remapping_controls_per_emulator): remaps pueden ser por emulador/juego, así que el certificador debe identificar core y remap efectivo.
- Batocera, [Menu tree](https://wiki.batocera.org/menu_tree): incluye favoritos, avisos de BIOS y opciones de controladores; preferir capacidades del frontend antes de instalar otra capa.
- Batocera, [Write themes for EmulationStation](https://wiki.batocera.org/write_themes_for_emulationstation): los themes pueden mostrar metadata y elementos visuales; revisar un tema existente antes de desarrollar overlay independiente.
- BYOAC, [Multi-player Games](https://wiki.arcadecontrols.com/index.php/Multi-Player_Games): referencia comunitaria para juegos multi-player y ejemplos como Gauntlet y X-Men. No certifica que esta instalación/core acepte el número de controles.
- GitHub, [Batocera-WebDashboard-Pro](https://github.com/DavidSchuchert/Batocera-WebDashboard-Pro): dashboard comunitario de alcance amplio; estudiar sólo ideas de lectura, no instalar sin auditar permisos, código y acciones.
- GitHub, [batocera-controlcenter](https://github.com/lbrpdx/batocera-controlcenter): idea de panel local; no instalar hasta revisar código y seguridad de endpoints.
- Reddit, [arcade party recommendations](https://www.reddit.com/r/arcade/comments/1kaveqf/your_top_10_arcade_games_for_parties_with/): sugerencias comunitarias de beat-em-ups/deportes; señal de curación, no métrica objetiva de popularidad.

## Recomendación de interfaz

Mostrar sólo título, número de jugadores de metadata, control recomendado certificado y disponibilidad de joystick. Conservar menú técnico en Admin Mode. Banners de jugadores deben decir “metadata” hasta que core/emulador y mandos estén verificados.

## Multiplayer 5–8P

El inventario detectó 163 filas con metadata cuyo máximo declarado es 5 o más; contiene números que pueden ser online o modos no simultáneos (ej. 2–32), por lo que no son 163 juegos 5–8P locales confirmados. `GAMES_5_TO_8_PLAYERS.md` separa los candidatos instalados de soporte runtime y certificación física, ambos NOT_TESTED. Revisar primero juegos arcade clásicos de 4/6 plazas y consolas con multitap; validar límites de USB y emulator antes de anunciar 5–8P.

## Decisión de terceros

No se instaló software/theme/proyecto externo. El dashboard debe iniciar read-only, LAN/VPN solamente, sin exponer acciones a WAN ni API de EmulationStation.
