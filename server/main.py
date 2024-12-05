from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

# . .venv/bin/activate
if __name__ == '__main__':
    app.run(debug=True, port=8888)  #开始运行flask应用程序，以调试模式运行
