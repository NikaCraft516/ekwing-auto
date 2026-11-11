# 文件说明

> 每个文件做什么、为什么存在、什么时候需要动它。改代码前先扫这张表，能少翻一半文件。
> 新增或删除文件时，记得同步更新这里。

## 一眼看全

| 文件 | 类型 | 一句话 |
|---|---|---|
| `browser.bat` | 入口 | 起一个带调试端口的 Edge/Chrome，并保证窗口真的看得见 |
| `ekw.bat` | 入口 | 找 Python、设编码和端口，把参数转交给主程序 |
| `ekwing_auto.py` | 主程序 | 全部业务逻辑：枚举 → 取题 → 判题型 → 作答 → 提交 → 汇总 |
| `cdp.py` | 底层 | 极简 CDP 客户端（HTTP 发现 + 裸 WebSocket），只跟浏览器说话 |
| `show-browser.ps1` | 辅助 | 把最小化的浏览器窗口唤到前台 |
| `samples/*.json` | 数据 | 四份示例题目 JSON，供 `--offline` 演示和回归 |
| `README.md` | 文档 | 面向使用者：支持范围、安装、用法、FAQ |
| `CONTRIBUTING.md` | 文档 | 面向贡献者：目录职责、新增题型的完整流程、约定 |
| `LICENSE` | 文档 | MIT，Copyright (c) 2026 NikaMiami |
| `.gitignore` | 配置 | 挡住运行产物：`answers/`、`__pycache__/`、日志、浏览器配置 |
| `.gitattributes` | 配置 | `* text=auto`，统一换行 |
| `.github/**` | 配置 | Issue 模板（bug / 新题型）与 PR 检查清单 |

## 运行链路

```
browser.bat            起浏览器（独立配置目录 + 调试端口）
    ↓  登录一次，登录态存在 %LOCALAPPDATA%\ekwing-auto-profile\
ekw.bat                找 Python（py → PATH → 常见安装路径 → DSH 自带）
    ↓  设 CDP_PORT=9224、PYTHONIOENCODING=utf-8
ekwing_auto.py         业务逻辑
    ↓  import cdp，连 127.0.0.1:9224 的 WebSocket
cdp.py                 Runtime.evaluate / Input.dispatchMouseEvent / Page.navigate
    ↓
Chrome / Edge          真正执行点击、键入、渲染判分
```

## 逐项说明

### `ekwing_auto.py`

主程序，约 800 行，全部逻辑都在这一个文件里，刻意不拆包（降低上手成本）。

内部顺序：

| 阶段 | 函数 | 说明 |
|---|---|---|
| 枚举 | `list_tasks()` | 读页面上的 Avalon 模型 `hwCntVm.list`，得到 `{name, biz, key}` |
| 取题 | `fetch_content()` | 用任务 `key` 走页面自己的 `/proxy` 接口，拿回带答案的 JSON |
| 解析 | `extract_items()` / `parse_answer()` | 把 `qus_item[]` 规整成 `{id, ask, answers, options}` |
| 判题型 | `JS_TASK_KIND` | 运行时判断 `dictation` / `fill` / `choice`，不写死 biz 编号 |
| 分发 | `KIND_HANDLERS` | `fill → _do_fill`、`choice → _do_choice`；听写按 `DICT_BIZ` 单独走 |
| 作答 | `_do_fill` / `_do_choice` / `solve_dictation` | 写 `ansData` / 点 radio / 逐词键入 |
| 提交 | `submit()` | 点「完成 → 确定」，读回 `等级 A` 或 `得分 100` |
| 汇总 | `main()` | 逐项打印结果，朗读类直接跳过 |

几个值得记住的点：

- **页面侧 JS 都以 `JS_*` 常量集中存放**（顶部），改选择器只改这一片；
- **选择题不能按答案字母硬点**：平台每次进入都会打乱选项，`answer` 是原始选项字母，
  radio 的 `value` 是显示顺序字母，必须用答案正文匹配（见 `_do_choice` / `_norm_opt`）；
- **`submit()` 认两种结果页**：多数题型给「等级 A」，词语听写只给「分数 + 答案对照表」；
- **朗读类靠 biz + 名字双保险**跳过（`SPEECH_BIZ` / `SPEECH_KEYWORDS`），宁可少做也不误点。

