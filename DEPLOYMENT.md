# CBIR 部署说明

本项目推荐部署为：

```text
前端 Vue: Cloudflare Pages / Vercel
后端 FastAPI: VPS
数据、索引、模型: VPS 磁盘
```

## 1. 本地开发保持不变

本地仍然可以继续使用原来的流程：

```powershell
cd C:\Users\wgq20\Documents\CBIR\cbir-system
.\start_cbir.ps1 -SkipEvaluateHealth
```

前端本地默认请求 `/api`，由 Vite 代理到后端；后端默认允许：

```text
http://localhost:5173
http://127.0.0.1:5173
```

所以不配置任何线上环境变量时，本地流程不受影响。

## 2. 推荐域名规划

假设你的域名是 `example.com`：

```text
https://cbir.example.com       前端
https://api.example.com        后端
```

DNS 建议：

```text
A      api      VPS_IP
CNAME  cbir     Cloudflare Pages 或 Vercel 提供的域名
```

## 3. 后端 VPS 部署

服务器示例目录：

```text
/opt/cbir-system
/opt/cbir-system/backend
/opt/cbir-system/data
```

安装基础环境：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx git
```

部署代码：

```bash
cd /opt
git clone 你的仓库地址 cbir-system
cd /opt/cbir-system/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

上传本地数据和模型：

```powershell
scp -r C:\Users\wgq20\Documents\CBIR\cbir-system\data root@VPS_IP:/opt/cbir-system/
```

生产环境修改 `/opt/cbir-system/backend/settings.yaml`：

```yaml
app:
  data_root: "../data"
  device: "auto"
  top_k: 12
  public_base_url: "https://api.example.com"
  cors_origins:
    - "https://cbir.example.com"
    - "https://www.example.com"
```

其中：

- `public_base_url` 用来让图片 URL 返回为 `https://api.example.com/static/...`
- `cors_origins` 用来允许前端域名访问后端 API

测试启动：

```bash
cd /opt/cbir-system/backend
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
```

## 4. systemd 托管后端

创建服务：

```bash
sudo nano /etc/systemd/system/cbir-backend.service
```

写入：

```ini
[Unit]
Description=CBIR FastAPI Backend
After=network.target

[Service]
WorkingDirectory=/opt/cbir-system/backend
ExecStart=/opt/cbir-system/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动：

```bash
sudo systemctl daemon-reload
sudo systemctl enable cbir-backend
sudo systemctl start cbir-backend
sudo systemctl status cbir-backend
```

## 5. Nginx 反向代理

创建配置：

```bash
sudo nano /etc/nginx/sites-available/cbir-api
```

写入：

```nginx
server {
    listen 80;
    server_name api.example.com;

    client_max_body_size 300M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用：

```bash
sudo ln -s /etc/nginx/sites-available/cbir-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

配置 HTTPS：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com
```

## 6. Cloudflare Pages 部署前端

配置：

```text
Root directory: frontend
Build command: npm run build
Build output directory: dist
```

环境变量：

```text
VITE_API_BASE_URL=https://api.example.com/api
```

## 7. Vercel 部署前端

配置：

```text
Framework: Vite
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

环境变量：

```text
VITE_API_BASE_URL=https://api.example.com/api
```

## 8. 线上验收

后端：

```bash
curl https://api.example.com/api/health
```

前端：

```text
https://cbir.example.com
```

重点检查：

- 图库图片是否能显示。
- 上传检索是否能返回结果。
- 搜索结果图片 URL 是否是 `https://api.example.com/static/...`。
- 任务中心是否能显示后台任务。

## 9. 注意事项

- 普通 VPS 一般没有 GPU，可以部署已有模型和索引，但不适合在线训练 CNN。
- 如果需要训练模型，建议使用 GPU VPS、RunPod、AutoDL 等。
- 数据、模型、索引都在 VPS 磁盘时，要定期备份 `/opt/cbir-system/data`。
