# Control overlay — estado

`/userdata/system/el_gordo_tools/control_overlay.py` produce metadata de título, jugadores y control recomendado usando `game_certification.csv`. Sólo etiqueta botones si `control_certification=CONTROL_CERTIFIED`; por ahora no hay mapeos físicos certificados. El helper no está conectado al selector ni al launcher; no se modificó `controller_dispatcher`, `selector_controles` ni configuración de ES.
