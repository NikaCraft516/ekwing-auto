# -*- coding: utf-8 -*-
"""对比接口里的选项顺序与页面上的选项顺序，确认乱序映射。"""
import json
import os
import sys

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402
import ekwing_auto as ea  # noqa: E402

NAME = sys.argv[1] if len(sys.argv) > 1 else "阅读理解"
HID = "5911"

c = cdp.CDP()
c.goto("https://www.ekwing.com/hw/do?hid=%s&param_term=" % HID, wait=6)
tasks = ea.list_tasks(c)
t = next(x for x in tasks if x["name"] == NAME)
data = ea.fetch_content(c, t["key"], "")

block = (data.get("data") or [])[0]
q = block.get("question") or {}
for it in (q.get("qus_item") or [])[:3]:
    print("--- qid", it.get("id"), "answer", it.get("answer"), "orders", it.get("orders"))
    for opt in (it.get("items") or [])[:6]:
        print("    ", json.dumps(opt, ensure_ascii=False)[:160])
    print("    ask:", json.dumps(it.get("ask"), ensure_ascii=False)[:160])

# 页面上的选项文案
before = ea.vm_ids(c)
ea.open_tile(c, NAME)
ea.start_task(c)
import time  # noqa: E402
time.sleep(1.0)
ids = ea.vm_ids(c)
vid = ([i for i in ids if i not in before] or ids)[-1]
print("--- DOM 选项 ---")
print(c.eval(r"""(function(){
  var w=document.getElementById('jsDoWorkCompContainer');
  var out=[];
  for(var i=1;i<=4;i++){
    var r=w.querySelector('input[name="choice_'+avalon.vmodels[%s].qus_items[0].id+'"][value="'+String.fromCharCode(64+i)+'"]');
    if(!r) continue;
    var lab=r.closest('label')||r.parentElement;
    out.push(String.fromCharCode(64+i)+' => '+(lab.textContent||'').replace(/\s+/g,' ').trim().slice(0,60));
  }
  return out;
})()""" % json.dumps(vid)))
c.eval("(function(){var w=document.getElementById('jsDoWorkCompContainer');"
       "if(w){w.style.display='none';w.innerHTML='';}})()")
c.close()
