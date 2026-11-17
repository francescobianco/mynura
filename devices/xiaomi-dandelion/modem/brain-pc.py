#!/usr/bin/env python3
"""Ponte sul PC tra il telefono e Claude Code, per le conversazioni in chiamata.

Il telefono non ha internet: scrive le frasi trascritte in /tmp/brain.q (una riga JSON {"id", "call", "text"}).
Questo programma le legge via SSH, chiede la risposta a `claude -p` (stessa sessione per tutta la chiamata)
e la riscrive in /tmp/brain.a come {"id", "text"}.

Uso sul PC: python3 brain-pc.py [utente@172.16.42.1] [modello]
"""
import json
import os
import subprocess
import sys
import tempfile
import uuid

PHONE = sys.argv[1] if len(sys.argv) > 1 else f'{os.environ.get("USER")}@172.16.42.1'
MODEL = sys.argv[2] if len(sys.argv) > 2 else 'haiku'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
       '-o', 'LogLevel=ERROR', '-o', 'ServerAliveInterval=10', PHONE]
SYSTEM = (
    'Sei Claude e stai parlando al telefono, in una chiamata vera: chi chiama sente la tua voce sintetizzata '
    'con Piper da un Redmi con Nura (postmarketOS). Rispondi in italiano parlato, con una o due frasi brevi, '
    'senza elenchi, simboli, emoji o markdown: tutto quello che scrivi viene letto ad alta voce. '
    'Le frasi di chi chiama arrivano da una trascrizione automatica e possono contenere errori: '
    'interpretale con buon senso e, se non capisci, chiedi di ripetere.'
)
# Cartella neutra: niente CLAUDE.md del progetto nel contesto
WORKDIR = tempfile.mkdtemp(prefix='brain-')
sessions = {}


def ask(call, text):
    cmd = ['claude', '-p', '--model', MODEL, '--tools', '', '--strict-mcp-config', '--setting-sources', '',
           '--system-prompt', SYSTEM]
    if call in sessions:
        cmd += ['--resume', sessions[call]]
    else:
        sessions[call] = str(uuid.uuid4())
        cmd += ['--session-id', sessions[call]]
    try:
        out = subprocess.run(cmd + [text], cwd=WORKDIR, capture_output=True, text=True, timeout=40).stdout
    except subprocess.TimeoutExpired:
        return 'Scusa, ci sto mettendo troppo. Puoi ripetere?'
    # Le istruzioni globali dell'utente aggiungono una riga 🔊: al telefono non serve
    lines = [l for l in out.splitlines() if l.strip() and not l.startswith('🔊')]
    return ' '.join(lines) or 'Scusa, non ho una risposta. Puoi ripetere?'


def reply(obj):
    data = json.dumps(obj, ensure_ascii=False) + '\n'
    subprocess.run(SSH + ['cat >> /tmp/brain.a'], input=data, text=True, timeout=20)


def main():
    print(f'ponte verso {PHONE}, modello {MODEL}', flush=True)
    p = subprocess.Popen(SSH + ['touch /tmp/brain.q /tmp/brain.a; tail -n0 -F /tmp/brain.q'],
                         stdout=subprocess.PIPE, text=True)
    for line in p.stdout:
        try:
            q = json.loads(line)
        except ValueError:
            continue
        print(f'<- {q["text"]}', flush=True)
        a = ask(q.get('call', 'x'), q['text'])
        print(f'-> {a}', flush=True)
        reply({'id': q['id'], 'text': a})


if __name__ == '__main__':
    main()
