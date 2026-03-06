# Docker 远程排障参考

用于在完成基线巡检后，针对具体故障继续深入。

## 1. 容器反复重启（Restarting）

```bash
/usr/local/bin/docker -H <remote> ps -a
/usr/local/bin/docker -H <remote> inspect <container>
/usr/local/bin/docker -H <remote> logs --tail 300 <container>
```

重点关注：

- `State.Restarting`、`State.ExitCode`、`State.OOMKilled`
- 应用启动参数、环境变量缺失
- 健康检查失败导致重启

## 2. 容器已退出（Exited）

```bash
/usr/local/bin/docker -H <remote> ps -a --filter "status=exited"
/usr/local/bin/docker -H <remote> inspect <container>
/usr/local/bin/docker -H <remote> logs --tail 300 <container>
```

重点关注退出码：

- `137`：常见为 OOM 或被强制终止
- `139`：常见为段错误
- `1`：应用启动失败或配置错误

## 3. 端口映射存在但服务不可达

```bash
/usr/local/bin/docker -H <remote> ps
/usr/local/bin/docker -H <remote> inspect <container>
/usr/local/bin/docker -H <remote> port <container>
```

重点检查：

- 容器内服务是否监听 `0.0.0.0` 而非 `127.0.0.1`
- `HostConfig.PortBindings` 与应用实际监听端口是否一致
- 宿主机防火墙/安全组是否开放对应端口

## 4. 镜像异常（拉取失败、镜像过大）

```bash
/usr/local/bin/docker -H <remote> images --digests
/usr/local/bin/docker -H <remote> inspect <image>
/usr/local/bin/docker -H <remote> history <image>
```

重点检查：

- 镜像 tag 是否存在、是否拼写错误
- 镜像层是否异常膨胀（大文件、缓存未清理）
- 私有仓库认证是否正确

## 5. docker compose 服务异常

如果当前工作目录存在 compose 文件，可执行：

```bash
/usr/local/bin/docker compose ps
/usr/local/bin/docker compose logs --tail 300 <service>
/usr/local/bin/docker compose config
```

重点检查：

- 环境变量是否注入
- 依赖服务是否已就绪
- 配置合并结果是否符合预期

## 6. 资源压力（CPU/内存）

```bash
/usr/local/bin/docker -H <remote> stats --no-stream
/usr/local/bin/docker -H <remote> inspect <container>
```

重点检查：

- 内存使用是否接近上限
- 是否设置了不合理的 CPU/内存限制
- 是否存在单容器资源突增
