"""Conversazione in chiamata: ascolta chi chiama, trascrive, chiede la risposta, la dice con Piper.

Servizio sempre acceso: carica Piper, Vosk e le frasi fisse una volta sola, poi aspetta i comandi di answer.py
su /tmp/convo.cmd:
  start <id_chiamata> <numero>   a chiamata connessa (voce del modem e stream già pronti): si saluta subito
  stop                           a fine chiamata

Ascolto continuo e interruzioni:
  - mtkaudio registra la chiamata senza sosta (cstart) in un file che cresce; qui un thread lo legge a frame da
    20 ms e decide quando chi chiama parla (soglia sul volume);
  - se chi chiama parla **mentre Piper parla** per almeno BARGE_MS, Piper si ferma (mstop), il resto della
    risposta si scarta e il ponte viene avvisato; la frase nuova arriva a Claude insieme a quello che Piper aveva
    fatto in tempo a dire, così la conversazione cambia strada;
  - la trascrizione avviene **sul PC** (brain-pc.py, Vosk con il modello italiano grande): l'audio di ogni frase
    va in /tmp/stt.q a pezzi da 200 ms mentre si parla, il testo torna in /tmp/brain.a appena la frase si chiude.
    Se il PC non risponde entro STT_WAIT secondi si trascrive qui con il modello piccolo (con STT=local sempre qui).
La risposta arriva da brain-pc.py una frase alla volta: si sintetizza e si mette in coda subito (la coda di
mtkaudio suona senza pause), e alla fine si suona il segnale "tocca a te" (assets/fine.raw, kalimba come
l'attacco del progetto speaker). Le azioni ([[riaggancia]], ...) si eseguono al loro posto.

Modalità autonoma: se il ponte non dà battito, Piper non resta muta. Capisce pochi comandi fissi riconosciuti nel
testo trascritto qui (ora, data, batteria, rete, ripeti, aiuto, saluto e riaggancio) e fa da **segreteria**:
registra audio e testo del messaggio in ~/nura/segreteria; quando il ponte torna, brain-pc.py li preleva e li
riferisce a Francesco alla sua prima chiamata.

Uso: sudo python3 convo.py
"""
import base64
import json
import os
import queue
import re
import struct
import subprocess
import threading
import time
import wave

HOME = '/home/francesco'
VOICE = f'{HOME}/piper-voices/it_IT-paola-medium.onnx'
PRONUNCIA = f'{HOME}/piper'  # copia del repository piper, tenuta aggiornata da brain-pc.py
VOSK_MODEL = f'{HOME}/stt/vosk-model-small-it-0.22'
CT = '/var/lib/miui-ct/data/local/tmp'  # la stessa cartella vista da mtkaudio come /data/local/tmp
LOG, CMD, CTL = '/tmp/mtkaudio.log', '/tmp/mtkaudio.cmd', '/tmp/convo.cmd'
Q, A = '/tmp/brain.q', '/tmp/brain.a'
STT_Q = '/tmp/stt.q'   # audio delle frasi verso il PC
STT_WAIT = 3.0         # secondi di attesa del testo dal PC, poi trascrizione locale
STT_LOCAL = os.environ.get('STT') == 'local'
ALIVE_S = 15           # il ponte scrive un battito in /tmp/brain.a ogni 5 s: oltre 15 s di silenzio è fermo
DOWN = 'Scusa, il mio cervello sul computer non risponde in questo momento. Riprova tra un po\'.'
AUTONOMA = ('Il mio cervello sul computer non risponde, ma posso aiutarti lo stesso: posso dirti l\'ora, la data, '
            'come sta il telefono, oppure registrare un messaggio per Francesco. Dimmi pure.')
SEGRETERIA = f'{HOME}/nura/segreteria'
GIORNI = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']
MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre',
        'novembre', 'dicembre']


def brain_alive():
    try:
        return time.time() - os.path.getmtime(A) < ALIVE_S
    except OSError:
        return False
