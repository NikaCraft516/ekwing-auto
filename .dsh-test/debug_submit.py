# -*- coding: utf-8 -*-
"""定位 submit() 里「完成 → 确定」失败的原因。"""
import os
import sys
import time

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9333"
import cdp  # noqa: E402

c = cdp.CDP()
c.goto("http://127.0.0.1:8765/index.html", wait=1.5)


def show(tag, v):
    print("%-22s %s" % (tag, v))


# 直接调用页面里的 openTask / startTask，绕开点击
c.eval("openTask(TASKS.filter(function(t){return t.biz==='104';})[0]);"
       "document.getElementById('startBtn').click(); 1")
time.sleep(0.4)
show("blanks", c.eval("document.querySelectorAll('#jsDoWorkCompContainer .jsDoHwFill').length"))
show("panel", c.eval("document.getElementById('jsDoWorkCompContainer').innerText.replace(/\\n/g,' | ')"))
show("fin?", c.eval("!!document.getElementById('fin')"))
show("find 完成", c.eval(
    "(function(){var els=document.getElementById('jsDoWorkCompContainer').querySelectorAll('a,button,div,span');"
    "for(var i=0;i<els.length;i++){var e=els[i];"
    "if((e.textContent||'').replace(/\\s+/g,'')!=='完成')continue;"
    "var r=e.getBoundingClientRect();return {tag:e.tagName,id:e.id,w:r.width,h:r.height};}return null;})()"))

# 点「完成」
c.eval("(function(){var els=document.querySelectorAll('#jsDoWorkCompContainer a');"
       "for(var i=0;i<els.length;i++){if(els[i].textContent.replace(/\\s+/g,'')==='完成'){els[i].click();return 1;}}return 0;})()")
time.sleep(0.5)
show("confirm exist", c.eval("document.querySelectorAll('#jsDoWorkCompContainer .confirm').length"))
show("panel after 完成", c.eval("document.getElementById('jsDoWorkCompContainer').innerText.replace(/\\n/g,' | ')"))
show("find 确定", c.eval(
    "(function(){var els=document.getElementById('jsDoWorkCompContainer').querySelectorAll('a,button,div,span');"
    "var out=[];for(var i=0;i<els.length;i++){var e=els[i];"
    "if((e.textContent||'').replace(/\\s+/g,'')!=='确定')continue;"
    "var r=e.getBoundingClientRect();out.push({tag:e.tagName,id:e.id,w:r.width,h:r.height,disp:getComputedStyle(e).display});}return out;})()"))

c.close()
