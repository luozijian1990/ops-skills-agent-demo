# MySQL SQL Analyzer 设计说明

## 概述

对单条 SQL 进行执行计划分析，自动读取涉及表的结构和索引，识别全表扫描、filesort、临时表等性能风险，给出索引优化和 SQL 改写建议。**全程只读，不执行原 SQL**。

## 架构

```
用户："帮我看下这条 SQL 为什么慢"
  → Agent 提取 SQL + 目标数据库信息
  → 调用 analyze_mysql_sql.py 脚本
  → 脚本执行 EXPLAIN FORMAT=JSON
  → 自动提取涉及表，查 information_schema 获取表结构/索引
  → 按规则引擎输出风险和建议
  → Agent 解读结果，给出优化方案
```

## 设计要点

- **纯只读分析**：仅执行 `EXPLAIN`、`SHOW`、`information_schema` 查询，禁止执行原 SQL（特别是 DML）
- **凭据与连接分离**：`host`/`port`/`database` 由用户输入提供，`MYSQL_USER`/`MYSQL_PASSWORD` 通过环境变量注入，回答中禁止回显密码
- **自动化程度高**：脚本自动完成"执行计划 → 提取涉及表 → 读表结构索引 → 规则匹配 → 输出建议"全流程
- **EXPLAIN ANALYZE 可选**：默认不执行（避免额外开销），仅在用户明确要求时通过 `--explain-analyze` 启用
- **多输出格式**：支持 `markdown`（人类阅读）和 `json`（程序消费）
- **环境变量自动加载**：与其他 Skill 一致的 `.env` 搜索链

## 风险识别规则

脚本内置规则引擎，自动检测以下性能风险：

| 风险项 | 检测方式 |
|--------|---------|
| 全表扫描 | access_type = ALL |
| 文件排序 | using_filesort = true |
| 临时表 | using_temporary_table = true |
| 无索引命中 | possible_keys 为空 |
| 大范围扫描 | rows 估算值过大 |

详细规则见 `references/rules.md`。

## 目录结构

```
backend/skills/mysql-sql-analyzer/
├── SKILL.md                        # 技能指令
├── scripts/
│   └── analyze_mysql_sql.py        # 分析脚本
└── references/
    ├── rules.md                    # 风险识别规则说明
    └── env-vars.md                 # 环境变量说明
```

## 输出规范

Agent 的分析回答必须包含：

1. **执行计划摘要**：访问类型、命中索引、预估扫描行数
2. **风险发现**：全表扫描 / filesort / 临时表等
3. **表结构与索引证据**：涉及表的列定义和现有索引
4. **优化建议**：推荐创建的索引、SQL 改写方向
