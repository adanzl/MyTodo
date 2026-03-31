# 安装

```bash
docker run -d \
  --device /dev/kfd \
  --device /dev/dri \
  --group-add video \
  -e HSA_OVERRIDE_GFX_VERSION=11.0.0 \
  -v /mnt/data/ollama:/root/.ollama \
  --restart=always \
  -p 9097:11434 \
  --name ollama \
  ollama/ollama:rocm
```


# 常用命令
## 查看已下载的所有模型
```bash
docker exec -it ollama ollama list
```

## 查看可下载模型
访问网页  https://ollama.com/library

## 查看正在运行的模型
```bash
docker exec -it ollama ollama ps
```
## 拉取新模型
```bash
docker exec -it ollama ollama pull qwen3.5:2b
```

## 运行模型对话
```bash
docker exec -it ollama ollama run qwen3.5:2b
```

## 删除不需要的模型
```bash
docker exec -it ollama ollama rm llama3.2
```
## 验证对话

```bash
curl http://localhost:9097/api/generate \
-H "Content-Type: application/json" \
-d "{\"model\":\"qwen3.5:2b\",\"prompt\":\"你好，简单介绍下自己\",\"stream\":false}"
```