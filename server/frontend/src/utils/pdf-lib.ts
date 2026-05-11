/**
 * PDF.js 封装：worker、WASM/CMap 等资源路径，以及文档加载与页面渲染为图片。
 */
import * as pdfjsLib from 'pdfjs-dist'
import type { PDFDocumentProxy, PDFPageProxy } from 'pdfjs-dist'
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker

/**
 * 本站静态资源根路径（`public/pdfjs/`，与 `import.meta.env.BASE_URL` 对齐）。
 * 内容由 `npm run pdfjs:copy-assets` 从当前依赖的 `node_modules/pdfjs-dist` 复制而来（postinstall / predev / prebuild 已挂钩），
 * 与 Vite 打包的 pdf.worker 同源版本，**不走 CDN**。
 * 浏览器内转为绝对 URL，避免 Worker 内同步请求 wasm 时相对路径解析错误。
 */
export function getPdfjsAssetsRoot(): string {
  const base = import.meta.env.BASE_URL ?? '/'
  const relative = base.endsWith('/') ? `${base}pdfjs/` : `${base}/pdfjs/`
  if (typeof window !== 'undefined') {
    try {
      return new URL(relative, window.location.href).href
    } catch {
      /* ignore */
    }
  }
  return relative
}

/**
 * wasm / cmaps / standard_fonts / iccs：一律指向 `public/pdfjs/`（由复制脚本从 node_modules 同步）。
 */
export function getPdfjsBinaryAssetUrls() {
  const root = getPdfjsAssetsRoot()
  return {
    wasmUrl: `${root}wasm/`,
    cMapUrl: `${root}cmaps/`,
    standardFontDataUrl: `${root}standard_fonts/`,
    iccUrl: `${root}iccs/`,
  }
}

/** getDocument 常用初始化参数（含与当前 pdfjs-dist 版本对齐的二进制资源 URL） */
export function getPdfDocumentInitParams() {
  return {
    cMapPacked: true,
    useSystemFonts: true,
    isEvalSupported: false,
    ...getPdfjsBinaryAssetUrls(),
  } as const
}

/** 从 URL 加载 PDF 文档 */
export async function loadPdfDocument(url: string): Promise<PDFDocumentProxy> {
  const loadingTask = pdfjsLib.getDocument({
    url,
    ...getPdfDocumentInitParams(),
  })
  return loadingTask.promise
}

export interface RenderPdfPageToDataUrlOptions {
  /** 视口缩放，默认 1 */
  scale?: number
  /** canvas.toDataURL 的 MIME，默认 image/jpeg */
  mimeType?: string
  /** JPEG 质量 0–1，默认 0.9 */
  quality?: number
}

/**
 * 将单页渲染为 Data URL（默认 JPEG）
 */
export async function renderPdfPageToDataUrl(
  page: PDFPageProxy,
  options?: RenderPdfPageToDataUrlOptions
): Promise<string> {
  const scale = options?.scale ?? 1.0
  const mimeType = options?.mimeType ?? 'image/jpeg'
  const quality = options?.quality ?? 0.9

  const viewport = page.getViewport({ scale })
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('无法获取 canvas 2d 上下文')
  }

  canvas.height = viewport.height
  canvas.width = viewport.width

  await page
    .render({
      canvasContext: context,
      viewport,
      canvas: canvas as unknown as HTMLCanvasElement,
    })
    .promise

  return canvas.toDataURL(mimeType, quality)
}

/** 需要直接使用 pdf.js API 时导出 */
export { pdfjsLib }
