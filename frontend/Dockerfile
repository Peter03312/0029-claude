# 多阶段构建：阶段一产出静态资源，阶段二用 nginx 托管并代理 /api。

FROM node:20-bookworm-slim AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY index.html vite.config.ts tsconfig.json ./
COPY src ./src
# 构建前做一次类型检查（build 脚本内含 tsc --noEmit）
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
