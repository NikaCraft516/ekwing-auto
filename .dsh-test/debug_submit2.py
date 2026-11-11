# -*- coding: utf-8 -*-
"""点对按钮之后，确认「确定 → 等级」链路是通的。"""
import os
import re
import sys
import time

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9333"
import cdp  # noqa: E402

c = cdp.CDP()
c.goto("http://127.0.0.1:8765/index.html", wait=1.5)
c.eval("openTask(TASKS.filter(function(t){return t.biz==='104';})[0]);"
       "document.getElementById('startBtn').click(); 1")
time.sleep(0.4)
# 真按 a#fin
c.eval("document.getElementById('fin').click(); 1")
time.sleep(0.4)
print("confirm:", c.eval("document.querySelectorAll('.confirm').length"))
c.eval("document.getElementById('ok').click(); 1")
time.sleep(0.4)
txt = c.eval("document.getElementById('jsDoWorkCompContainer').innerText")
print("panel:", (txt or "").replace("\n", " | "))
m = re.search(r"等级[:：]\s*([A-E])", txt or "")
print("grade:", m.group(1) if m else None)
print("score:", c.eval("window.__lastScore"))
c.close()
