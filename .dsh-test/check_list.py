# -*- coding: utf-8 -*-
"""看作业列表页结构，找作业 id。"""
import os
import re
import sys

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402

c = cdp.CDP()
print("url:", c.eval("location.href"))
txt = c.eval("document.body.innerText") or ""
print("--- text ---")
print(txt[:1500])
html = c.eval("document.documentElement.innerHTML") or ""
ids = sorted(set(re.findall(r"hid[=:%22'\s]{1,6}(\d{4,})", html)))
print("--- hid candidates ---", ids[:20])
for pat in ("data-hid", "hwid", "homework_id", "hw_id"):
    if pat in html:
        print("found attr:", pat, html.count(pat))
c.close()
