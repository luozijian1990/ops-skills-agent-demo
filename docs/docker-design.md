# Docker 远程排障技能设计说明

## 概述

通过 Docker CLI 的 `-H` 参数连接远程 Docker Engine 管理端口，实现远程容器诊断，无需在目标机器上部署额外服务。

## 架构

```
用户："帮我看下 10.0.0.8 上的容器状态"
  → Agent 解析远程端点（tcp://10.0.0.8:2375）
  → docker -H <remote> ps -a （基线巡检）
  → docker -H <remote> logs / inspect（深入分析）
  → 给出诊断结论和建议
```

## 设计要点

- **远程端点发现**：用户提供 > 环境变量 `DOCKER_HOST` > `endpoint` 文件，三级降级
- **协议自动补全**：`10.0.0.8:2375` 自动补为 `tcp://10.0.0.8:2375`
- **TLS 支持**：通过 `DOCKER_TLS_VERIFY` 和 `DOCKER_CERT_PATH` 配置安全连接
- **只读优先**：基线巡检全部使用只读命令（`ps`、`logs`、`inspect`、`stats`）
- **写操作护栏**：`restart`、`rm`、`compose down` 等操作必须用户确认
- **快速诊断脚本**：问题描述不清时先跑 `docker_readonly_diagnose.sh` 全面巡检

## 目录结构

```
backend/skills/docker/
├── SKILL.md                          # 技能指令
├── endpoint                          # 远程端点配置（可选）
├── scripts/
│   └── docker_readonly_diagnose.sh   # 只读诊断脚本
└── references/
    └── troubleshooting.md            # 常见故障排查手册
```
