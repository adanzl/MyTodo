# 服务器

## app 服务

> `sudo vim /etc/systemd/system/my-todo.service`

> `sudo systemctl restart my-todo`

## 配置 natapp

`cat /opt/natapp/logs/natapp_web.log`

`sudo vim /opt/natapp/config_web.ini`

`sudo vim /etc/systemd/system/natapp_web.service`

`sudo systemctl restart natapp_web`

## 配置 caddy

`sudo vim /etc/caddy/Caddyfile`

`caddy reload --config=/etc/caddy/Caddyfile`

## 配置 nginx

`sudo vim /etc/nginx/sites-available/default`

`sudo nginx -s reload`

## 重启 code-server

`sudo systemctl restart code-server@leo`

`sudo systemctl daemon-reload`

## 打包

`git pull && npx npm run build --  --mode=production && npx capawesome manifests:generate --path dist npx cap copy`

## portainer

创建了用于存储 Portainer 数据的卷 portainer_data

    docker volume create portainer_data

拉取并启动 docker

    docker run -d -p 9000:9000 --name portainer \
        --restart=always \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v portainer_data:/data \
        portainer/portainer-ce`

## cloud-beaver
https://github.com/dbeaver/cloudbeaver/wiki/CloudBeaver-Community-deployment-from-docker-image

## 服务器端口

| Server       |     Port |
| ------------ | -------: |
| my-todo      |     8000 |
| code-server  |     8001 |
| nginx        | 8848/443 |
| cockpit      |     9090 |
| portainer    |     9000 |
| cloud-beaver |        x |
