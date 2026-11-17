#!/usr/bin/env bash
# Aggiorna kernel e pacchetto del dispositivo di xiaomi-dandelion, senza riscrivere userdata.
# Installa sul telefono il pacchetto linux compilato da port-xiaomi-dandelion.sh,
# prende il boot.img rigenerato dal telefono, aggiunge il footer AVB sul PC
# e lo scrive nella partizione boot dal telefono stesso. Prima salva la boot attuale.
# Serve sudo senza password sul telefono. Uso: kernel-update-xiaomi-dandelion.sh
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
dossier="$root/devices/xiaomi-dandelion"
phone="${PHONE:-$USER@172.16.42.1}"
pmb_bin="$HOME/.local/bin/pmbootstrap"
aports="$HOME/src/pmaports"
avbtool="$HOME/.local/share/mynura-tools/avbtool"
boot_partition_size=67108864
step() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERRORE: %s\033[0m\n' "$*" >&2; exit 1; }
ssh_() { ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "$phone" "$@"; }
scp_() { scp -q -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR "$@"; }

[[ -f "$avbtool" ]] || die "avbtool non trovato in $avbtool: lancia una volta flash-xiaomi-dandelion.sh"
work="$("$pmb_bin" -p "$aports" config work)"
apk="$(find "$work/packages" -name 'linux-xiaomi-dandelion-*.apk' | sort -V | tail -1)"
[[ -n "$apk" ]] || die "pacchetto del kernel non trovato: lancia prima port-xiaomi-dandelion.sh"
devapk="$(find "$work/packages" -name 'device-xiaomi-dandelion-*.apk' | sort -V | tail -1)"
echo "Pacchetti: $(basename "$apk") ${devapk:+$(basename "$devapk")}"
ssh_ 'sudo -n true' || die "sul telefono serve sudo senza password (vedi il diario del dossier)"

stamp="$(date +%Y%m%d-%H%M%S)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

step "1/4 Backup della partizione boot attuale"
mkdir -p "$dossier/raw/backup"
ssh_ 'sudo cat /dev/disk/by-partlabel/boot' > "$dossier/raw/backup/boot-prima-$stamp.img"
[[ "$(stat -c %s "$dossier/raw/backup/boot-prima-$stamp.img")" -eq "$boot_partition_size" ]] \
    || die "backup della boot con dimensione inattesa"

step "2/4 Installazione del kernel sul telefono"
scp_ "$apk" "$phone:/tmp/linux-new.apk"
pkgs=/tmp/linux-new.apk
if [[ -n "$devapk" ]]; then scp_ "$devapk" "$phone:/tmp/device-new.apk"; pkgs="$pkgs /tmp/device-new.apk"; fi
ssh_ "sudo apk add --allow-untrusted $pkgs && ls -la /boot/boot.img"
scp_ "$phone:/boot/boot.img" "$tmp/boot.img"

step "3/4 Footer AVB"
python3 -I "$avbtool" add_hash_footer --image "$tmp/boot.img" \
    --partition_name boot --partition_size "$boot_partition_size"
[[ "$(stat -c %s "$tmp/boot.img")" -eq "$boot_partition_size" ]] || die "boot.img con dimensione inattesa"
cp "$tmp/boot.img" "$dossier/raw/backup/pmos-boot-$stamp-avb.img"

step "4/4 Scrittura della partizione boot e riavvio"
scp_ "$tmp/boot.img" "$phone:/tmp/boot-avb.img"
ssh_ 'sudo dd if=/tmp/boot-avb.img of=/dev/disk/by-partlabel/boot bs=1M conv=fsync status=none && sync &&
      sudo cmp /tmp/boot-avb.img /dev/disk/by-partlabel/boot && echo "boot scritta e verificata"'
ssh_ 'sudo reboot' || true
echo "Il telefono si riavvia. Backup della boot precedente: raw/backup/boot-prima-$stamp.img"
