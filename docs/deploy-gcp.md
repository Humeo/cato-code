# CatoCode — GCP 部署指南

目标实例：`instance-20260305-132242`（us-central1-c）

## 架构概览

```
Internet → Nginx (443/80)
              ├─ api.your-domain.com  → 127.0.0.1:8000  (Docker: catocode backend)
              └─ your-domain.com      → 127.0.0.1:3000  (PM2: Next.js frontend)
```

---

## 第一步：登录服务器

```bash
gcloud compute ssh --zone "us-central1-c" "instance-20260305-132242" \
  --project "project-1820ca5f-338b-48bf-878"
```

---

## 第二步：安装依赖（首次）

```bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # 不用重新登录就能用 docker

# 安装 Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# 安装 Node.js 20 + bun（前端用）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc

# 安装 PM2（托管 Next.js 进程）
sudo npm install -g pm2

# 安装 Nginx + Certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

# 安装 git
sudo apt-get install -y git
```

---

## 第三步：克隆项目

```bash
cd ~
git clone https://github.com/你的账号/CatoCode.git catocode
cd catocode
```

---

## 第四步：配置环境变量

### 4.1 后端 .env

```bash
cp .env.example .env
nano .env
```

填写以下内容（参考 `.env.example` 注释）：

```bash
# AI
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_BASE_URL=https://cc.580ai.net   # 你的自定义 base URL

# GitHub App
GITHUB_APP_ID=你的AppID
GITHUB_APP_PRIVATE_KEY="$(cat ~/catocode-bot.private-key.pem | awk '{printf "%s\\n", $0}')"
GITHUB_APP_WEBHOOK_SECRET=0b57b793f6a564292f2e1ddd5f507e9e4a7f5ac9c548a197dd24001433d32260
GITHUB_APP_NAME=catocode-bot

# GitHub OAuth
GITHUB_OAUTH_CLIENT_ID=Ov23li...
GITHUB_OAUTH_CLIENT_SECRET=...

# Session（你本地已生成的值）
SESSION_SECRET_KEY=...

# URLs（替换成你的实际域名）
CATOCODE_BASE_URL=https://api.your-domain.com
FRONTEND_URL=https://your-domain.com

# Embedding / RAG 去重（可选）
# EMBEDDING_API_KEY=...

# Haiku 模型（可覆盖）
# SUMMARY_MODEL=claude-haiku-4-5-20251001
```

> **Private Key 格式注意**：PEM 文件里的换行必须转成 `\n` 才能放进 .env 单行。
> 上传 PEM 文件后用以下命令生成正确格式：
> ```bash
> # 本地执行，把文件传到服务器
> scp catocode-bot.*.private-key.pem \
>   你的用户名@服务器IP:~/catocode-bot.private-key.pem
>
> # 服务器上生成单行格式并追加到 .env
> echo "GITHUB_APP_PRIVATE_KEY=\"$(awk 'NF {sub(/\r/, ""); printf "%s\\n", $0}' ~/catocode-bot.private-key.pem)\"" >> .env
> ```

### 4.2 前端 .env.local

```bash
cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=https://api.your-domain.com
EOF
```

---

## 第五步：启动后端（Docker）

```bash
cd ~/catocode

# 构建并启动（首次需要几分钟下载镜像）
docker compose up -d --build

# 查看日志
docker compose logs -f

# 验证后端正常
curl http://localhost:8000/webhook/health
# 期望返回: {"status":"ok"}
```

---

## 第六步：构建并启动前端（Next.js）

```bash
cd ~/catocode/frontend

# 安装依赖
bun install

# 构建生产版本
bun run build

# 用 PM2 启动（保持后台运行 + 自动重启）
pm2 start "bun run start -- --port 3000" --name catocode-frontend
pm2 save
pm2 startup   # 复制输出的命令并执行，开机自启
```

---

## 第七步：配置 GCP 防火墙

