
# GIT
`git -C /home/orangepi/project/MyTodo pull`
# 服务器
## app服务
`sudo vim /etc/systemd/system/myTodo.service`

`sudo systemctl restart myTodo.service`
## 配置natapp
`cat /usr/env/natapp/log/natapp.log`

`sudo vim /usr/env/natapp/config.ini`

`sudo vim /etc/systemd/system/natapp.service`

`sudo systemctl restart natapp.service`
## 配置caddy
`sudo vim /etc/caddy/Caddyfile`

`caddy reload --config=/etc/caddy/Caddyfile`

## 重启code-server
`sudo systemctl restart code-server@orangepi.service`

`sudo systemctl daemon-reload`
## 打包
`git pull && npx npm run build --  --mode=production && npx capawesome manifests:generate --path dist npx cap copy`