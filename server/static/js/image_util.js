/**
 * 图片压缩并转换为 Base64
 * @param {File} file - 输入的图片文件（File对象）
 * @param {object} options - 配置参数（可选）
 * @param {number} options.maxWidth - 最大宽度（默认：800px）
 * @param {number} options.maxHeight - 最大高度（默认：600px）
 * @param {string} options.format - 输出格式（'image/jpeg'/'image/png'，默认：'image/jpeg'）
 * @param {number} options.quality - 压缩质量（0-1，仅JPEG有效，默认：0.8）
 * @returns {Promise<string>} - 压缩后的Base64字符串
 */
export async function compressImageToBase64(file, options = {}) {
  const defaultOptions = {
    maxWidth: 800,
    maxHeight: 600,
    quality: 0.8,
  };
  const opt = { ...defaultOptions, ...options };

  // 如果是SVG文件，直接读取内容
  if (file.type === 'image/svg+xml') {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const svgContent = e.target.result;
        // 检查是否是base64编码的SVG
        if (svgContent.startsWith('data:image/svg+xml;base64,')) {
          resolve(svgContent);
        } else {
          // 如果不是base64编码，则转换为base64
          const base64 = btoa(new TextEncoder().encode(svgContent).reduce((data, byte) => data + String.fromCharCode(byte), ''));
          resolve(`data:image/svg+xml;base64,${base64}`);
        }
      };
      reader.onerror = (error) => reject(`SVG读取失败: ${error.message}`);
      reader.readAsText(file);
    });
  }

  // 根据文件类型设置输出格式
  const outputFormat = file.type === 'image/png' ? 'image/png' : 'image/jpeg';

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.src = URL.createObjectURL(file);
    img.onload = async () => {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
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
        reject(`压缩失败: ${error.message}`);
      }
    };

    img.onerror = (error) => {
      reject(`图片加载失败: ${error.message}`);
      URL.revokeObjectURL(img.src);
    };
  });
}

