# 部署指南

本文档介绍如何将 TextLoom Web Frontend 部署到生产环境。

## 📋 目录

- [构建准备](#构建准备)
- [本地构建](#本地构建)
- [部署方案](#部署方案)
- [环境配置](#环境配置)
- [性能优化](#性能优化)
- [监控与维护](#监控与维护)

## 🔧 构建准备

### 环境要求

| 软件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Node.js | 18.0.0 | 20.x LTS |
| pnpm | 8.6.0 | 最新版本 |

### 检查清单

- [ ] 确认所有依赖已安装
- [ ] 配置环境变量
- [ ] 运行类型检查
- [ ] 运行代码检查
- [ ] 测试构建流程

```bash
# 安装依赖
pnpm install

# 类型检查
pnpm type-check

# 代码检查
pnpm lint

# 测试构建
pnpm build
```

## 🏗️ 本地构建

### 1. 配置生产环境变量

创建 `.env.production` 文件：

```env
# 生产环境 API 地址
VITE_API_BASE_URL=https://api.yourdomain.com

# 可选：启用生产环境日志
VITE_ENABLE_LOGGING=false

# 可选：启用分析模式
VITE_ANALYZE=false
```

### 2. 执行构建

```bash
# 构建生产版本
pnpm build

# 构建输出目录：dist/
# - dist/index.html
# - dist/assets/*.js
# - dist/assets/*.css
```

### 3. 预览构建结果

```bash
# 本地预览生产构建
pnpm preview

# 访问 http://localhost:4173
```

### 4. 验证构建产物

检查构建产物：

```bash
# 查看构建产物大小
ls -lh dist/assets/

# 预期输出示例：
# index-*.js      ~150KB (gzip 后约 50KB)
# index-*.css     ~20KB  (gzip 后约 5KB)
# vendor-*.js     ~300KB (gzip 后约 100KB)
```

## 🚀 部署方案

### 方案 1: 静态托管服务

#### Vercel (推荐)

**优势:**
- 零配置自动部署
- 全球 CDN 加速
- 自动 HTTPS
- 免费套餐充足

**部署步骤:**

1. 安装 Vercel CLI
```bash
npm install -g vercel
```

2. 登录 Vercel
```bash
vercel login
```

3. 部署项目
```bash
cd frontend
vercel

# 首次部署会询问配置
# - 项目名称：textloom-frontend
# - 输出目录：dist
# - 构建命令：pnpm build
```

4. 配置环境变量（在 Vercel 控制台）
```
VITE_API_BASE_URL=https://api.yourdomain.com
```

5. 重新部署
```bash
vercel --prod
```

**vercel.json 配置:**

```json
{
  "buildCommand": "pnpm build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

---

#### Netlify

**优势:**
- 简单易用
- 表单处理功能
- 分支预览
- 免费 SSL

**部署步骤:**

1. 创建 `netlify.toml`
```toml
[build]
  command = "pnpm build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200

[[headers]]
  for = "/assets/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
```

2. 连接 Git 仓库并部署

3. 在 Netlify 控制台配置环境变量

---

#### Cloudflare Pages

**优势:**
- 全球 CDN
- 无限带宽
- Workers 集成
- 免费

**部署步骤:**

1. 连接 GitHub 仓库

2. 配置构建设置：
   - 构建命令：`pnpm build`
   - 输出目录：`dist`
   - 根目录：`frontend`

3. 配置环境变量

4. 部署

---

### 方案 2: Docker 容器化部署

#### Dockerfile

```dockerfile
# 构建阶段
FROM node:20-alpine AS builder

# 安装 pnpm
RUN npm install -g pnpm

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY package.json pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源代码
COPY . .

# 构建应用
RUN pnpm build

# 生产阶段
FROM nginx:alpine

# 复制构建产物到 Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
```

#### nginx.conf

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # 启用 gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/x-javascript application/xml+rss
               application/javascript application/json;

    # 静态资源缓存
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA 路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 健康检查
    location /health {
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
```

#### 构建和运行

```bash
# 构建镜像
docker build -t textloom-frontend:latest .

# 运行容器
docker run -d \
  -p 8080:80 \
  --name textloom-frontend \
  textloom-frontend:latest

# 访问 http://localhost:8080
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:80"
    environment:
      - VITE_API_BASE_URL=https://api.yourdomain.com
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### 方案 3: 传统服务器部署

#### Nginx 静态托管

**步骤:**

1. 构建应用
```bash
pnpm build
```

2. 上传到服务器
```bash
# 使用 rsync
rsync -avz dist/ user@server:/var/www/textloom-frontend/

# 或使用 scp
scp -r dist/* user@server:/var/www/textloom-frontend/
```

3. 配置 Nginx
```nginx
server {
    listen 80;
    server_name textloom.yourdomain.com;
    root /var/www/textloom-frontend;
    index index.html;

    # 强制 HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name textloom.yourdomain.com;
    root /var/www/textloom-frontend;
    index index.html;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/textloom.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/textloom.yourdomain.com/privkey.pem;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 静态资源
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

4. 重载 Nginx
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## ⚙️ 环境配置

### 环境变量清单

| 变量名 | 说明 | 开发环境 | 生产环境 |
|--------|------|----------|----------|
| VITE_API_BASE_URL | API 基础地址 | http://localhost:48095 | https://api.yourdomain.com |
| VITE_ENABLE_LOGGING | 启用日志 | true | false |
| VITE_ANALYZE | 构建分析 | false | false |

### 多环境配置

**开发环境** (`.env.development`):
```env
VITE_API_BASE_URL=http://localhost:48095
VITE_ENABLE_LOGGING=true
```

**测试环境** (`.env.staging`):
```env
VITE_API_BASE_URL=https://api-staging.yourdomain.com
VITE_ENABLE_LOGGING=true
```

**生产环境** (`.env.production`):
```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_ENABLE_LOGGING=false
```

**构建命令:**
```bash
# 开发环境
pnpm build --mode development

# 测试环境
pnpm build --mode staging

# 生产环境
pnpm build --mode production
```

---

## 🚄 性能优化

### 1. 代码分割

已在 `vite.config.ts` 中配置：

```typescript
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui': ['@radix-ui/react-slot'],
          'charts': ['recharts'],
          'state': ['zustand', '@tanstack/react-query'],
        },
      },
    },
  },
});
```

### 2. 资源压缩

启用 Vite 内置压缩：

```bash
pnpm add -D vite-plugin-compression
```

```typescript
// vite.config.ts
import compression from 'vite-plugin-compression';

export default defineConfig({
  plugins: [
    react(),
    compression({
      algorithm: 'gzip',
      ext: '.gz',
    }),
    compression({
      algorithm: 'brotliCompress',
      ext: '.br',
    }),
  ],
});
```

### 3. 图片优化

使用 WebP 格式：

```bash
pnpm add -D vite-plugin-imagemin
```

### 4. CDN 加速

将静态资源托管到 CDN：

```typescript
// vite.config.ts
export default defineConfig({
  base: 'https://cdn.yourdomain.com/',
});
```

### 5. 预加载关键资源

在 `index.html` 中添加：

```html
<head>
  <!-- 预连接 API 服务器 -->
  <link rel="preconnect" href="https://api.yourdomain.com">

  <!-- 预加载字体 -->
  <link rel="preload" as="font" href="/fonts/main.woff2" crossorigin>
</head>
```

---

## 📊 监控与维护

### 1. 错误监控

集成 Sentry：

```bash
pnpm add @sentry/react
```

```typescript
// src/main.tsx
import * as Sentry from '@sentry/react';

if (import.meta.env.PROD) {
  Sentry.init({
    dsn: 'YOUR_SENTRY_DSN',
    integrations: [
      new Sentry.BrowserTracing(),
      new Sentry.Replay(),
    ],
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
  });
}
```

### 2. 性能监控

使用 Web Vitals：

```bash
pnpm add web-vitals
```

```typescript
// src/main.tsx
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendToAnalytics(metric: any) {
  console.log(metric);
  // 发送到分析服务
}

getCLS(sendToAnalytics);
getFID(sendToAnalytics);
getFCP(sendToAnalytics);
getLCP(sendToAnalytics);
getTTFB(sendToAnalytics);
```

### 3. 日志记录

创建日志服务：

```typescript
// src/utils/logger.ts
const isDev = import.meta.env.DEV;

export const logger = {
  info: (message: string, data?: any) => {
    if (isDev) console.log(`[INFO] ${message}`, data);
  },
  error: (message: string, error?: any) => {
    console.error(`[ERROR] ${message}`, error);
    // 发送到错误监控服务
  },
  warn: (message: string, data?: any) => {
    if (isDev) console.warn(`[WARN] ${message}`, data);
  },
};
```

### 4. 健康检查

添加健康检查端点（如果使用 Docker）：

```typescript
// 在 nginx.conf 中配置
location /health {
  return 200 "OK";
  add_header Content-Type text/plain;
}
```

### 5. 更新策略

**滚动更新:**

```bash
# 1. 构建新版本
pnpm build

# 2. 上传到服务器（使用临时目录）
rsync -avz dist/ user@server:/var/www/textloom-frontend-new/

# 3. 原子性切换
ssh user@server "mv /var/www/textloom-frontend /var/www/textloom-frontend-old && \
                mv /var/www/textloom-frontend-new /var/www/textloom-frontend && \
                rm -rf /var/www/textloom-frontend-old"

# 4. 重载 Nginx
ssh user@server "sudo systemctl reload nginx"
```

---

## 🔒 安全检查

### 部署前检查清单

- [ ] 移除所有 console.log（生产环境）
- [ ] 验证环境变量正确配置
- [ ] 检查 API 基础 URL 是 HTTPS
- [ ] 启用 CORS 正确配置
- [ ] 配置安全响应头
- [ ] 启用 HTTPS 和 HSTS
- [ ] 配置 CSP (Content Security Policy)
- [ ] 移除开发依赖包
- [ ] 运行安全审计

```bash
# 安全审计
pnpm audit

# 修复可修复的漏洞
pnpm audit fix
```

### 安全响应头

在 Nginx 配置中添加：

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

---

## 📝 故障排查

### 常见问题

**1. 部署后页面空白**

- 检查 `base` 配置是否正确
- 检查控制台错误
- 验证静态资源路径

**2. API 请求失败**

- 检查 `VITE_API_BASE_URL` 配置
- 验证 CORS 设置
- 检查网络防火墙规则

**3. 路由 404 错误**

- 确认服务器配置了 SPA 回退
- 检查 Nginx `try_files` 配置

**4. 构建失败**

- 清理缓存：`pnpm clean && pnpm install`
- 检查 Node.js 版本
- 查看构建日志

---

## 🔗 相关资源

- [Vite 部署文档](https://vitejs.dev/guide/static-deploy.html)
- [Nginx 配置指南](https://nginx.org/en/docs/)
- [Docker 最佳实践](https://docs.docker.com/develop/dev-best-practices/)
- [Web 性能优化](https://web.dev/fast/)

---

**最后更新**: 2025-01-27
