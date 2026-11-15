# Certificación de controles

`controllers_live.json` es una instantánea runtime: cuatro paneles P1–P4 y dos gamepads externos conectados en el momento indicado. La identidad de los paneles se basa en perfil USB/event path; no se reasignó nada. El DualShock aparece como dispositivo SDL y también posee capacidad de audio; esto concuerda con el issue `AUD-002`.

`arcade_control_certifier.py` lee eventos EV_KEY/EV_ABS desde un `/dev/input/eventN` concreto, muestra identidad sysfs y solicita confirmación humana por acción. No inyecta input. Un registro completo crea sólo evidencia candidata; deja `control_certified=false` para revisión porque la secuencia aislada no prueba acción dentro del juego. No se han capturado secuencias físicas en esta fase.

Usar con atención humana: `python3 /userdata/system/el_gordo_tools/arcade_control_certifier.py --player P1 --device /dev/input/event17 --system mame --game kov2p`. Repetir con el player/device exacto, sin usar `jsN` como identidad única.
