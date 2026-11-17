"""Conversazione in chiamata: ascolta chi chiama, trascrive, chiede la risposta, la dice con Piper.

Servizio sempre acceso: carica Piper e Vosk una volta sola (Piper impiega 12 s a caricare il modello e circa
1 s a sintetizzare una frase) e prepara le frasi fisse. Aspetta i comandi di answer.py su /tmp/convo.cmd:
  start <id_chiamata> <numero>   a chiamata connessa: la voce del modem e gli stream sono già pronti, si saluta subito
  stop                  a fine chiamata
Per rispondere in fretta:
  - Vosk trascrive **mentre** chi chiama parla: mtkaudio (recvad) scrive l'audio frame per frame e qui lo si
    legge man mano che il file cresce; a fine frase il testo è già pronto;
  - la risposta arriva da brain-pc.py una frase alla volta: la prima si sintetizza e si suona mentre Claude
    scrive le altre, e la sintesi della frase successiva avviene mentre si suona la precedente.
Comanda mtkaudio via /tmp/mtkaudio.cmd e ne legge le risposte da /tmp/mtkaudio.log.

Uso: sudo python3 convo.py
"""
import json
import os
import queue
import re
import subprocess
import threading
import time
import wave

HOME = '/home/francesco'
VOICE = f'{HOME}/piper-voices/it_IT-paola-medium.onnx'
# Pronuncia: copia del repository github.com/francescobianco/piper, tenuta aggiornata da brain-pc.py.
# Dizionario e impostazioni si rileggono a ogni frase: una correzione vale dalla frase successiva.
PRONUNCIA = f'{HOME}/piper'
VOSK_MODEL = f'{HOME}/stt/vosk-model-small-it-0.22'
CT = '/var/lib/miui-ct/data/local/tmp'  # la stessa cartella vista da mtkaudio come /data/local/tmp
LOG, CMD, CTL = '/tmp/mtkaudio.log', '/tmp/mtkaudio.cmd', '/tmp/convo.cmd'
Q, A = '/tmp/brain.q', '/tmp/brain.a'
GREETING = 'Ciao, sono Piper. Dimmi pure.'
AT_FIFO = '/tmp/answer.cmd'  # comandi AT, inviati da answer.py che tiene aperta la porta del modem
SILENCE_MS = 700   # pausa che chiude la frase di chi chiama
THRESHOLD = 700    # soglia RMS del parlato

active = threading.Event()
call_id = ['']
caller = ['']
mtk_lock = threading.Lock()


def log(msg):
    print(f'{time.strftime("%H:%M:%S")} [convo] {msg}', flush=True)


def mtk(cmd, wait=None, timeout=60):
    """Manda un comando a mtkaudio e, se richiesto, aspetta la riga di log che inizia con `wait`."""
    with mtk_lock:
        pos = os.path.getsize(LOG)
        with open(CMD, 'w') as f:
            f.write(cmd + '\n')
        if not wait:
            return ''
        end = time.time() + timeout
        while time.time() < end:
            with open(LOG, errors='replace') as f:
                f.seek(pos)
                for line in f.read().splitlines():
                    if line.startswith(wait):
                        return line
            time.sleep(0.03)
        return ''


def render(text, raw):
    """Frase -> PCM 16 bit mono 16 kHz, con il modello di Piper già caricato e il dizionario di pronuncia."""
    wav = raw + '.wav'
    with wave.open(wav, 'wb') as w:
        pron.sintetizza(voice, text, w)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-ar', '16000', '-ac', '1', '-f', 's16le', raw])
    os.unlink(wav)


def play(name):
    mtk(f'mplay /data/local/tmp/{name}', 'play:', timeout=120)


def at(*cmds, pause=0.0):
    """Manda comandi AT tramite answer.py (che tiene la porta del modem)."""
    for c in cmds:
        fd = os.open(AT_FIFO, os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (c + '\n').encode())
        os.close(fd)
        if pause:
            time.sleep(pause)


def execute(action):
    """Azione arrivata dal ponte, nel punto della risposta in cui Claude l'ha scritta. Controllo anche qui."""
    kind = action.get('type')
    num = str(action.get('number', ''))
    log(f'azione: {action}')
    if kind == 'hangup':
        at('ATH')
        active.clear()  # answer.py vede la chiamata chiusa e manda stop; intanto si smette di ascoltare
    elif kind == 'dial' and re.fullmatch(r'\+?\d{6,15}', num):
        at(f'ATD{num};')
    elif kind == 'sms' and re.fullmatch(r'\+?\d{6,15}', num):
        text = ''.join(c for c in str(action.get('text', ''))[:160] if c.isprintable())
        at('AT+CMGF=1', 'AT+CSCS="GSM"', pause=0.3)
        at(f'AT+CMGS="{num}"', pause=1.0)  # il modem risponde con ">" e aspetta il testo
        at(text + '\x1a')
    elif kind == 'at' and re.fullmatch(r'AT[A-Z0-9+?=,"#*.:;_ -]{0,60}', str(action.get('command', '')), re.I):
        at(action['command'])
    else:
        log(f'azione scartata: {action}')


def speak(items):
    """Sintetizza e suona le frasi man mano che arrivano (la sintesi della successiva va in parallelo) ed esegue
    le azioni nel loro punto, dopo che le frasi precedenti sono state dette."""
    ready = queue.Queue()

    def synth():
        for i, s in enumerate(items):
            if not active.is_set():
                break
            if isinstance(s, dict):
                ready.put(s)
                continue
            name = f'say-{i % 8}.raw'
            t = time.time()
            render(s, f'{CT}/{name}')
            log(f'piper {time.time() - t:.1f} s: {s}')
            ready.put(name)
        ready.put(None)

    threading.Thread(target=synth, daemon=True).start()
    while (name := ready.get()) is not None:
        if isinstance(name, dict):
            execute(name)
        elif active.is_set():
            play(name)


