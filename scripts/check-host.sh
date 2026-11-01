#!/usr/bin/env bash
# Controlla che sul PC ci siano gli strumenti necessari al porting.
set -uo pipefail

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { echo "Uso: $(basename "$0")"; exit 0; }

missing=0
check() {
    local cmd="$1" level="$2" hint="$3"
    if command -v "$cmd" >/dev/null 2>&1; then
        printf '  ✅ %-16s %s\n' "$cmd" "$(command -v "$cmd")"
    else
        printf '  %s %-16s %s\n' "$([[ $level == req ]] && echo '❌' || echo '⚠️ ')" "$cmd" "$hint"
        [[ $level == req ]] && missing=$((missing + 1))
    fi
}

echo "Essenziali:"
check pmbootstrap   req "vedi docs/01-setup-ambiente.md"
check git           req "apt install git"
check adb           req "apt install adb (o Android SDK platform-tools)"
check fastboot      req "apt install fastboot"
check ssh           req "apt install openssh-client"

echo "Utili:"
check unpack_bootimg opt "apt install mkbootimg"
check extract-dtb   opt "pipx install extract-dtb"
check dtc           opt "apt install device-tree-compiler"
check heimdall      opt "apt install heimdall-flash (solo Samsung)"
check mtk           opt "mtkclient, solo MediaTek: https://github.com/bkerler/mtkclient"
check telnet        opt "apt install telnet (debug shell)"
check picocom       opt "apt install picocom (console seriale)"
check shellcheck    opt "apt install shellcheck"

if command -v adb >/dev/null; then
    echo "Dispositivi adb:"
    adb devices | tail -n +2 | sed '/^$/d; s/^/  /'
fi
if command -v fastboot >/dev/null; then
    echo "Dispositivi fastboot:"
    timeout 3 fastboot devices 2>/dev/null | sed 's/^/  /'
fi

exit $missing