AT_FIFO = '/tmp/answer.cmd'  # comandi AT, inviati da answer.py che tiene aperta la porta del modem
CAPTURE = 'cattura.raw'
GREETING = 'Ciao, sono Piper. Dimmi pure.'

FRAME = 640          # 20 ms a 16 kHz mono, 16 bit
THRESHOLD = 700      # RMS del parlato
START_MS = 120       # parlato continuo per dire che una frase è iniziata
SILENCE_MS = 700     # pausa che chiude la frase
BARGE_MS = 300       # parlato continuo mentre Piper parla per interromperla
PREROLL_MS = 300     # audio prima dell'inizio frase passato comunque a Vosk (prime sillabe)
QUIET_S = 12         # dopo tanto silenzio, una volta sola: "Ci sei?"

active = threading.Event()      # c'è una chiamata
speaking = threading.Event()    # Piper sta parlando
barge = threading.Event()       # chi chiama ha preso la parola mentre Piper parlava
utterances = queue.Queue()      # frasi trascritte di chi chiama
call = {'id': '', 'caller': ''}


def log(msg):
    print(f'{time.strftime("%H:%M:%S")} [convo] {msg}', flush=True)


def mtk(cmd):
    """Manda un comando a mtkaudio senza aspettare (una write piccola su FIFO è atomica: più thread possono usarla)."""
    with open(CMD, 'w') as f:
        f.write(cmd + '\n')


def log_lines_since(pos):
    """Righe nuove del log di mtkaudio dalla posizione pos; restituisce (righe complete, nuova posizione)."""
    with open(LOG, 'rb') as f:
        f.seek(pos)
        data = f.read()
    end = data.rfind(b'\n') + 1
    return data[:end].decode(errors='replace').splitlines(), pos + end


