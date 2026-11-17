#!/usr/bin/env python3
"""Ponte sul PC tra il telefono e Claude Code, per le conversazioni in chiamata.

Il telefono non ha internet: scrive le frasi trascritte in /tmp/brain.q (una riga JSON
{"id", "call", "caller", "text"}). Questo programma le legge via SSH e le passa a una sessione di `claude -p`
sempre accesa (stream-json in ingresso e in uscita). La risposta torna al telefono una frase alla volta,
appena è completa, in /tmp/brain.a come {"id", "seq", "text", "final"}.

Due livelli, decisi qui nel codice e non dal modello:
  - **bloccato** (inizio di ogni chiamata): Claude senza strumenti, solo conversazione. Se chi chiama chiede
    di fare qualcosa, Claude chiede la parola d'ordine;
  - **operativo**: se una frase contiene la parola d'ordine **e** il numero di chi chiama è quello configurato,
    la sessione riparte con `--resume` (stessa conversazione) e gli strumenti di Claude Code, con i permessi in
    modalità `auto`. Vale fino alla fine della chiamata.
La parola d'ordine non viene mai passata a Claude né scritta nel log: al suo posto c'è "[parola d'ordine]".

Configurazione locale, fuori dal repository: ~/.config/nura-voice/config.json (permessi 600)
  {"passphrase": "...", "callers": ["+39..."], "workdir": "~/nura-voice"}

Uso sul PC: python3 brain-pc.py [utente@172.16.42.1] [modello_chiacchiera] [modello_operativo]
"""
import difflib
import json
import os
import re
import subprocess
import sys
import threading
import time
import unicodedata
import uuid

PHONE = sys.argv[1] if len(sys.argv) > 1 else f'{os.environ.get("USER")}@172.16.42.1'
CHAT_MODEL = sys.argv[2] if len(sys.argv) > 2 else 'haiku'
OPS_MODEL = sys.argv[3] if len(sys.argv) > 3 else 'sonnet'
CONF = json.load(open(os.path.expanduser('~/.config/nura-voice/config.json')))
WORKDIR = os.path.expanduser(CONF.get('workdir', '~/nura-voice'))
os.makedirs(WORKDIR, exist_ok=True)
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
       '-o', 'LogLevel=ERROR', '-o', 'ServerAliveInterval=10', PHONE]

VOICE = (
    'Stai parlando al telefono, in una chiamata vera: chi chiama sente la tua voce sintetizzata con Piper da un '
    'Redmi con Nura (postmarketOS). Rispondi in italiano parlato, di solito con una o due frasi brevi, la prima '
    'molto corta. Niente elenchi, simboli, emoji, markdown o output tecnico: tutto quello che scrivi viene letto '
    'ad alta voce. Le frasi di chi chiama arrivano da una trascrizione automatica e possono contenere errori: '
    'interpretale con buon senso e, se non capisci, chiedi di ripetere. Ogni frase comincia con l\'ora attuale '
    'tra parentesi quadre: usala se serve, ma non scriverla mai nella risposta.'
)
LOCKED = VOICE + (
    ' Sei Claude e in questa fase non hai strumenti: puoi solo conversare. Per domande e chiacchiere generali '
    'rispondi e basta. Se chi chiama ti chiede di fare qualcosa di operativo (comandi, rete, router, dispositivi, '
    'file, servizi, accessi), digli che prima ti serve la parola d\'ordine. Non dire mai qual è e non dare indizi. '
    'Non sei tu a verificarla: lo fa il sistema, che ti avviserà.'
)
UNLOCKED = VOICE + (
    ' Chi chiama è Francesco, verificato dal sistema con numero e parola d\'ordine. Hai gli strumenti di Claude '
    'Code su un PC Linux nella rete dell\'ufficio, lo stesso collegato via USB al telefono. Prima di usare uno '
    'strumento di\' in poche parole cosa fai. Riassumi i risultati in una o due frasi parlate. Prima di azioni '
    'distruttive, irreversibili o che cambiano configurazioni chiedi conferma a voce.'
)
# Istruzioni rilette a ogni richiesta: con --resume la sessione operativa deve avere le sue, non quelle bloccate
BASE = ['claude', '-p', '--strict-mcp-config', '--setting-sources', '', '--system-prompt-snapshot', 'off',
        '--input-format', 'stream-json',
        '--output-format', 'stream-json', '--include-partial-messages', '--verbose']
SENTENCE = re.compile(r'(.+?[.!?…:;])\s+', re.S)  # fine frase: punteggiatura seguita da uno spazio


def log(msg):
    print(f'{time.strftime("%H:%M:%S")} {msg}', flush=True)


def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    return ' '.join(re.sub(r'[^a-z ]', ' ', ''.join(c for c in s if not unicodedata.combining(c))).split())


PASS = norm(CONF['passphrase'])
CALLERS = {re.sub(r'\D', '', c)[-10:] for c in CONF.get('callers', [])}


