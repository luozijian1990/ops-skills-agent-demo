---
name: code_explainer
description: "接收一段代码和语言类型，提供详细的逐行解释和注释。"
parameters:
  properties:
    code:
      type: string
      description: "需要解释的代码内容"
    language:
      type: string
      description: "代码的编程语言，例如 'python', 'javascript', 'go'"
  required:
    - code
    - language
---

# 代码解释器

帮助用户理解代码。接收代码片段后，提供：

1. **总体概述** — 代码的目的和功能
2. **逐行注释** — 关键行的详细解释
3. **设计模式** — 使用的编程模式或最佳实践
4. **潜在问题** — 可能的 bug 或改进空间

## 使用提示

- 当用户粘贴代码并问"这段代码做了什么"时使用
- 当用户对某个函数或类不理解时使用
- 解释时使用中文，保持代码原有的变量名和函数名