什么时候要改它：新增题型、页面选择器改版、答案格式变化。

> 小瑕疵：`FILL_BIZ` 和 `SPEECH_NAMES` 目前定义后没有被引用，属于历史遗留，可以删。

### `cdp.py`

235 行，纯标准库实现的 Chrome DevTools Protocol 客户端，不依赖 `websocket-client`。

- `http_json()`：先试 `127.0.0.1` 再试 `::1`（调试端口有时只绑 IPv6），也认 `CDP_HOST`；
- `page_target()`：从 `/json/list` 里挑一个页面（跳过 devtools 页面）；
- `WS`：手写 WebSocket 握手 + 帧编解码（含 ping/pong、分片），够用就好；
- `CDP`：`cmd()` 发命令并等对应 `id` 的回复，`eval()` 走 `Runtime.evaluate`，
  另有 `goto()` / `shot()`；
- 命令行还能单独用：`python cdp.py targets|nav|eval|shot|cmd ...`，调试时很方便。

一般不用改；只有 CDP 协议本身变化或要加新能力时才动。

### `browser.bat`

纯 ASCII（**不要写中文**，cmd 按 OEM 码页解析会破坏引号），只做四件事：

1. 探测浏览器：Edge 优先，其次 Chrome，装在 Program Files / x86 / LOCALAPPDATA 都认；
2. 端口已在监听 → 直接复用，不再重复启动；
3. 配置目录被占用但端口没开 → 说明是个没带调试参数的旧实例，先按 `--user-data-dir` 精确匹配干掉再启动；
4. 启动后轮询端口（最多约 12 秒）确认真的可用，最后把窗口唤到前台。

第 2～4 步都是为了解决同一个坑：Chrome 按 `--user-data-dir` 做单例，第二个进程只会
转交标签页，`--remote-debugging-port` 直接被忽略，端口永远起不来。

### `show-browser.ps1`

一行参数（`chrome.exe` / `msedge.exe`），用 `ShowWindow(SW_RESTORE)` + `SetForegroundWindow`
把窗口从最小化拽回来。脚本启动的 Chrome 常常是最小化的，不唤一下就"看起来根本没启动"。

单独成文件是为了避开 `.bat` 里嵌套引号的转义地狱。

### `ekw.bat`

只管三件事：找 Python（`py` → PATH → `%LOCALAPPDATA%\Programs\Python\Python3*` → DSH 自带运行时）、
设 `CDP_PORT=9224` 和 `PYTHONIOENCODING=utf-8`、把参数原样转交给 `ekwing_auto.py`。
出错时 `pause` 并回显退出码。

### `samples/`

`task104 / task304 / task333 / task349.json` 是四种典型题型的接口返回样本，
用于 `ekw.bat --offline --json-dir samples` 跑通「解析 + 打印答案」，不需要浏览器。
改解析逻辑时先用它们回归。

### `README.md` / `CONTRIBUTING.md`

- README 给使用者：支持范围、环境、三条命令、工作原理、FAQ、已知限制；
- CONTRIBUTING 给贡献者：目录职责、新增题型的「侦察 → 判定 → handler」三步、
  代码约定（**只用标准库**）、以及选项乱序这个必读坑。

两者有重叠（目录结构、题型表），改动时最好一起看。

### `.github/`

- `ISSUE_TEMPLATE/bug_report.yml`：报障，要求贴完整终端输出和命令；
- `ISSUE_TEMPLATE/feature_request.yml`：新题型，要求给任务名、biz、当前表现；
- `pull_request_template.md`：PR 自查清单，重点是"没提交账号 / 作业 ID / `answers/`"。

### `.gitignore` / `.gitattributes`

忽略运行产物（`answers/` 可能含真实作业内容）、`__pycache__`、日志和浏览器配置目录。
`.gitattributes` 只有 `* text=auto`；`.bat` 用 LF 在 Win11 实测没问题。

## 不会提交的运行时产物

| 路径 | 来源 | 说明 |
|---|---|---|
| `answers/` | `ekwing_auto.py --save-dir` | 题目 JSON + `--inspect` 导出，**可能含真实作业信息** |
| `__pycache__/` | Python | 字节码缓存 |
| `%LOCALAPPDATA%\ekwing-auto-profile\` | `browser.bat` | **含登录态**，绝不外传 |
