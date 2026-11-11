# -*- coding: utf-8 -*-
"""看 ekwing 登录 cookie 是否还在。"""
import os
import shutil
import sqlite3
import tempfile
import time

src = os.path.join(os.environ["LOCALAPPDATA"], "ekwing-auto-profile", "Chrome",
                   "Default", "Network", "Cookies")
tmp = os.path.join(tempfile.gettempdir(), "ekw-cookies.db")
shutil.copyfile(src, tmp)
con = sqlite3.connect(tmp)
rows = con.execute(
    "select host_key, name, expires_utc, length(encrypted_value), is_httponly "
    "from cookies where host_key like '%ekwing%' order by host_key, name").fetchall()
print("cookies:", len(rows))
now = time.time()
CHROME_EPOCH = 11644473600
for host, name, exp, n, httponly in rows:
    t = exp / 1e6 - CHROME_EPOCH if exp else 0
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t > 0 else "session"
    state = "EXPIRED" if (exp and t < now) else "ok"
    print("%-24s %-28s %-16s len=%-4d http=%d %s" % (host, name, when, n, httponly, state))
