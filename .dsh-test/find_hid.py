# -*- coding: utf-8 -*-
"""找到「做训练」按钮真实指向的作业地址。"""
import os
import sys

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402

c = cdp.CDP()
info = c.eval(r"""(function(){
  var out=[];
  var els=document.querySelectorAll('a,button,div,span');
  for(var i=0;i<els.length;i++){
    var e=els[i];
    var t=(e.textContent||'').replace(/\s+/g,'');
    if(t!=='做训练' && t!=='重做训练') continue;
    var chain=[], box=e;
    for(var k=0;k<5&&box;k++){
      chain.push({tag:box.tagName, cls:box.className||'', href:box.getAttribute&&box.getAttribute('href'),
                  onclick:(box.getAttribute&&box.getAttribute('onclick')||'').slice(0,120),
                  href2:(box.getAttribute&&box.getAttribute('data-href'))||''});
      box=box.parentElement;
    }
    out.push(chain);
  }
  return out;
})()""")
for i, chain in enumerate(info or []):
    print("== button", i)
    for node in chain:
        print("   ", node)
c.close()
