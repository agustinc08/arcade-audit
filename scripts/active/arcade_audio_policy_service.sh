#!/bin/sh
set -eu

# Batocera user service: select the arcade TV HDMI sink by stable node name.
# Does not disable or reconfigure any controller, Bluetooth, or input device.
. /etc/profile.d/xdg.sh
TARGET='alsa_output.pci-0000_01_00.1.hdmi-stereo'
LOG='/userdata/system/logs/arcade_audio_policy.log'

case "${1:-start}" in
  start) ;;
  stop) exit 0 ;;
  *) exit 2 ;;
esac

n=0
sink_id=''
while [ "$n" -lt 30 ]; do
    sink_id="$(wpctl status -n 2>/dev/null | awk -v target="$TARGET" '
        /Sinks:/ { in_sinks=1; next }
        in_sinks && /Sources:/ { exit }
        in_sinks && index($0, target) {
            for (i=1; i<=NF; i++) if ($i ~ /^[0-9]+\.$/) {
                sub(/\.$/, "", $i); print $i; exit
            }
        }')"
    [ -n "$sink_id" ] && break
    n=$((n + 1))
    sleep 1
done

if [ -z "$sink_id" ]; then
    printf '%s HDMI_SINK_NOT_FOUND\n' "$(date '+%F %T')" >> "$LOG"
    exit 1
fi

if ! wpctl set-default "$sink_id" >/dev/null 2>&1; then
    printf '%s HDMI_DEFAULT_SET_FAILED\n' "$(date '+%F %T')" >> "$LOG"
    exit 1
fi

current="$(pactl get-default-sink 2>/dev/null || true)"
if [ "$current" != "$TARGET" ]; then
    printf '%s HDMI_DEFAULT_VERIFY_FAILED\n' "$(date '+%F %T')" >> "$LOG"
    exit 1
fi

printf '%s HDMI_DEFAULT_POLICY_APPLIED\n' "$(date '+%F %T')" >> "$LOG"
exit 0
