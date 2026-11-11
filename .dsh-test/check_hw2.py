# -*- coding: utf-8 -*-
"""看清作业页的完成进度与「提交训练」是什么。"""
import os
import sys

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402

c = cdp.CDP()
print("keys:", c.eval("Object.keys(avalon.vmodels['hwCntVm'].list[0]).join(',')"))
print("first:", c.eval("JSON.stringify(avalon.vmodels['hwCntVm'].list[0]).slice(0,500)"))
print("progress text:", c.eval(
    r"""(function(){
  var t=document.body.innerText;
  var i=t.indexOf('我的完成进度');
  return t.slice(i, i+120).replace(/\n/g,' | ');
})()"""))
print("submit btn:", c.eval(
    r"""(function(){
  var els=document.querySelectorAll('a,button,span,div');
  for(var i=0;i<els.length;i++){
    var e=els[i];
    if((e.textContent||'').replace(/\s+/g,'')!=='提交训练') continue;
    if(e.children.length) continue;
    var r=e.getBoundingClientRect();
    if(r.width<5) continue;
    return {tag:e.tagName, cls:e.className||'', w:r.width, h:r.height,
            parent:e.parentElement.className||'', disabled:e.className.indexOf('disable')>=0};
  }
  return null;
})()"""))
c.close()
