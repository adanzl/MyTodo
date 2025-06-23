/**
 * 计算图片在画布上的绘制位置和大小，使其在画布上居中显示。
 * @param img 图片对象
 * @param canvasWidth 画布的宽度
 * @param canvasHeight 画布的高度
 * @returns {dx, dy, drawWidth, drawHeight} 绘制位置和大小
 */
export function calcImgPos(img: HTMLImageElement, canvasWidth: number, canvasHeight: number): any {
  const imageRatio = img.width / img.height;
  const canvasRatio = canvasWidth / canvasHeight;

  let drawWidth: number, drawHeight: number;

  if (imageRatio > canvasRatio) {
    // 如果图像的宽高比大于画布的宽高比，则以画布的宽度为基准计算绘制的高度
    drawWidth = canvasWidth;
    drawHeight = canvasWidth / imageRatio;
  } else {
    // 如果图像的宽高比小于或等于画布的宽高比，则以画布的高度为基准计算绘制的宽度
    drawHeight = canvasHeight;
    drawWidth = canvasHeight * imageRatio;
  }
  // 计算图像在画布上的绘制位置，使其居中显示
  const dx = (canvasWidth - drawWidth) / 2;
  const dy = (canvasHeight - drawHeight) / 2;
  return { dx, dy, drawWidth, drawHeight };
}

export default {};
