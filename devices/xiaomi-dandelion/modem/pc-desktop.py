#!/usr/bin/env python3
"""Computer use sul desktop X11 del PC: lo usa la sessione operativa di Piper per vedere lo schermo e agire.

Niente sudo: XTest via python-xlib per mouse e tastiera, mss per gli screenshot (nel venv ~/nura-voice/venv).
Il ciclo è quello classico: screenshot -> guardare l'immagine -> un'azione -> nuovo screenshot per verificare.
Le coordinate di click e move sono quelle dello screenshot ridotto: lo script le riporta sullo schermo vero.

Uso (con il Python del venv):
  pc-desktop.py screenshot [file.png] [--monitor N] [--max 1600]
                                                    salva lo schermo (N = 1, 2...: un solo monitor, più leggibile;
                                                    0: tutti) ridotto a --max pixel di larghezza; stampa scala e origine
  pc-desktop.py click X Y [--right|--middle] [--double]
  pc-desktop.py move X Y
  pc-desktop.py scroll su|giu [N]
  pc-desktop.py type "testo"                        scrive il testo nella finestra attiva
  pc-desktop.py key ctrl+shift+t                    combinazione di tasti (nomi X: Return, Escape, Tab, F5, ...)
  pc-desktop.py windows                             finestre aperte: id, desktop, titolo
  pc-desktop.py focus "parte del titolo"            porta in primo piano la finestra
  pc-desktop.py launch comando [argomenti...]       avvia un programma sul desktop (per esempio webstorm)
"""
import json
import os
import subprocess
import sys
import time

os.environ.setdefault('DISPLAY', ':0')
if 'XAUTHORITY' not in os.environ and os.path.exists(f'/run/user/{os.getuid()}/gdm/Xauthority'):
    os.environ['XAUTHORITY'] = f'/run/user/{os.getuid()}/gdm/Xauthority'

from Xlib import X, XK, display, protocol  # noqa: E402
from Xlib.ext import xtest  # noqa: E402

STATE = os.path.expanduser('~/nura-voice/desktop-scala.json')  # scala dell'ultimo screenshot
d = display.Display()
root = d.screen().root


def scale():
    try:
        return json.load(open(STATE))['scala']
    except (OSError, ValueError, KeyError):
        return 1.0


def real(x, y):
    try:
        st = json.load(open(STATE))
    except (OSError, ValueError):
        st = {}
    s, ox, oy = st.get('scala', 1.0), st.get('x0', 0), st.get('y0', 0)
    return ox + int(float(x) * s), oy + int(float(y) * s)


def screenshot(path='/tmp/schermo.png', maxw=1600, monitor=0):
    import mss
    from PIL import Image
    with (mss.MSS() if hasattr(mss, 'MSS') else mss.mss()) as m:
        mon = m.monitors[monitor] if monitor < len(m.monitors) else m.monitors[0]  # 0 = tutti insieme
        shot = m.grab(mon)
        img = Image.frombytes('RGB', shot.size, shot.bgra, 'raw', 'BGRX')
        nmon = len(m.monitors) - 1
    s = max(1.0, img.width / maxw)
    if s > 1:
        img = img.resize((int(img.width / s), int(img.height / s)))
    img.save(path)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({'scala': s, 'file': path, 'x0': mon['left'], 'y0': mon['top']}, open(STATE, 'w'))
    print(f'{path}: {img.width}x{img.height} (monitor {monitor} di {nmon}, {shot.size[0]}x{shot.size[1]} '
          f'da {mon["left"]},{mon["top"]}, scala {s:.3f}); le coordinate di click valgono per questa immagine')


def move(x, y):
    rx, ry = real(x, y)
    xtest.fake_input(d, X.MotionNotify, x=rx, y=ry)
    d.sync()


def click(x, y, button=1, double=False):
    move(x, y)
    for _ in range(2 if double else 1):
        xtest.fake_input(d, X.ButtonPress, button)
        xtest.fake_input(d, X.ButtonRelease, button)
        d.sync()
        time.sleep(0.08)


def scroll(direction, n=3):
    b = 4 if direction.startswith('s') else 5  # su / giu
    for _ in range(int(n)):
        xtest.fake_input(d, X.ButtonPress, b)
        xtest.fake_input(d, X.ButtonRelease, b)
    d.sync()


