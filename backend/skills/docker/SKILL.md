---
name: docker
description: "基于 /usr/local/bin/docker 连接远程 Docker 管理端口进行容器排障与状态诊断。当用户询问容器启动失败、反复重启、日志报错、端口不通、镜像或资源异常、docker compose 服务状态等问题时使用。"
---

# Docker 远程排障技能

使用此技能通过 Docker CLI 连接远程 Docker Engine 管理端口，执行诊断与排障。

## 运行约束

- 固定使用 `/usr/local/bin/docker`。
- 优先使用只读命令进行诊断。
- `rm`、`rmi`、`stop`、`restart`、`kill`、`compose down` 等修改性操作必须先确认。
- 禁止在回答中输出敏感凭据（认证 token、私有 registry 密码、证书私钥内容）。

## 远程连接信息来源

按以下顺序解析远程端点：

1. 用户显式提供的远程地址（如 `tcp://10.0.0.8:2375` 或 `10.0.0.8:2375`）
2. 环境变量 `DOCKER_HOST`
3. `./skills/docker/endpoint` 文件首行

如果地址不带协议（例如 `10.0.0.8:2375`），自动补全为 `tcp://10.0.0.8:2375`。

如果远程服务启用了 TLS：

- 使用 `DOCKER_TLS_VERIFY=1`
- 使用 `DOCKER_CERT_PATH=<cert目录>`

## 标准工作流

1. 校验 Docker CLI 可用：
   - `test -x /usr/local/bin/docker`
2. 校验远程端点可用：
   - `/usr/local/bin/docker -H <remote> version`
   - `/usr/local/bin/docker -H <remote> info`
3. 执行基线只读巡检：
   - `/usr/local/bin/docker -H <remote> ps -a`
   - `/usr/local/bin/docker -H <remote> images`
   - `/usr/local/bin/docker -H <remote> network ls`
   - `/usr/local/bin/docker -H <remote> volume ls`
   - `/usr/local/bin/docker -H <remote> stats --no-stream`
4. 针对目标容器深入分析（若用户给了容器名/ID）：
   - `/usr/local/bin/docker -H <remote> inspect <container>`
   - `/usr/local/bin/docker -H <remote> logs --tail <n> <container>`
   - `/usr/local/bin/docker -H <remote> top <container>`
5. 用证据化结构回答：
   - 诊断结论
   - 已执行命令
   - 关键证据
   - 建议操作（涉及写操作时先确认）

## 推荐脚本

当问题描述较宽泛时，先执行只读诊断脚本：

```bash
bash ./skills/docker/scripts/docker_readonly_diagnose.sh [remote_host_or_endpoint] [container] [log_lines]
```

示例：

```bash
bash ./skills/docker/scripts/docker_readonly_diagnose.sh 10.0.0.8:2375
bash ./skills/docker/scripts/docker_readonly_diagnose.sh tcp://10.0.0.8:2375 demo-agent-backend 300
```

## 参考资料

在以下情况读取 `./skills/docker/references/troubleshooting.md`：

- 容器状态为 `Restarting`、`Exited`、`OOMKilled`
- 端口映射存在但服务不可达
- 镜像拉取失败或镜像层异常膨胀
- 需要给出 compose 相关排障命令

## 写操作护栏

对于修改性操作（例如 `docker restart`、`docker rm`、`docker compose down`）：

1. 先说明具体命令与影响范围。
2. 要求用户明确确认。
3. 仅在确认后执行。
4. 返回执行结果，并给出回滚或恢复建议。
