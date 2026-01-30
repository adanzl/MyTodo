#!/usr/bin/env node

/**
 * 部署脚本：将构建产物复制到 static 目录
 */
import { readFileSync, writeFileSync, copyFileSync, existsSync, cpSync, rmSync, readdirSync, statSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const projectRoot = join(__dirname, "..");
const staticDir = join(projectRoot, "static");
const distDir = join(__dirname, "dist");

console.log("🚀 开始部署...");
console.log(`📦 构建目录: ${distDir}`);
console.log(`📁 目标目录: ${staticDir}`);

// 检查构建目录是否存在
if (!existsSync(distDir)) {
    console.error("❌ 错误: 构建目录不存在，请先运行 npm run build");
    process.exit(1);
}

// 清空 static 目录（保留目录结构，只删除文件）
if (existsSync(staticDir)) {
    console.log("🧹 清空 static 目录...");
    try {
        const clearDir = (dirPath) => {
            const items = readdirSync(dirPath);
            for (const item of items) {
                const itemPath = join(dirPath, item);
                const stat = statSync(itemPath);
                if (stat.isDirectory()) {
                    clearDir(itemPath);
                    rmSync(itemPath, { recursive: true, force: true });
                } else {
                    rmSync(itemPath, { force: true });
                }
            }
        };
        clearDir(staticDir);
        console.log("✅ static 目录已清空");
    } catch (error) {
        console.error(`❌ 清空 static 目录失败: ${error.message}`);
        process.exit(1);
    }
} else {
    // 如果 static 目录不存在，创建它
    mkdirSync(staticDir, { recursive: true });
    console.log("✅ 已创建 static 目录");
}

// 读取构建后的 index.html
const indexPath = join(distDir, "index.html");
if (!existsSync(indexPath)) {
    console.error("❌ 错误: 找不到构建后的 index.html");
    process.exit(1);
}

let indexHtml = readFileSync(indexPath, "utf-8");

// 生产环境 base 为 /web/，资源已是 /web/assets/...；仅兜底替换（若构建出 /assets/ 或 /webassets/）
indexHtml = indexHtml.replace(/src="\/webassets\//g, 'src="/web/assets/');
indexHtml = indexHtml.replace(/href="\/webassets\//g, 'href="/web/assets/');
indexHtml = indexHtml.replace(/src="\/assets\//g, 'src="/web/assets/');
indexHtml = indexHtml.replace(/href="\/assets\//g, 'href="/web/assets/');
indexHtml = indexHtml.replace(/href="\/favicon\.ico"/g, 'href="/web/favicon.ico"');

// 保存修复后的 index.html 到 static 目录
const staticIndexPath = join(staticDir, "index.html");
writeFileSync(staticIndexPath, indexHtml, "utf-8");
console.log("✅ 已更新 index.html");

// 复制 assets 目录
const distAssetsDir = join(distDir, "assets");
const staticAssetsDir = join(staticDir, "assets");

if (existsSync(distAssetsDir)) {
    try {
        cpSync(distAssetsDir, staticAssetsDir, { recursive: true, force: true });
        console.log(`✅ 已复制 assets 目录`);
    } catch (error) {
        console.error(`❌ 复制 assets 目录失败: ${error.message}`);
        process.exit(1);
    }
} else {
    console.log("⚠️  未找到 assets 目录，跳过复制");
}

// 复制 favicon.ico（如果存在）
const distFavicon = join(distDir, "favicon.ico");
const staticFavicon = join(staticDir, "favicon.ico");
if (existsSync(distFavicon)) {
    try {
        copyFileSync(distFavicon, staticFavicon);
        console.log("✅ 已复制 favicon.ico");
    } catch (error) {
        console.error(`❌ 复制 favicon.ico 失败: ${error.message}`);
    }
}

console.log("🎉 部署完成！");
console.log(`📝 访问地址: http://localhost:8000/web/index.html`);
