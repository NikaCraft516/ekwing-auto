## 这个 PR 做了什么

<!-- 一句话说明，例如：新增"连线题"支持（biz 123） -->

## 类型

- [ ] 新增题型支持
- [ ] 修复页面改版导致的失效
- [ ] 文档 / 脚本改进
- [ ] 其他：

## 涉及的任务

| 题型 | biz | 判定结果（fill/choice/新增） |
|---|---|---|
|  |  |  |

## 测试情况

- [ ] `python -m py_compile ekwing_auto.py cdp.py` 通过
- [ ] `ekw.bat --offline --json-dir samples` 正常
- [ ] `ekw.bat --url ... --list` 正常
- [ ] `--dry-run` 能识别该题型
- [ ] 实际运行拿到等级（贴结果：等级 X）

```
<!-- 这里贴终端输出 -->
```

## 结构依据（新题型必填）

<!-- 贴 --inspect 导出的 modelKeys / firstItem / dom，注意脱敏 -->

## 自查

- [ ] 没有提交账号、姓名、学校、真实作业 ID
- [ ] 没有提交 `answers/`、日志、浏览器配置目录
- [ ] 没有引入第三方依赖
- [ ] `dry=True` 时不会写答案或提交
