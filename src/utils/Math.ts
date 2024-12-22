export function calcImgPos(img: HTMLImageElement, canvasWidth: number, canvasHeight: number) {
  // 计算图像的宽高比
  const imageRatio = img.width / img.height;
  // 计算画布的宽高比
  const canvasRatio = canvasWidth / canvasHeight;

  let drawWidth, drawHeight;

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

export default {
  calcImgPos,
};
