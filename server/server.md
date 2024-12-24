8ae2d9ac3a0f4055
# GIT
`git -C /home/orangepi/project/MyTodo pull`
# 服务器
## 重启app服务
`sudo vim /etc/systemd/system/myTodo.service`

`sudo systemctl restart myTodo.service`
## 配置natapp
`sudo vim /etc/systemd/system/natapp.service`
## 配置caddy
`sudo vim /etc/caddy/Caddyfile`

`caddy reload --config=/etc/caddy/Caddyfile`

## 重启code-server
`sudo systemctl restart code-server@orangepi.service`

`sudo systemctl daemon-reload`