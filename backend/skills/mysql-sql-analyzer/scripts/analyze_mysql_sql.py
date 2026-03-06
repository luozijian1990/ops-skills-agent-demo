#!/usr/bin/env python3
"""MySQL SQL 执行计划分析脚本。

功能：
1. 读取完整 SQL（命令行或文件）
2. 使用 EXPLAIN FORMAT=JSON 分析执行计划
3. 自动识别涉及表并读取列定义与索引信息
4. 按规则输出风险点与优化建议

安全约束：
- 只执行 EXPLAIN/SHOW/INFORMATION_SCHEMA 查询，不执行原 SQL。
- 用户名和密码来自环境变量；host/port/database 由参数传入。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, URL


def load_runtime_env() -> None:
    """自动加载 skill 相关 .env（不覆盖已存在环境变量）。"""
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    backend_root = Path(__file__).resolve().parents[3]
    cwd = Path.cwd()

    candidates = [
        cwd / "skills" / "mysql-sql-analyzer" / ".env",
        cwd / "backend" / "skills" / "mysql-sql-analyzer" / ".env",
        cwd / ".env",
        cwd / "backend" / ".env",
        backend_root / "skills" / "mysql-sql-analyzer" / ".env",
        backend_root / ".env",
    ]

    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            load_dotenv(path, override=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MySQL SQL 执行计划分析器")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sql", help="完整 SQL（单条语句）")
    group.add_argument("--sql-file", help="SQL 文件路径（单条语句）")

    parser.add_argument("--host", required=True, help="MySQL 地址")
    parser.add_argument("--port", type=int, default=3306, help="MySQL 端口，默认 3306")
    parser.add_argument("--database", required=True, help="目标数据库名")
    parser.add_argument(
        "--schema",
        default="",
        help="用于读取元数据的 schema，默认使用 --database",
    )
    parser.add_argument(
        "--explain-analyze",
        action="store_true",
        help="额外执行 EXPLAIN ANALYZE（MySQL 8.0.18+，仅建议受控环境）",
    )
    parser.add_argument(
        "--output",
        choices=("markdown", "json"),
        default="markdown",
        help="输出格式，默认 markdown",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="JSON 输出时进行格式化（默认紧凑输出）",
    )
    return parser.parse_args()


def build_engine(args: argparse.Namespace):
    connect_timeout = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "5"))
    user = os.getenv("MYSQL_USER", "").strip()
    password = os.getenv("MYSQL_PASSWORD", "")
    charset = os.getenv("MYSQL_CHARSET", "utf8mb4").strip()

    if not user:
        raise RuntimeError(
            "缺少环境变量 MYSQL_USER。请通过环境变量注入只读账号。"
        )

    url = URL.create(
        drivername="mysql+pymysql",
        username=user,
        password=password,
        host=args.host,
        port=args.port,
        database=args.database,
        query={"charset": charset},
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": connect_timeout},
    )


def read_sql(args: argparse.Namespace) -> str:
    if args.sql:
        raw = args.sql
    else:
        path = Path(args.sql_file).resolve()
        if not path.exists():
            raise RuntimeError(f"SQL 文件不存在: {path}")
        raw = path.read_text(encoding="utf-8")
    return normalize_sql(raw)


def normalize_sql(raw_sql: str) -> str:
    sql = raw_sql.strip()
    if not sql:
        raise RuntimeError("SQL 为空")

    while sql.endswith(";"):
        sql = sql[:-1].rstrip()

    # 第一版仅支持单语句，避免误分析。
    if ";" in sql:
        raise RuntimeError("仅支持单条 SQL 语句，请移除多语句输入。")

    return sql


def detect_statement_type(sql: str) -> str:
    tokens = re.findall(r"[A-Za-z_]+", sql.upper())
    if not tokens:
        return "UNKNOWN"

    first = tokens[0]
    if first != "WITH":
        return first

    for token in tokens[1:]:
        if token in {"SELECT", "UPDATE", "DELETE", "INSERT", "REPLACE"}:
            return token
    return "WITH"


def get_current_database(conn: Connection) -> str:
    value = conn.exec_driver_sql("SELECT DATABASE()").scalar()
    return str(value) if value else ""


def explain_json(conn: Connection, sql: str) -> dict[str, Any]:
    rows = conn.exec_driver_sql(f"EXPLAIN FORMAT=JSON {sql}").mappings().all()
    if not rows:
        raise RuntimeError("EXPLAIN FORMAT=JSON 未返回结果")

    row = rows[0]
    raw = row.get("EXPLAIN")
    if raw is None and row:
        raw = next(iter(row.values()))

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")

    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, dict):
        return raw
    raise RuntimeError("无法解析 EXPLAIN FORMAT=JSON 输出")


def explain_analyze(conn: Connection, sql: str) -> dict[str, Any]:
    try:
        rows = conn.exec_driver_sql(f"EXPLAIN ANALYZE {sql}").all()
    except Exception as exc:
        return {
            "supported": False,
            "error": str(exc),
        }

    lines: list[str] = []
    for row in rows:
        if len(row) == 1:
            lines.append(str(row[0]))
        else:
            lines.append(" | ".join(str(item) for item in row))

    return {
        "supported": True,
        "text": "\n".join(lines).strip(),
    }


def to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value)]


def collect_plan_tables(node: Any, output: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if "table_name" in node:
            output.append(
                {
                    "database_name": node.get("database_name"),
                    "table_name": node.get("table_name"),
                    "access_type": node.get("access_type"),
                    "possible_keys": to_list(node.get("possible_keys")),
                    "key": node.get("key"),
                    "used_key_parts": to_list(node.get("used_key_parts")),
                    "rows_examined_per_scan": node.get("rows_examined_per_scan"),
                    "rows_produced_per_join": node.get("rows_produced_per_join"),
                    "filtered": node.get("filtered"),
                    "using_temporary_table": bool(node.get("using_temporary_table", False)),
                    "using_filesort": bool(node.get("using_filesort", False)),
                    "attached_condition": node.get("attached_condition"),
                }
            )
        for value in node.values():
            collect_plan_tables(value, output)
        return

    if isinstance(node, list):
        for item in node:
            collect_plan_tables(item, output)


def quote_ident(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


def fetch_columns(conn: Connection, schema: str, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                COLUMN_NAME,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                EXTRA
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
            ORDER BY ORDINAL_POSITION
            """
        ),
        {"schema": schema, "table": table},
    ).mappings()
    return [
        {
            "column_name": row["COLUMN_NAME"],
            "column_type": row["COLUMN_TYPE"],
            "is_nullable": row["IS_NULLABLE"],
            "column_key": row["COLUMN_KEY"],
            "extra": row["EXTRA"],
        }
        for row in rows
    ]


