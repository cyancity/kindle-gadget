"""Minimal telnet client for the Kindle's root shell (busybox telnetd -l /bin/sh).

Usage: python tk.py 'id; uname -a' [wait_seconds]
"""
import socket
import sys
import time

HOST = "192.168.0.100"
PORT = 23
IAC, WILL, WONT, DO, DONT = 255, 251, 252, 253, 254


def strip_iac(buf: bytes):
    replies = bytearray()
    clean = bytearray()
    i = 0
    while i < len(buf):
        b = buf[i]
        if b == IAC and i + 2 < len(buf):
            cmd, opt = buf[i + 1], buf[i + 2]
            if cmd in (WILL, WONT, DO, DONT):
                replies += bytes([IAC, DONT if cmd == WILL else WONT, opt])
            i += 3
            continue
        clean.append(b)
        i += 1
    return bytes(replies), bytes(clean)


def run(cmd: str, wait: float = 5.0) -> str:
    s = socket.create_connection((HOST, PORT), timeout=10)
    s.settimeout(wait)
    acc = bytearray()

    def drain(until: float):
        while time.time() < until:
            try:
                d = s.recv(4096)
            except socket.timeout:
                return
            if not d:
                return
            replies, clean = strip_iac(d)
            if replies:
                s.sendall(replies)
            acc.extend(clean)

    drain(time.time() + 0.5)
    mark = f"__TKEND{int(time.time()) % 99991}__"
    flat = cmd.replace("\r\n", "\n").rstrip("\n").replace("\n", " ; ")
    s.sendall(f"{flat} ; echo {mark}\n".encode())
    drain(time.time() + wait)
    s.close()

    text = acc.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if lines and mark in lines[-1]:
        lines.pop()
    if lines and mark in lines[-1]:
        lines.pop()
    if lines and lines[0].strip().startswith(flat[:32]):
        lines.pop(0)
    return "\n".join(lines).strip()


if __name__ == "__main__":
    print(run(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 5.0))
