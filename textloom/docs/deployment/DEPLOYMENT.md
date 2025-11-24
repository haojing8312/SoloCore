## Flower 安全部署

目标：关闭 Flower 未认证访问，先支持本机访问，生产通过反向代理加鉴权与 IP 白名单。

### 本机仅回环监听

- 本地脚本 `start_celery_worker.sh` 已将 Flower 启动为仅监听 `127.0.0.1:5555`，并默认关闭未认证 API。
- 可通过设置环境变量启用基础认证：

```bash
export FLOWER_BASIC_AUTH="admin:strong-password"
./start_celery_worker.sh flower
```

### Docker Compose

- `docker-compose.yml` 将 Flower 端口映射到本机回环：

```yaml
ports:
  - "127.0.0.1:5555:5555"
command: celery -A celery_config flower --address=127.0.0.1 --port=5555 --logging=info --enable_events
```

### 生产反向代理（示例：Nginx）

将 Nginx 部署到公网，Flower 仍绑定到 `127.0.0.1`，通过 Nginx 暴露受控入口。

```nginx
server {
    listen 80;
    server_name flower.example.com;

    # IP 白名单（示例）
    set $allowed_ip 0;
    if ($remote_addr = 1.2.3.4) { set $allowed_ip 1; }
    if ($remote_addr = 5.6.7.8) { set $allowed_ip 1; }
    if ($allowed_ip = 0) { return 403; }

    # 基础认证
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://127.0.0.1:5555;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

生成 `.htpasswd`：

```bash
sudo apt-get install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd admin
sudo systemctl reload nginx
```

### Kubernetes（可选）

- Service 使用 `ClusterIP` 限制为集群内访问。
- 通过 Ingress（Nginx/Traefik）启用 BasicAuth 与 IP 白名单（`nginx.ingress.kubernetes.io/whitelist-source-range`）。

### 验证

```bash
# 本机验证
curl -sI http://127.0.0.1:5555 | head -n1

# 外网访问应不可达/403（当仅回环绑定或启用Nginx白名单时）
```


