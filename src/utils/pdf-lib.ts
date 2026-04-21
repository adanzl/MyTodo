/**
 * PDF 工具函数
 * 提供 PDF 渲染相关功能
 */
import * as pdfjsLib from 'pdfjs-dist';

// 设置 worker 源为本地包
// 注意：在 Vite 项目中，需要从 node_modules 中导入
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

/**
 * 加载 PDF 文档
 * @param url - PDF 文件 URL
 * @returns PDF 文档对象
 */
export async function loadPDF(url: string) {
  try {
    const loadingTask = pdfjsLib.getDocument(url);
    const pdf = await loadingTask.promise;
    return pdf;
  } catch (error) {
    console.error('加载 PDF 失败:', error);
    throw error;
  }
}

/**
 * 获取 PDF 页面
 * @param pdf - PDF 文档对象
 * @param pageNumber - 页码（从 1 开始）
 * @returns PDF 页面对象
 */
export async function getPDFPage(pdf: any, pageNumber: number) {
  try {
    const page = await pdf.getPage(pageNumber);
    return page;
  } catch (error) {
    console.error(`获取第 ${pageNumber} 页失败:`, error);
    throw error;
  }
}

/**
 * 渲染 PDF 页面到 Canvas
 * @param page - PDF 页面对象
 * @param canvas - Canvas 元素
 * @param scale - 缩放比例，默认 1.5
 */
export async function renderPDFPageToCanvas(
  page: any,
  canvas: HTMLCanvasElement,
  scale: number = 1.5
) {
  try {
    const viewport = page.getViewport({ scale });
    
    // 设置 canvas 尺寸
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('无法获取 canvas 上下文');
    }
    
    // 渲染配置
    const renderContext = {
      canvasContext: context,
      viewport: viewport,
    };
    
    await page.render(renderContext).promise;
  } catch (error) {
    console.error('渲染 PDF 页面失败:', error);
    throw error;
  }
}

/**
 * 将 PDF 页面渲染为图片 Data URL
 * @param page - PDF 页面对象
 * @param scale - 缩放比例，默认 1.5
 * @returns Data URL
 */
export async function renderPDFPageToImage(
  page: any,
  scale: number = 1.5
): Promise<string> {
  const canvas = document.createElement('canvas');
  await renderPDFPageToCanvas(page, canvas, scale);
  return canvas.toDataURL('image/png');
}

/**
 * 获取 PDF 总页数
 * @param pdf - PDF 文档对象
 * @returns 总页数
 */
export function getPDFPageCount(pdf: any): number {
  return pdf.numPages;
}
