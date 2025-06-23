import LocalCache from "./LocalCache.ts";
import { calcImgPos } from "./Math.ts";
import { delPic, getPic, setPic } from "./NetUtil.ts";

export async function getImage(id?: number) {
  if(id === undefined){
    return '';
  }
  let ret = LocalCache.get<string>("img_" + id);
  if (ret === null) {
    ret = await getPic(id);
    if (ret) {
      LocalCache.set("img_" + id, ret, 10 * 60);
    }
  }
  return ret;
}

export async function setImage(id: number | undefined, data: string) {
  // console.log("setImage", id, data);
  const ret = await setPic(id, data);
  LocalCache.remove("img_" + id);
  return ret;
}

export async function delImage(id: number) {
  console.log("delImage", id);
  const ret = await delPic(id);
  LocalCache.remove("img_" + id);
  return ret;
}

/**
 * load image and save to server and return image id
 * 加载图片并保存到服务器并返回图片id
 * @param imgId 图片id 如果为undefined则新增，否则更新
 * @param canvasHeight 画布高度
 * @param canvasWidth 画布宽度
 * @returns
 */
export async function loadAndSetImage(
  imgId: number | undefined,
  canvasHeight?: number,
  canvasWidth?: number
): Promise<number | null> {
  return new Promise((resolve) => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/*";
    fileInput.addEventListener("change", async (event: any) => {
      const file = event.target?.files[0];
      if (!file) {
        resolve(null);
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const imageUrl = e.target!.result as string;
        const img = new Image();
        img.src = imageUrl;
        img.onload = () => {
          if (canvasWidth === undefined) canvasWidth = img.width;
          if (canvasHeight === undefined) canvasHeight = img.height;
          const { drawWidth, drawHeight } = calcImgPos(img, canvasWidth, canvasHeight);
          const canvas = document.createElement("canvas");
          canvas.width = drawWidth;
          canvas.height = drawHeight;
          console.log("canvas", drawHeight, drawWidth);
          const ctx = canvas.getContext("2d");
          if (!ctx) {
            resolve(null);
            return;
          }
          ctx.clearRect(0, 0, canvasWidth, canvasHeight);
          ctx.drawImage(img, 0, 0, drawWidth, drawHeight);
          canvas.toBlob((blob: any) => {
            const reader = new FileReader();
            reader.onload = async () => {
              const base64 = reader.result as string;
              const ret = await setImage(imgId, base64);
              return resolve(parseInt(ret));
            };
            reader.readAsDataURL(blob);
          }, "image/webp");
        };
      };
      reader.readAsDataURL(file);
    });
    fileInput.click();
  });
}
/**
 * 拍照图片并保存到服务器并返回图片id
 * @param imgId 图片id 如果为undefined则新增，否则更新
 * @param canvasHeight 画布高度
 * @param canvasWidth 画布宽度
 * @returns
 */
export async function cameraAndSetImage(
  imgId: number | undefined,
  canvasHeight?: number,
  canvasWidth?: number
): Promise<number | null> {
  return new Promise((resolve) => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/*";
    fileInput.capture = "camera";
    fileInput.addEventListener("change", async (event: any) => {
      const file = event.target?.files[0];
      if (!file) {
        resolve(null);
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const imageUrl = e.target!.result as string;
        const img = new Image();
        img.src = imageUrl;
        img.onload = () => {
          if (canvasWidth === undefined) canvasWidth = img.width;
          if (canvasHeight === undefined) canvasHeight = img.height;
          const { drawWidth, drawHeight } = calcImgPos(img, canvasWidth, canvasHeight);
          const canvas = document.createElement("canvas");
          canvas.width = drawWidth;
          canvas.height = drawHeight;
          console.log("canvas", drawHeight, drawWidth);
          const ctx = canvas.getContext("2d");
          if (!ctx) {
            resolve(null);
            return;
          }
          ctx.clearRect(0, 0, canvasWidth, canvasHeight);
          ctx.drawImage(img, 0, 0, drawWidth, drawHeight);
          canvas.toBlob((blob: any) => {
            const reader = new FileReader();
            reader.onload = async () => {
              const base64 = reader.result as string;
              const ret = await setImage(imgId, base64);
              return resolve(parseInt(ret));
            };
            reader.readAsDataURL(blob);
          }, "image/webp");
        };
      };
      reader.readAsDataURL(file);
    });
    fileInput.click();
  });
}
export default {};
