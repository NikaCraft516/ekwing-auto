# -*- coding: utf-8 -*-
"""看上一轮听写到底敲进去了什么。"""
import json
import os
import sys

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9333"
import cdp  # noqa: E402

c = cdp.CDP()
print("state   =", c.eval("JSON.stringify(window.__lastVm && window.__lastVm.state)"))
print("input   =", c.eval("(function(){var e=document.getElementById('wordInput');"
                         "return e ? e.value : null;})()"))
print("progress=", c.eval("(function(){var e=document.getElementById('dictProgress');"
                          "return e ? e.textContent : null;})()"))
print("panel   =", c.eval("document.getElementById('jsDoWorkCompContainer').innerText.replace(/\\n/g,' | ')"))
c.close()
