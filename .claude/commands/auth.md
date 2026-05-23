# Auth Management

管理选股系统的用户认证和管理员配置。

## 用法

```
/auth <操作>
```

示例：
- `/auth status`       — 查看当前用户数和管理员配置
- `/auth add-admin`    — 将邮箱添加为管理员
- `/auth list`         — 列出所有注册用户
- `/auth delete`       — 删除指定用户

---

## 执行步骤

**参数：** $ARGUMENTS

### status — 查看状态

1. 读取 `.cache/users.db`，统计注册用户总数
2. 读取 `.streamlit/secrets.toml`（本地）或说明 Streamlit Cloud 配置路径，显示当前 `ADMIN_EMAILS`
3. 报告：用户总数、当前管理员邮箱列表、数据库路径

### add-admin — 添加管理员

1. 询问要设为管理员的邮箱
2. 检查该邮箱是否已注册（查 `.cache/users.db`）；若未注册，提示需先在 app 内注册
3. 检查 `.streamlit/secrets.toml` 是否存在：
   - **存在**：将邮箱追加到 `ADMIN_EMAILS` 字段（保持原有邮箱）
   - **不存在**：创建 `.streamlit/secrets.toml`，写入 `ADMIN_EMAILS = "email"`
4. 提示：Streamlit Cloud 部署需在 **App Settings → Secrets** 中同步更新

### list — 列出用户

1. 查询 `.cache/users.db`
2. 以表格输出：邮箱、注册时间，并标注哪些是管理员

### delete — 删除用户

1. 询问要删除的邮箱
2. 二次确认
3. 从 `.cache/users.db` 删除该用户
4. 若该邮箱在 `ADMIN_EMAILS` 中，同时从配置中移除并提示

---

## 相关文件

| 文件 | 用途 |
|------|------|
| `auth.py` | `register()` / `verify()` / `list_users()` / `delete_user()` |
| `.cache/users.db` | SQLite 用户数据库（git-ignored） |
| `.streamlit/secrets.toml` | 本地管理员配置（git-ignored） |
| `.streamlit/secrets.toml.example` | 配置模板（已提交） |

## 注意事项

- `.streamlit/secrets.toml` 已被 git 忽略，不要提交
- Streamlit Community Cloud 的 Secrets 需在网页端手动配置，无法通过代码推送
- 删除用户为永久操作，无法撤销
- 不要创建 Pull Request，除非用户明确要求
