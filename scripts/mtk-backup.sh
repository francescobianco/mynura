#!/usr/bin/env bash
# Backup completo delle partizioni di un telefono MediaTek via BROM (mtkclient).
# Funziona con bootloader bloccato e senza root. Legge soltanto, non scrive niente sul telefono.
set -euo pipefail

TOOLS="${MYNURA_TOOLS:-$HOME/.local/share/mynura-tools}"
MTK="$TOOLS/venv-mtk/bin/mtk"
SKIP_DEFAULT="userdata,super,cache"

usage() {
    cat <<EOF
Uso: $(basename "$0") <vendor-codename> [--skip lista] [--copy-to DIR]

  --skip     partizioni da saltare (default: $SKIP_DEFAULT; userdata contiene i dati
             personali e super il sistema, che si riscarica dal firmware ufficiale)
  --copy-to  copia anche il backup in DIR (es. un disco esterno)

Procedura:
  1. Telefono SPENTO, cavo scollegato.
  2. Lancia lo script: rimane in attesa del telefono.
  3. Tieni premuti Vol Su + Vol Giù e collega il cavo. Rilascia quando il PC lo rileva.

Risultato: devices/<codename>/raw/backup/mtk-AAAA-MM-GG/ (escluso da git), con gpt.txt e SHA256SUMS.
Se il telefono non viene rilevato: sudo systemctl stop ModemManager (a volte occupa la porta).
EOF
}

[[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]] && { usage; [[ $# -lt 1 ]] && exit 1; exit 0; }

codename="$1"; shift
skip="$SKIP_DEFAULT"; copy_to=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip) skip="$2"; shift 2 ;;
        --copy-to) copy_to="$2"; shift 2 ;;
        *) echo "Opzione sconosciuta: $1" >&2; exit 1 ;;
    esac
done

[[ -x "$MTK" ]] || { echo "mtkclient non installato: ./scripts/setup-tools.sh mtkclient" >&2; exit 1; }

root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/devices/$codename/raw/backup/mtk-$(date +%F)"
mkdir -p "$out"

echo "Spegni il telefono, poi tieni premuti Vol Su + Vol Giù e collega il cavo..."
"$MTK" printgpt 2>&1 | tee "$out/gpt.txt"
echo
echo "Lettura di tutte le partizioni tranne: $skip"
echo "Ricollega il telefono nello stesso modo se richiesto."
"$MTK" rl "$out" --skip "$skip" 2>&1 | tee "$out/mtk-rl.log"

(cd "$out" && sha256sum -- *.bin > SHA256SUMS) || echo "ATTENZIONE: checksum non calcolati"
echo
ls -la "$out"
for p in nvram nvdata nvcfg persist protect1 protect2 proinfo; do
    [[ -s "$out/$p.bin" ]] && echo "  ✅ $p" || echo "  ❌ $p MANCANTE"
done

if [[ -n "$copy_to" ]]; then
    mkdir -p "$copy_to"
    cp -r "$out" "$copy_to/"
    (cd "$copy_to/$(basename "$out")" && sha256sum -c --quiet SHA256SUMS) && echo "Copia verificata in $copy_to"
fi
echo "Fatto. Il backup NON è versionato: conservane una copia su un altro disco."
