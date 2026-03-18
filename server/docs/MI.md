# 小米服务命令行
https://github.com/Yonsm/MiService
## 安装
    /opt/miniconda3/bin/python3 -m pip install -U pip setuptools wheel
    /opt/miniconda3/bin/python3 -m pip install aiofiles aiohttp
    /opt/miniconda3/bin/python3 -m pip install --no-build-isolation miservice
## 激活环境
### conda
`conda activate flask_env`
### env
`while IFS= read -r line; do line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'); [[ -z "$line" || "$line" =~ ^# ]] && continue; line=${line%%#*}; [[ -n "$line" && "$line" =~ = ]] && eval "export $line"; done < .env`

## 查询命令
### 查询设备

所有 `micli list`

只要音箱，查看3行  `micli list | grep -A3 音箱`
```text
    "name": "小爱音箱Play增强版",
    "model": "xiaomi.wifispeaker.l05c",
    "did": "982124869",
    "token": "1d2412b5bcb22a867393f7146ba29e2f"
```

设置DID export MI_DID=982124869

### 查询设备的接口文档
`micli spec xiaomi.wifispeaker.l05c`

数字查询的命令支持批量 如 micli 1,2,3 ，返回则是数组

### 查询设备音量
`micli 2-1`

### 查询设备播放状态
`micli 3-1`

## 设置命令
### 设置音量
`micli 2=#20`

    参数类型要根据接口描述文档来确定:
    #是强制文本类型，还可以用单引号'和双引号"来强制文本类型'（可单个引号，也可以两个）;
    如果不强制文本类型，默认将检测类型；可能的检测结果是 JSON 的 null、false、true、整数、浮点数或者文本