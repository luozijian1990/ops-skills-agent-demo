# Remote-Ops SSH Skill 设计文档

## 设计思路

让 AI Agent 具备**远程服务器运维能力**，通过 SSH 连接目标服务器并执行命令，实现自动化故障排查和运维操作。

### 核心理念

> Agent 不需要写 Python 代码来远程执行命令 —— 只需要教会它"用 SSH"就行。

本项目的 Agent 本身已有 shell 执行能力（`execute` 工具），SSH 本质上就是"远程 shell"，因此只需要一个 **Skill（Markdown 指令文件）** 来告诉 Agent 如何使用 SSH 连接远程服务器，而不需要开发任何新的代码或 API。

## 架构图

```
┌──────────────┐   WebSocket    ┌───────────────┐    SSH       ┌──────────────────┐
│   Frontend   │ ◄────────────► │  Backend Agent │ ─────────►  │  Remote Server   │
│  (Vue 3)     │   streaming    │  (DeepAgents)  │  port 65300  │  (agent-ops)     │
└──────────────┘                │                │  or 22       │                  │
                                │  execute(      │              │  sudo whitelist  │
                                │   "ssh ..."    │  ◄─────────  │  only!           │
                                │  )             │   stdout     │                  │
                                └───────────────┘              └──────────────────┘
```

## 三层安全模型

```
┌─────────────────────────────────────────────────┐
│  Layer 1: LLM 层（SKILL.md 安全约束）            │
│  • 禁止危险命令（rm -rf, shutdown 等）            │
│  • 修改前先备份，优先只读命令                       │
│  • 每步操作前向用户说明意图                         │
├─────────────────────────────────────────────────┤
│  Layer 2: OS 用户层（agent-ops 非 root）          │
│  • SSH 登录为普通用户，无特权                      │
│  • 不带 sudo 只能执行普通操作                      │
├─────────────────────────────────────────────────┤
│  Layer 3: Sudoers 白名单                         │
│  • /etc/sudoers.d/agent-ops 精确列出允许的命令     │
│  • 即使 Agent "犯错"，OS 也会 permission denied   │
│  • 最后一道防线，硬性拦截                          │
└─────────────────────────────────────────────────┘
```

## 目录结构

```
backend/skills/remote-ops/
├── SKILL.md                            # 技能描述（Agent 读取此文件获取能力）
├── .gitignore                          # 排除 keys/ 防止秘钥入库
├── keys/
│   ├── agent_ops_key                   # Ed25519 SSH 私钥（600 权限）
│   └── agent_ops_key.pub              # 对应公钥（部署到远程服务器）
└── references/
    └── sudoers_whitelist.md           # sudoers 免密命令白名单文档
```

## 快速部署

### 1. 生成 SSH 秘钥

```bash
ssh-keygen -t ed25519 -C "agent-ops" -f ~/.ssh/agent_ops_key -N ""
cp ~/.ssh/agent_ops_key* backend/skills/remote-ops/keys/
chmod 600 backend/skills/remote-ops/keys/agent_ops_key
```

### 2. 远程服务器配置

```bash
# 创建专用用户
useradd -m -s /bin/bash agent-ops

# 部署公钥
su - agent-ops
mkdir -p ~/.ssh && chmod 700 ~/.ssh
vim ~/.ssh/authorized_keys   # 粘贴 agent_ops_key.pub 内容
chmod 600 ~/.ssh/authorized_keys

# 配置 sudoers 白名单
sudo visudo -f /etc/sudoers.d/agent-ops
# 参考 references/sudoers_whitelist.md 中的配置
```

### 3. 验证连接

```bash
ssh -i backend/skills/remote-ops/keys/agent_ops_key -p 65300 agent-ops@<SERVER_IP> "hostname"
```

### 4. 重启后端

Agent 会自动加载 `skills/remote-ops/` 目录下的 SKILL.md，获得远程运维能力。

## Agent 使用方式

直接用自然语言描述你的运维需求：

- "帮我看下 10.0.0.1 这台机器的磁盘使用情况"
- "检查一下 prod-web-01 的 Nginx 状态和最近的错误日志"
- "排查下 K8s 集群里 payment-service 这个 Pod 为什么一直重启"

Agent 会自动 SSH 到目标服务器，逐步执行命令，分析输出，给出诊断结论。

## 为什么不用 HTTP Agent？

| 对比 | SSH Skill | HTTP Agent（mTLS） |
|------|----------|-------------------|
| 开发量 | 零代码，只写 Markdown | 需要新服务 + 证书体系 |
| 远程改动 | 仅需创建用户 + 部署公钥 | 需部署 Agent 进程 |
| 多主机 | 天然支持 `ssh user@host` | 每台主机部署服务 |
| 安全性 | sudoers 硬限制 | API 层面限制 |
| 维护成本 | 几乎为零 | 证书续期 + 服务监控 |

SSH Skill 方案足够满足绝大多数运维场景，当需要企业级审计或多团队权限隔离时再考虑 HTTP Agent。
