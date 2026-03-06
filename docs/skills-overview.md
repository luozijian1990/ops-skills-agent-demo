# Skills 设计文档索引

本项目的 Agent 通过 **Markdown 零代码技能文件** 获取能力。每个 Skill 是一个独立目录，包含 `SKILL.md` 指令、可选的脚本和参考资料。

> 💡 所有 Skill 均可通过 [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) 自动生成。

## 技能设计文档

| 技能 | 用途 | 设计文档 |
|------|------|---------|
| remote-ops | SSH 远程服务器运维 | [remote-ops-design.md](remote-ops-design.md) |
| nginx-es-analyzer | Nginx 日志异常分析 | [nginx-es-analyzer-design.md](nginx-es-analyzer-design.md) |
| kubernetes | K8s 集群排障 | [kubernetes-design.md](kubernetes-design.md) |
| docker | Docker 容器排障 | [docker-design.md](docker-design.md) |
| mysql-sql-analyzer | MySQL SQL 执行计划分析 | [mysql-sql-analyzer-design.md](mysql-sql-analyzer-design.md) |
| shell_command / file_reader / code_explainer | 基础内置能力 | [builtin-skills-design.md](builtin-skills-design.md) |

## 添加新 Skill

```bash
mkdir -p backend/skills/my-skill/references
# 编写 backend/skills/my-skill/SKILL.md
# 重启后端，自动加载
```
