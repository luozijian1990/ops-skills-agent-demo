# ==========================================
# 第一阶段：构建 (Build Stage)
# ==========================================
FROM node:22.22-slim AS builder

# 设置工作目录
WORKDIR /app

# 配置 npm 源并安装 pnpm (可选，如果项目使用 npm 则忽略 pnpm)
# RUN npm config set registry https://registry.npmmirror.com

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖项
RUN npm config set registry https://registry.npmmirror.com && npm install

# 复制源码
COPY . .

# 执行构建，生成静态文件到 /app/dist
RUN npm run build:prod

# ==========================================
# 第二阶段：生产服务 (Production Stage)
# ==========================================
FROM nginx:alpine

# 配置 Nginx 路由转发，解决前端直接同域调用 /api 和 /ws 的跨域/连接问题
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从 builder 阶段复制构建后的 dist 文件到 Nginx 默认静态资源目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 暴露 80 端口
EXPOSE 80

# 启动 nginx
CMD ["nginx", "-g", "daemon off;"]
