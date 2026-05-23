# Sector Management

针对 `universe.py` 中指定板块进行股票池管理。

## 用法
```
/sector <板块名称>
```

示例：
- `/sector Memory`
- `/sector IDM / Foundry`
- `/sector Fabless Design`
- `/sector Equipment / EDA`
- `/sector Packaging / Test`

---

## 执行步骤

**参数：** $ARGUMENTS

1. 读取 `universe.py`，找到 `$ARGUMENTS` 对应的板块
2. 列出该板块当前所有股票，格式为表格（代码 + 公司全名）
3. 显示该板块股票数量，以及占总股票池的比例
4. 询问用户想执行哪种操作：
   - **添加股票**：用户提供代码，确认交易所格式（US / .HK / .KS / .TW 等），写入 `universe.py`
   - **删除股票**：用户指定代码，从 `universe.py` 移除
   - **替换股票**：删除旧代码，添加新代码
   - **仅查看**：不做任何修改，结束
5. 如有修改，更新 `universe.py`，然后 commit 并 push 到当前分支

## 注意事项

- 公司名称从已知知识库提供，不调用外部 API
- 若用户提供的代码属于非美股（港股、韩股、台股等），需确认正确的 yfinance 后缀格式
- 修改后自动更新 CLAUDE.md 中的股票池总数（如有记录）
- 不要创建 Pull Request，除非用户明确要求
