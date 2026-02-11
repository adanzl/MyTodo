import LocalCache from "./LocalCache.ts";
import { calcImgPos } from "./Math.ts";
import { delPic, getPic, setPic, getPicDisplayUrl } from "@/api/pic";

/** 图片展示尺寸 */
export const PicDisplaySize = {
  /** 列表缩略图 */
  LIST: 96,
  /** 详情/弹窗展示 */
  ITEM: 160,
} as const;

/** 上传图片尺寸限制（与 TTS 任务拍照一致） */
export const PicUploadLimit = {
  MAX_WIDTH: 1920,
  MAX_HEIGHT: 1080,
} as const;

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

/**
 * 根据文件名获取图片的本地缓存（data URL），若本地无缓存则从服务端拉取并写入缓存。
 * 适用于 `/pic/view?name=xxx&w=..&h=..` 这类按文件名访问的图片。
 * @param name  图片文件名，如 image_29.jpg
 * @param w     目标宽度，对应接口的 w 参数
 * @param h     目标高度，对应接口的 h 参数
 * @param ttl   缓存时长（秒），默认 1 小时
 */
export async function getCachedPicByName(
  name: string,
  w?: number,
  h?: number,
  ttl: number = 60 * 60
): Promise<string> {
  if (!name) return "";

  const key = `pic_file_${name}_${w || 0}_${h || 0}`;
  const cached = LocalCache.get<string>(key);
  if (cached) {
    return cached;
  }

  const url = getPicDisplayUrl(name, w, h);
  try {
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error("图片加载失败");
    }
    const blob = await resp.blob();

    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result as string);
      reader.onerror = () => reject(new Error("图片读取失败"));
      reader.readAsDataURL(blob);
    });

    // 写入本地缓存（localStorage），后续直接用 data URL 展示，无需再次走网络
    LocalCache.set(key, dataUrl, ttl);
    return dataUrl;
  } catch (err) {
    // 失败时退回原始 URL，至少能正常展示
    console.warn("getCachedPicByName fail:", err);
    return url;
  }
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

/**
 * 将图片等比缩放到最大限制尺寸（与 TTS 拍照、礼品上传一致），返回新的 File
 * @param file 原始图片文件
 * @returns 缩放后的 File，若无需缩放则返回原文件
 */
export async function resizeImageToFile(file: File): Promise<File> {
  if (file.type === "image/svg+xml") {
    return file;
  }

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.src = URL.createObjectURL(file);
    img.onload = () => {
      let { width, height } = { width: img.width, height: img.height };

      if (width <= PicUploadLimit.MAX_WIDTH && height <= PicUploadLimit.MAX_HEIGHT) {
        URL.revokeObjectURL(img.src);
        resolve(file);
        return;
      }

      const ratio = Math.min(PicUploadLimit.MAX_WIDTH / width, PicUploadLimit.MAX_HEIGHT / height);
      width = Math.floor(width * ratio);
      height = Math.floor(height * ratio);

      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        URL.revokeObjectURL(img.src);
        reject(new Error("无法获取 canvas 上下文"));
        return;
      }
      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(img.src);

      const outputFormat = file.type === "image/png" ? "image/png" : "image/jpeg";
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("压缩失败"));
            return;
          }
          const ext = file.name.split(".").pop() || "jpg";
          const baseName = file.name.replace(/\.[^.]+$/, "");
          resolve(new File([blob], `${baseName}.${ext}`, { type: blob.type }));
        },
        outputFormat,
        0.85
      );
    };
    img.onerror = () => {
      URL.revokeObjectURL(img.src);
      reject(new Error("图片加载失败"));
    };
  });
}

export default {};
