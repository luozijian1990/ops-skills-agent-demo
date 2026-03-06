---
name: mysql-sql-analyzer
description: "基于 MySQL 与 SQLAlchemy 的 SQL 执行过程分析技能。用于分析单条 SQL 的执行计划（EXPLAIN FORMAT=JSON）、自动识别涉及表并读取表结构与索引、定位全表扫描/filesort/temporary table 等风险并给出优化建议。当用户要求“分析 MySQL SQL 为什么慢”“看执行计划”“给索引优化建议”时使用。连接目标（host/port/database）由输入提供，凭据通过环境变量注入，避免泄露敏感信息。"
---

# MySQL SQL 执行分析技能

使用此技能分析 MySQL SQL 的执行过程与性能风险，不执行原 SQL。

## 运行约束

- 仅执行只读分析语句：`EXPLAIN`、`SHOW`、`information_schema` 查询。
- 禁止执行原 SQL（尤其是 `UPDATE/DELETE/INSERT`）。
- 禁止在回答中回显数据库密码或完整连接串。
- 需要在可访问目标 MySQL 的环境中运行脚本。

## 环境变量

必需：

- `MYSQL_USER`
- `MYSQL_PASSWORD`

可选：

- `MYSQL_CHARSET`（默认 `utf8mb4`）
- `MYSQL_CONNECT_TIMEOUT`（默认 `5` 秒）

## 环境变量自动加载

脚本会自动加载 `.env`（不覆盖已存在变量），按以下顺序：

1. `./skills/mysql-sql-analyzer/.env`
2. `./backend/skills/mysql-sql-analyzer/.env`
3. `./.env`
4. `./backend/.env`
5. `<backend>/skills/mysql-sql-analyzer/.env`
6. `<backend>/.env`

## 标准流程

1. 获取用户提供的完整 SQL（单条）。
2. 运行分析脚本（默认不执行 `EXPLAIN ANALYZE`）：

```bash
python3 ./backend/skills/mysql-sql-analyzer/scripts/analyze_mysql_sql.py \
  --host "<db_host>" \
  --port 3306 \
  --database "<db_name>" \
  --sql "<完整 SQL>" \
  --output markdown
```

或：

```bash
python3 ./backend/skills/mysql-sql-analyzer/scripts/analyze_mysql_sql.py \
  --host "<db_host>" \
  --port 3306 \
  --database "<db_name>" \
  --sql-file /tmp/query.sql \
  --output json \
  --pretty
```

3. 仅在用户明确要求并可接受额外开销时，增加真实执行信息：

```bash
python3 ./backend/skills/mysql-sql-analyzer/scripts/analyze_mysql_sql.py \
  --host "<db_host>" \
  --port 3306 \
  --database "<db_name>" \
  --sql "<完整 SQL>" \
  --explain-analyze
```

4. 按以下结构返回结论：
   - 执行计划摘要（访问类型、命中索引、rows/scan）
   - 风险发现（full scan/filesort/temporary 等）
   - 表结构与索引证据
   - 优化建议（索引与 SQL 改写方向）

## 脚本能力说明

- 自动运行 `EXPLAIN FORMAT=JSON`
- 自动从执行计划抽取涉及表
- 自动读取表列定义与索引（`information_schema` + `SHOW CREATE TABLE`）
- 自动按规则输出风险与建议

## 参考文件

- 规则说明：`./backend/skills/mysql-sql-analyzer/references/rules.md`
- 环境变量说明：`./backend/skills/mysql-sql-analyzer/references/env-vars.md`
