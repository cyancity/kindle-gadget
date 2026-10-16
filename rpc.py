"""Send a shell command to the Kindle file-RPC agent and print its output.

Usage: python rpc.py 'id; uname -a'
Transport: H:\\qoder\\cmd.sh + cmd.go markers, answered by agentd.sh on device.
"""
import os
import sys
import time

Q = "H:/qoder/"
TIMEOUT = 180


def run(script: str, timeout: int = TIMEOUT) -> str:
    for junk in ("cmd.done",):
        if os.path.exists(Q + junk):
            os.remove(Q + junk)
    with open(Q + "cmd.sh", "wb") as f:
        f.write(script.replace("\r\n", "\n").encode())
    with open(Q + "cmd.go", "wb") as f:
        f.write(b"go")
    start = time.time()
    while not os.path.exists(Q + "cmd.done"):
        if time.time() - start > timeout:
            return "TIMEOUT: agent not answering. Re-tap 'Qoder Agent 02' on the Kindle."
        time.sleep(0.5)
    with open(Q + "cmd.done", "rb") as f:
        out = f.read().decode("utf-8", "replace")
    os.remove(Q + "cmd.done")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "id"
    print(run(cmd))
