"""Conversazione in chiamata: ascolta chi chiama, trascrive, chiede la risposta, la dice con Piper.

Servizio sempre acceso: carica Piper e Vosk una volta sola (Piper impiega 12 s a caricare il modello e 1 s
a sintetizzare una frase), poi aspetta i comandi di answer.py su /tmp/convo.cmd:
  start <id_chiamata>   a chiamata connessa (voce del modem accesa e stream incall music aperto)
  stop                  a fine chiamata
Comanda mtkaudio via /tmp/mtkaudio.cmd e ne legge le risposte da /tmp/mtkaudio.log.
La risposta la dà brain-pc.py sul PC: domande in /tmp/brain.q, risposte in /tmp/brain.a.
Trascrizione con Vosk (modello piccolo italiano): whisper.cpp base trascrive meglio ma ci mette 15 s per 6 s
di audio sul Helio G25. Con STT=whisper nell'ambiente si usa whisper.cpp.

Uso: sudo python3 convo.py
"""
import json
import os
import subprocess
import threading
import time
import wave

HOME = '/home/francesco'
VOICE = f'{HOME}/piper-voices/it_IT-paola-medium.onnx'
WHISPER = f'{HOME}/stt/whisper.cpp-1.7.6/build/bin/whisper-cli'
WHISPER_MODEL = f'{HOME}/stt/ggml-base-q5_1.bin'
VOSK_MODEL = f'{HOME}/stt/vosk-model-small-it-0.22'
CT = '/var/lib/miui-ct/data/local/tmp'  # la stessa cartella vista da mtkaudio come /data/local/tmp
LOG, CMD, CTL = '/tmp/mtkaudio.log', '/tmp/mtkaudio.cmd', '/tmp/convo.cmd'
Q, A = '/tmp/brain.q', '/tmp/brain.a'
GREETING = 'Ciao, sono Claude. Ti ascolto, dimmi pure.'

active = threading.Event()
call_id = ['']


def log(msg):
    print(f'{time.strftime("%H:%M:%S")} [convo] {msg}', flush=True)


def mtk(cmd, wait=None, timeout=60):
    """Manda un comando a mtkaudio e, se richiesto, aspetta la riga di log che inizia con `wait`."""
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
        time.sleep(0.1)
    return ''


def render(text, raw):
    """Frase -> PCM 16 bit mono 16 kHz, con il modello di Piper già caricato."""
    wav = raw + '.wav'
    with wave.open(wav, 'wb') as w:
        voice.synthesize_wav(text, w)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-ar', '16000', '-ac', '1', '-f', 's16le', raw])
    os.unlink(wav)


def say(text, n=[0]):
    if not active.is_set():
        return
    n[0] += 1
    name = f'say-{n[0] % 2}.raw'
    t = time.time()
    render(text, f'{CT}/{name}')
    log(f'piper {time.time() - t:.1f} s: {text}')
    mtk(f'mplay /data/local/tmp/{name}', 'play:', timeout=120)


def listen():
    mtk('recvad /data/local/tmp/ascolto.raw 15 900 700', 'recvad:', timeout=30)
    raw = f'{CT}/ascolto.raw'
    if not active.is_set() or not os.path.exists(raw) or os.path.getsize(raw) < 16000:
        return ''  # meno di mezzo secondo di parlato
    t = time.time()
    if os.environ.get('STT') == 'whisper' and os.path.exists(WHISPER):
        wav = '/tmp/ascolto.wav'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', '16000', '-ac', '1', '-i', raw, wav])
        out = subprocess.run([WHISPER, '-m', WHISPER_MODEL, '-l', 'it', '-nt', '-np', '-t', '8', '-f', wav],
                             capture_output=True, text=True).stdout
        text = ' '.join(out.split())
    else:
        r = vosk.KaldiRecognizer(vosk_model, 16000)
        r.AcceptWaveform(open(raw, 'rb').read())
        text = json.loads(r.FinalResult())['text']
    log(f'trascrizione {time.time() - t:.1f} s: {text}')
    return text


def think(text, n=[0]):
    n[0] += 1
    qid = f'{call_id[0]}-{n[0]}'
    pos = os.path.getsize(A)
    with open(Q, 'a') as f:
        f.write(json.dumps({'id': qid, 'call': call_id[0], 'text': text}, ensure_ascii=False) + '\n')
    t = time.time()
    while time.time() - t < 45 and active.is_set():
        with open(A, errors='replace') as f:
            f.seek(pos)
            for line in f.read().splitlines():
                try:
                    a = json.loads(line)
                except ValueError:
                    continue
                if a.get('id') == qid:
                    log(f'risposta {time.time() - t:.1f} s')
                    return a['text']
        time.sleep(0.2)
    return 'Scusa, il mio cervello sul computer non risponde. Riprova tra poco.'


def conversation():
    mtk('iopen 80000040 3 16000 1', 'open_input_stream')
    mtk('mplay /data/local/tmp/saluto.raw', 'play:', timeout=30)
    silent = 0
    while active.is_set():
        text = listen()
        if not active.is_set():
            break
        if not text:
            silent += 1
            if silent == 2:
                mtk('mplay /data/local/tmp/cisei.raw', 'play:', timeout=30)
            continue
        silent = 0
        say(think(text))
    log('conversazione finita')


def main():
    global voice, vosk, vosk_model
    t = time.time()
    from piper import PiperVoice
    import vosk
    vosk.SetLogLevel(-1)
    voice = PiperVoice.load(VOICE)
    vosk_model = vosk.Model(VOSK_MODEL)
    # Le frasi fisse si preparano subito, così il saluto parte appena si risponde
    render(GREETING, f'{CT}/saluto.raw')
    render('Ci sei? Non ti sento.', f'{CT}/cisei.raw')
    for p in (Q, A):
        open(p, 'a').close()
        os.chmod(p, 0o666)
    if not os.path.exists(CTL):
        os.mkfifo(CTL, 0o600)
    log(f'pronto in {time.time() - t:.1f} s')
    worker = None
    while True:
        with open(CTL) as f:  # si blocca finché answer.py non scrive
            for line in f:
                cmd = line.split()
                if not cmd:
                    continue
                if cmd[0] == 'start' and not active.is_set():
                    call_id[0] = cmd[1] if len(cmd) > 1 else str(int(time.time()))
                    active.set()
                    worker = threading.Thread(target=conversation, daemon=True)
                    worker.start()
                    log(f'chiamata {call_id[0]}')
                elif cmd[0] == 'stop':
                    active.clear()


if __name__ == '__main__':
    main()