在 GCP Console 或 gcloud 开放 80/443 端口：

```bash
gcloud compute firewall-rules create allow-http-https \
  --project "project-1820ca5f-338b-48bf-878" \
  --allow tcp:80,tcp:443 \
  --target-tags http-server,https-server \
  --description "Allow HTTP and HTTPS traffic"

# 给实例添加网络标签
gcloud compute instances add-tags instance-20260305-132242 \
  --zone us-central1-c \
  --project "project-1820ca5f-338b-48bf-878" \
  --tags http-server,https-server
```

---

## 第八步：配置 Nginx + HTTPS

### 8.1 创建 Nginx 配置

```bash
sudo nano /etc/nginx/sites-available/catocode
```

粘贴以下内容（替换 `your-domain.com`）：

```nginx
# 前端
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# 后端 API
server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE（日志流）不能缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/catocode /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 8.2 申请 SSL 证书

```bash
# 申请证书（自动修改 Nginx 配置加上 HTTPS）
sudo certbot --nginx \
  -d your-domain.com \
  -d api.your-domain.com \
  --non-interactive \
  --agree-tos \
  -m your-email@example.com

# 测试自动续期
sudo certbot renew --dry-run
```

---

## 第九步：更新 GitHub App Webhook URL

打开 [github.com/settings/apps](https://github.com/settings/apps) → 你的 App：

- **Webhook URL**：`https://api.your-domain.com/webhook/app`
- **Webhook secret**：填入 `.env` 里的 `GITHUB_APP_WEBHOOK_SECRET` 值
- **GitHub App OAuth callback URL**：`https://api.your-domain.com/auth/github/callback`

---

## 验证部署

```bash
# 后端健康检查
curl https://api.your-domain.com/webhook/health

# 查看后端日志（实时）
docker compose -f ~/catocode/docker-compose.yml logs -f

# 查看前端状态
pm2 status
pm2 logs catocode-frontend
```

---

## 日常运维

### 更新代码

```bash
cd ~/catocode
git pull

# 更新后端
docker compose up -d --build

# 更新前端
cd frontend && bun install && bun run build
pm2 restart catocode-frontend
```

### 修改环境变量

```bash
nano ~/catocode/.env
docker compose restart catocode

# 前端变量
nano ~/catocode/frontend/.env.local
cd ~/catocode/frontend && bun run build
pm2 restart catocode-frontend
```

### 查看资源占用

```bash
docker stats catocode-catocode-1   # 后端容器
pm2 monit                           # 前端进程
```

### 数据库备份

```bash
# 备份 SQLite（停机备份最安全）
docker compose stop
docker run --rm -v catocode-catocode-data:/data alpine \
  tar czf - /data > ~/backup-$(date +%Y%m%d).tar.gz
docker compose start

# 检查备份
ls -lh ~/backup-*.tar.gz
```

---

## 常见问题

**后端启动失败 — `GITHUB_APP_PRIVATE_KEY` 格式错误**

PEM 换行没转成 `\n`。重新生成：
```bash
echo "GITHUB_APP_PRIVATE_KEY=\"$(awk 'NF {sub(/\r/, ""); printf "%s\\n", $0}' ~/catocode-bot.private-key.pem)\"" > /tmp/key.env
# 检查格式
head -c 200 /tmp/key.env
# 确认正确后追加到 .env（先删旧的）
grep -v GITHUB_APP_PRIVATE_KEY ~/catocode/.env > /tmp/env.tmp
cat /tmp/env.tmp /tmp/key.env > ~/catocode/.env
```

**Webhook 收到 401 — signature 验证失败**

确认 GitHub App 设置里的 secret 和 `.env` 里的 `GITHUB_APP_WEBHOOK_SECRET` 完全一致（无多余空格）。

**SSE 日志流断开**

Nginx 的 `proxy_read_timeout` 需要足够长（已设 300s）。如果仍然断开，检查 GCP 负载均衡器的超时设置。
