# -*- coding: utf-8 -*-
"""打开某个任务，导出模型与 DOM 细节，判断通用逻辑能不能作答。"""
import json
import os
import sys
import time

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402
import ekwing_auto as ea  # noqa: E402

HID = "5911"
PROBE = r"""
(function(vid){
  var vm=avalon.vmodels[vid], out={vid:vid};
  if(vm){
    out.keys=Object.keys(vm).join(',');
    out.qus=(vm.qus_items||[]).slice(0,2).map(function(q){
      return {id:q.id, answer:q.answer, orders:q.orders, keys:Object.keys(q).join(',')};
    });
    out.ans=JSON.stringify(vm.ansData||{}).slice(0,300);
    out.allData=(vm.allData||[]).slice(0,3);
  }
  var w=document.getElementById('jsDoWorkCompContainer');
  if(w){
    out.radios=Array.prototype.map.call(w.querySelectorAll('input[type=radio]'),
      function(r){return r.name+'='+r.value;}).slice(0,12);
    out.textInputs=w.querySelectorAll('input[type=text]').length;
    out.textareas=w.querySelectorAll('textarea').length;
    out.fills=w.querySelectorAll('.jsDoHwFill').length;
    out.fillText=Array.prototype.map.call(w.querySelectorAll('.jsDoHwFill'),
      function(e){return (e.textContent||'').trim();}).slice(0,8);
    out.buttons=Array.prototype.map.call(w.querySelectorAll('a,button'),
      function(e){return (e.textContent||'').replace(/\s+/g,'').slice(0,12);}).slice(0,12);
    out.html=w.innerHTML.replace(/\s+/g,' ').slice(0,700);
  }
  return out;
})(%s)
"""


def probe(name):
    c = cdp.CDP()
    try:
        c.goto("https://www.ekwing.com/hw/do?hid=%s&param_term=" % HID, wait=6)
        tasks = ea.list_tasks(c)
        t = next((x for x in tasks if x["name"] == name), None)
        if not t:
            print("no task", name)
            return
        data = ea.fetch_content(c, t["key"], "")
        items = ea.extract_items(data)
        before = ea.vm_ids(c)
        if not ea.open_tile(c, name):
            print("!! 打不开任务", name)
            return
        ea.start_task(c)
        time.sleep(1.2)
        ids = ea.vm_ids(c)
        fresh = [i for i in ids if i not in before] or ids
        vid = fresh[-1]
        info = c.eval(PROBE % json.dumps(vid))
        print("=" * 70)
        print("任务:", name, "biz:", t["biz"], "题目数:", len(items))
        print("题型判定:", c.eval(ea.JS_TASK_KIND % json.dumps(vid)))
        print("答案:", " | ".join(" / ".join(it["answers"]) for it in items[:6]))
        for k, v in info.items():
            if k in ("vid", "html"):
                continue
            print("  %-10s %s" % (k, v))
        print("  html      ", info.get("html", "")[:600])
        # 收尾
        c.eval("(function(){var w=document.getElementById('jsDoWorkCompContainer');"
               "if(w){w.style.display='none';w.innerHTML='';}})()")
        ea.clear_overlays(c)
    finally:
        c.close()


if __name__ == "__main__":
    probe(sys.argv[1])
