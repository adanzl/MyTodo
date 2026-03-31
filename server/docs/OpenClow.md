# OpenClaw

## 安装

### 获取代码

```bash
git clone https://github.com/openclaw/openclaw.git
```

### 构建镜像

```bash
# 构建本地镜像
docker build -t openclaw:local -f Dockerfile .
```

### 配置
```bash
# 编辑环境文件
vim .env
OPENCLAW_CONFIG_DIR=/mnt/data/openclaw/data/.openclaw
OPENCLAW_WORKSPACE_DIR=/mnt/data/openclaw/data/.openclaw/workspace
OPENCLAW_IMAGE=openclaw:local

# 编辑docker文件 
vim docker-compose.yml
删除了 network_mode: service:openclaw-gateway
添加了 extra_hosts 让容器能访问宿主机
  extra_hosts:
    - host.docker.internal:host-gateway

# 编辑配置文件
vim .openclaw/openclaw.json 添加

"tls": {
  "enabled": true,
  "autoGenerate": true
},
"controlUi": {
  "enabled": true,
  "allowInsecureAuth": false,
  "allowedOrigins":["https://192.168.50.172:18789","http://192.168.50.172:18789"]
}

# 运行初始化脚本
docker compose run --rm openclaw-cli onboard

# ollama base url
http://host.docker.internal:9097
```

### 启动
```bash
# 后台启动网关
docker compose up -d openclaw-gateway

517dd2b056d51bdcc5ad36514d69c9a285ba894d4ddda8db█
```

### 停止容器
```bash
docker compose down
```

#### 控制 UI 令牌 + 配对（Docker）
```bash
如果你看到”unauthorized”或”disconnected (1008): pairing required”，获取新的仪表板链接并批准浏览器设备：

docker compose run --rm openclaw-cli dashboard --no-open
docker compose run --rm openclaw-cli devices list
docker compose run --rm openclaw-cli devices approve <requestId>
```

