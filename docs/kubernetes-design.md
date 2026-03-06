# Kubernetes 排障技能设计说明

## 概述

利用 kubectl 命令行工具排障，Skill 定义标准排障工作流和命令模板，Agent 按流程逐步执行和分析。

## 架构

```
用户："payment-service 这个 Pod 为什么一直重启"
  → Agent 加载 kubeconfig
  → 先跑基线诊断（nodes → pods → events）
  → 按问题分支深入（CrashLoopBackOff → logs → describe）
  → 给出诊断结论和修复建议
```

## 设计要点

- **Kubeconfig 自动发现**：按 7 个候选路径依次查找，用户无需手动指定
- **分层诊断流程**：先基线（集群全貌），再按问题类型分支深入
- **四大排障分支**：
  - 工作负载：Pod / Deployment / StatefulSet / DaemonSet
  - 网络：Service / Endpoints / Ingress
  - 发布：Rollout 历史与状态
  - 资源：Quota / Limits / 调度 / Pending
- **写操作护栏**：apply、delete、scale 等修改操作必须先说明影响、用户确认后才执行
- **参考文档驱动**：遇到特定故障模式时自动读取 `troubleshooting.md` 获取检查清单

## 目录结构

```
backend/skills/kubernetes/
├── SKILL.md                      # 技能指令
├── kubeconfig                    # kubeconfig 文件（.gitignore 排除）
├── scripts/
│   └── k8s_readonly_diagnose.sh  # 只读快速诊断脚本
└── references/
    └── troubleshooting.md        # 常见故障排查手册
```
