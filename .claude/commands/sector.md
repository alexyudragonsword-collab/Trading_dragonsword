# Sector Management

针对 `universe.py` 中指定板块进行股票池管理，也可新建板块。

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
- `/sector Display Drivers`   ← 新板块示例

---

## 执行步骤

**参数：** $ARGUMENTS

1. 读取 `universe.py`，检查 `$ARGUMENTS` 是否已存在于 `SUBSECTOR_MAP`
2. **若板块已存在**：
   - 列出该板块当前所有股票，格式为表格（代码 + 公司全名）
   - 显示股票数量及占总池比例
   - 询问用户想执行哪种操作：
     - **添加股票**：用户提供代码，确认交易所格式，写入该板块
     - **删除股票**：用户指定代码，从该板块移除
     - **替换股票**：删除旧代码，添加新代码
     - **重命名板块**：修改 `SUBSECTOR_MAP` 中的 key 名称
     - **删除整个板块**：移除该板块及其所有股票（二次确认）
     - **仅查看**：不做任何修改，结束
3. **若板块不存在**（新板块）：
   - 提示用户确认板块名称是否正确
   - 确认后，在 `SUBSECTOR_MAP` 末尾新增该板块，初始为空列表
   - 询问用户要添加哪些股票（代码 + 确认交易所格式）
   - 将所有股票写入新板块
4. 如有任何修改，更新 `universe.py`，然后 commit 并 push 到当前分支

## 注意事项

- 公司名称从已知知识库提供，不调用外部 API
- 若用户提供的代码属于非美股（港股、韩股、台股等），需确认正确的 yfinance 后缀格式：
  - 港股：`XXXX.HK`
  - 韩股：`XXXXXX.KS`
  - 台股：`XXXX.TW`
  - 上交所：`XXXXXX.SS`
  - 深交所：`XXXXXX.SZ`
- 新建板块后，`scorer.py` 的 `FACTOR_GROUPS` / `DEFAULT_GROUP_WEIGHTS` 无需修改（板块分组与因子组独立）
- 不要创建 Pull Request，除非用户明确要求
