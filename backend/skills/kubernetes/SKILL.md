---
name: kubernetes
description: "基于 kubectl 和 ./skills/kubernetes 下 kubeconfig 的 Kubernetes 排障技能。当用户使用自然语言（中文或英文）询问 pod/deployment/service/ingress 状态、logs/events、rollout、调度失败、CrashLoopBackOff、ImagePullBackOff、Pending、连通性或其他集群诊断问题时使用。"
---

# Kubernetes 排障技能

使用此技能通过命令驱动的方式解决 Kubernetes 问题。

## 运行约束

- 默认使用 `/usr/local/bin/kubectl`。
- 默认从 `./skills/kubernetes/` 目录读取 kubeconfig。
- 除非用户明确要求并确认，否则仅执行只读操作。
- 回答中禁止输出 kubeconfig 敏感信息（token、key、cert data）。

## Kubeconfig 发现顺序

按以下顺序解析 kubeconfig：

1. 用户显式提供的路径
2. `./skills/kubernetes/kubeconfig`
3. `./skills/kubernetes/kubeconfig.yaml`
4. `./skills/kubernetes/.kubeconfig`
5. `./skills/kubeconfig`（兼容旧路径）
6. `./skills/kubeconfig.yaml`（兼容旧路径）
7. `./skills/.kubeconfig`（兼容旧路径）

如果都不存在，要求用户将 kubeconfig 放到 `./skills/kubernetes/` 目录。

## 标准工作流

1. 先校验工具与目标：
   - `test -x /usr/local/bin/kubectl`
   - `test -f <kubeconfig_path>`
   - `/usr/local/bin/kubectl --kubeconfig <kubeconfig_path> config get-contexts`
   - `/usr/local/bin/kubectl --kubeconfig <kubeconfig_path> config current-context`
2. 深入排查前先跑基线诊断：
   - `/usr/local/bin/kubectl --kubeconfig <kubeconfig_path> get nodes -o wide`
   - `/usr/local/bin/kubectl --kubeconfig <kubeconfig_path> get ns`
   - `/usr/local/bin/kubectl --kubeconfig <kubeconfig_path> get pods -A -o wide`
3. 根据用户问题选择排障分支：
   - 工作负载分支：pod/deployment/statefulset/daemonset
   - 网络分支：service/endpoints/ingress
   - 发布分支：deployment 历史与 rollout 状态
   - 资源分支：quota、limits、调度与 Pending
4. 用证据化结构输出结论：
   - 诊断结论
   - 已执行命令
   - 输出中的关键证据
   - 下一步建议

## 推荐脚本

当问题范围较大或描述不清时，先执行只读快速诊断：

```bash
bash ./skills/kubernetes/scripts/k8s_readonly_diagnose.sh [kubeconfig_path] [namespace] [resource]
```

## 常见命令模式

在以下场景读取 `./skills/kubernetes/references/troubleshooting.md`：

- 用户报告特定故障（`CrashLoopBackOff`、`ImagePullBackOff`、`Pending`、`OOMKilled`）
- 需要按分支执行更细的命令集（service 连通性、ingress、rollout）
- 在给出修复建议前需要一份简明检查清单

## 写操作护栏

对于 `apply`、`delete`、`patch`、`scale`、`rollout restart` 或任何修改性操作：

1. 先说明计划执行的命令和预期影响。
2. 明确要求用户确认。
3. 仅在确认后执行。
4. 返回执行结果，并在需要时给出回滚选项。
