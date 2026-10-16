"""Minimal telnet client for the Kindle (busybox telnetd, no negotiation needed).
Usage: python -I telnet_run.py "cmd1; cmd2"
"""
import os, socket, sys, time

HOST, PORT = os.environ.get('KINDLE_HOST', '192.168.1.189'), 23


def recv_until_idle(s, idle=1.5, timeout=20):
    s.settimeout(0.5)
    buf = b''
    last = time.time()
    end = last + timeout
    while time.time() < end:
        try:
            d = s.recv(65536)
            if not d:
                break
            buf += d
            last = time.time()
        except socket.timeout:
            if time.time() - last >= idle:
                break
        except OSError:
            break
    return buf


def strip_iac(data):
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == 255:
            if i + 1 >= len(data):
                break
            c = data[i + 1]
            if c == 255:
                out.append(255)
                i += 2
                continue
            if c in (251, 252, 253, 254):
                i += 3
                continue
            if c == 250:
                j = data.find(b'\xff\xf0', i)
                i = (j + 2) if j != -1 else len(data)
                continue
            i += 2
            continue
        out.append(b)
        i += 1
    return bytes(out)


def run(cmds, idle=2.0, timeout=25):
    s = socket.create_connection((HOST, PORT), timeout=8)
    time.sleep(0.3)
    first = recv_until_idle(s, idle=1.0, timeout=4)
    import os
    s.sendall(b'\r')
    time.sleep(0.5)
    s.sendall(cmds.encode() + b'\r')
    out = recv_until_idle(s, idle=idle, timeout=timeout)
    s.close()
    if os.environ.get('TELNET_DEBUG'):
        sys.stderr.write(f'[debug] banner={len(first)}B out={len(out)}B\n')
    return first + out


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-':
        cmds = sys.stdin.read()
    else:
        cmds = sys.argv[1] if len(sys.argv) > 1 else 'id'
    text = run(cmds)
    sys.stdout.write(strip_iac(text).decode('utf-8', 'replace'))
