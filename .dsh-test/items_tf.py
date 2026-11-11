# -*- coding: utf-8 -*-
"""看判断题/选择题在接口里的选项结构。"""
import json
import os
import sys

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402
import ekwing_auto as ea  # noqa: E402

c = cdp.CDP()
c.goto("https://www.ekwing.com/hw/do?hid=5911&param_term=", wait=6)
tasks = ea.list_tasks(c)
for name in ("阅读判断", "听力判断"):
    t = next(x for x in tasks if x["name"] == name)
    data = ea.fetch_content(c, t["key"], "")
    qus = ((data.get("data") or [{}])[0].get("question") or {}).get("qus_item") or []
    print("===", name)
    for it in qus[:2]:
        print("  answer", it.get("answer"), "orders", it.get("orders"))
        for opt in (it.get("items") or []):
            print("     ", json.dumps(opt, ensure_ascii=False)[:120])
c.close()
