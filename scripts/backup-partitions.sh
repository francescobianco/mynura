#!/usr/bin/env bash
# Backup di partizioni del telefono via adb. Richiede root (su) o TWRP.
# Legge soltanto dal telefono, non scrive niente.
set -euo pipefail

usage() {
    cat <<EOF
Uso: $(basename "$0") <vendor-codename> <partizione> [partizione...]
     $(basename "$0") <vendor-codename> --list

Esempi:
  $(basename "$0") xiaomi-dandelion --list
  $(basename "$0") xiaomi-dandelion boot recovery nvram nvdata persist

I file vanno in devices/<codename>/raw/backup/ (escluso da git) con lo sha256 accanto.
EOF
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 2 ]] && { usage; [[ $# -lt 2 ]] && exit 1; exit 0; }

codename="$1"; shift
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/devices/$codename/raw/backup"
mkdir -p "$out"

adb wait-for-device

if [[ "$(adb shell id -u | tr -d '\r')" == "0" ]]; then
    RUN() { adb exec-out "$1"; }
elif adb shell 'su -c id' 2>/dev/null | grep -q 'uid=0'; then
    RUN() { adb exec-out "su -c '$1'"; }
else
    echo "Errore: serve root (su) o TWRP." >&2
    exit 1
fi

# Trova la cartella by-name
# shellcheck disable=SC2016  # espanso sul telefono, non qui
byname="$(RUN 'for d in /dev/block/by-name /dev/block/platform/*/by-name /dev/block/platform/*/*/by-name; do [ -d "$d" ] && echo "$d" && break; done' | tr -d '\r')"
[[ -z "$byname" ]] && { echo "Errore: cartella by-name non trovata" >&2; exit 1; }

if [[ "$1" == "--list" ]]; then
    RUN "ls -l $byname" | tr -d '\r'
    exit 0
fi

for part in "$@"; do
    [[ "$part" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "Nome partizione non valido: $part" >&2; continue; }
    if ! RUN "[ -e $byname/$part ] && echo yes" | grep -q yes; then
        echo "  $part: non esiste, salto"
        continue
    fi
    dest="$out/$part.img"
    echo "  $part -> ${dest#"$root"/}"
    RUN "dd if=$byname/$part bs=4M 2>/dev/null" > "$dest"
    remote_sum="$(RUN "sha256sum $byname/$part" | awk '{print $1}')"
    local_sum="$(sha256sum "$dest" | awk '{print $1}')"
    if [[ -n "$remote_sum" && "$remote_sum" != "$local_sum" ]]; then
        echo "    ATTENZIONE: checksum diverso (remoto $remote_sum, locale $local_sum)" >&2
    fi
    echo "$local_sum  $part.img" > "$dest.sha256"
done

echo "Fatto. Copia raw/backup/ su un disco esterno: NON è versionato."
