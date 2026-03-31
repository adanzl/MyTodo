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

### 局域网访问

```text
需要开启https
```
### 配置
```bash
# 编辑环境文件
vim /mnt/data/openclaw/.env
OPENCLAW_CONFIG_DIR=/mnt/data/openclaw/data/.openclaw
OPENCLAW_WORKSPACE_DIR=/mnt/data/openclaw/data/.openclaw/workspace
OPENCLAW_IMAGE=openclaw:local
OPENCLAW_GATEWAY_TOKEN=517dd2b056d51bdcc5ad36514d69c9a285ba894d4ddda8db

# 编辑docker文件 
vim /mnt/data/openclaw/docker-compose.yml
删除了 network_mode: service:openclaw-gateway
添加了 extra_hosts 让容器能访问宿主机 两个子容器都要添加
  extra_hosts:
    - host.docker.internal:host-gateway

# 编辑配置文件
vim /mnt/data/openclaw/data/.openclaw/openclaw.json 
添加
"gateway":{
    "tls": {
        "enabled": true,
        "autoGenerate": true
    },
    "controlUi": {
        "enabled": true,
        "allowInsecureAuth": false,
        "allowedOrigins":[
            "https://192.168.50.172:18789",
            "http://192.168.50.172:18789"
        ]
    },
    "auth": {
        "mode": "token",
        "token": "517dd2b056d51bdcc5ad36514d69c9a285ba894d4ddda8db"
    },
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
```

### 停止容器
```bash
docker compose down
```

### 控制 UI 令牌 + 配对（Docker）
```bash
如果你看到”unauthorized”或”disconnected (1008): pairing required”，获取新的仪表板链接并批准浏览器设备：

docker 配对目前不好用，需要进入容器内部执行

# docker compose run --rm openclaw-cli dashboard --no-open
# docker compose run --rm openclaw-cli devices list
# docker compose run --rm openclaw-cli devices approve <requestId>
openclaw devices list
openclaw devices approve <requestId>
```

### 飞书

docker compose run --rm openclaw-cli pairing approve feishu 8RA4EVA6

