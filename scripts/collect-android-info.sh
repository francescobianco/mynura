#!/usr/bin/env bash
# Raccoglie via adb tutte le informazioni utili al porting da un telefono con Android.
# Non scrive niente sul telefono.
set -euo pipefail

usage() {
    cat <<EOF
Uso: $(basename "$0") <vendor-codename> [-s SERIALE]

Salva l'output in devices/<vendor-codename>/raw/android-info/.
Se il telefono ha root (su) o è in TWRP, raccoglie anche dmesg, cmdline, ecc.
EOF
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 1 ]] && { usage; [[ $# -lt 1 ]] && exit 1; exit 0; }

codename="$1"; shift
adb_args=()
if [[ "${1:-}" == "-s" ]]; then adb_args=(-s "$2"); fi

root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/devices/$codename/raw/android-info"
mkdir -p "$out"

command -v adb >/dev/null || { echo "Errore: adb non trovato" >&2; exit 1; }
adb "${adb_args[@]}" wait-for-device

ADB() { adb "${adb_args[@]}" "$@"; }

# Root disponibile? (TWRP: già root; Android rootato: su -c)
SU=""
if [[ "$(ADB shell id -u 2>/dev/null | tr -d '\r')" == "0" ]]; then
    SU="root"
elif ADB shell 'su -c id' 2>/dev/null | grep -q 'uid=0'; then
    SU="su"
fi
echo "Accesso root: ${SU:-no}"

failed=()

# grab <file> <comando> [root]
grab() {
    local file="$1" cmd="$2" need_root="${3:-}"
    local full="$cmd"
    if [[ -n "$need_root" && "$SU" == "su" ]]; then
        full="su -c '$cmd'"
    fi
    printf '  %-28s' "$file"
    ADB shell "$full" 2>&1 | tr -d '\r' > "$out/$file" || true
    # Ok se c'è almeno una riga utile che non sia un messaggio d'errore
    if grep -qviE '(permission denied|not found|no such file|can.t open|^\s*$|^total 0$|:$)' "$out/$file"; then
        echo "ok"
    elif grep -qiE 'permission denied|can.t open' "$out/$file"; then
        echo "serve root"
        failed+=("$file")
    else
        echo "vuoto"
        failed+=("$file")
    fi
}

# Oscura IMEI, numeri di serie, MAC e ICCID nei file da committare.
# La copia integrale di getprop finisce in raw/backup/ (escluso da git).
redact() {
    local backup="$root/devices/$codename/raw/backup"
    mkdir -p "$backup"
    cp "$out/getprop.txt" "$backup/getprop-full.txt"
    local serial
    serial="$(grep -F '[ro.serialno]' "$out/getprop.txt" | sed 's/.*: \[\(.*\)\]/\1/' || true)"
    local f
    for f in "$out"/*.txt; do
        sed -i -E \
            -e 's/^(\[[^]]*(imei|meid|serial|iccid|icid|imsi|msisdn|wifimac|btaddr|macaddr|mac_addr|boot\.chipid|cpuid|hostname)[^]]*\]: \[)[^]]+\]/\1REDACTED]/I' \
            -e 's/([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}/xx:xx:xx:xx:xx:xx/g' \
            -e 's/\b[0-9]{15}\b/REDACTED_IMEI/g' \
            "$f"
        if [[ -n "$serial" ]]; then sed -i "s/$serial/REDACTED_SERIAL/g" "$f"; fi
    done
}

echo "Raccolta in: ${out#"$root"/}"
grab getprop.txt           "getprop"
grab uname.txt             "uname -a"
grab version.txt           "cat /proc/version"
grab cpuinfo.txt           "cat /proc/cpuinfo"
grab meminfo.txt           "cat /proc/meminfo"
grab soc.txt               "getprop ro.board.platform; getprop ro.hardware; getprop ro.product.cpu.abilist; cat /sys/devices/soc0/machine 2>/dev/null"
grab partitions.txt        "cat /proc/partitions"
grab by-name.txt           "ls -l /dev/block/by-name/ 2>/dev/null || ls -l /dev/block/platform/*/by-name/ 2>/dev/null || ls -l /dev/block/platform/*/*/by-name/" root
grab mounts.txt            "cat /proc/mounts"
grab cmdline.txt           "cat /proc/cmdline" root
grab dmesg.txt             "dmesg" root
grab last_kmsg.txt         "cat /proc/last_kmsg 2>/dev/null || cat /sys/fs/pstore/console-ramoops* 2>/dev/null" root
grab lsmod.txt             "lsmod 2>/dev/null || cat /proc/modules"
grab modules-files.txt     "ls -lR /vendor/lib/modules /system/lib/modules /lib/modules 2>/dev/null"
grab firmware-files.txt    "ls -lR /vendor/firmware /system/etc/firmware /vendor/etc/firmware /firmware 2>/dev/null"
grab dt-model.txt          "cat /proc/device-tree/model; echo"
grab dt-compatible.txt     "tr '\\0' '\\n' < /proc/device-tree/compatible"
grab input-devices.txt     "cat /proc/bus/input/devices"
grab i2c-devices.txt       "for d in /sys/bus/i2c/devices/*; do echo \"\$d: \$(cat \$d/name 2>/dev/null)\"; done"
grab spi-devices.txt       "ls -l /sys/bus/spi/devices/ 2>/dev/null"
grab platform-drivers.txt  "ls /sys/bus/platform/drivers/"
grab display.txt           "wm size; wm density; ls /sys/class/graphics/ /sys/class/backlight/ /sys/class/drm/ 2>/dev/null"
grab power-supply.txt      "for d in /sys/class/power_supply/*; do echo \"== \$d\"; cat \$d/uevent 2>/dev/null; done"
grab interrupts.txt        "cat /proc/interrupts"
grab iomem.txt             "cat /proc/iomem" root
grab kernel-config.txt     "zcat /proc/config.gz" root
grab bootloader-props.txt  "getprop | grep -iE 'boot|verified|unlock|secure|flash|slot'"

redact

{
    echo "Raccolto il $(date -Iseconds) con scripts/collect-android-info.sh"
    echo "root: ${SU:-no}"
    echo "Falliti: ${failed[*]:-nessuno}"
} > "$out/_README.txt"

echo
echo "Riassunto:"
for p in ro.product.device ro.product.model ro.product.manufacturer ro.board.platform ro.product.cpu.abi ro.build.version.release ro.boot.slot_suffix; do
    printf '  %-28s %s\n' "$p" "$(grep -F "[$p]" "$out/getprop.txt" | sed 's/.*: \[\(.*\)\]/\1/' || true)"
done
[[ ${#failed[@]} -gt 0 ]] && echo "Falliti (spesso serve root): ${failed[*]}"
echo "Fatto. IMEI/seriale/MAC oscurati; getprop completo in raw/backup/getprop-full.txt (non versionato)."
echo "Dai comunque un'occhiata ai file prima di committarli."
