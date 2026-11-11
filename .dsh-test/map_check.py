# -*- coding: utf-8 -*-
"""核对乱序映射：接口答案字母 -> 页面上该点的字母。"""
import json
import os
import sys
import time

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402
import ekwing_auto as ea  # noqa: E402

NAME = sys.argv[1] if len(sys.argv) > 1 else "阅读理解"

c = cdp.CDP()
c.goto("https://www.ekwing.com/hw/do?hid=5911&param_term=", wait=6)
tasks = ea.list_tasks(c)
t = next(x for x in tasks if x["name"] == NAME)
items = ea.extract_items(ea.fetch_content(c, t["key"], ""))
before = ea.vm_ids(c)
ea.open_tile(c, NAME)
ea.start_task(c)
time.sleep(1.0)
ids = ea.vm_ids(c)
vid = ([i for i in ids if i not in before] or ids)[-1]
dom = c.eval(ea.JS_CHOICE_OPTIONS % json.dumps(vid))
api = {it["id"]: it for it in items}
print("%-10s %-8s %-8s %s" % ("qid", "答案", "应点", "对应选项正文"))
ok = 0
for q in dom:
    it = api.get(q["id"]) or {}
    ans = (it.get("answers") or [""])[0]
    want = next((o["text"] for o in it.get("options") or [] if o["key"] == ans), "")
    val, txt = None, ""
    for o in q["opts"]:
        if want and ea._norm_opt(o["t"]) == ea._norm_opt(want):
            val, txt = o["v"], o["t"]
            break
    if val is None:
        val, txt = ans, "(按字母)"
    ok += 1
    print("%-10s %-8s %-8s %s" % (q["id"], ans, val, txt[:60]))
print("共 %d 题" % ok)
c.eval("(function(){var w=document.getElementById('jsDoWorkCompContainer');"
       "if(w){w.style.display='none';w.innerHTML='';}})()")
c.close()
