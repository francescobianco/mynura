#!/bin/sh
# Profilo Sxmo per Xiaomi Redmi 9A / 9AT (dandelion).
# Il nome del file deve corrispondere al compatible del device tree: mediatek,MT6765.
export SXMO_TOUCHSCREEN_ID="pointer:fts_ts"
# Il modem MediaTek non è ancora supportato: niente servizi inutili
export SXMO_NO_MODEM=1
