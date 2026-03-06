---
name: shell_command
description: "执行本地 shell 命令并返回输出。仅允许安全的只读命令（如 ls、cat、grep 等）。"
parameters:
  properties:
    command:
      type: string
      description: "要执行的 shell 命令，例如 'ls -la /tmp' 或 'cat /etc/hosts'"
  required:
    - command
---

# Shell 命令执行器

你可以使用这个工具来执行本地 shell 命令，帮助用户查看系统信息、文件列表等。

## 安全限制

仅允许以下只读命令：

- `ls`, `cat`, `head`, `tail` — 查看文件
- `grep`, `find`, `wc` — 搜索和统计
- `pwd`, `echo`, `date`, `whoami` — 系统信息
- `df`, `du`, `ps` — 资源信息
- `env`, `uname`, `file`, `which`, `tree` — 其他只读工具

## 使用提示

- 当用户想查看目录结构时，使用 `ls -la` 或 `tree`
- 当用户想查看文件内容时，使用 `cat` 或 `head`
- 命令执行超时限制为 10 秒
