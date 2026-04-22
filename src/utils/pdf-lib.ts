/**
 * PDF 工具函数
 * 提供 PDF 渲染相关功能
 */
import * as pdfjsLib from 'pdfjs-dist/legacy/build/pdf.mjs';
import workerSrc from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

// legacy 版本对 Android WebView 兼容更好
pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

const isAndroid = /Android/i.test(navigator.userAgent);

/**
 * 加载 PDF 文档
 * @param url - PDF 文件 URL
 * @returns PDF 文档对象
 */
export async function loadPDF(url: string) {
  try {
    let loadingTask = pdfjsLib.getDocument({
      url,
      // 安卓 WebView 经常出现 worker 初始化失败，默认走主线程可避免白屏
      disableWorker: isAndroid,
      // 提升兼容性，避免部分设备字体/解码异常
      useSystemFonts: true,
      isEvalSupported: false,
    } as any);

    try {
      return await loadingTask.promise;
    } catch (workerError) {
      if (!isAndroid) {
        console.warn('PDF worker 模式失败，降级为 disableWorker:', workerError);
        loadingTask.destroy();
        loadingTask = pdfjsLib.getDocument({
          url,
          disableWorker: true,
          useSystemFonts: true,
          isEvalSupported: false,
        } as any);
      } else {
        throw workerError;
      }
    }
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
  scale?: number
) {
  try {
    const defaultScale = isAndroid ? 0.9 : 1.2;
    const finalScale = scale ?? defaultScale;
    const viewport = page.getViewport({ scale: finalScale });
    
    // 控制尺寸，避免移动端内存占用过高导致白屏
    const MAX_CANVAS_SIZE = 3072;
    let width = viewport.width;
    let height = viewport.height;
    if (width > MAX_CANVAS_SIZE || height > MAX_CANVAS_SIZE) {
      const ratio = Math.min(MAX_CANVAS_SIZE / width, MAX_CANVAS_SIZE / height);
      width = Math.floor(width * ratio);
      height = Math.floor(height * ratio);
    }

    canvas.height = height;
    canvas.width = width;
    
    const context = canvas.getContext('2d', { alpha: false });
    if (!context) {
      throw new Error('无法获取 canvas 上下文');
    }

    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    
    // 渲染配置
    const renderContext = {
      canvasContext: context,
      viewport: page.getViewport({ scale: finalScale * (width / viewport.width) }),
      enableWebGL: false,
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
