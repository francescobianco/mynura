#!/usr/bin/env bash
# Installa gli strumenti esterni (mtkclient, MiUnlockTool) in ambienti Python separati.
# Codice di terze parti: leggi i repository prima di usarli.
set -euo pipefail

TOOLS="${MYNURA_TOOLS:-$HOME/.local/share/mynura-tools}"

usage() {
    cat <<EOF
Uso: $(basename "$0") [mtkclient|miunlock|all]   (default: all)

Installa in $TOOLS (cambia cartella con MYNURA_TOOLS=...):
  mtkclient   https://github.com/bkerler/mtkclient     -> $TOOLS/venv-mtk/bin/python $TOOLS/mtkclient/mtk.py
  miunlock    https://github.com/MiForge/MiUnlockTool  -> $TOOLS/venv-miunlock/bin/miunlock

Per mtkclient servono le regole udev (una volta sola, chiede sudo):
  sudo cp $TOOLS/mtkclient/Setup/Linux/*.rules /etc/udev/rules.d/ && sudo udevadm control -R && sudo udevadm trigger
EOF
}

what="${1:-all}"
[[ "$what" == "-h" || "$what" == "--help" ]] && { usage; exit 0; }

mkdir -p "$TOOLS"
cd "$TOOLS"

clone() {  # clone <url> <dir>
    if [[ -d "$2/.git" ]]; then git -C "$2" pull -q --ff-only; else git clone -q --depth 1 "$1" "$2"; fi
    echo "  $2 @ $(git -C "$2" log -1 --format='%h %cs')"
}

if [[ "$what" == all || "$what" == mtkclient ]]; then
    echo "== mtkclient"
    clone https://github.com/bkerler/mtkclient.git mtkclient
    python3 -m venv venv-mtk
    venv-mtk/bin/pip install -q -U pip
    venv-mtk/bin/pip install -q -r mtkclient/requirements.txt
    venv-mtk/bin/pip install -q -e mtkclient
    echo "  ok: $TOOLS/venv-mtk/bin/python $TOOLS/mtkclient/mtk.py"
fi

if [[ "$what" == all || "$what" == miunlock ]]; then
    echo "== MiUnlockTool"
    clone https://github.com/MiForge/MiUnlockTool.git MiUnlockTool
    python3 -m venv venv-miunlock
    venv-miunlock/bin/pip install -q -U pip
    venv-miunlock/bin/pip install -q ./MiUnlockTool/MiUnlockTool
    echo "  ok: $TOOLS/venv-miunlock/bin/miunlock"
fi
