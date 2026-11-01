#!/usr/bin/env bash
# Analizza un boot.img Android: parametri per il deviceinfo, kernel, ramdisk e dtb.
set -euo pipefail

usage() {
    cat <<EOF
Uso: $(basename "$0") <vendor-codename> <boot.img>

Scrive:
  devices/<codename>/raw/bootimg-analyze.txt   (testo, da committare)
  devices/<codename>/raw/bootimg/              (file estratti, esclusi da git)
EOF
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" || $# -lt 2 ]] && { usage; [[ $# -lt 2 ]] && exit 1; exit 0; }

codename="$1"
img="$(realpath "$2")"
root="$(cd "$(dirname "$0")/.." && pwd)"
raw="$root/devices/$codename/raw"
ext="$raw/bootimg"
report="$raw/bootimg-analyze.txt"
mkdir -p "$ext"

{
    echo "# Analisi di $(basename "$img") — $(date -I)"
    echo "# sha256: $(sha256sum "$img" | awk '{print $1}')"
    echo
    echo "## file"
    file "$img" || true
    echo
} > "$report"

if command -v pmbootstrap >/dev/null; then
    echo "## pmbootstrap bootimg_analyze" >> "$report"
    pmbootstrap bootimg_analyze "$img" >> "$report" 2>&1 || echo "(fallito)" >> "$report"
    echo >> "$report"
else
    echo "pmbootstrap non trovato: salto bootimg_analyze" >&2
fi

if command -v unpack_bootimg >/dev/null; then
    echo "## unpack_bootimg" >> "$report"
    unpack_bootimg --boot_img "$img" --out "$ext" >> "$report" 2>&1 || echo "(fallito)" >> "$report"
    echo >> "$report"
else
    echo "unpack_bootimg non trovato (pacchetto mkbootimg): salto l'estrazione" >&2
fi

# dtb accodati al kernel (comune su MediaTek e Qualcomm vecchi)
if [[ -f "$ext/kernel" ]] && command -v extract-dtb >/dev/null; then
    echo "## extract-dtb (dtb accodati al kernel)" >> "$report"
    extract-dtb "$ext/kernel" -o "$ext/dtb-from-kernel" >> "$report" 2>&1 || true
    echo >> "$report"
fi

# Decompila i dtb trovati per leggerne model/compatible
if command -v dtc >/dev/null; then
    mapfile -t dtbs < <(find "$ext" -type f \( -name '*.dtb' -o -name 'dtb' \) 2>/dev/null)
    if [[ ${#dtbs[@]} -gt 0 ]]; then
        echo "## device tree trovati" >> "$report"
        for d in "${dtbs[@]}"; do
            dtc -I dtb -O dts -o "$d.dts" "$d" 2>/dev/null || continue
            {
                echo "- ${d#"$raw"/}"
                grep -m1 -E '^\s*model\s*=' "$d.dts" | sed 's/^\s*/    /' || true
                grep -m1 -E '^\s*compatible\s*=' "$d.dts" | sed 's/^\s*/    /' || true
            } >> "$report"
        done
    fi
fi

echo "Report: ${report#"$root"/}"
echo
grep -E '^deviceinfo_' "$report" || echo "(nessuna riga deviceinfo_: controlla il report)"
