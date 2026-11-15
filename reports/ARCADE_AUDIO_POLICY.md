# Política de audio arcade

Estado: `AUDIO_POLICY_INSTALLED`; salida HDMI verificada mientras el endpoint de audio del DualShock 4 está conectado, incluso durante el control positivo `altair` de 21,25 s. `AUDIO_PS4_PHYSICAL_RECONNECT_TEST: PENDING`; reboot validation pendiente.

## Causa observada

WirePlumber exponía el sink HDMI `alsa_output.pci-0000_01_00.1.hdmi-stereo` y el sink del mando `alsa_output.usb-Sony_Interactive_Entertainment_Wireless_Controller-00.analog-stereo`; el DualShock 4 era default. La regla de prioridad anterior bajo `/etc/wireplumber` apunta a un BDF PCI obsoleto. No se cambió `/etc`, overlay ni `batocera.conf`.

## Política mínima aplicada

El servicio ya habilitado `/userdata/system/services/custom_service` llama a `/userdata/system/el_gordo_tools/arcade_audio_policy_service.sh` durante `start`. El helper busca el ID actual por `node.name` con `wpctl status -n`, ejecuta `wpctl set-default` y comprueba con `pactl get-default-sink`. No se guardan IDs numéricos ni se deshabilitan USB, Bluetooth, HID, rumble o perfiles de audio. El helper falla en modo cerrado y deja una línea de diagnóstico sin datos sensibles. El backup y diff del servicio están en `blocker_resolution/backups/`.

## Prueba

- DS4 conectado durante la prueba; el sink y su fuente siguieron disponibles.
- Después de aplicar el helper, `wpctl status` marcó HDMI como default y `pactl get-default-sink` devolvió el node HDMI exacto. Durante el control positivo `altair`, el sink HDMI continuó como default en el muestreo de monitorización.
- No se reinició PipeWire/WirePlumber ni Batocera. Se intentó terminación controlada de WirePlumber, pero el PID siguió activo; no se forzó.
- La persistencia esperada usa el servicio de usuario ya habilitado en `system.services`; reboot validation sigue pendiente. La desconexión/reconexión física debe comprobarse.

## Limitación

El default de captura sigue siendo el micrófono del DS4; sólo se fijó la salida de audio al TV, que es el requisito actual. Mientras no se haga reconnect físico, el resultado es policy installed, no certificación física completa.

## Límite de certificación

El helper se ejecutó y el HDMI permaneció default durante una prueba real con el endpoint DS4 presente. No se desconectó/reconectó el mando ni se reinició el sistema: `AUDIO_POLICY_INSTALLED`, `AUDIO_PS4_PHYSICAL_RECONNECT_TEST=PENDING`, `REBOOT_VALIDATION_PENDING`. En futuros tests automáticos se debe monitorizar el sink default y pausar nuevos lanzamientos si deja de ser HDMI.
