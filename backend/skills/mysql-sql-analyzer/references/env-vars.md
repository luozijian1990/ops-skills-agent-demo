# 环境变量说明

## 必需

- `MYSQL_USER`
- `MYSQL_PASSWORD`

连接目标由命令参数提供：`--host`、`--port`、`--database`。

## 可选

- `MYSQL_CHARSET`（默认 `utf8mb4`）
- `MYSQL_CONNECT_TIMEOUT`（默认 `5`）

## 安全建议

- 使用只读账号（最少权限：`SELECT`、`SHOW VIEW`、`PROCESS` 可按需）。
- 禁止把密码写进命令行，优先使用 `.env` 或安全注入环境变量。
- 多实例场景可复用同一个只读账号，仅切换 `--host/--port/--database`。
