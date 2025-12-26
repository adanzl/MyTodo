/**
 * 图片处理工具函数
 */

interface CompressOptions {
  maxWidth?: number;
  maxHeight?: number;
  format?: string;
  quality?: number;
}

/**
 * 图片压缩并转换为 Base64
 */
export async function compressImageToBase64(
  file: File,
  options: CompressOptions = {}
): Promise<string> {
  const defaultOptions = {
    maxWidth: 800,
    maxHeight: 600,
    quality: 0.8,
  };
  const opt = { ...defaultOptions, ...options };

  // 如果是SVG文件，直接读取内容
  if (file.type === "image/svg+xml") {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = e => {
        const svgContent = e.target?.result as string;
        // 检查是否是base64编码的SVG
        if (svgContent.startsWith("data:image/svg+xml;base64,")) {
          resolve(svgContent);
        } else {
          // 如果不是base64编码，则转换为base64
          const base64 = btoa(
            new TextEncoder()
              .encode(svgContent)
              .reduce((data, byte) => data + String.fromCharCode(byte), "")
          );
          resolve(`data:image/svg+xml;base64,${base64}`);
        }
      };
      reader.onerror = () => reject(`SVG读取失败: 文件读取错误`);
      reader.readAsText(file);
    });
  }

  // 根据文件类型设置输出格式
  const outputFormat = file.type === "image/png" ? "image/png" : "image/jpeg";

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.src = URL.createObjectURL(file);
    img.onload = async () => {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject("无法获取 canvas 上下文");
        return;
      }
      let [width, height] = [img.width, img.height];

      // 计算缩放尺寸
      if (width > opt.maxWidth || height > opt.maxHeight) {
        const ratio = Math.min(opt.maxWidth / width, opt.maxHeight / height);
        width = Math.floor(width * ratio);
        height = Math.floor(height * ratio);
      }

      // 绘制压缩图
      canvas.width = width;
      canvas.height = height;
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);

      // 生成Base64
      try {
        const base64 = canvas.toDataURL(outputFormat, opt.quality);
        URL.revokeObjectURL(img.src); // 释放内存
        resolve(base64);
      } catch (error) {
        reject(`压缩失败: ${error instanceof Error ? error.message : "未知错误"}`);
      }
    };

    img.onerror = error => {
      reject(`图片加载失败: ${error instanceof Error ? error.message : "未知错误"}`);
      URL.revokeObjectURL(img.src);
    };
  });
}
