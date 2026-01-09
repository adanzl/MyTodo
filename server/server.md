# 服务器

## app 依赖

> pip3 install websocket-client flask requests flask_cors flask_socketio

## app 服务

> `sudo vim /etc/systemd/system/my-todo.service`

> `sudo systemctl restart my-todo`

> 本地调试 运行main.py

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

> 配置证书

`sudo certbot certonly --nginx --preferred-challenges tls-alpn-01 -d leo-dify.tbit.top -m adanzl@163.com --agree-tos --no-eff-email`

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

## redis-insight

创建了用于存储数据的卷 redis_insight

    docker volume create redis_insight

拉取并启动 docker

    docker run -d -p 9001:5540 --name redis_insight \
        --restart=always \
        -v redis_insight:/data \
        -e "RI_PROXY_PATH=redis_insight" \
        -e "RI_LOG_LEVEL=http" \
        redis/redisinsight:latest

## cloud-beaver

https://github.com/dbeaver/cloudbeaver/wiki/CloudBeaver-Community-deployment-from-docker-image

## redis

配置文件 /mnt/data/redis/redis-stack.conf

数据文件 /mnt/data/redis/data

    docker run -d -p 6379:6379 --name redis_stack \
        --restart=always \
        -v /mnt/data/redis/redis-stack.conf:/redis-stack.conf  \
        -v /mnt/data/redis/data:/data \
        redis/redis-stack-server:latest

## MySQL

配置文件 /mnt/data/mysql/conf

数据文件 /mnt/data/mysql/data

日志文件 /mnt/data/mysql/logs

    docker run -d -p 8002:3306 --name mysql --restart=always \
        -v /mnt/data/mysql/conf:/etc/mysql/conf.d \
        -v /mnt/data/mysql/logs:/logs \
        -v /mnt/data/mysql/data:/var/lib/mysql \
        -e MYSQL_ROOT_PASSWORD='!Zhao575936' mysql:5.7.44

## DBGate

    docker run -d -it -p 8003:3000 --name DBGate --restart=always \
        -v /mnt/data/project/MyTodo/server/data.db:/home/data.db \
        -e LOGIN=leo \
        -e PASSWORD=\!Zhao575936 \
        -e CONNECTIONS=con1,con2 \
        -e LABEL_con1=MYSQL \
        -e SERVER_con1=192.168.50.171 \
        -e USER_con1=leo \
        -e PORT_con1=8002 \
        -e PASSWORD_con1=H^12345678 \
        -e ENGINE_con1=mysql@dbgate-plugin-mysql \
        -e LABEL_con2=SQLite \
        -e FILE_con2=/home/data.db \
        -e ENGINE_con2=sqlite@dbgate-plugin-sqlite \
        dbgate/dbgate:latest

## funASR online

    # 拉取镜像
    docker pull registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12
    # 创建模型文件夹
    mkdir -p /mnt/data/funasr/models
    # 运行容器
    # cSpell: disable-next-line
    docker run -p 9095:10095 -itd -w /workspace/FunASR/runtime --privileged=true --name funASR_online --restart=always -v /mnt/data/funasr/models:/workspace/models registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-online-cpu-0.1.12 bash -c "nohup bash /workspace/FunASR/runtime/run_server_2pass.sh --download-model-dir /workspace/models --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx --model-dir iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online --online-model-dir damo/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-online-onnx --punc-dir damo/punc_ct-transformer_zh-cn-common-vad_realtime-vocab272727-onnx --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst --itn-dir thuduj12/fst_itn_zh --certfile 0 --hotword /workspace/models/hotwords.txt > /var/log/funasr.log 2>&1 & tail -f /var/log/funasr.log"

## funASR offline

    # 拉取镜像
    docker pull registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-cpu-0.4.6
    # 创建模型文件夹
    mkdir -p /mnt/data/funasr/models
    # 运行容器
    # cSpell: disable-next-line
    docker run -p 9096:10095 -itd -w /workspace/FunASR/runtime --privileged=true --name funASR_offline --restart=always -v /mnt/data/funasr/models:/workspace/models registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-cpu-0.4.6 bash -c "nohup bash /workspace/FunASR/runtime/run_server.sh --download-model-dir /workspace/models --vad-dir damo/speech_fsmn_vad_zh-cn-16k-common-onnx --model-dir damo/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-onnx  --punc-dir damo/punc_ct-transformer_cn-en-common-vocab471067-large-onnx --lm-dir damo/speech_ngram_lm_zh-cn-ai-wesp-fst --itn-dir thuduj12/fst_itn_zh --certfile 0 --hotword /workspace/models/hotwords.txt > /var/log/funasr.log 2>&1 & tail -f /var/log/funasr.log"

## Ollama

    docker run -d --device /dev/kfd --device /dev/dri \
    -v /mnt/data/ollama:/root/.ollama --restart=always \
    -p 9097:11434 \
    --name Ollama ollama/ollama:rocm serve

## Cosy-voice

    git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
    cd CosyVoice/
    cd runtime/python/
    docker build -t cosy-voice .

    docker run -d -p 9099:50000 --name cosy-voice --restart=always -v /mnt/data/CosyVoice/pretrained_models:/models \
    cosy-voice /bin/bash -c "cd /opt/CosyVoice/CosyVoice/runtime/python/fastapi && python3 server.py --port 50000 --model_dir /models/CosyVoice2-0.5B && sleep infinity"

    cd fastapi && python3 client.py --port 50000 --mode <sft|zero_shot|cross_lingual|instruct>

## gewechat

    docker run -itd -v /mnt/data/gewechat:/root/temp -p 9101:2531 -p 9102:2532 --restart=always --name=geWechat gewe

## dify-on-wechat

    cd /mnt/data/dify-on-wechat
    conda activate py3_11
    nohup python3 -u app.py >app.log 2>&1 &

## docker-chrome

    docker run \
        --name chrome-novnc --restart=always \
        -e PORT=8080 \
        -p 9103:8080 \
        -e VNC_PASS=Zhao575936 \
        -e VNC_RESOLUTION=1600x900 \
        -d vital987/chrome-novnc:latest

## 服务器端口

| Server        | Port     | Server         |  Port |
| ------------- | -------- | -------------- | ----: |
| my-todo       | 8000     | funASR-online  |  9095 |
| code-server   | 8001     | funASR-offline |  9096 |
| mysql         | 8002     | ollama         |  9097 |
| DBGate        | 8003     | dify           |  9098 |
| nginx         | 8848/443 | cosy-voice     | x9099 |
| redis         | 6379     | geWechat       |  9101 |
| cockpit       | 9090     | geWechat       |  9102 |
| portainer     | 9000     | chrome         |  9103 |
| redis_insight | 9001     |                |       |
