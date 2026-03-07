# 使用官方 Python 3.10 基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装系统级依赖（如有需要，如 git, curl 等可以加在这里）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ssh\
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY bin/ /usr/local/bin/
RUN chmod +x /usr/local/bin/*

# 复制后端代码
COPY . .

# 删除工作目录中多余的 bin 副本（可选，保持容器内整洁）
RUN rm -rf bin
# 暴露 FastAPI 默认端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
