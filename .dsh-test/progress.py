# -*- coding: utf-8 -*-
"""读作业整体进度（从 hwCntVm 里取，而不是靠截图文字）。"""
import json
import os
import sys

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402

HID = sys.argv[1] if len(sys.argv) > 1 else "5911"
c = cdp.CDP()
print("url:", c.eval("location.href"))
print("vm keys:", c.eval("Object.keys(avalon.vmodels['hwCntVm']).join(',')"))
for k in ("done", "finish", "finishNum", "progress", "percent", "total", "finish_num", "complete"):
    v = c.eval("(function(){var v=avalon.vmodels['hwCntVm'];"
               "return v && v['%s']!==undefined ? JSON.stringify(v['%s']) : null;})()" % (k, k))
    if v is not None:
        print("  %-12s %s" % (k, v))
print("--- 每项 finish/do ---")
print(c.eval(r"""(function(){
  var v=avalon.vmodels['hwCntVm'];
  return v.list.map(function(it){
    return it.type_name+'  finish='+it.finish+'  do='+it.do;
  }).join('\n');
})()"""))
c.close()
