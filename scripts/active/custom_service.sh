#!/bin/sh

# El Gordo Arcade - corrección persistente y acotada del generador Xenia.
# Sólo se instala sobre la versión base auditada de Batocera 43.1.
XENIA_GENERATOR_SRC=/userdata/system/configgen_persistent/xenia/xeniaGenerator.py
XENIA_GENERATOR_DST=/usr/lib/python3.12/site-packages/configgen/generators/xenia/xeniaGenerator.py
XENIA_GENERATOR_BASE_SHA256=1a0991c38be74c1c263916309b58131220359054f247ccb22c082f6e5bb3a8cc
XENIA_GENERATOR_PATCH_SHA256=ca0b6b33c65d0df0cbc7a7fd5d5fc0d365141c8012412b44e941cdd6898cc188
XENIA_GENERATOR_LOG=/userdata/system/logs/xenia_generator_persistent.log

if [ -r "$XENIA_GENERATOR_SRC" ] && [ -r "$XENIA_GENERATOR_DST" ]; then
    current_hash="$(sha256sum "$XENIA_GENERATOR_DST" | awk '{print $1}')"
    source_hash="$(sha256sum "$XENIA_GENERATOR_SRC" | awk '{print $1}')"
    if [ "$current_hash" = "$XENIA_GENERATOR_PATCH_SHA256" ]; then
        :
    elif [ "$current_hash" = "$XENIA_GENERATOR_BASE_SHA256" ] && [ "$source_hash" = "$XENIA_GENERATOR_PATCH_SHA256" ]; then
        cp -f "$XENIA_GENERATOR_SRC" "$XENIA_GENERATOR_DST"
        printf '%s installed persistent Xenia generator fix\n' "$(date '+%F %T')" >> "$XENIA_GENERATOR_LOG"
    else
        printf '%s refused Xenia generator fix: dst=%s src=%s\n' "$(date '+%F %T')" "$current_hash" "$source_hash" >> "$XENIA_GENERATOR_LOG"
    fi
fi

# Keep the arcade TV as the default output when WirePlumber exposes audio
# endpoints for USB/Bluetooth controllers. This is output selection only.
if [ "${1:-}" = "start" ] && [ -x /userdata/system/el_gordo_tools/arcade_audio_policy_service.sh ]; then
    /userdata/system/el_gordo_tools/arcade_audio_policy_service.sh start || true
fi
