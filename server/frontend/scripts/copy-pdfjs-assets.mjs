/**
 * 将已安装的 pdfjs-dist 中的 wasm / cmaps / standard_fonts / iccs 复制到 public/pdfjs/。
 * 构建时 Vite 会复制到 dist/pdfjs/，并由 vite 插件再镜像到 dist/web/pdfjs/（与 base=/web/ 的 URL /web/pdfjs/ 一致）。
 */
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const pkgRoot = path.resolve(__dirname, '..')
const pdfjsDist = path.resolve(pkgRoot, 'node_modules/pdfjs-dist')
const destRoot = path.resolve(pkgRoot, 'public/pdfjs')

const DIRS = ['wasm', 'cmaps', 'standard_fonts', 'iccs']

if (!fs.existsSync(pdfjsDist)) {
  console.error(`[copy-pdfjs-assets] 未找到 pdfjs-dist：${pdfjsDist}\n请先在该目录执行 npm install`)
  process.exit(1)
}

fs.mkdirSync(destRoot, { recursive: true })

for (const name of DIRS) {
  const src = path.join(pdfjsDist, name)
  const dest = path.join(destRoot, name)
  if (!fs.existsSync(src)) {
    console.warn(`[copy-pdfjs-assets] 跳过（不存在）：${src}`)
    continue
  }
  fs.rmSync(dest, { recursive: true, force: true })
  fs.cpSync(src, dest, { recursive: true })
}

console.log(`[copy-pdfjs-assets] 已复制到 ${destRoot}`)
