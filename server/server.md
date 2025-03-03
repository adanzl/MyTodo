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
        portainer/portainer-ce

## cloud-beaver

https://github.com/dbeaver/cloudbeaver/wiki/CloudBeaver-Community-deployment-from-docker-image

## redis

配置文件 /data/redis/redis.conf

数据文件 /data/redis/data

    docker run -d -p 6379:6379 --name redis \
        --restart=always \
        -v /data/redis/redis.conf:/usr/local/etc/redis/redis.conf \
        -v /data/redis/data:/data \
        hub.rat.dev/redis redis-server /usr/local/etc/redis/redis.conf


## funASR

    # 拉取镜像
    docker pull registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12
    # 创建模型文件夹
    mkdir -p /mnt/data/funasr/models
    # 运行容器
    docker run -p 9095:10095 -itd -w /workspace/FunASR/runtime --privileged=true --name funASR_online --restart=always -v /mnt/data/funasr/models:/workspace/models registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12 bash -c "nohup bash /workspace/FunASR/runtime/run_server_2pass.sh --download-model-dir /workspace/models --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx --model-dir iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online --online-model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx --punc-dir damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst --itn-dir thuduj12/fst_itn_zh --certfile 0 --hotword /workspace/models/hotwords.txt > /var/log/funasr.log 2>&1 & tail -f /var/log/funasr.log"


## 服务器端口

| Server       |     Port |
| ------------ | -------: |
| my-todo      |     8000 |
| code-server  |     8001 |
| nginx        | 8848/443 |
| cockpit      |     9090 |
| portainer    |     9000 |
| funASR       |     9095 |
| cloud-beaver |        x |
| redis        |     6379 |
