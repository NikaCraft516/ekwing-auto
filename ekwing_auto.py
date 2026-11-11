#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
翼课网同步训练自动完成工具（只处理填空/选择类，自动跳过朗读类）

用法示例
--------
列出作业里的所有任务：
    python ekwing_auto.py --url "https://www.ekwing.com/hw/do?hid=<作业ID>" --list

只取答案、不动页面（推荐先跑这个看清楚要做什么）：
    python ekwing_auto.py --url "..." --dry-run

自动做完并提交填空题：
    python ekwing_auto.py --url "..."

只做指定几项：
    python ekwing_auto.py --url "..." --only 词语听写,单句首字母填空

离线解析已经下载的题目 JSON：
    python ekwing_auto.py --offline --json-dir samples

前置条件
--------
1. 用 start-chrome.bat 启动一个带调试端口的 Chrome，并登录翼课网；
2. 用本目录的 python 运行（见 README）。
"""

import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 语音评测类：需要真人录音，工具直接跳过
SPEECH_BIZ = {
    "005": "读记词语",
    "008": "读记目标句",
    "525": "课文背诵",
    "002": "课文跟读",
}
SPEECH_NAMES = set(SPEECH_BIZ.values())

# 名字兜底：即使出现没登记过的 biz，只要任务名里带这些词也跳过
SPEECH_KEYWORDS = ("跟读", "背诵", "读记", "朗读", "口语", "配音")


def is_speech(task):
    name = task.get("name") or ""
    return task.get("biz") in SPEECH_BIZ or any(k in name for k in SPEECH_KEYWORDS)

# 填空 / 选词类：答案可以直接写进 ansData 模型
FILL_BIZ = {"104", "304", "333", "349"}
# 词语听写：答案在 allData[].text 里，需要逐题输入
DICT_BIZ = {"030"}

API_URL = "https://acpf.ekwing.com/wapi/getbaseworktimucontent"
DEFAULT_PARAM_TERM = "20260901"


# --------------------------------------------------------------------------
# 页面侧 JS 片段
# --------------------------------------------------------------------------
JS_TILE_RECT = r"""
(function(name){
  var els=document.querySelectorAll('*');
  for(var i=0;i<els.length;i++){
    var e=els[i];
    if(e.children.length) continue;
    if((e.textContent||'').replace(/\s+/g,'')!==name) continue;
    var box=e;
    for(var k=0;k<5&&box;k++){
      var links=box.querySelectorAll('a');
      for(var j=0;j<links.length;j++){
        var lt=(links[j].textContent||'').replace(/\s+/g,'');
        if(lt!=='马上做'&&lt!=='再做一次') continue;
        links[j].scrollIntoView({block:'center'});
        var r=links[j].getBoundingClientRect();
        if(r.width>0) return {x:r.left+r.width/2, y:r.top+r.height/2, action:lt};
      }
      box=box.parentElement;
    }
  }
  return null;
})(%s)
"""

JS_PANEL_TEXT = r"""
(function(){
  var w=document.getElementById('jsDoWorkCompContainer');
  return w && getComputedStyle(w).display!=='none' ? (w.innerText||'') : '';
})()
"""

JS_CLICK_START = r"""
(function(){
  var a=document.querySelector('#jsDoWorkCompContainer .startNow a') ||
        document.querySelector('#jsDoWorkCompContainer .start_btn');
  if(!a) return null;
  var r=a.getBoundingClientRect();
  a.click();
  return {x:r.left+r.width/2, y:r.top+r.height/2};
})()
"""

JS_BLANK_COUNT = r"""
(function(){
  var n=0;
  document.querySelectorAll('#jsDoWorkCompContainer .jsDoHwFill').forEach(function(e){
    if(e.getBoundingClientRect().width>0) n++;
  });
  return n;
})()
"""

# 把答案写进 avalon 的 ansData 模型（填空/选词类通用）
JS_SET_ANSWERS = r"""
(function(vid, items){
  var vm=avalon.vmodels[vid];
  if(!vm || !vm.qus_items || !vm.ansData) return {ok:false, err:'模型未就绪'};
  var set=0;
  for(var i=0;i<vm.qus_items.length && i<items.length;i++){
    vm.ansData[vm.qus_items[i].id] = [items[i]];
    set++;
  }
  return {ok:true, vid:vid, set:set, total:vm.qus_items.length};
})(%s, %s)
"""

JS_BLANK_TEXT = r"""
(function(){
  var out=[];
  document.querySelectorAll('#jsDoWorkCompContainer .jsDoHwFill').forEach(function(e){
    if(e.getBoundingClientRect().width>0) out.push((e.textContent||'').replace(/\s+/g,''));
  });
  return out;
})()
"""

# 词语听写：题目数据在 allData 里，每项 .text 就是答案
JS_ALLDATA_WORDS = r"""
(function(vid){
  var vm=avalon.vmodels[vid];
  if(!vm || !vm.allData || !vm.allData.length) return null;
  return {vid:vid, words: vm.allData.map(function(w){return w.text;})};
})(%s)
"""

JS_VM_IDS = r"""
(function(){
  var a=[];
  for(var id in avalon.vmodels){
    var vm=avalon.vmodels[id];
    if(vm && (vm.qus_items || vm.allData)) a.push(id);
  }
  return a;
})()
"""

# 给贡献者用的"侦察"：导出一个任务的模型结构与 DOM 特征
JS_INSPECT = r"""
(function(vid){
  var vm=avalon.vmodels[vid];
  var w=document.getElementById('jsDoWorkCompContainer');
  var out={vid:vid, panelText:(w?w.innerText:'').replace(/\s+/g,' ').slice(0,300)};
  if(vm){
    var keys=[]; for(var k in vm){ if(typeof vm[k]!=='function') keys.push(k); }
    out.modelKeys=keys.join(',');
    out.itemCount=(vm.qus_items||[]).length;
    out.firstItem=JSON.stringify((vm.qus_items||[])[0]||null).slice(0,900);
    out.ansSample=JSON.stringify(vm.ansData||{}).slice(0,400);
  }
  if(w){
    out.dom={
      jsDoHwFill:w.querySelectorAll('.jsDoHwFill').length,
      radios:w.querySelectorAll('input[type=radio]').length,
      textInputs:w.querySelectorAll('input[type=text]').length,
      textareas:w.querySelectorAll('textarea').length,
      selects:w.querySelectorAll('select').length
    };
    out.htmlHint=w.innerHTML.slice(0,800);
  }
  return out;
})(%s)
"""

JS_TASK_KIND = r"""
(function(vid){
  var vm=avalon.vmodels[vid];
  if(!vm) return 'unknown';
  if(vm.allData) return 'dictation';
  if(vm.qus_items && vm.qus_items.length){
    var a=vm.ansData && vm.ansData[vm.qus_items[0].id];
    if(a && typeof a==='object' && 'ans' in a) return 'choice';
    return 'fill';
  }
  return 'unknown';
})(%s)
"""

# 选择题：正确答案在 VM 的 qus_items[].answer，选项是 input[name=choice_<qid>][value=A-D]
JS_CHOICE_ITEMS = r"""
(function(vid){
  var vm=avalon.vmodels[vid];
  if(!vm || !vm.qus_items) return null;
  var items=vm.qus_items.map(function(q){
    var a='';
    try { a = JSON.parse(q.answer)[0]; } catch(e) { a = (q.answer||'').replace(/["\[\]]/g,''); }
    return {id:q.id, answer:a};
  });
  return {vid:vid, items:items};
})(%s)
"""

JS_CLICK_CHOICE = r"""
(function(qid, ans){
  var r=document.querySelector('input[name="choice_'+qid+'"][value="'+ans+'"]');
  if(!r) return false;
  r.click();
  return true;
})(%s, %s)
"""

JS_CHOICE_DONE = r"""
(function(vid){
  var vm=avalon.vmodels[vid];
  if(!vm || !vm.qus_items) return null;
  var ok=0;
  vm.qus_items.forEach(function(q){ if(vm.ansData[q.id] && vm.ansData[q.id].ans) ok++; });
  return {answered:ok, total:vm.qus_items.length};
})(%s)
"""

JS_CLEAR_OVERLAYS = r"""
(function(){
  var n = 0;
  // 会员推广弹窗：直接删掉
  document.querySelectorAll('.new_pop_wrap.need_vip').forEach(function(e){ e.remove(); n++; });
  // 各种遮罩层：隐藏（有的页面用 mask_wrap / popup-mask）
  document.querySelectorAll('.popup-mask, .mask_wrap, .mask, .pop_shade').forEach(function(e){
    if(getComputedStyle(e).display !== 'none'){ e.style.display = 'none'; n++; }
  });
  document.body.classList.remove('popup-modal');
  document.documentElement.classList.remove('popup-modal');
  return n;
})()
"""

JS_HAS_PANEL = r"""
(function(){
  var w=document.getElementById('jsDoWorkCompContainer');
  if(!w) return false;
  if(getComputedStyle(w).display==='none') return false;
  return (w.innerText||'').trim().length > 0;
})()
"""

JS_CLICK_TEXT = r"""(function(t){
  var scope=document.getElementById('jsDoWorkCompContainer') || document.body;
  var els=scope.querySelectorAll('a,button,div,span');
  for(var i=0;i<els.length;i++){
    var e=els[i];
    if((e.textContent||'').replace(/\s+/g,'')!==t) continue;
    var r=e.getBoundingClientRect();
    if(r.width>10 && r.height>8){ e.click(); return {x:r.left+r.width/2, y:r.top+r.height/2}; }
  }
  return null;
})(%s)
"""

JS_CONFIRM_RECT = r"""
(function(t){
  var els=document.querySelectorAll('a,button,div,span');
  for(var i=0;i<els.length;i++){
    var e=els[i];
    if((e.textContent||'').replace(/\s+/g,'')!==t) continue;
    var r=e.getBoundingClientRect();
    if(r.width>0 && r.height>0 && e.offsetParent) return {x:r.left+r.width/2, y:r.top+r.height/2};
  }
  return null;
})(%s)
"""


# --------------------------------------------------------------------------
# 基础操作
# --------------------------------------------------------------------------
def log(msg):
    print(msg, flush=True)


def real_click(c, x, y, wait=1.0):
    c.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
    c.cmd("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
    c.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)
    time.sleep(wait)


def click_text(c, text, wait=1.0):
    """先 JS click，失败再用真实鼠标点一次。"""
    r = c.eval(JS_CLICK_TEXT % json.dumps(text))
    if r:
        time.sleep(wait)
        return True
    r = c.eval(JS_CONFIRM_RECT % json.dumps(text))
    if r:
        real_click(c, r["x"], r["y"], wait)
        return True
    return False


def clear_overlays(c):
    """清掉 VIP 推广弹窗和各种遮罩层，否则会挡住后续点击。"""
    try:
        return c.eval(JS_CLEAR_OVERLAYS) or 0
    except Exception:
        return 0


def open_tile(c, name, timeout=12, retries=2):
    """滚动到任务卡片并点"马上做/再做一次"，必要时刷新页面重试。"""
    for attempt in range(retries + 1):
        clear_overlays(c)
        r = c.eval(JS_TILE_RECT % json.dumps(name))
        if not r:
            return False
        real_click(c, r["x"], r["y"], 2.5)
        t0 = time.time()
        while time.time() - t0 < timeout:
            if c.eval(JS_HAS_PANEL):
                return True
            clear_overlays(c)
            time.sleep(0.6)
        if attempt < retries:
            url = c.eval("location.href")
            log("  · 页面状态异常，刷新后重试（第 %d 次）" % (attempt + 1))
            c.goto(url, wait=7)
    return False


def start_task(c, timeout=20):
    """点 START NOW，返回是否成功。"""
    r = c.eval(JS_CLICK_START)
    if r is None:
        # 有的题型按钮是 button.start-btn / .ready a
        r = c.eval("(function(){var b=document.querySelector('#jsDoWorkCompContainer button.start-btn');"
                   "if(!b)return null;var r=b.getBoundingClientRect();if(r.width<10)return null;"
                   "b.click();return {x:r.left+r.width/2,y:r.top+r.height/2};})()")
    if r is None:
        return False
    t0 = time.time()
    while time.time() - t0 < timeout:
        txt = (c.eval(JS_PANEL_TEXT) or "").strip()
        if txt and "道小题" not in txt and "START" not in txt:
            return True
        time.sleep(0.8)
    return bool((c.eval(JS_PANEL_TEXT) or "").strip())


# --------------------------------------------------------------------------
# 取题目 / 答案
# --------------------------------------------------------------------------
def fetch_content(c, key, param_term=DEFAULT_PARAM_TERM):
    """通过页面自己的 /proxy 接口取题目（含答案）。"""
    js = r"""
    (async function(key, param){
      var payload = {url:'%s', method:'POST', data:{keys:key, param_term:param}};
      var body = 'url=' + encodeURIComponent(payload.url) +
                 '&method=POST&data=' + encodeURIComponent(JSON.stringify(payload.data));
      var r = await fetch('/proxy', {method:'POST', credentials:'include',
        headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'},
        body: body});
      var t = await r.text();
      return t;
    })(%s, %s)
    """ % (API_URL, json.dumps(key), json.dumps(param_term))
    raw = c.eval(js, await_promise=True)
    try:
        return json.loads(raw)
    except Exception:
        return {"errno": -1, "err_info": "非 JSON 响应", "raw": (raw or "")[:300]}


def extract_items(data):
    """从接口返回里抽出题目列表：[{id, ask, answers, analyz, context}]"""
    items = []
    for block in data.get("data") or []:
        # 对话/语篇类题目：题干在这个 content 里，qus_item 的 ask 可能是空的
        ctx = ""
        for piece in block.get("content") or []:
            if isinstance(piece, dict) and piece.get("content"):
                ctx += str(piece["content"]) + "\n"
        q = block.get("question") or {}
        for it in q.get("qus_item") or []:
            ask = " ".join(str(a.get("content", "")) for a in it.get("ask") or [])
            items.append({
                "id": it.get("id"),
                "orders": it.get("orders"),
                "ask": ask.strip(),
                "context": ctx.strip(),
                "raw_answer": it.get("answer"),
                "answers": parse_answer(it.get("answer")),
                "analyz": it.get("analyz", ""),
            })
    return items


def parse_answer(raw):
    """解析 "[s]trange||[s]urprising" 这种答案格式，返回候选列表。"""
    if not raw:
        return []
    try:
        arr = json.loads(raw)
    except Exception:
        arr = [raw]
    out = []
    for a in arr:
        for part in str(a).split("||"):
            p = part.replace("[", "").replace("]", "").strip()
            if p:
                out.append(p)
    return out


# --------------------------------------------------------------------------
# 各题型处理
# --------------------------------------------------------------------------
def vm_ids(c):
    """当前页面上所有带题目的 Avalon 模型（旧任务的模型不会自动销毁）。"""
    try:
        return c.eval(JS_VM_IDS) or []
    except Exception:
        return []


def solve_task(c, name, items, dry=False):
    """打开任务 → 锁定新出现的模型 → 识别题型（选择/填空）→ 作答 → 提交。"""
    log("  · 打开任务：%s" % name)
    before = vm_ids(c)
    if not open_tile(c, name):
        return {"ok": False, "msg": "找不到任务卡片（可能被弹窗挡住或页面结构变了）"}
    if not start_task(c):
        log("  · 没有 START 按钮，直接作答")
    time.sleep(1.0)

    ids = vm_ids(c)
    fresh = [i for i in ids if i not in before]
    vid = fresh[-1] if fresh else (ids[-1] if ids else None)
    if not vid:
        return {"ok": False, "msg": "页面上没有题目模型"}
    log("  · 当前题目模型：%s" % vid)

    kind = c.eval(JS_TASK_KIND % json.dumps(vid))
    log("  · 识别题型：%s" % kind)
    handler = KIND_HANDLERS.get(kind)
    if not handler:
        return {"ok": False, "msg": "未识别的题型（%s），可用 --inspect 导出结构" % kind}
    return handler(c, vid, items, dry)


def _do_choice(c, vid, items=None, dry=False):
    """选择题：按 VM 里的 answer 点对应 radio。"""
    data = c.eval(JS_CHOICE_ITEMS % json.dumps(vid))
    if not data:
        return {"ok": False, "msg": "没读到选择题模型"}
    items = data["items"]
    log("  · %d 道选择题，答案：%s" % (len(items), " ".join(i["answer"] for i in items)))
    if dry:
        return {"ok": True, "msg": "dry-run，未作答"}
    for it in items:
        ok = c.eval(JS_CLICK_CHOICE % (json.dumps(it["id"]), json.dumps(it["answer"])))
        if not ok:
            log("    ! 题目 %s 找不到选项 %s" % (it["id"], it["answer"]))
        time.sleep(0.15)
    done = c.eval(JS_CHOICE_DONE % json.dumps(vid)) or {}
    log("  · 已答 %s/%s 题" % (done.get("answered"), done.get("total")))
    if done.get("answered") != done.get("total"):
        return {"ok": False, "msg": "有题目没选上"}
    return submit(c)


def _do_fill(c, vid, items, dry=False):
    """填空/选词/填表：把答案写进 ansData。"""
    t0 = time.time()
    n = 0
    while time.time() - t0 < 20:
        n = c.eval(JS_BLANK_COUNT) or 0
        if n >= len(items):
            break
        time.sleep(0.8)
    log("  · 检测到 %d 个空（题目 %d 题）" % (n, len(items)))
    if dry:
        return {"ok": True, "msg": "dry-run，未作答"}

    answers = [it["answers"][0] if it["answers"] else "" for it in items]
    res = c.eval(JS_SET_ANSWERS % (json.dumps(vid), json.dumps(answers)))
    log("  · 写入答案：%s" % json.dumps(res, ensure_ascii=False))
    time.sleep(0.6)
    shown = c.eval(JS_BLANK_TEXT) or []
    log("  · 页面显示：%s" % " | ".join(shown[:8]))
    if len(shown) < len(items):
        return {"ok": False, "msg": "空白数与题目数不符"}
    return submit(c)


def solve_dictation(c, name, dry=False):
    """词语听写：从 allData 取词，逐题输入。"""
    log("  · 打开任务：%s" % name)
    before = vm_ids(c)
    if not open_tile(c, name):
        return {"ok": False, "msg": "找不到任务卡片"}
    if not start_task(c):
        log("  · 未点到 START，继续尝试")
    time.sleep(1.5)
    ids = vm_ids(c)
    fresh = [i for i in ids if i not in before] or ids
    data = None
    for vid in reversed(fresh):
        data = c.eval(JS_ALLDATA_WORDS % json.dumps(vid))
        if data:
            break
    if not data:
        return {"ok": False, "msg": "没读到 allData 词表"}
    words = data["words"]
    log("  · 取到 %d 个词：%s ..." % (len(words), ", ".join(words[:6])))
    if dry:
        return {"ok": True, "msg": "dry-run，未作答", "words": words}

    focus = ("(function(){var e=document.querySelector('#jsDoWorkCompContainer input[type=text]');"
             "if(!e)return null;e.focus();e.select&&e.select();return e.placeholder||'';})()")
    for i, w in enumerate(words):
        if c.eval(focus) is None:
            return {"ok": False, "msg": "第 %d 题找不到输入框" % (i + 1)}
        c.cmd("Input.insertText", text=w)
        c.cmd("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter",
              windowsVirtualKeyCode=13, nativeVirtualKeyCode=13)
        c.cmd("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter",
              windowsVirtualKeyCode=13, nativeVirtualKeyCode=13)
        time.sleep(0.32)
        if (i + 1) % 5 == 0:
            log("  · 已填 %d/%d" % (i + 1, len(words)))
    return submit(c)


# --------------------------------------------------------------------------
# 题型注册表
#   key   = JS_TASK_KIND 返回的字符串
#   value = handler(c, vid, items, dry) -> {"ok": bool, ...}
#
# 新增一种题型的步骤：
#   1) 在 JS_TASK_KIND 里加一个判定分支，返回新的 kind 字符串；
#   2) 照着 _do_fill / _do_choice 写一个 handler；
#   3) 在下面注册；用 --inspect 导出结构，能少走很多弯路。
# --------------------------------------------------------------------------
KIND_HANDLERS = {
    "choice": _do_choice,
    "fill": _do_fill,
}


def submit(c):
    """点完成 → 确定，读回等级。"""
    if not click_text(c, "完成", wait=2.5):
        return {"ok": False, "msg": "找不到完成按钮"}
    if not click_text(c, "确定", wait=4.0):
        log("  · 没出现确认弹窗（可能直接提交了）")
    time.sleep(3)
    txt = (c.eval(JS_PANEL_TEXT) or "").replace("\n", " ")
    m = re.search(r"等级[:：]\s*([A-E])", txt)
    grade = m.group(1) if m else "?"
    m2 = re.search(r"用时[:：]\s*([0-9分秒]+)", txt)
    used = m2.group(1) if m2 else ""
    return {"ok": True, "grade": grade, "used": used, "msg": txt[:80]}


# --------------------------------------------------------------------------
# 任务枚举
# --------------------------------------------------------------------------
def list_tasks(c):
    js = r"""
    (function(){
      var vm = avalon.vmodels['hwCntVm'];
      if(!vm || !vm.list) return null;
      return vm.list.map(function(it){
        return {name: it.type_name, biz: it.biz, key: it.key,
                code: it.type_code, ids: String(it.ids||'').slice(0,40)};
      });
    })()
    """
    return c.eval(js) or []


def inspect_task(c, name, save_dir):
    """导出一个任务的模型结构与 DOM 特征，供贡献者写题型适配。"""
    log("== 侦察：%s ==" % name)
    before = vm_ids(c)
    if not open_tile(c, name):
        return {"ok": False, "msg": "找不到任务卡片"}
    start_task(c)
    time.sleep(1.5)
    ids = vm_ids(c)
    fresh = [i for i in ids if i not in before] or ids
    vid = fresh[-1] if fresh else None
    info = c.eval(JS_INSPECT % json.dumps(vid)) if vid else {"err": "没有模型"}
    info["kind"] = c.eval(JS_TASK_KIND % json.dumps(vid)) if vid else "unknown"
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, "inspect_%s.json" % re.sub(r"[^\w\-]", "_", name))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    log("  · 题型判定：%s" % info["kind"])
    log("  · 结构已保存：%s" % path)
    return {"ok": True, "path": path, "kind": info["kind"]}


def main():
    ap = argparse.ArgumentParser(description="翼课网作业自动完成（跳过朗读类）")
    ap.add_argument("--url", help="作业页 URL，如 https://www.ekwing.com/hw/do?hid=<作业ID>")
    ap.add_argument("--hid", help="只给作业 id 也可以")
    ap.add_argument("--port", type=int, default=int(os.environ.get("CDP_PORT", "9224")))
    ap.add_argument("--param-term", default=DEFAULT_PARAM_TERM)
    ap.add_argument("--only", help="只做这些任务，逗号分隔")
    ap.add_argument("--list", action="store_true", help="只列出任务")
    ap.add_argument("--inspect", metavar="任务名", help="导出该任务的模型结构（开发新题型适配用）")
    ap.add_argument("--dry-run", action="store_true", help="只取答案，不点页面")
    ap.add_argument("--offline", action="store_true", help="离线解析本地 JSON")
    ap.add_argument("--json-dir", default=os.path.join(HERE, "samples"))
    ap.add_argument("--save-dir", default=os.path.join(HERE, "answers"))
    args = ap.parse_args()

    # ---------- 离线模式：只解析本地 JSON ----------
    if args.offline:
        files = sorted(f for f in os.listdir(args.json_dir) if f.endswith(".json"))
        if not files:
            log("目录里没有 json：%s" % args.json_dir)
            return 1
        for f in files:
            data = json.load(open(os.path.join(args.json_dir, f), encoding="utf-8"))
            items = extract_items(data)
            log("\n=== %s（%d 题）===" % (f, len(items)))
            ctx = items[0].get("context") if items else ""
            if ctx and not any(it.get("ask") for it in items):
                log("  --- 对话/语篇 ---")
                for line in ctx.splitlines():
                    log("  " + line)
            for it in items:
                if it["ask"]:
                    log("  %s. %s" % (it["orders"] or "?", it["ask"]))
                else:
                    log("  %s. （见上方对话，第 %s 空）" % (it["orders"] or "?", it["orders"] or "?"))
                log("     答案: %s" % " / ".join(it["answers"]))
        return 0

    # ---------- 在线模式 ----------
    if not args.url and not args.hid:
        ap.error("需要 --url 或 --hid（或者用 --offline）")
    os.environ["CDP_PORT"] = str(args.port)
    import importlib
    import cdp as cdp_mod
    importlib.reload(cdp_mod)

    url = args.url or "https://www.ekwing.com/hw/do?hid=%s&param_term=" % args.hid
    try:
        c = cdp_mod.CDP()
    except Exception as e:
        log("！连不上 Chrome 调试端口 %d：%s" % (args.port, e))
        log("  请先双击 start-chrome.bat 打开浏览器并登录翼课网，保持它开着再运行本工具。")
        return 4
    try:
        c.goto(url, wait=8)
        log("当前页面：%s" % c.eval("location.href"))
        if "site/index" in (c.eval("location.href") or ""):
            log("！未登录，请先在浏览器里登录翼课网后重试")
            return 2

        tasks = list_tasks(c)
        if not tasks:
            log("！没读到任务列表（hwCntVm 为空），页面可能还没加载完")
            return 3

        log("\n作业共 %d 项：" % len(tasks))
        for t in tasks:
            tag = "朗读(跳过)" if is_speech(t) else "自动"
            log("  - %-16s biz=%-4s %s" % (t["name"], t["biz"], tag))
        if args.list:
            return 0

        if args.inspect:
            target = next((t for t in tasks if t["name"] == args.inspect), None)
            if not target:
                log("！没有名为「%s」的任务，先用 --list 看看有哪些" % args.inspect)
                return 5
            r = inspect_task(c, args.inspect, args.save_dir)
            return 0 if r.get("ok") else 1

        only = set(x.strip() for x in args.only.split(",")) if args.only else None
        os.makedirs(args.save_dir, exist_ok=True)
        results = []

        for t in tasks:
            name, biz = t["name"], str(t["biz"])
            if is_speech(t):
                results.append((name, "跳过（朗读类需真人）"))
                continue
            if only and name not in only:
                results.append((name, "未选中"))
                continue

            log("\n== 处理：%s ==" % name)
            clear_overlays(c)
            data = fetch_content(c, t["key"], args.param_term)
            if data.get("errno") not in (0, "0"):
                log("  ！取题失败：%s" % json.dumps(data, ensure_ascii=False)[:200])
                results.append((name, "取题失败"))
                continue

            fn = os.path.join(args.save_dir, "%s_%s.json" % (biz, (t["key"] or "").replace("|", "_")))
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)

            if biz in DICT_BIZ:      # 词语听写
                r = solve_dictation(c, name, args.dry_run)
            else:                    # 其余题型：打开后自动识别选择/填空
                items = extract_items(data)
                if not items:
                    results.append((name, "无题目数据"))
                    continue
                log("  · 解析出 %d 题" % len(items))
                r = solve_task(c, name, items, args.dry_run)

            if r.get("ok"):
                msg = "等级 %s" % r.get("grade", "-") if r.get("grade") else r.get("msg", "完成")
            else:
                msg = "失败：" + r.get("msg", "?")
            results.append((name, msg))
            log("  → %s" % msg)

            # 收尾：关面板 + 清遮罩，准备下一项
            c.eval("(function(){var w=document.getElementById('jsDoWorkCompContainer');if(w){w.style.display='none';w.innerHTML='';}})()")
            clear_overlays(c)
            time.sleep(0.5)

        log("\n================ 汇总 ================")
        for name, msg in results:
            log("%-18s %s" % (name, msg))
        return 0
    finally:
        c.close()


if __name__ == "__main__":
    sys.exit(main())
