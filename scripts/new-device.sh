#!/usr/bin/env bash
# Crea il dossier di un nuovo dispositivo partendo da devices/_TEMPLATE.
set -euo pipefail

usage() {
    cat <<EOF
Uso: $(basename "$0") <vendor-codename> "Nome commerciale" [autore]

Esempio: $(basename "$0") samsung-i9100 "Samsung Galaxy S II" francesco
EOF
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { usage; exit 0; }
[[ $# -lt 2 ]] && { usage; exit 1; }

codename="$1"
name="$2"
author="${3:-$(git config user.name 2>/dev/null || echo "$USER")}"

if [[ ! "$codename" =~ ^[a-z0-9]+-[a-z0-9_-]+$ ]]; then
    echo "Errore: il codename deve essere nel formato vendor-codename, in minuscolo (es. xiaomi-dandelion)" >&2
    exit 1
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
dest="$root/devices/$codename"

if [[ -e "$dest" ]]; then
    echo "Errore: $dest esiste già" >&2
    exit 1
fi

cp -r "$root/devices/_TEMPLATE" "$dest"
mkdir -p "$dest/raw" "$dest/pmaports"
touch "$dest/raw/.gitkeep" "$dest/pmaports/.gitkeep"

today="$(date +%F)"
# Escape per sed: & / \ e | nel nome
esc() { printf '%s' "$1" | sed 's/[&/\|]/\\&/g'; }
sed -i \
    -e "s|__CODENAME__|$(esc "$codename")|g" \
    -e "s|__NAME__|$(esc "$name")|g" \
    -e "s|__AUTHOR__|$(esc "$author")|g" \
    -e "s|__DATE__|$today|g" \
    "$dest/README.md"

echo "Creato: devices/$codename/"
echo "Ricordati di aggiungere una riga in devices/README.md"
