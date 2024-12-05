from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

# . .venv/bin/activate
# sudo vim /etc/systemd/system/MyTodo.service
# sudo systemctl restart code-server@orangepi.service
# sudo vim  /etc/caddy/Caddyfile
# caddy reload --config=/etc/caddy/Caddyfile
if __name__ == '__main__':
    app.run(debug=True, port=8888)  #开始运行flask应用程序，以调试模式运行