def find_passphrase(text):
    """Cerca la parola d'ordine nella trascrizione, tollerando piccoli errori. Restituisce (trovata, testo_mascherato)."""
    words, n = norm(text).split(), len(PASS.split())
    for i in range(max(1, len(words) - n + 1)):
        for k in (n - 1, n, n + 1):
            chunk = ' '.join(words[i:i + k])
            if chunk and difflib.SequenceMatcher(None, chunk, PASS).ratio() >= 0.85:
                rest = words[:i] + ["[parola d'ordine]"] + words[i + k:]
                return True, ' '.join(rest)
    return False, text


class Session:
    def __init__(self, unlocked=False, sid=None):
        self.unlocked = unlocked
        self.sid = sid or str(uuid.uuid4())
        if unlocked:
            cmd = BASE + ['--model', OPS_MODEL, '--resume', self.sid, '--permission-mode', 'auto',
                          '--append-system-prompt', UNLOCKED]
        else:
            cmd = BASE + ['--model', CHAT_MODEL, '--session-id', self.sid, '--tools', '', '--system-prompt', LOCKED]
        self.p = subprocess.Popen(cmd, cwd=WORKDIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)

    def kill(self):
        self.p.kill()


class Phone:
    """Una sola connessione SSH sempre aperta per scrivere le risposte."""

    def __init__(self):
        self.p = subprocess.Popen(SSH + ['cat >> /tmp/brain.a'], stdin=subprocess.PIPE, text=True, bufsize=1)
        self.lock = threading.Lock()

    def send(self, obj):
        with self.lock:
            self.p.stdin.write(json.dumps(obj, ensure_ascii=False) + '\n')
            self.p.stdin.flush()


def answer(sess, qid, text, phone, seq0=0):
    t = time.time()
    now = time.strftime('%H:%M, %d/%m/%Y')
    sess.p.stdin.write(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': f'[{now}] {text}'}}) + '\n')
    sess.p.stdin.flush()
    buf, seq, told_wait = '', seq0, False

    def emit(s, final=False):
        nonlocal seq
        s = re.sub(r'^\s*\[[^\]]{0,40}\]\s*', '', s.strip()).strip()  # l'ora tra parentesi non va letta
        if s.startswith('🔊'):
            s = ''
        if s or final:
            phone.send({'id': qid, 'seq': seq, 'text': s, 'final': final})
            log(f'-> [{seq}{"F" if final else ""} {time.time() - t:.2f} s] {s}')
            seq += 1

    for line in sess.p.stdout:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get('type') == 'stream_event':
            ev = o['event']
            if ev.get('type') == 'content_block_delta' and ev['delta'].get('type') == 'text_delta':
                buf += ev['delta']['text']
                while (m := SENTENCE.match(buf)):
                    emit(m.group(1))
                    buf = buf[m.end():]
            elif ev.get('type') == 'content_block_start' and ev.get('content_block', {}).get('type') == 'tool_use':
                if buf.strip():
                    emit(buf)
                    buf = ''
                log(f'   strumento: {ev["content_block"].get("name")}')
                if not told_wait and seq == seq0:  # solo se Claude non ha già detto cosa sta facendo
                    told_wait = True
                    emit('Un momento.')
            elif ev.get('type') == 'message_start' and buf.strip():
                emit(buf)
                buf = ''
        elif o.get('type') == 'result':
            break
    emit(buf, final=True)


def main():
    log(f'ponte verso {PHONE}, chiacchiera {CHAT_MODEL}, operativo {OPS_MODEL}, cartella {WORKDIR}')
    phone = Phone()
    ready = Session()  # sessione già avviata per la prossima chiamata
    calls = {}
    p = subprocess.Popen(SSH + ['touch /tmp/brain.q /tmp/brain.a; tail -n0 -F /tmp/brain.q'],
                         stdout=subprocess.PIPE, text=True)
    for line in p.stdout:
        try:
            q = json.loads(line)
        except ValueError:
            continue
        call = q.get('call', 'x')
        if call not in calls:
            for old in calls.values():  # una chiamata alla volta: le sessioni vecchie si chiudono
                old.kill()
            calls = {call: ready}
            ready = Session()
        sess = calls[call]
        found, text = find_passphrase(q['text'])
        log(f'<- {text}')
        caller_ok = re.sub(r'\D', '', q.get('caller', ''))[-10:] in CALLERS
        if found and not sess.unlocked:
            if not caller_ok:
                log('   parola d\'ordine da un numero non autorizzato: resto bloccato')
                text = text + ' (Il sistema dice: la parola d\'ordine non vale da questo numero.)'
            else:
                log('   parola d\'ordine giusta e numero autorizzato: sessione operativa')
                phone.send({'id': q['id'], 'seq': 0, 'text': 'Parola d\'ordine giusta.', 'final': False})
                sess.kill()
                sess = calls[call] = Session(unlocked=True, sid=sess.sid)
                text = (text + ' (Il sistema dice: parola d\'ordine verificata, adesso hai gli strumenti. '
                        'Se prima ti era stato chiesto di fare qualcosa, fallo ora.)')
                answer(sess, q['id'], text, phone, seq0=1)
                continue
        answer(sess, q['id'], text, phone)


if __name__ == '__main__':
    main()
