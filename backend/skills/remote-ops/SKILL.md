---
name: remote-ops
description: 通过 SSH 在远程服务器上执行运维命令，排查和解决线上问题
---

# Remote-Ops：远程服务器运维技能

## 概述

你具备通过 SSH 连接远程服务器并执行运维命令的能力。你可以帮助用户排查线上问题、查看服务状态、分析日志等。

## 连接方式

使用项目内置的 SSH 私钥连接远程服务器：

```bash
ssh -i ./skills/remote-ops/keys/agent_ops_key -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p <PORT> agent-ops@<HOST> "<COMMAND>"
```

### 端口策略

> ⚠️ SSH 端口**不一定是 22**！请按以下顺序尝试：
>
> 1. **优先使用 65300 端口**：`-p 65300`
> 2. 如果 65300 连接超时或拒绝，**回退到 22 端口**：`-p 22`

### 参数说明

- **秘钥路径**：`./skills/remote-ops/keys/agent_ops_key`（相对于 backend 工作目录）
- **用户名**：`agent-ops`（非 root 受限用户）
- **超时**：10 秒连接超时，避免卡死

## 主机清单

> ⚠️ 请用户在使用前告知要操作的服务器 IP 或主机名。

## 权限模型

`agent-ops` 是非 root 用户，部分命令需要 `sudo` 提权。**只有白名单内的命令可以免密 sudo**。

### ⚠️ 强制前置步骤

> **在你第一次使用 `sudo` 之前，必须先读取 sudoers 白名单文件：**
>
> ```bash
> cat ./skills/remote-ops/references/sudoers_whitelist.md
> ```
>
> 阅读后你才能知道哪些命令可以 `sudo`。**未在白名单中的命令一律不要加 `sudo`**，否则会被系统拒绝。
> 每次会话只需读取一次，记住内容即可。

### 使用 sudo 的方式

```bash
ssh -i ./skills/remote-ops/keys/agent_ops_key -p <PORT> agent-ops@<HOST> "sudo systemctl status nginx"
```

## 安全约束 ⛔

你**必须**遵守以下安全规则：

1. **绝对禁止**执行以下命令：
   - `rm -rf /` 或任何大范围删除
   - `shutdown`、`reboot`、`halt`、`poweroff`
   - `mkfs`、`fdisk`、`dd`（磁盘操作）
   - `chmod 777`、`chown root` 等权限篡改
   - 任何下载并执行远程脚本（如 `curl | bash`）

2. **谨慎操作**：
   - `systemctl restart` — 仅在用户明确要求时执行
   - `kill` / `pkill` — 需要用户确认进程名
   - 文件修改 — 先备份再修改

3. **操作原则**：
   - 优先使用**只读命令**排查问题（`cat`、`tail`、`grep`、`df`、`free`、`top`）
   - 每一步操作前向用户说明意图
   - 修改操作前先展示当前状态

