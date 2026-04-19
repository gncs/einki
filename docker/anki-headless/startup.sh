#!/bin/bash
ANKICONNECT_CONFIG_FILE=/data/addons21/AnkiConnectDev/config.json
ANKICONNECT_CONFIG_BACKUP="${ANKICONNECT_CONFIG_FILE}_bak_ha"

if [ "${ANKICONNECT_WILDCARD_ORIGIN:-}" = "1" ]; then
    echo "[i] ANKICONNECT_WILDCARD_ORIGIN set to 1, setting wildcard webCorsOriginList!"
    cp $ANKICONNECT_CONFIG_FILE $ANKICONNECT_CONFIG_BACKUP
    jq '.webCorsOriginList = ["*"]' $ANKICONNECT_CONFIG_FILE > tmp_file
    mv tmp_file $ANKICONNECT_CONFIG_FILE
else
    if [ -f $ANKICONNECT_CONFIG_BACKUP ]; then
        echo "[i] ANKICONNECT_WILDCARD_ORIGIN unset/not set to 1, restoring backed up ANKICONNECT config file '$ANKICONNECT_CONFIG_BACKUP'!"
        mv $ANKICONNECT_CONFIG_BACKUP $ANKICONNECT_CONFIG_FILE
    fi
fi

# exec replaces bash with anki as PID 1, ensuring it receives SIGTERM
# directly from Docker and can flush prefs21.db on graceful shutdown.
exec anki -b /data
