# 贡献指南

感谢你愿意改进 ekwing-auto。这个项目靠"遇到新题型 → 补一个适配器"慢慢长大，
所以**最欢迎的 PR 是新增题型支持**。

## 目录与职责

| 文件 | 职责 |
|---|---|
| `ekwing_auto.py` | 全部逻辑：枚举任务、取题、识别题型、作答、提交 |
| `cdp.py` | 极简 CDP 客户端（WebSocket 帧 + HTTP），一般不用改 |
| `start-browser.bat` | 启动可控浏览器（Edge/Chrome 自动探测） |
| `ekw.bat` | 运行入口（找 Python、设端口和编码） |
| `samples/` | 示例题目 JSON，用于 `--offline` 演示 |
| `answers/` | 运行时产物，**已在 .gitignore 中，不要提交** |

`ekwing_auto.py` 内部按这个顺序工作：

```
list_tasks()      读 hwCntVm.list 得到 [{name, biz, key}]
fetch_content()   POST /proxy 取题目与答案
extract_items()   把 qus_item[] 规整成 [{id, ask, answers}]
solve_task()      open_tile → start_task → 锁定新出现的模型 → JS_TASK_KIND 判题型
KIND_HANDLERS     按 kind 分发到 _do_fill / _do_choice
submit()          点「完成 → 确定」，读回等级
```

## 新增一种题型

以"连线题"为例，三步：

**1. 先侦察**

```bat
ekw.bat --url "https://www.ekwing.com/hw/do?hid=<ID>" --inspect 连线题
```

会导出 `answers/inspect_连线题.json`，里面有：

- `modelKeys`：视图模型有哪些字段（找 `qus_items` / `ansData` / `allData`）
- `firstItem`：第一题的数据结构，答案字段通常就在里面
- `dom`：页面上有多少输入框 / radio / textarea
- `htmlHint`：容器 HTML 片段，用来找选择器

**2. 加判定**

在 `JS_TASK_KIND` 里加分支，返回新的 kind：

```js
if (vm.qus_items && vm.qus_items[0].pairs) return 'match';
```

**3. 写 handler 并注册**

```python
def _do_match(c, vid, items=None, dry=False):
    """连线题：按 pairs 依次点击左右两侧。"""
    data = c.eval(JS_MATCH_ITEMS % json.dumps(vid))
    if not data:
        return {"ok": False, "msg": "没读到连线数据"}
    if dry:
        return {"ok": True, "msg": "dry-run，未作答"}
    for pair in data["pairs"]:
        c.eval(JS_CLICK_PAIR % (json.dumps(pair["left"]), json.dumps(pair["right"])))
    return submit(c)


KIND_HANDLERS = {
    "choice": _do_choice,
    "fill": _do_fill,
    "match": _do_match,      # ← 注册
}
```

约定：

- handler 签名统一为 `(c, vid, items=None, dry=False)`；
- 返回 `{"ok": True, "grade": "A"}` 或 `{"ok": False, "msg": "原因"}`；
- `dry=True` 时**绝对不能**写答案或点提交，只做读取与校验；
- 失败信息写清楚"哪一题、什么现象"，不要只抛异常。

## 调试技巧

- `--list`：只列任务，不碰页面
- `--dry-run`：取答案 + 识别题型，但不作答
- `--only 任务名`：只跑一个任务，减少干扰
- `--inspect 任务名`：导出模型与 DOM 结构

在浏览器里手动观察时，可以在 DevTools Console 里执行：

```js
Object.keys(avalon.vmodels).filter(id => avalon.vmodels[id].qus_items)
```

## 代码风格

- Python 3.9+，**只用标准库**
- 4 空格缩进，函数加一句中文 docstring 说明"做什么"
- 新增 JS 片段命名 `JS_XXX`，跟着现有写法用 IIFE 包裹
- 中文注释，面向"下一个读代码的人"
- 不要引入 `requests` / `selenium` / `playwright` 等依赖

## 提交前自测

请至少确认：

1. `python -m py_compile ekwing_auto.py cdp.py` 通过
2. `ekw.bat --offline --json-dir samples` 能正确打印答案
3. `ekw.bat --url ... --list` 能列出任务
4. 新题型：`--dry-run` 能识别，实际运行能拿到等级
5. 没把 `answers/`、日志、浏览器配置目录提交进去

## PR 要求

- 一个 PR 只做一件事（新增题型 / 修复某个选择器 / 文档），方便 review
- 描述里写清：**题型名 + biz 编号 + 页面结构要点 + 测试结果**（截图或终端输出）
- 涉及页面改版的修复，请附上改版后的 `--inspect` JSON（可脱敏）
- **不要提交**：真实姓名、学校、作业 ID、`answers/` 里的题目数据、任何账号信息

提交信息建议用 Conventional Commits：

```
feat: support 连线题 (biz 123)
fix: 修复会员弹窗遮挡导致点不开卡片
docs: 补充 --inspect 用法
```

## 行为准则

- 讨论对事不对人
- 不接受"代写/代做"类需求，也不接受为此类服务做优化的 PR
- 维护者可能因平台改版、合规风险等原因拒绝某些改动，请理解
