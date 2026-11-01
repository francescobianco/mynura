#!/usr/bin/env bash
# Alleggerisce Android via adb (senza root): rimuove app per l'utente 0, riduce le animazioni,
# ricompila le app. Tutto reversibile.
set -euo pipefail

usage() {
    cat <<EOF
Uso: $(basename "$0") <lista.txt> [--restore] [--no-tweaks] [--compile]

  <lista.txt>   un pacchetto per riga, # per i commenti (es. devices/xiaomi-dandelion/android-debloat.txt)
  --restore     reinstalla per l'utente 0 i pacchetti della lista (annulla la rimozione)
  --no-tweaks   non cambiare la velocità delle animazioni
  --compile     ricompila tutte le app (dexopt): lento (10-30 min), poi il telefono è più reattivo

Prima di toccare qualcosa salva l'elenco dei pacchetti in <cartella della lista>/raw/backup/packages-before-AAAA-MM-GG.txt
EOF
}

[[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]] && { usage; [[ $# -lt 1 ]] && exit 1; exit 0; }

list="$1"; shift
restore=0; tweaks=1; compile=0
for a in "$@"; do
    case "$a" in
        --restore) restore=1 ;;
        --no-tweaks) tweaks=0 ;;
        --compile) compile=1 ;;
        *) echo "Opzione sconosciuta: $a" >&2; exit 1 ;;
    esac
done

[[ -f "$list" ]] || { echo "Lista non trovata: $list" >&2; exit 1; }
adb wait-for-device

mapfile -t pkgs < <(sed 's/#.*//; s/[[:space:]]//g; /^$/d' "$list")

if [[ $restore -eq 1 ]]; then
    for p in "${pkgs[@]}"; do
        printf '  %-50s %s\n' "$p" "$(adb shell cmd package install-existing "$p" 2>&1 | tr -d '\r')"
    done
    adb shell settings put global window_animation_scale 1.0
    adb shell settings put global transition_animation_scale 1.0
    adb shell settings put global animator_duration_scale 1.0
    exit 0
fi

rawdir="$(dirname "$list")/raw/backup"   # escluso da git: elenco app personali
mkdir -p "$rawdir"
snap="$rawdir/packages-before-$(date +%F).txt"
adb shell pm list packages -u | tr -d '\r' | sort > "$snap"
echo "Elenco pacchetti salvato in $snap"

installed="$(adb shell pm list packages | tr -d '\r')"
removed=0
for p in "${pkgs[@]}"; do
    if ! grep -qx "package:$p" <<<"$installed"; then
        printf '  %-50s %s\n' "$p" "(già assente)"
        continue
    fi
    res="$(adb shell pm uninstall --user 0 "$p" 2>&1 | tr -d '\r' || true)"
    if [[ "$res" != Success ]]; then
        # Alcune app (es. aggiornate dallo store) non si disinstallano: le disattiviamo
        if adb shell pm disable-user --user 0 "$p" 2>&1 | grep -q 'disabled-user'; then
            res="$res -> disattivata"
            adb shell am force-stop "$p" || true
        fi
    fi
    printf '  %-50s %s\n' "$p" "$res"
    [[ "$res" == Success* || "$res" == *disattivata ]] && removed=$((removed + 1))
done
echo "Rimossi o disattivati: $removed"

if [[ $tweaks -eq 1 ]]; then
    echo "Animazioni a 0.5x"
    if ! { adb shell settings put global window_animation_scale 0.5 &&
           adb shell settings put global transition_animation_scale 0.5 &&
           adb shell settings put global animator_duration_scale 0.5; } 2>&1 | grep -q 'SecurityException'; then
        echo "  ok"
    else
        echo "  NEGATO: su MIUI attiva anche 'Debug USB (Impostazioni di sicurezza)' nelle Opzioni sviluppatore,"
        echo "  oppure imposta a mano le tre 'Scala animazione' a 0.5x."
    fi
fi

if [[ $compile -eq 1 ]]; then
    echo "Ricompilazione app (speed-profile), può richiedere parecchi minuti..."
    adb shell cmd package compile -m speed-profile -a
fi

echo "Fatto. Riavvia il telefono: adb reboot"
