# -*- coding: utf-8 -*-
"""用 CDP 读 ekwing 的 cookie / localStorage，判断登录态。"""
import os
import sys
import time

sys.path.insert(0, r"E:\Code\ekwing-auto")
os.environ["CDP_PORT"] = "9224"
import cdp  # noqa: E402

c = cdp.CDP()
cookies = c.cmd("Network.getCookies", urls=["https://www.ekwing.com/"])["cookies"]
print("cookies(%d):" % len(cookies))
now = time.time()
for ck in cookies:
    exp = ck.get("expires", -1)
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(exp)) if exp > 0 else "session"
    print("  %-28s exp=%-16s size=%d http=%s" % (ck["name"], when, len(ck.get("value", "")), ck.get("httpOnly")))
print("secure now:", time.strftime("%Y-%m-%d %H:%M", time.localtime(now)))
print("ua:", c.eval("navigator.userAgent"))
print("localStorage:", c.eval("JSON.stringify(Object.keys(localStorage))")[:300])
print("sessionStorage:", c.eval("JSON.stringify(Object.keys(sessionStorage))")[:300])
c.close()