def fetch_indexes(conn: Connection, schema: str, table: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT
                INDEX_NAME,
                NON_UNIQUE,
                SEQ_IN_INDEX,
                COLUMN_NAME,
                COLLATION,
                CARDINALITY,
                SUB_PART,
                NULLABLE,
                INDEX_TYPE
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = :schema AND TABLE_NAME = :table
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """
        ),
        {"schema": schema, "table": table},
    ).mappings()
    return [
        {
            "index_name": row["INDEX_NAME"],
            "non_unique": row["NON_UNIQUE"],
            "seq_in_index": row["SEQ_IN_INDEX"],
            "column_name": row["COLUMN_NAME"],
            "collation": row["COLLATION"],
            "cardinality": row["CARDINALITY"],
            "sub_part": row["SUB_PART"],
            "nullable": row["NULLABLE"],
            "index_type": row["INDEX_TYPE"],
        }
        for row in rows
    ]


def fetch_create_table(conn: Connection, schema: str, table: str) -> str:
    sql = f"SHOW CREATE TABLE {quote_ident(schema)}.{quote_ident(table)}"
    row = conn.exec_driver_sql(sql).mappings().first()
    if not row:
        return ""
    for key, value in row.items():
        if "create" in str(key).lower():
            return str(value)
    return ""


def normalize_table_refs(plan_tables: list[dict[str, Any]], default_schema: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in plan_tables:
        table = str(item.get("table_name") or "").strip()
        if not table:
            continue
        # 跳过派生/临时结果节点
        if table.startswith("<") or table.upper().startswith("DERIVED"):
            continue

        schema = str(item.get("database_name") or default_schema).strip()
        if not schema:
            continue

        key = (schema, table)
        if key in seen:
            continue
        seen.add(key)
        refs.append({"schema": schema, "table": table})

    return refs


def table_label(item: dict[str, Any]) -> str:
    schema = str(item.get("database_name") or "").strip()
    table = str(item.get("table_name") or "").strip()
    if schema and table:
        return f"{schema}.{table}"
    return table or "<unknown>"


def add_finding(
    findings: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    rule_id: str,
    table: str,
    severity: str,
    message: str,
) -> None:
    key = (rule_id, table)
    if key in seen:
        return
    seen.add(key)
    findings.append(
        {
            "rule_id": rule_id,
            "table": table,
            "severity": severity,
            "message": message,
        }
    )


def build_findings(plan_tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for item in plan_tables:
        table = table_label(item)
        access_type = str(item.get("access_type") or "").upper()
        key_used = item.get("key")
        possible_keys = item.get("possible_keys") or []
        rows = item.get("rows_examined_per_scan")
        filtered = item.get("filtered")

        if access_type == "ALL":
            suffix = f"（估算 rows_examined_per_scan={rows}）" if rows is not None else ""
            add_finding(
                findings,
                seen,
                "full_table_scan",
                table,
                "high",
                f"{table} 使用 ALL 全表扫描 {suffix}".strip(),
            )

        if (not key_used) and possible_keys:
            add_finding(
                findings,
                seen,
                "index_not_chosen",
                table,
                "medium",
                f"{table} 存在 possible_keys={possible_keys} 但未命中索引",
            )

        if bool(item.get("using_filesort")):
            add_finding(
                findings,
                seen,
                "using_filesort",
                table,
                "medium",
                f"{table} 使用 filesort，ORDER BY 可能未命中合适索引",
            )

        if bool(item.get("using_temporary_table")):
            add_finding(
                findings,
                seen,
                "using_temporary_table",
                table,
                "medium",
                f"{table} 使用 temporary table，GROUP BY/ORDER BY 代价偏高",
            )

        if (
            isinstance(filtered, (int, float))
            and isinstance(rows, (int, float))
            and rows > 1000
            and filtered < 20
        ):
            add_finding(
                findings,
                seen,
                "low_filtered_ratio",
                table,
                "medium",
                f"{table} filtered={filtered}% 偏低，扫描后过滤成本较高",
            )

    return findings


def build_recommendations(findings: list[dict[str, Any]]) -> list[str]:
    if not findings:
        return ["未命中明显风险规则，建议结合业务 SLA 与慢日志继续观察。"]

    rules = {item["rule_id"] for item in findings}
    recommendations: list[str] = []

    if "full_table_scan" in rules or "index_not_chosen" in rules:
        recommendations.append(
            "检查 WHERE/JOIN 条件列是否存在可用索引，优先建立与过滤条件顺序匹配的联合索引。"
        )
        recommendations.append("确认条件列未被函数包裹、未发生隐式类型转换。")

    if "using_filesort" in rules or "using_temporary_table" in rules:
        recommendations.append(
            "检查 ORDER BY/GROUP BY 与索引顺序是否一致，必要时建立覆盖排序/分组的复合索引。"
        )

    if "low_filtered_ratio" in rules:
        recommendations.append("提升谓词选择性，减少大范围扫描后的二次过滤。")

    recommendations.append("在低峰期执行 ANALYZE TABLE 刷新统计信息后重新对比 EXPLAIN。")
    return recommendations


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# MySQL SQL 执行分析报告")
    lines.append("")
    lines.append("## SQL")
    lines.append("```sql")
    lines.append(report["sql"])
    lines.append("```")
    lines.append("")
    lines.append("## 执行计划摘要")

    plan_tables = report.get("plan_tables", [])
    if plan_tables:
        lines.append(
            "| 表 | 访问类型 | 命中索引 | possible_keys | rows/scan | filtered | filesort | temporary |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for item in plan_tables:
            label = table_label(item)
            access = str(item.get("access_type") or "-")
            key = str(item.get("key") or "-")
            possible = ", ".join(item.get("possible_keys") or []) or "-"
            rows = str(item.get("rows_examined_per_scan") or "-")
            filtered = str(item.get("filtered") or "-")
            filesort = "Y" if item.get("using_filesort") else "N"
            temporary = "Y" if item.get("using_temporary_table") else "N"
            lines.append(
                f"| `{label}` | `{access}` | `{key}` | `{possible}` | "
                f"`{rows}` | `{filtered}` | `{filesort}` | `{temporary}` |"
            )
    else:
        lines.append("未在 EXPLAIN JSON 中识别到基础表。")

    lines.append("")
    lines.append("## 主要发现")
    findings = report.get("findings", [])
    if findings:
        for item in findings:
            severity = str(item.get("severity", "info")).upper()
            lines.append(f"- [{severity}] {item.get('message')}")
    else:
        lines.append("- 未命中预置风险规则。")

    lines.append("")
    lines.append("## 建议动作")
    for item in report.get("recommendations", []):
        lines.append(f"- {item}")

    lines.append("")
    lines.append("## 表结构与索引")
    table_metadata = report.get("table_metadata", [])
    if not table_metadata:
        lines.append("未读取到表元数据。")
    for item in table_metadata:
        schema = item.get("schema")
        table = item.get("table")
        lines.append(f"### `{schema}.{table}`")
        lines.append("")
        lines.append("Columns:")
        lines.append("| 列 | 类型 | 可空 | 键 | 额外 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for col in item.get("columns", []):
            lines.append(
                f"| `{col['column_name']}` | `{col['column_type']}` | "
                f"`{col['is_nullable']}` | `{col['column_key'] or '-'}` | "
                f"`{col['extra'] or '-'}` |"
            )

        lines.append("")
        lines.append("Indexes:")
        lines.append("| 索引名 | 唯一 | 序号 | 列 | 基数 | 类型 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        indexes = item.get("indexes", [])
        if not indexes:
            lines.append("| `-` | `-` | `-` | `-` | `-` | `-` |")
        for idx in indexes:
            unique = "NO" if idx["non_unique"] else "YES"
            lines.append(
                f"| `{idx['index_name']}` | `{unique}` | `{idx['seq_in_index']}` | "
                f"`{idx['column_name']}` | `{idx['cardinality']}` | `{idx['index_type']}` |"
            )
        lines.append("")

    if report.get("explain_analyze"):
        analyze = report["explain_analyze"]
        lines.append("## EXPLAIN ANALYZE")
        if analyze.get("supported"):
            lines.append("```text")
            lines.append(analyze.get("text") or "")
            lines.append("```")
        else:
            lines.append(f"- EXPLAIN ANALYZE 执行失败：{analyze.get('error')}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_table_metadata(
    conn: Connection,
    refs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for ref in refs:
        schema = ref["schema"]
        table = ref["table"]
        try:
            columns = fetch_columns(conn, schema, table)
            indexes = fetch_indexes(conn, schema, table)
            ddl = fetch_create_table(conn, schema, table)
            output.append(
                {
                    "schema": schema,
                    "table": table,
                    "columns": columns,
                    "indexes": indexes,
                    "create_table_sql": ddl,
                }
            )
        except Exception as exc:
            output.append(
                {
                    "schema": schema,
                    "table": table,
                    "error": str(exc),
                    "columns": [],
                    "indexes": [],
                }
            )
    return output


def main() -> int:
    load_runtime_env()
    args = parse_args()

    try:
        sql = read_sql(args)
        statement_type = detect_statement_type(sql)
        engine = build_engine(args)

        with engine.connect() as conn:
            current_db = get_current_database(conn)
            metadata_schema = (args.schema or current_db or args.database).strip()

            if not metadata_schema:
                raise RuntimeError("无法确定 schema，请通过 --schema 或 --database 指定。")

            explain = explain_json(conn, sql)

            plan_tables: list[dict[str, Any]] = []
            collect_plan_tables(explain, plan_tables)

            refs = normalize_table_refs(plan_tables, metadata_schema)
            table_metadata = build_table_metadata(conn, refs)
            findings = build_findings(plan_tables)
            recommendations = build_recommendations(findings)

            analyze_output = None
            if args.explain_analyze:
                analyze_output = explain_analyze(conn, sql)

        report = {
            "statement_type": statement_type,
            "database": current_db,
            "schema_for_metadata": metadata_schema,
            "sql": sql,
            "plan_tables": plan_tables,
            "findings": findings,
            "recommendations": recommendations,
            "table_metadata": table_metadata,
            "explain_json": explain,
            "explain_analyze": analyze_output,
        }

        if args.output == "json":
            if args.pretty:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(report, ensure_ascii=False))
        else:
            print(render_markdown(report), end="")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