def listen():
    """Registra fino alla pausa e trascrive in contemporanea. Restituisce il testo (anche vuoto)."""
    raw = f'{CT}/ascolto.raw'
    try:
        os.unlink(raw)
    except FileNotFoundError:
        pass
    rec = vosk.KaldiRecognizer(vosk_model, 16000)
    pos = os.path.getsize(LOG)
    with open(CMD, 'w') as f:
        f.write(f'recvad /data/local/tmp/ascolto.raw 15 {SILENCE_MS} {THRESHOLD}\n')
    off, done, t_end, fd = 0, False, None, None
    deadline = time.time() + 30
    while time.time() < deadline:
        if not done:
            with open(LOG, errors='replace') as f:
                f.seek(pos)
                done = any(l.startswith('recvad:') for l in f.read().splitlines())
                if done:
                    t_end = time.time()
        if fd is None and os.path.exists(raw):
            fd = open(raw, 'rb')
        if fd:
            chunk = fd.read()
            if len(chunk) % 2:
                fd.seek(-1, 1)
                chunk = chunk[:-1]
            if chunk:
                rec.AcceptWaveform(chunk)
                off += len(chunk)
        if done:
            break
        time.sleep(0.05)
    if fd:
        fd.close()
    if off < 16000:  # meno di mezzo secondo di parlato
        return ''
    text = json.loads(rec.FinalResult())['text']
    log(f'trascrizione pronta {time.time() - (t_end or time.time()):.2f} s dopo la pausa: {text}')
    return text


def ask(text, n=[0]):
    """Manda la frase al ponte e restituisce le frasi della risposta man mano che arrivano."""
    n[0] += 1
    qid = f'{call_id[0]}-{n[0]}'
    pos = os.path.getsize(A)
    with open(Q, 'a') as f:
        f.write(json.dumps({'id': qid, 'call': call_id[0], 'caller': caller[0], 'text': text},
                           ensure_ascii=False) + '\n')
    t = time.time()
    got = 0
    while time.time() - t < 180 and active.is_set():  # con gli strumenti una risposta può richiedere tempo
        with open(A, errors='replace') as f:
            f.seek(pos)
            data = f.read()
        lines = data.split('\n')
        pos += len(data.encode()) - len(lines[-1].encode())  # l'ultima riga può essere ancora a metà
        for line in lines[:-1]:
            try:
                a = json.loads(line)
            except ValueError:
                continue
            if a.get('id') != qid:
                continue
            if got == 0:
                log(f'prima frase dopo {time.time() - t:.2f} s')
            got += 1
            if a.get('action'):
                yield a['action']
            elif a['text']:
                yield a['text']
            if a.get('final'):
                return
        time.sleep(0.03)
    if not got:
        yield 'Scusa, il mio cervello sul computer non risponde. Riprova tra poco.'


def conversation():
    play('saluto.raw')
    silent = 0
    while active.is_set():
        text = listen()
        if not active.is_set():
            break
        if not text:
            silent += 1
            if silent == 2:
                play('cisei.raw')
            continue
        silent = 0
        speak(ask(text))
    log('conversazione finita')


def render_fixed():
    render(GREETING, f'{CT}/saluto.raw')
    render('Ci sei? Non ti sento.', f'{CT}/cisei.raw')


def watch_pronuncia():
    """Se dizionario o impostazioni cambiano, rigenera subito le frasi fisse (pronte per la prossima chiamata)."""
    def stamp():
        return [os.path.getmtime(f) if os.path.exists(f) else 0 for f in (pron.tsv, pron.json)]
    last = stamp()
    while True:
        time.sleep(2)
        now = stamp()
        if now != last and not active.is_set():
            last = now
            render_fixed()
            log('pronuncia aggiornata: frasi fisse rigenerate')


def main():
    global voice, vosk, vosk_model, pron
    t = time.time()
    import sys
    sys.path.insert(0, PRONUNCIA)
    from pronuncia import Pronuncia
    pron = Pronuncia()
    from piper import PiperVoice
    import vosk
    vosk.SetLogLevel(-1)
    voice = PiperVoice.load(VOICE)
    vosk_model = vosk.Model(VOSK_MODEL)
    # Le frasi fisse si preparano subito, così il saluto parte appena si risponde
    render_fixed()
    threading.Thread(target=watch_pronuncia, daemon=True).start()
    for p in (Q, A):
        open(p, 'a').close()
        os.chmod(p, 0o666)
    if not os.path.exists(CTL):
        os.mkfifo(CTL, 0o600)
    log(f'pronto in {time.time() - t:.1f} s')
    while True:
        with open(CTL) as f:  # si blocca finché answer.py non scrive
            for line in f:
                cmd = line.split()
                if not cmd:
                    continue
                if cmd[0] == 'start' and not active.is_set():
                    call_id[0] = cmd[1] if len(cmd) > 1 else str(int(time.time()))
                    caller[0] = cmd[2] if len(cmd) > 2 else ''
                    active.set()
                    threading.Thread(target=conversation, daemon=True).start()
                    log(f'chiamata {call_id[0]}')
                elif cmd[0] == 'stop':
                    active.clear()


if __name__ == '__main__':
    main()
