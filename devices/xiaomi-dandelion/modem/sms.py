# Manda un SMS in modo testo. Uso: sudo python3 sms.py /dev/ttyC0 +39... "testo"
import os, sys, time, tty, termios, select
dev, number, text = sys.argv[1], sys.argv[2], sys.argv[3]
fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
try: tty.setraw(fd)
except termios.error: pass
def read_until(tokens, t):
    out = b''; end = time.time() + t
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try: out += os.read(fd, 4096)
            except BlockingIOError: pass
            if any(k in out for k in tokens): break
    return out.decode(errors='replace').replace('\r', '')
def cmd(c, tokens=(b'OK', b'ERROR'), t=5):
    os.write(fd, (c + '\r').encode()); r = read_until(tokens, t); print(f'>>> {c}\n{r.strip()}\n'); return r
read_until([b'#'], 0.5)
cmd('AT+CMGF=1'); cmd('AT+CSCS="GSM"'); cmd('AT+CSQ')
r = cmd(f'AT+CMGS="{number}"', tokens=(b'>', b'ERROR'))
if '>' in r:
    os.write(fd, text.encode() + b'\x1a')
    print('>>> [testo + Ctrl-Z]\n' + read_until((b'+CMGS', b'ERROR'), 60).strip())
    print(read_until((b'OK', b'ERROR'), 5).strip())
os.close(fd)
