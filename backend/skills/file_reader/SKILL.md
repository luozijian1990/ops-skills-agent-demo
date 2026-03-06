---
name: file_reader
description: "读取指定路径的本地文件内容并返回。支持文本文件，最大 100KB。"
parameters:
  properties:
    path:
      type: string
      description: "要读取的文件的绝对路径，例如 '/Users/me/notes.txt'"
  required:
    - path
---

# 文件读取器

读取本地文件的内容。用户可能会要求你查看特定文件的内容。

## 用法

- 接受绝对路径或 `~` 开头的路径
- 自动处理中文编码
- 文件大小限制为 100KB

## 使用提示

- 当用户提到"读取"、"查看"、"打开"某个文件时使用
- 如果文件是代码文件，读取后可以结合你的知识进行解释
