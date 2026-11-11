#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本地 mock 翼课网作业页：给自动化工具一个可控的靶子。

GET  /                -> mock.html
GET  /api/tasks       -> 任务列表 + 题目（页面渲染用）
POST /proxy           -> 模拟 getbaseworktimucontent 的返回
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "mock.html")

# ---------------------------------------------------------------- 题目数据
FILL_ITEMS = [
    {"id": "3098106", "orders": "1", "ask": "In the past, it felt s### to see robots serving food.",
     "answer": json.dumps(["strange"])},
    {"id": "3098107", "orders": "2", "ask": "Can you g### when I started using a digital device?",
     "answer": json.dumps(["guess"])},
    {"id": "3098108", "orders": "3", "ask": "Students are using AI to help with their h###.",
     "answer": json.dumps(["homework"])},
]

CHOICE_ITEMS = [
    {"id": "477880001", "orders": "1", "ask": "Which word is a noun?", "answer": json.dumps(["B"])},
    {"id": "477880002", "orders": "2", "ask": "Choose the correct form.", "answer": json.dumps(["A"])},
    {"id": "477880003", "orders": "3", "ask": "Pick the best answer.", "answer": json.dumps(["C"])},
    {"id": "477880004", "orders": "4", "ask": "What does the passage say?", "answer": json.dumps(["D"])},
]

DICT_WORDS = ["apple", "banana", "orange"]

TASKS = [
    {"name": "读记词语", "biz": "005", "key": "voice-1", "kind": "voice", "items": [], "words": []},
    {"name": "单句首字母填空", "biz": "104", "key": "fill-1", "kind": "fill", "items": FILL_ITEMS, "words": []},
    {"name": "语法选择", "biz": "007", "key": "choice-1", "kind": "choice", "items": CHOICE_ITEMS, "words": []},
    {"name": "词语听写", "biz": "030", "key": "dict-1", "kind": "dictation", "items": [], "words": DICT_WORDS},
]

CONTEXT = {
    "fill-1": "用括号中词语的正确形式或适当的词填空。",
    "choice-1": "阅读下列句子，选出最佳答案。",
    "dict-1": "听录音，写出你听到的单词。",
}


def payload_for(key):
    task = next((t for t in TASKS if t["key"] == key), None)
    if task is None:
        return {"errno": 4004, "err_info": "no such key"}
    qus = []
    for it in task["items"]:
        qus.append({
            "id": it["id"],
            "orders": it["orders"],
            "ask": [{"content": it["ask"]}],
            "answer": it["answer"],
            "analyz": "mock",
        })
    return {
        "errno": 0,
        "data": [{
            "content": [{"content": CONTEXT.get(key, "")}],
            "question": {"qus_item": qus},
        }],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ekw-mock"

    def log_message(self, fmt, *args):  # 安静点
        sys.stderr.write("[mock] " + (fmt % args) + "\n")

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/hw/do"):
            with open(PAGE, encoding="utf-8") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif path == "/api/tasks":
            self._send(200, json.dumps(TASKS, ensure_ascii=False))
        elif path == "/json/version":
            self._send(200, json.dumps({"Browser": "mock"}))
        else:
            self._send(404, json.dumps({"errno": 404}))

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/proxy":
            self._send(404, json.dumps({"errno": 404}))
            return
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
        form = parse_qs(raw)
        data = json.loads((form.get("data") or ["{}"])[0])
        if form.get("url", [""])[0] and "getbaseworktimucontent" not in form["url"][0]:
            self._send(200, json.dumps({"errno": 4001, "err_info": "wrong api"}))
            return
        self._send(200, json.dumps(payload_for(data.get("keys")), ensure_ascii=False))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("mock listening on http://127.0.0.1:%d/" % port, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
