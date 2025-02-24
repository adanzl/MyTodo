
# 服务器
## app服务
`sudo vim /etc/systemd/system/my-todo.service`

`sudo systemctl restart my-todo.service`
## 配置natapp
`cat /opt/natapp/logs/natapp_web.log`

`sudo vim /opt/natapp/config_web.ini`

`sudo vim /etc/systemd/system/natapp_web.service`

`sudo systemctl restart natapp_web`
## 配置caddy
`sudo vim /etc/caddy/Caddyfile`

`caddy reload --config=/etc/caddy/Caddyfile`
## 配置nginx
`sudo vim /etc/nginx/sites-available/default`

`sudo nginx -s reload`

## 重启code-server
`sudo systemctl restart code-server@orangepi.service`

`sudo systemctl daemon-reload`
## 打包
`git pull && npx npm run build --  --mode=production && npx capawesome manifests:generate --path dist npx cap copy`