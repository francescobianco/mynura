#!/usr/bin/env bash
# Piper, l'assistente al telefono con Nura: un solo comando per accendere, controllare e fermare tutto.
# Si lancia sul PC collegato via USB al telefono, anche da remoto:
#   ssh francesco@192.168.144.10 ~/Develop/_/mynura/devices/xiaomi-dandelion/modem/piper.sh avvia
#
#   avvia    controlla ogni pezzo e avvia solo quello che manca (anche dopo un riavvio del telefono)
#   riavvia  ferma conversazione, risposta automatica, audio e ponte, poi riavvia tutto
#   ferma    ferma il ponte sul PC e i servizi di Piper sul telefono (il modem resta acceso)
#   stato    cosa gira, se il telefono è registrato in rete, se il ponte è vivo
#   log      segue i log del telefono e del ponte (Ctrl-C per uscire)
#
# Sul telefono gli script stanno in ~/nura (permanente), il binario mtkaudio si ricompila solo se serve.
# Sul PC il ponte gira in un ciclo che lo riavvia da solo e sopravvive alla chiusura di SSH:
# pid in ~/nura-voice/brain.pid, log in ~/nura-voice/brain.log.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PHONE="${PHONE:-$USER@172.16.42.1}"
PY="$HOME/nura-voice/venv/bin/python"
BRAIN_PID="$HOME/nura-voice/brain.pid"
BRAIN_LOG="$HOME/nura-voice/brain.log"
SSH=(ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR
     -o ConnectTimeout=5)

