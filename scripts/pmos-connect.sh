#!/usr/bin/env bash
# Collegamento al telefono con postmarketOS via rete USB (172.16.42.1).
set -euo pipefail

IP="${PMOS_IP:-172.16.42.1}"

usage() {
    cat <<EOF
Uso: $(basename "$0") [--telnet] [utente]

  (default)  ssh <utente>@$IP   (utente: \$PMOS_USER, oppure quello di pmbootstrap, oppure \$USER)
  --telnet   telnet $IP (debug shell dell'initramfs, avviata con pmos.debug-shell)

Variabili: PMOS_IP, PMOS_USER
EOF
}

mode=ssh
case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    --telnet) mode=telnet; shift ;;
esac

# Interfaccia USB presente?
iface="$(ip -o -4 addr show | awk '/172\.16\.42\./ {print $2; exit}')"
if [[ -z "$iface" ]]; then
    echo "Nessuna interfaccia con IP 172.16.42.x sul PC."
    echo "Interfacce USB viste (cerca usb0/enx…/rndis):"
    ip -br link | grep -vE '^(lo|docker|br-|veth|virbr)' || true
    echo
    echo "Se l'interfaccia c'è ma non ha IP:  sudo dhclient <iface>  oppure"
    echo "  sudo ip addr add 172.16.42.2/24 dev <iface> && sudo ip link set <iface> up"
    echo "Se non c'è proprio: il kernel non è partito o manca l'USB gadget (vedi docs/04-flash-e-debug.md)."
    exit 1
fi
echo "Interfaccia: $iface"

if [[ "$mode" == telnet ]]; then
    command -v telnet >/dev/null || { echo "Installa telnet" >&2; exit 1; }
    exec telnet "$IP"
fi

user="${1:-${PMOS_USER:-}}"
if [[ -z "$user" ]] && command -v pmbootstrap >/dev/null; then
    user="$(pmbootstrap config user 2>/dev/null || true)"
fi
user="${user:-$USER}"

# Ogni reinstallazione cambia la chiave dell'host: non inquinare known_hosts
exec ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$user@$IP"
