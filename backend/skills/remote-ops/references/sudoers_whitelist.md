# agent-ops 用户 Sudoers 白名单

以下是 `agent-ops` 用户可以免密 `sudo` 执行的命令清单。

> 💡 将以下内容添加到远程服务器的 `/etc/sudoers.d/agent-ops`（使用 `visudo -f /etc/sudoers.d/agent-ops`）

## Sudoers 配置文件

```sudoers
# /etc/sudoers.d/agent-ops
# agent-ops 用户 — AI Agent 运维专用，免密 sudo 白名单

# ─── 服务管理 ───
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart php-fpm
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx

# ─── 日志查看 ───
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/tail /var/log/*
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/cat /var/log/*
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/head /var/log/*
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/less /var/log/*
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/grep * /var/log/*

# ─── 系统状态 ───
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/df *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/du *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/free *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/top -bn1
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/iostat *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/vmstat *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/sar *
agent-ops ALL=(ALL) NOPASSWD: /usr/sbin/ss *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/netstat *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/lsof *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/ps *

# ─── Kubernetes ───
agent-ops ALL=(ALL) NOPASSWD: /usr/local/bin/kubectl get *
agent-ops ALL=(ALL) NOPASSWD: /usr/local/bin/kubectl describe *
agent-ops ALL=(ALL) NOPASSWD: /usr/local/bin/kubectl logs *
agent-ops ALL=(ALL) NOPASSWD: /usr/local/bin/kubectl top *
agent-ops ALL=(ALL) NOPASSWD: /usr/local/bin/kubectl exec *

# ─── Docker ───
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/docker ps *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/docker logs *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/docker inspect *
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/docker stats --no-stream *

# ─── Nginx 配置检查 ───
agent-ops ALL=(ALL) NOPASSWD: /usr/sbin/nginx -t
agent-ops ALL=(ALL) NOPASSWD: /usr/bin/cat /etc/nginx/*
```

## 命令分类速查

| 分类 | 可用命令 | 用途 |
|------|---------|------|
| 服务管理 | `systemctl status/restart/reload` | 查看和重启 Nginx、PHP-FPM |
| 日志 | `journalctl`, `tail`, `cat`, `grep` | 查看系统和应用日志 |
| 系统状态 | `df`, `du`, `free`, `top`, `iostat` | 磁盘、内存、CPU 监控 |
| 网络 | `ss`, `netstat`, `lsof` | 端口和连接排查 |
| 进程 | `ps` | 进程列表 |
| K8s | `kubectl get/describe/logs/top/exec` | Pod 状态和日志 |
| Docker | `docker ps/logs/inspect/stats` | 容器状态 |
| Nginx | `nginx -t`, `cat /etc/nginx/*` | 配置检测 |

## 安装方法

```bash
# 在远程服务器上执行
sudo visudo -f /etc/sudoers.d/agent-ops
# 粘贴上面的 sudoers 配置内容，保存退出

# 验证语法
sudo visudo -c

# 测试
su - agent-ops
sudo systemctl status nginx   # 应免密成功
sudo rm -rf /tmp/test          # 应被拒绝
```

## 注意事项

- 根据实际需要增减命令，**最小权限原则**
- `systemctl restart` 只开放了 `nginx` 和 `php-fpm`，需要其他服务请手动添加
- kubectl 路径可能是 `/usr/bin/kubectl`，根据实际 `which kubectl` 调整
- 修改后用 `visudo -c` 验证语法，避免锁死 sudo