def wait_log(prefix, pos, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        lines, pos = log_lines_since(pos)
        for line in lines:
            if line.startswith(prefix):
                return line
        time.sleep(0.03)
    return ''


def render(text, raw):
    """Frase -> PCM 16 bit mono 16 kHz, con Piper già caricato e il dizionario di pronuncia."""
    wav = raw + '.wav'
    with wave.open(wav, 'wb') as w:
        pron.sintetizza(voice, text, w)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', wav, '-ar', '16000', '-ac', '1', '-f', 's16le', raw])
    os.unlink(wav)


def render_fixed():
    render(GREETING, f'{CT}/saluto.raw')
    render('Ci sei? Non ti sento.', f'{CT}/cisei.raw')
    render(DOWN, f'{CT}/giu.raw')
    render(AUTONOMA, f'{CT}/autonoma.raw')


# ---------------------------------------------------------------- ascolto
def listener():
    """Legge la registrazione continua, decide quando chi chiama parla, interrompe Piper, passa l'audio a Vosk."""
    path = f'{CT}/{CAPTURE}'
    while not os.path.exists(path) and active.is_set():
        time.sleep(0.05)
    f = open(path, 'rb')
    pre = []                  # ultimi frame prima dell'inizio frase
    in_speech, loud, quiet = False, 0, 0
    to_stt = None
    while active.is_set():
        data = f.read(FRAME)
        if len(data) < FRAME:
            if data:
                f.seek(-len(data), 1)
            time.sleep(0.01)
            continue
        n = FRAME // 2
        samples = struct.unpack(f'<{n}h', data)
        rms2 = sum(x * x for x in samples) / n
        voiced = rms2 >= THRESHOLD * THRESHOLD
        loud = loud + 20 if voiced else 0
        if speaking.is_set() and loud >= BARGE_MS and not barge.is_set():
            barge.set()
            mtk('mstop')
            log('interruzione: chi chiama parla mentre Piper parla')
        if not in_speech:
            pre.append(data)
            pre = pre[-(PREROLL_MS // 20):]
            if loud >= START_MS:
                in_speech, quiet = True, 0
                to_stt = queue.Queue()
                threading.Thread(target=transcriber, args=(to_stt,), daemon=True).start()
                for p in pre:
                    to_stt.put(p)
                pre = []
            continue
        to_stt.put(data)
        quiet = 0 if voiced else quiet + 20
        if quiet >= SILENCE_MS:
            in_speech = False
            to_stt.put(None)  # fine frase: il trascrittore consegna il testo
    if in_speech and to_stt:
        to_stt.put(None)
    f.close()


def stt_send(obj):
    with open(STT_Q, 'a') as f:
        f.write(json.dumps(obj) + '\n')


def stt_wait(uid, pos, timeout):
    """Aspetta il testo della frase uid dal PC in /tmp/brain.a (None se non arriva)."""
    end = time.time() + timeout
    while time.time() < end:
        with open(A, 'rb') as f:
            f.seek(pos)
            data = f.read()
        for line in data.decode(errors='replace').splitlines():
            if '"stt"' in line:
                try:
                    a = json.loads(line)
                except ValueError:
                    continue
                if a.get('stt') == uid:
                    return a.get('text', '')
        time.sleep(0.02)
    return None


def transcriber(frames, n=[0]):
    """Una frase: l'audio va al PC mentre arriva (o a Vosk qui), il testo finale va in `utterances`."""
    n[0] += 1
    uid = f'{call["id"]}-u{n[0]}'
    remote = not STT_LOCAL and brain_alive()
    pos = os.path.getsize(A)
    if remote:
        stt_send({'t': 'b', 'u': uid})
    audio, chunk = [], b''
    while (fr := frames.get()) is not None:
        audio.append(fr)
        chunk += fr
        if len(chunk) >= FRAME * 10:  # blocchi da 200 ms
            if remote:
                stt_send({'t': 'a', 'u': uid, 'd': base64.b64encode(chunk).decode()})
            chunk = b''
    t = time.time()
    total = sum(map(len, audio))
    if total < 16000:  # meno di mezzo secondo di audio (16 bit)
        if remote:
            stt_send({'t': 'e', 'u': uid, 'skip': True})
        return
    text, where = None, 'PC'
    if remote:
        if chunk:
            stt_send({'t': 'a', 'u': uid, 'd': base64.b64encode(chunk).decode()})
        stt_send({'t': 'e', 'u': uid})
        text = stt_wait(uid, pos, STT_WAIT)
    if text is None:  # PC lento o spento: modello piccolo qui
        where = 'telefono'
        rec = vosk.KaldiRecognizer(vosk_model, 16000)
        data = b''.join(audio)
        for i in range(0, len(data), FRAME * 10):
            rec.AcceptWaveform(data[i:i + FRAME * 10])
        text = json.loads(rec.FinalResult())['text']
    if text.strip():
        log(f'trascrizione ({where}) pronta {time.time() - t:.2f} s dopo la pausa: {text}')
        utterances.put(text)


# ---------------------------------------------------------------- azioni
def at(*cmds, pause=0.0):
    for c in cmds:
        fd = os.open(AT_FIFO, os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (c + '\n').encode())
        os.close(fd)
        if pause:
            time.sleep(pause)


def execute(action):
    """Azione arrivata dal ponte, nel punto della risposta in cui Claude l'ha scritta. Controllo anche qui."""
    kind, num = action.get('type'), str(action.get('number', ''))
    log(f'azione: {action}')
    if kind == 'hangup':
        at('ATH')
        active.clear()
    elif kind == 'dial' and re.fullmatch(r'\+?\d{6,15}', num):
        at(f'ATD{num};')
    elif kind == 'sms' and re.fullmatch(r'\+?\d{6,15}', num):
        text = ''.join(c for c in str(action.get('text', ''))[:160] if c.isprintable())
        at('AT+CMGF=1', 'AT+CSCS="GSM"', pause=0.3)
        at(f'AT+CMGS="{num}"', pause=1.0)
        at(text + '\x1a')
    elif kind == 'at' and re.fullmatch(r'AT[A-Z0-9+?=,"#*.:;_ -]{0,60}', str(action.get('command', '')), re.I):
        at(action['command'])
    else:
        log(f'azione scartata: {action}')


# ---------------------------------------------------------------- parlare
def play_files(names):
    """Suona dei file già pronti (frasi fisse, segnale). Restituisce False se chi chiama ha interrotto."""
    pos = os.path.getsize(LOG)
    barge.clear()
    speaking.set()
    for n in names:
        mtk(f'mplay /data/local/tmp/{n}')
    done = 0
    try:
        end = time.time() + 60
        while done < len(names) and active.is_set() and time.time() < end:
            lines, pos = log_lines_since(pos)
            for line in lines:
                if line.startswith('play:'):
                    done += 1
                    if 'interrotto' in line:
                        return False
            time.sleep(0.02)
        return not barge.is_set()
    finally:
        speaking.clear()


def speak(items):
    """Frasi e azioni della risposta, nell'ordine. Ogni frase si sintetizza e va subito in coda a mtkaudio.
    Restituisce (interrotta, frasi dette per intero)."""
    pos = os.path.getsize(LOG)
    barge.clear()
    queued, said, n = [], [], 0  # "speaking" solo da quando la prima frase è in coda, non durante l'attesa

    def collect():
        nonlocal pos
        lines, pos = log_lines_since(pos)
        for line in lines:
            if line.startswith('play:') and queued:
                text = queued.pop(0)
                if 'interrotto' not in line:
                    said.append(text)

    try:
        for item in items:
            collect()
            if barge.is_set() or not active.is_set():
                break
            if isinstance(item, dict):
                while queued and not barge.is_set() and active.is_set():  # dopo le frasi che la precedono
                    collect()
                    time.sleep(0.02)
                if not barge.is_set():
                    execute(item)
                continue
            name = f'say-{n % 16}.raw'
            n += 1
            t = time.time()
            render(item, f'{CT}/{name}')
            log(f'piper {time.time() - t:.1f} s: {item}')
            if barge.is_set():
                break
            queued.append(item)
            speaking.set()
            mtk(f'mplay /data/local/tmp/{name}')
        end = time.time() + 120  # aspetta che finisca di suonare (o l'interruzione)
        while queued and active.is_set() and time.time() < end:
            collect()
            time.sleep(0.02)
        interrupted = barge.is_set()
        if not interrupted and active.is_set() and os.path.exists(f'{CT}/fine.raw'):
            mtk('mplay /data/local/tmp/fine.raw')  # "tocca a te"
            wait_log('play:', pos, timeout=5)
        return interrupted, said
    finally:
        speaking.clear()


# ---------------------------------------------------------------- ponte
def ask(text, n=[0], note=None):
    """Manda la frase al ponte; restituisce (id, generatore di frasi e azioni man mano che arrivano)."""
    n[0] += 1
    qid = f'{call["id"]}-{n[0]}'
    pos = os.path.getsize(A)
    q = {'id': qid, 'call': call['id'], 'caller': call['caller'], 'text': text}
    if note:
        q['interrupted'] = note
    with open(Q, 'a') as f:
        f.write(json.dumps(q, ensure_ascii=False) + '\n')

    def items():
        nonlocal pos
        t, got = time.time(), 0
        while time.time() - t < 180 and active.is_set() and not barge.is_set():
            with open(A, 'rb') as f:
                f.seek(pos)
                data = f.read()
            end = data.rfind(b'\n') + 1
            pos += end
            for line in data[:end].decode(errors='replace').splitlines():
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
                elif a.get('text'):
                    yield a['text']
                if a.get('final'):
                    return
            time.sleep(0.03)
            if not got and not brain_alive():
                break
        if not got and not barge.is_set() and active.is_set():
            yield DOWN
    return qid, items()


def cancel(qid):
    with open(Q, 'a') as f:
        f.write(json.dumps({'type': 'cancel', 'id': qid, 'call': call['id']}) + '\n')


# ---------------------------------------------------------------- modalità autonoma
def say_now(text, name='auto.raw'):
    """Una frase composta al momento (circa 1 s di sintesi), poi il segnale di fine."""
    render(text, f'{CT}/{name}')
    log(f'autonoma: {text}')
    return play_files([name, 'fine.raw'] if os.path.exists(f'{CT}/fine.raw') else [name])


def battery():
    b = '/sys/class/power_supply/battery'
    def rd(f):
        try:
            return open(f'{b}/{f}').read().strip()
        except OSError:
            return ''
    cap, volt, stat, temp = rd('capacity'), rd('voltage_now'), rd('status'), rd('temp')
    parts = []
    if cap and cap != '-1':
        parts.append(f'La batteria è al {cap} per cento')
    elif volt:
        v = int(volt) / 1e6
        stima = max(0, min(100, round((v - 3.45) / (4.35 - 3.45) * 100)))
        parts.append(f'La percentuale non la leggo ancora, ma dalla tensione di {f'{v:.2f}'.replace('.', ',')} volt stimo circa il {stima} per cento')
    stati = {'Charging': 'in carica', 'Full': 'carica e collegata alla corrente', 'Discharging': 'scollegata dalla corrente',
             'Not charging': 'collegata ma non in carica'}
    if stat in stati:
        parts.append(f'ed è {stati[stat]}')
    if temp:
        parts.append(f'La temperatura è di {int(temp) / 10:.0f} gradi')
    return ' '.join(parts[:2]) + '. ' + (parts[2] + '.' if len(parts) > 2 else '')


def network():
    """Segnale e operatore chiesti al modem tramite answer.py, risposta letta dal suo log."""
    log_path = '/tmp/answer.log'
    pos = os.path.getsize(log_path)
    at('AT+CSQ', 'AT+COPS?', pause=0.2)
    time.sleep(1.0)
    with open(log_path, 'rb') as f:
        f.seek(pos)
        txt = f.read().decode(errors='replace')
    csq = re.search(r'\+CSQ:\s*(\d+)', txt)
    cops = re.search(r'\+COPS:\s*\d+,\d+,"([^"]*)",(\d+)', txt)
    parts = []
    if cops:
        tech = {'7': 'in 4G', '2': 'in 3G', '0': 'in 2G'}.get(cops.group(2), '')
        parts.append(f'Sono registrata sulla rete {tech}'.strip())
    if csq and csq.group(1) != '99':
        q = int(csq.group(1))
        giudizio = 'debole' if q < 10 else 'discreto' if q < 18 else 'buono'
        parts.append(f'con un segnale {giudizio}, {q} su 31')
    return (' '.join(parts) + '.') if parts else 'Non riesco a leggere lo stato della rete in questo momento.'


def voicemail():
    """Registra un messaggio: audio dalla registrazione continua, testo dalle frasi trascritte."""
    say_now('Parla pure dopo questo messaggio. Quando hai finito resta in silenzio qualche secondo.', 'msg.raw')
    cap = f'{CT}/{CAPTURE}'
    start, t0, texts, last = os.path.getsize(cap), time.time(), [], time.time()
    while active.is_set() and time.time() - t0 < 90:
        try:
            texts.append(utterances.get(timeout=0.5))
            last = time.time()
        except queue.Empty:
            if time.time() - last > (6 if texts else 10):
                break
    end = os.path.getsize(cap)
    if not texts:
        say_now('Non ho sentito nessun messaggio. Se vuoi riprovare, dimmi lascia un messaggio.', 'msg.raw')
        return
    os.makedirs(SEGRETERIA, exist_ok=True)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    with open(cap, 'rb') as f:
        f.seek(start)
        audio = f.read(end - start)
    with open(f'{SEGRETERIA}/{stamp}.raw', 'wb') as f:
        f.write(audio)
    with open(f'{SEGRETERIA}/{stamp}.json', 'w') as f:
        json.dump({'quando': time.strftime('%Y-%m-%d %H:%M'), 'chi': call['caller'], 'testo': ' '.join(texts),
                   'audio': f'{stamp}.raw', 'secondi': round(len(audio) / 32000)}, f, ensure_ascii=False)
    log(f'segreteria: messaggio {stamp} di {len(audio) // 32000} s')
    say_now('Messaggio registrato. Lo riferisco a Francesco appena torno in contatto con lui. Vuoi altro?', 'msg.raw')


def autonomous(text, last=['']):
    """Un turno senza ponte: comandi fissi riconosciuti dalle parole. Restituisce False se la chiamata va chiusa."""
    t = text.lower()
    has = lambda *ws: any(w in t for w in ws)
    now = time.localtime()
    if has('messaggio', 'segreteria', 'lasciare', 'lascia', 'riferire', 'riferisci'):
        voicemail()
        return True
    # Solo formule chiare: un "ciao" all'inizio della chiamata non deve chiuderla
    if has('arrivederci', 'riaggancia', 'chiudi la chiamata', 'puoi chiudere', 'ciao ciao', 'a presto',
           'devo andare', 'basta così'):
        say_now('Va bene, a presto!', 'auto.raw')
        at('ATH')
        active.clear()
        return False
    if has('ripeti', 'come hai detto', 'non ho capito') and last[0]:
        reply = last[0]
    elif has('che ore', 'ora è', "ore sono", 'orario'):
        reply = f'Sono le {now.tm_hour} e {now.tm_min:02d}.' if now.tm_min else f'Sono le {now.tm_hour} in punto.'
    elif has('che giorno', 'data', 'oggi'):
        reply = f'Oggi è {GIORNI[now.tm_wday]} {now.tm_mday} {MESI[now.tm_mon - 1]} {now.tm_year}.'
    elif has('batteria', 'carica'):
        reply = battery()
    elif has('rete', 'segnale', 'campo', 'linea', 'operatore'):
        reply = network()
    elif has('stato', 'come stai', 'telefono'):
        reply = battery() + ' ' + network()
    else:
        reply = ('Senza il mio cervello capisco solo poche cose: l\'ora, la data, la batteria, la rete, oppure posso '
                 'registrare un messaggio per Francesco. Cosa preferisci?')
    last[0] = reply
    say_now(reply)
    return True


# ---------------------------------------------------------------- chiamata
def conversation():
    while not utterances.empty():
        utterances.get()
    open(STT_Q, 'w').close()  # coda audio verso il PC: si riparte da zero
    os.chmod(STT_Q, 0o666)
    try:
        os.unlink(f'{CT}/{CAPTURE}')  # niente audio della chiamata precedente
    except FileNotFoundError:
        pass
    mtk(f'cstart /data/local/tmp/{CAPTURE}')
    threading.Thread(target=listener, daemon=True).start()
    play_files(['saluto.raw'])
    autonomous_intro = [False]
    if not brain_alive():  # già all'inizio senza ponte: lo si dice subito
        autonomous_intro[0] = True
        log('ponte fermo: modalità autonoma')
        play_files(['autonoma.raw'])
    asked_quiet, note = False, None
    while active.is_set():
        try:
            text = utterances.get(timeout=QUIET_S)
        except queue.Empty:
            if not asked_quiet and active.is_set():
                asked_quiet = True
                play_files(['cisei.raw'])
            continue
        asked_quiet = False
        while not utterances.empty():  # frasi arrivate insieme: una domanda sola
            text += ' ' + utterances.get()
        if not brain_alive():  # il ponte sul PC è fermo: modalità autonoma
            if not autonomous_intro[0]:
                autonomous_intro[0] = True
                log('ponte fermo: modalità autonoma')
                play_files(['autonoma.raw'])
            autonomous(text)
            continue
        qid, items = ask(text, note=note)
        interrupted, said = speak(items)
        note = None
        if interrupted:
            cancel(qid)
            note = ' '.join(said) if said else '(non avevi ancora detto niente)'
            log(f'interrotta dopo: {note}')
    mtk('cstop')
    log('conversazione finita')


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
                    call['id'] = cmd[1] if len(cmd) > 1 else str(int(time.time()))
                    call['caller'] = cmd[2] if len(cmd) > 2 else ''
                    active.set()
                    threading.Thread(target=conversation, daemon=True).start()
                    log(f'chiamata {call["id"]}')
                elif cmd[0] == 'stop':
                    active.clear()


if __name__ == '__main__':
    main()
