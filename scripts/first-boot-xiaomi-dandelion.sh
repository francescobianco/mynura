#!/usr/bin/env bash
# Primo avvio di xiaomi-dandelion: crea il sistema con pmbootstrap install e carica il kernel in RAM
# con "fastboot boot". NON scrive partizioni: al riavvio il telefono torna com'era.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
dossier="$root/devices/xiaomi-dandelion"
logdir="$dossier/raw/build-logs"
aports="$HOME/src/pmaports"
pmb_bin="$HOME/.local/bin/pmbootstrap"

step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERRORE: %s\033[0m\n' "$*" >&2; exit 1; }
pmb() { "$pmb_bin" -p "$aports" "$@"; }

[[ -t 0 ]] || die "Serve un terminale interattivo: lancia lo script da un terminale normale."
[[ -x "$pmb_bin" ]] || die "pmbootstrap non trovato: lancia prima scripts/port-xiaomi-dandelion.sh"

step "Password di sudo"
sudo -v

step "1/4 Telefono in fastboot"
fastboot devices | grep -q fastboot \
    || die "telefono non visto in fastboot: Vol Giù + Accensione, cavo su una porta diretta del PC"
echo "Telefono trovato in fastboot"

# Smonta quanto lasciato da un'esecuzione precedente: altrimenti la pulizia dei chroot fallisce
clean_mounts() {
    local work rootfs
    work="$(pmb config work)"
    rootfs="$work/chroot_native/mnt/rootfs_xiaomi-dandelion"
    if findmnt -rn -o TARGET | grep -qF "$rootfs"; then
        sudo umount -R "$rootfs" || true
    fi
    pmb shutdown || true
}

step "Pulizia dei mount rimasti"
clean_mounts

step "2/4 pmbootstrap install"
echo "Ti chiederà una password per l'utente del telefono: serve per entrare via SSH."
pmb install --zap

step "3/4 Copia del boot.img per il controllo"
work="$(pmb config work)"
boot_img="$work/chroot_rootfs_xiaomi-dandelion/boot/boot.img"
copy="$dossier/raw/backup/pmos-boot-$(date +%Y%m%d-%H%M%S).img"
if sudo test -f "$boot_img"; then
    sudo cp "$boot_img" "$copy"
    sudo chown "$(id -u):$(id -g)" "$copy"
    echo "Copia: ${copy#"$root"/}"
else
    echo "boot.img non trovato in $boot_img: proseguo comunque."
fi

step "4/4 Avvio del kernel in RAM"
echo "Non viene scritta nessuna partizione. Lo schermo può restare nero o sulla schermata Redmi."
read -r -p "Premi Invio per avviare (Ctrl+C per fermarti) " _

mkdir -p "$logdir"
log="$logdir/first-boot-$(date +%Y%m%d-%H%M%S).log"
set +e
timeout --foreground 180 "$pmb_bin" -p "$aports" flasher boot 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
set -e
echo "flasher boot: codice di uscita $status" | tee -a "$log"
clean_mounts >> "$log" 2>&1 || true

if [[ "$status" -ne 0 ]]; then
    {
        echo "--- pmbootstrap log"
        tail -n 80 "$(pmb config work)/log.txt" 2>&1 || true
        echo "--- fastboot"
        timeout 10 fastboot devices -l 2>&1 || true
    } >> "$log"
    die "avvio da RAM non riuscito. Log: ${log#"$root"/}"
fi

step "Attendo la rete USB del telefono (fino a 90 secondi)"
found=no
for _ in $(seq 1 30); do
    if lsusb | grep -q '18d1:d001'; then
        found=yes
        break
    fi
    sleep 3
done

{
    echo "--- esito rete USB: $found"
    echo "--- lsusb"
    lsusb | grep -iE '18d1|0e8d|2717' || echo "telefono non visibile su USB"
    echo "--- interfacce"
    ip -brief addr | grep -iE 'usb|enx|172\.16\.42' || echo "nessuna interfaccia USB"
    echo "--- dmesg del PC"
    sudo dmesg | tail -25
} 2>&1 | tee -a "$log"

step "Fatto"
if [[ "$found" == yes ]]; then
    echo "Il kernel è partito e la rete USB è comparsa."
else
    echo "Rete USB non comparsa entro 90 secondi."
fi
echo "Log: ${log#"$root"/}"
