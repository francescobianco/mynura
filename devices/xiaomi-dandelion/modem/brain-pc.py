#!/usr/bin/env python3
"""Ponte sul PC tra il telefono e Claude Code, per le conversazioni in chiamata.

Il telefono non ha internet: scrive le frasi trascritte in /tmp/brain.q (una riga JSON {"id", "call", "text"}).
Questo programma le legge via SSH e le passa a una sessione di `claude -p` sempre accesa (stream-json in
ingresso e in uscita): il primo pezzo di risposta arriva in circa 1 s invece dei 3-6 s di un `claude -p` per
frase. La risposta torna al telefono **una frase alla volta**, appena è completa, in /tmp/brain.a come
{"id", "seq", "text", "final"}: il telefono comincia a parlare mentre Claude scrive ancora il resto.

C'è sempre una sessione pronta per la prossima chiamata, avviata in anticipo.

Uso sul PC: python3 brain-pc.py [utente@172.16.42.1] [modello]
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time

PHONE = sys.argv[1] if len(sys.argv) > 1 else f'{os.environ.get("USER")}@172.16.42.1'
MODEL = sys.argv[2] if len(sys.argv) > 2 else 'haiku'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
       '-o', 'LogLevel=ERROR', '-o', 'ServerAliveInterval=10', PHONE]
SYSTEM = (
    'Sei Claude e stai parlando al telefono, in una chiamata vera: chi chiama sente la tua voce sintetizzata '
    'con Piper da un Redmi con Nura (postmarketOS). Rispondi in italiano parlato, di solito con una o due frasi '
    'brevi, la prima molto corta: comincia a parlare appena la prima frase è pronta. Niente elenchi, simboli, '
    'emoji o markdown: tutto quello che scrivi viene letto ad alta voce. Le frasi di chi chiama arrivano da una '
    'trascrizione automatica e possono contenere errori: interpretale con buon senso e, se non capisci, chiedi '
    'di ripetere. Ogni frase comincia con l\'ora attuale tra parentesi quadre: usala se serve, non ripeterla.'
)
WORKDIR = tempfile.mkdtemp(prefix='brain-')  # cartella neutra: niente CLAUDE.md del progetto
CMD = ['claude', '-p', '--model', MODEL, '--tools', '', '--strict-mcp-config', '--setting-sources', '',
       '--no-session-persistence', '--input-format', 'stream-json', '--output-format', 'stream-json',
       '--include-partial-messages', '--verbose', '--system-prompt', SYSTEM]
# Fine frase: punteggiatura seguita da uno spazio
SENTENCE = re.compile(r'(.+?[.!?…:;])\s+', re.S)


def log(msg):
    print(f'{time.strftime("%H:%M:%S")} {msg}', flush=True)


def new_session():
    return subprocess.Popen(CMD, cwd=WORKDIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, bufsize=1)


class Phone:
    """Una sola connessione SSH sempre aperta per scrivere le risposte."""

    def __init__(self):
        self.p = subprocess.Popen(SSH + ['cat >> /tmp/brain.a'], stdin=subprocess.PIPE, text=True, bufsize=1)
        self.lock = threading.Lock()

    def send(self, obj):
        with self.lock:
            self.p.stdin.write(json.dumps(obj, ensure_ascii=False) + '\n')
            self.p.stdin.flush()


def answer(sess, qid, text, phone):
    t = time.time()
    now = time.strftime('%H:%M, %d/%m/%Y')
    sess.stdin.write(json.dumps({'type': 'user', 'message': {'role': 'user', 'content': f'[{now}] {text}'}}) + '\n')
    sess.stdin.flush()
    buf, seq, first = '', 0, None

    def emit(s, final=False):
        nonlocal seq
        s = s.strip()
        if s.startswith('🔊'):
            s = ''
        if s or final:
            phone.send({'id': qid, 'seq': seq, 'text': s, 'final': final})
            log(f'-> [{seq}{"F" if final else ""} {time.time() - t:.2f} s] {s}')
            seq += 1

    for line in sess.stdout:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get('type') == 'stream_event':
            ev = o['event']
            if ev.get('type') == 'content_block_delta' and ev['delta'].get('type') == 'text_delta':
                if first is None:
                    first = time.time() - t
                buf += ev['delta']['text']
                while (m := SENTENCE.match(buf)):
                    emit(m.group(1))
                    buf = buf[m.end():]
        elif o.get('type') == 'result':
            break
    emit(buf, final=True)


def main():
    log(f'ponte verso {PHONE}, modello {MODEL}')
    phone = Phone()
    ready = new_session()  # sessione già avviata per la prossima chiamata
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
            ready = new_session()
        log(f'<- {q["text"]}')
        answer(calls[call], q['id'], q['text'], phone)


if __name__ == '__main__':
    main()