ok()   { printf '\033[1;32m  ✓\033[0m %s\n' "$*"; }
info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  !\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m  ✗ %s\033[0m\n' "$*" >&2; exit 1; }
phone() { "${SSH[@]}" "$PHONE" "$@" </dev/null; }   # comando senza input
phone_in() { "${SSH[@]}" "$PHONE" "$@"; }           # comando che legge dallo stdin (tar, script)

# ------------------------------------------------------------------ ponte sul PC
brain_running() { [[ -f "$BRAIN_PID" ]] && kill -0 "$(cat "$BRAIN_PID")" 2>/dev/null; }

brain_start() {
    [[ -x "$PY" ]] || die "manca $PY (python -m venv ~/nura-voice/venv; ~/nura-voice/venv/bin/pip install vosk)"
    if brain_running; then ok "ponte già acceso (pid $(cat "$BRAIN_PID"))"; return; fi
    local others
    others="$(pgrep -f 'brain-pc\.py' | tr '\n' ' ')"
    if [[ -n "$others" ]]; then
        warn "c'è già un ponte avviato a mano (pid $others): lo fermo per non averne due"
        kill $others 2>/dev/null; sleep 1
    fi
    mkdir -p "$(dirname "$BRAIN_PID")"
    setsid nohup bash -c "while true; do '$PY' -u '$HERE/brain-pc.py' >> '$BRAIN_LOG' 2>&1; \
        echo \"\$(date +%T) ponte uscito, riparto tra 5 s\" >> '$BRAIN_LOG'; sleep 5; done" >/dev/null 2>&1 &
    echo $! > "$BRAIN_PID"
    ok "ponte acceso (pid $!, log $BRAIN_LOG)"
}

brain_stop() {
    if brain_running; then kill -- -"$(cat "$BRAIN_PID")" 2>/dev/null || kill "$(cat "$BRAIN_PID")"; fi
    rm -f "$BRAIN_PID"
    pkill -f 'brain-pc\.py' 2>/dev/null
    ok "ponte fermo"
}

# ------------------------------------------------------------------ telefono
copy_to_phone() {
    tar -C "$HERE" -cf - answer.py convo.py at.py sms.py call.py miui-mount.sh ct-setup.sh ct-start.sh init.rc \
        audio/mtkaudio.c audio/build.sh audio/start.sh assets/fine.raw \
        | phone_in 'mkdir -p ~/nura && tar -C ~/nura -xf -' || die "copia sul telefono non riuscita"
}

# Script eseguito sul telefono: avvia quello che manca, in ordine. $1 = "riavvia" per fermare prima i servizi.
PHONE_SCRIPT='
set -u
N=$HOME/nura; B=/var/lib/miui-ct; T=$B/data/local/tmp
say() { echo "  $*"; }
if [ "${1:-}" = riavvia ]; then
    for p in $(pgrep -f "^python3 -u .*(convo|answer)\.py") $(pgrep -f "^/data/local/tmp/mtkaudio|^nsenter .*mtkaudio|^sleep 2147483647|^/bin/sleep 2147483647"); do
        sudo kill $p 2>/dev/null
    done
    sleep 1; say "servizi di Piper fermati"
fi
# 1. contenitore Android con il modem
if ! pgrep -f "^/system/bin/init second_stage" >/dev/null; then
    say "contenitore del modem spento: lo avvio"
    cd $N && sh miui-mount.sh >/dev/null && sh ct-setup.sh >/dev/null || { say "ERRORE: preparazione del contenitore"; exit 1; }
    sudo cp ct-start.sh init.rc $B/
    sudo setsid sh -c "unshare -m -p -f --propagation private sh $B/ct-start.sh > $B/ct.log 2>&1" </dev/null >/dev/null 2>&1 &
    i=0; until sudo cat /sys/kernel/ccci/boot 2>/dev/null | grep -q "md1:4"; do
        i=$((i+1)); [ $i -gt 90 ] && { say "ERRORE: il modem non arriva a ready"; exit 1; }; sleep 1
    done
fi
say "modem: $(sudo cat /sys/kernel/ccci/boot | cut -d" " -f1)"
# 2. radio accesa e registrata (solo se la porta AT è libera, cioè answer.py non gira)
if ! pgrep -f "^python3 -u .*answer\.py" >/dev/null; then
    sudo python3 $N/at.py /dev/ttyC0 AT+CFUN=1 >/dev/null 2>&1
    i=0; until sudo python3 $N/at.py /dev/ttyC0 AT+CREG? 2>/dev/null | grep -qE "\+CREG: [0-9],[15]"; do
        i=$((i+1)); [ $i -gt 30 ] && { say "ATTENZIONE: non ancora registrato in rete"; break; }; sleep 2
    done
fi
# 3. audio: mtkaudio dentro il contenitore
sudo mkdir -p $T && sudo cp $N/assets/fine.raw $T/
if ! pgrep -f "^/data/local/tmp/mtkaudio" >/dev/null; then
    if [ ! -x $N/audio/mtkaudio ] || [ $N/audio/mtkaudio.c -nt $N/audio/mtkaudio ]; then
        say "compilo mtkaudio"; sh $N/audio/build.sh >/dev/null 2>&1 || { say "ERRORE: compilazione di mtkaudio"; exit 1; }
    fi
    sudo setsid sh $N/audio/start.sh </dev/null >/tmp/start.out 2>&1 &
    i=0; until grep -q "^pronto" /tmp/mtkaudio.log 2>/dev/null && pgrep -f "^/data/local/tmp/mtkaudio" >/dev/null; do
        i=$((i+1)); [ $i -gt 20 ] && { say "ERRORE: mtkaudio non parte"; exit 1; }; sleep 1
    done
fi
say "audio: mtkaudio acceso"
# 4. conversazione (Piper, Vosk, frasi fisse: circa 20 s per caricare)
if ! pgrep -f "^python3 -u .*convo\.py" >/dev/null; then
    sudo setsid sh -c "python3 -u $N/convo.py >> /tmp/answer.log 2>&1" </dev/null >/dev/null 2>&1 &
    i=0; until tail -n 5 /tmp/answer.log 2>/dev/null | grep -q "\[convo\] pronto"; do
        i=$((i+1)); [ $i -gt 60 ] && { say "ERRORE: convo.py non è pronto"; exit 1; }; sleep 1
    done
fi
say "conversazione: pronta"
# 5. risposta automatica
if ! pgrep -f "^python3 -u .*answer\.py" >/dev/null; then
    sudo setsid sh -c "python3 -u $N/answer.py /dev/ttyC0 600 convo >> /tmp/answer.log 2>&1" </dev/null >/dev/null 2>&1 &
    sleep 3
fi
pgrep -f "^python3 -u .*answer\.py" >/dev/null && say "risposta automatica: in ascolto" || { say "ERRORE: answer.py"; exit 1; }
'

LLM_FILE=gemma-3-270m-it-Q4_K_M.gguf  # cervello piccolo per la modalità autonoma (llama.cpp sul telefono)

phone_start() {
    phone true || die "telefono non raggiungibile su $PHONE (cavo USB? rete USB?)"
    copy_to_phone
    if ! phone "test -s ~/nura/llm/$LLM_FILE" && [[ -s "$HOME/nura-voice/llm/$LLM_FILE" ]]; then
        echo "  copio il cervello piccolo sul telefono ($LLM_FILE)"
        phone 'mkdir -p ~/nura/llm'
        "${SSH[@]/#ssh/scp}" -q "$HOME/nura-voice/llm/$LLM_FILE" "$PHONE:nura/llm/" 2>/dev/null \
            || scp -q -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                "$HOME/nura-voice/llm/$LLM_FILE" "$PHONE:nura/llm/"
    fi
    phone_in "sh -s -- ${1:-}" <<<"$PHONE_SCRIPT" || die "avvio sul telefono non riuscito"
}

phone_stop() {
    phone 'for p in $(pgrep -f "^python3 -u .*(convo|answer)\.py") $(pgrep -f "^/data/local/tmp/mtkaudio|^nsenter .*mtkaudio|^sleep 2147483647|^/bin/sleep 2147483647"); do sudo kill $p 2>/dev/null; done' \
        && ok "servizi di Piper sul telefono fermati (il modem resta acceso)"
}

status() {
    info "PC"
    if brain_running; then ok "ponte acceso (pid $(cat "$BRAIN_PID"))"; else
        p="$(pgrep -f 'brain-pc\.py' | tr '\n' ' ')"
        [[ -n "$p" ]] && warn "ponte avviato a mano (pid $p): piper.sh riavvia lo prende in carico" || warn "ponte spento"
    fi
    info "telefono"
    phone true || { warn "non raggiungibile su $PHONE"; return; }
    phone 'B=/var/lib/miui-ct
        pgrep -f "^/system/bin/init second_stage" >/dev/null && echo "  contenitore: acceso ($(sudo cat /sys/kernel/ccci/boot | cut -d" " -f1))" || echo "  contenitore: spento"
        pgrep -f "^/data/local/tmp/mtkaudio" >/dev/null && echo "  mtkaudio: acceso" || echo "  mtkaudio: spento"
        for s in convo answer; do pgrep -f "^python3 -u .*/$s[.]py" >/dev/null && echo "  $s.py: acceso" || echo "  $s.py: spento"; done
        a=$(( $(date +%s) - $(stat -c %Y /tmp/brain.a 2>/dev/null || echo 0) ))
        [ $a -lt 15 ] && echo "  battito del ponte: ${a} s fa" || echo "  battito del ponte: assente da ${a} s"
        echo "  ultima registrazione in rete: $(grep -o "+CREG: [0-9,]*" /tmp/answer.log 2>/dev/null | tail -1)"
        echo "  ultima chiamata: $(grep -E "connessa|chiamata chiusa" /tmp/answer.log 2>/dev/null | tail -1)"'
}

case "${1:-avvia}" in
    avvia)   info "telefono"; phone_start; info "PC"; brain_start; info "Piper è pronto: chiamalo." ;;
    riavvia) info "PC"; brain_stop; info "telefono"; phone_start riavvia; info "PC"; brain_start
             info "Piper è pronto: chiamalo." ;;
    ferma)   brain_stop; phone_stop ;;
    stato)   status ;;
    log)     tail -n 20 -F "$BRAIN_LOG" & trap 'kill $!' EXIT; phone 'tail -n 20 -F /tmp/answer.log' ;;
    *)       sed -n '2,12p' "$0"; exit 1 ;;
esac