def keycode(name):
    alias = {'ctrl': 'Control_L', 'shift': 'Shift_L', 'alt': 'Alt_L', 'super': 'Super_L', 'win': 'Super_L',
             'enter': 'Return', 'invio': 'Return', 'esc': 'Escape', 'tab': 'Tab', 'spazio': 'space',
             'space': 'space', 'backspace': 'BackSpace', 'canc': 'Delete', 'del': 'Delete'}
    sym = XK.string_to_keysym(alias.get(name.lower(), name))
    if not sym and len(name) == 1:
        sym = ord(name)
    code = d.keysym_to_keycode(sym)
    if not code:
        sys.exit(f'tasto sconosciuto: {name}')
    return code


def key(combo):
    codes = [keycode(k) for k in combo.split('+')]
    for c in codes:
        xtest.fake_input(d, X.KeyPress, c)
    for c in reversed(codes):
        xtest.fake_input(d, X.KeyRelease, c)
    d.sync()


def type_text(text):
    """Scrive carattere per carattere; per i caratteri senza tasto diretto usa un keycode libero rimappato."""
    spare = None
    for ch in text:
        sym = XK.string_to_keysym({'\n': 'Return', '\t': 'Tab', ' ': 'space'}.get(ch, ch)) or ord(ch)
        if ord(ch) > 255 and sym == ord(ch):
            sym = 0x01000000 + ord(ch)  # keysym Unicode
        code = d.keysym_to_keycode(sym)
        shift = False
        if code:
            shift = d.keycode_to_keysym(code, 0) != sym and d.keycode_to_keysym(code, 1) == sym
        else:  # carattere senza tasto (accenti, simboli): si rimappa un keycode libero
            if spare is None:
                mapping = d.get_keyboard_mapping(8, 248)
                spare = next(i + 8 for i, m in enumerate(mapping) if not any(m))
            d.change_keyboard_mapping(spare, [(sym,) * 4])
            d.sync()
            time.sleep(0.02)
            code = spare
        if shift:
            xtest.fake_input(d, X.KeyPress, keycode('shift'))
        xtest.fake_input(d, X.KeyPress, code)
        xtest.fake_input(d, X.KeyRelease, code)
        if shift:
            xtest.fake_input(d, X.KeyRelease, keycode('shift'))
        d.sync()
        time.sleep(0.01)


def windows():
    atom = d.intern_atom
    ids = root.get_full_property(atom('_NET_CLIENT_LIST'), X.AnyPropertyType)
    out = []
    for wid in (ids.value if ids else []):
        w = d.create_resource_object('window', wid)
        try:
            name = w.get_full_property(atom('_NET_WM_NAME'), atom('UTF8_STRING'))
            title = name.value.decode(errors='replace') if name else (w.get_wm_name() or '')
            desk = w.get_full_property(atom('_NET_WM_DESKTOP'), X.AnyPropertyType)
            out.append((wid, desk.value[0] if desk else -1, title))
        except Exception:
            pass
    return out


def focus(part):
    for wid, _, title in windows():
        if part.lower() in title.lower():
            w = d.create_resource_object('window', wid)
            ev = protocol.event.ClientMessage(window=w, client_type=d.intern_atom('_NET_ACTIVE_WINDOW'),
                                              data=(32, [2, X.CurrentTime, 0, 0, 0]))
            root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            d.sync()
            print(f'in primo piano: {title}')
            return
    sys.exit(f'nessuna finestra con «{part}» nel titolo')


def main(a):
    if not a:
        print(__doc__)
        return
    cmd, args = a[0], a[1:]
    if cmd == 'screenshot':
        maxw = int(args[args.index('--max') + 1]) if '--max' in args else 1600
        mon = int(args[args.index('--monitor') + 1]) if '--monitor' in args else 0
        files = [x for x in args if x.endswith('.png')]
        screenshot(files[0] if files else '/tmp/schermo.png', maxw, mon)
    elif cmd == 'click':
        btn = 3 if '--right' in args else 2 if '--middle' in args else 1
        click(args[0], args[1], btn, '--double' in args)
    elif cmd == 'move':
        move(args[0], args[1])
    elif cmd == 'scroll':
        scroll(args[0], args[1] if len(args) > 1 else 3)
    elif cmd == 'type':
        type_text(' '.join(args))
    elif cmd == 'key':
        key(args[0])
    elif cmd == 'windows':
        for wid, desk, title in windows():
            print(f'0x{wid:08x}  desktop {desk}  {title}')
    elif cmd == 'focus':
        focus(' '.join(args))
    elif cmd == 'launch':
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(f'avviato: {" ".join(args)}')
    else:
        sys.exit(f'comando sconosciuto: {cmd}\n{__doc__}')


if __name__ == '__main__':
    main(sys.argv[1:])
