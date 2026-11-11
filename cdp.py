#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Minimal Chrome DevTools Protocol client (stdlib only)."""
import base64
import json
import os
import socket
import struct
import sys
import time
import urllib.request

HOST, PORT = "127.0.0.1", int(os.environ.get("CDP_PORT", "9222"))


def _http_get(host, path):
    url = "http://%s:%d%s" % ("[%s]" % host if ":" in host else host, PORT, path)
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def http_json(path):
    """调试端口有时只绑 ::1，有时只绑 127.0.0.1，两个都试。"""
    hosts = [os.environ["CDP_HOST"]] if os.environ.get("CDP_HOST") else ["127.0.0.1", "::1"]
    last = None
    for h in hosts:
        try:
            return _http_get(h, path)
        except Exception as e:
            last = e
    raise last


def page_target(url_filter=None):
    targets = [t for t in http_json("/json/list") if t.get("type") == "page"]
    if url_filter:
        for t in targets:
            if url_filter in t.get("url", ""):
                return t
    for t in targets:
        if not t.get("url", "").startswith("devtools://"):
            return t
    if targets:
        return targets[0]
    raise RuntimeError("no page target")


class WS(object):
    def __init__(self, url):
        assert url.startswith("ws://")
        rest = url[5:]
        hostport, path = rest.split("/", 1)
        path = "/" + path
        if hostport.startswith("["):          # [::1]:9224
            host, port = hostport[1:].split("]:", 1)
        else:
            host, port = hostport.rsplit(":", 1)
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n"
            "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("handshake failed")
            buf += chunk
        head, rest_data = buf.split(b"\r\n\r\n", 1)
        if b"101" not in head.split(b"\r\n")[0]:
            raise RuntimeError("handshake rejected: %r" % head[:200])
        self.buf = rest_data

    def _read_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("connection closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        payload = text.encode("utf-8")
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        masked = bytearray(payload)
        for i in range(n):
            masked[i] ^= mask[i & 3]
        self.sock.sendall(bytes(header) + bytes(masked))

    def recv(self):
        while True:
            b0, b1 = self._read_exact(2)
            opcode = b0 & 0x0F
            length = b1 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            payload = self._read_exact(length) if length else b""
            if opcode == 0x9:  # ping
                self.sock.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
                continue
            if opcode in (0x1, 0x0):
                text = payload.decode("utf-8", "replace")
                try:
                    return json.loads(text)
                except ValueError:
                    continue
            if opcode == 0x8:
                raise RuntimeError("ws closed")
            continue

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class CDP(object):
    def __init__(self, url_filter=None):
        self.target = page_target(url_filter)
        self.ws = WS(self.target["webSocketDebuggerUrl"])
        self.next_id = 0
        self.events = []

    def cmd(self, method, **params):
        self.next_id += 1
        mid = self.next_id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        deadline = time.time() + 60
        while time.time() < deadline:
            msg = self.ws.recv()
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s failed: %s" % (method, msg["error"]))
                return msg.get("result", {})
            if "method" in msg:
                self.events.append(msg)
        raise RuntimeError("timeout waiting for %s" % method)

    def eval(self, expr, await_promise=False):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True,
                     awaitPromise=await_promise, userGesture=True)
        if r.get("exceptionDetails"):
            raise RuntimeError("JS error: %s" % json.dumps(r["exceptionDetails"])[:800])
        return r.get("result", {}).get("value")

    def goto(self, url, wait=2.0):
        self.cmd("Page.enable")
        self.cmd("Page.navigate", url=url)
        time.sleep(wait)

    def shot(self, path):
        data = self.cmd("Page.captureScreenshot", format="png").get("data", "")
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        return path

    def close(self):
        self.ws.close()


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: cdp.py <eval|shot|nav|targets> ...")
        return
    op = args[0]
    if op == "targets":
        for t in http_json("/json/list"):
            print("%-8s %s" % (t.get("type"), t.get("url")[:120]))
        return
    if op == "nav":
        c = CDP()
        try:
            c.goto(args[1], float(args[2]) if len(args) > 2 else 2.0)
            print("title:", c.eval("document.title"))
            print("url:", c.eval("location.href"))
        finally:
            c.close()
        return
    if op == "cmd":
        method = args[1]
        params = json.loads(args[2]) if len(args) > 2 else {}
        c = CDP()
        try:
            print(json.dumps(c.cmd(method, **params), ensure_ascii=False))
        finally:
            c.close()
        return
    if op == "shot":
        c = CDP()
        try:
            print(c.shot(args[1]))
        finally:
            c.close()
        return
    if op == "eval":
        expr = args[1] if len(args) > 1 else "1"
        awaitp = len(args) > 2 and args[2] == "--await"
        c = CDP()
        try:
            val = c.eval(expr, await_promise=awaitp)
            if isinstance(val, (dict, list)):
                print(json.dumps(val, ensure_ascii=False, indent=1))
            else:
                print(val)
        finally:
            c.close()
        return
    print("unknown op", op)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.stderr.write("ERROR: %s\n" % e)
        sys.exit(1)
