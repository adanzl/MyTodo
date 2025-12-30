# 前端项目

## 环境要求

- Node.js: v22.21.1（见 `.nvmrc` 文件）

## 安装依赖

```bash
# macOS/Linux (使用 nvm)
nvm use
npm install

# Windows (使用 nvm-windows)
nvm use
npm install
```

## 开发

```bash
npm run dev
```

## 构建

```bash
npm run build
```

## 部署

```bash
npm run deploy
# 或者
npm run build && node deploy.js
```

## Windows 用户注意事项

1. 安装 [nvm-windows](https://github.com/coreybutler/nvm-windows)
2. 在项目根目录运行 `nvm use` 切换到正确的 Node.js 版本
3. 确保使用 PowerShell 或 CMD 运行命令
