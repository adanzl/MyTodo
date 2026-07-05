na # Project Notes for AI Agents

## Python Environment

- Python 路径: `/opt/homebrew/Caskroom/miniconda/base/bin/python`
- 使用 conda 管理，当前默认环境为 **flask_env**
- 依赖安装: `pip install -r requirements.txt`（在 server 目录下）
- 运行测试: `python -m pytest`（需先安装依赖）

## Server

- 入口: `server/main.py`
- 启动方式: `python main.py`
- 默认端口: 8000


## SSH

主机名：局域网 mini 或者 (57c42474b0ea.ofalias.net 端口 58186)
用户名 leo
密码 见.env 里的 SSH_PASSWORD
工作目录 /mnt/data/project/MyTodo/server

## 快捷命令

- push 表示执行提交git 并执行push