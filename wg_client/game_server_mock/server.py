import os
import socketserver
import time


MODE = os.getenv("MODE", "ok").lower()  # ok | err | slow
DELAY_SEC = float(os.getenv("DELAY_SEC", "0.0"))


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        peer = self.client_address
        print(f"[mock] connection from {peer}", flush=True)
        buf = b""
        while True:
            data = self.request.recv(4096)
            if not data:
                break
            buf += data
            while b"\x00" in buf:
                msg, buf = buf.split(b"\x00", 1)
                txt = msg.decode("utf-8", "replace")
                print("[mock] RX:", txt, flush=True)
                if MODE == "slow" and DELAY_SEC > 0:
                    time.sleep(DELAY_SEC)
                if MODE == "err":
                    self.request.sendall(b"<ERR code=\"REGISTER_DENIED\"/>\x00")
                else:
                    self.request.sendall(b"<OK/>\x00")


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("0.0.0.0", 5190), Handler) as s:
        print("[mock] Listening 0.0.0.0:5190", "mode=", MODE, "delay=", DELAY_SEC)
        s.serve_forever()


