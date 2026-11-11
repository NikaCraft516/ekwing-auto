# -*- coding: utf-8 -*-
"""看真实作业页现在的完成状态（只读，不点任何按钮）。"""
import os
import sys
import time

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402

c = cdp.CDP()
HID = sys.argv[1] if len(sys.argv) > 1 else "38064"
c.goto("https://www.ekwing.com/hw/do?hid=%s&param_term=" % HID, wait=6)
print("url:", c.eval("location.href"))
print("--- 任务状态 ---")
print(c.eval(r"""(function(){
  var vm=avalon.vmodels['hwCntVm'];
  if(!vm||!vm.list) return 'no list';
  return vm.list.map(function(it){
    return [it.type_name, 'biz='+it.biz, '完成='+(it.finish_num!==undefined?it.finish_num:'?'),
            '状态='+(it.status!==undefined?it.status:'?')].join('  ');
  }).join('\n');
})()"""))
print("--- 页面文字 ---")
txt = c.eval("document.body.innerText") or ""
for line in txt.splitlines():
    s = line.strip()
    if any(k in s for k in ("已完成", "未完成", "进度", "提交", "项", "分")):
        print("  ", s[:120])
c.close()
