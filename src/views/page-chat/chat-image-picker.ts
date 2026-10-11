/**
 * 对话输入区（AI 对话 / 聊天室）待处理图片的本地管理逻辑。
 *
 * 职责是「选择 + 预览 + 上传状态 + 释放」：
 * - 本模块不发任何网络请求，上传由调用方负责，只把结果写回 `filename`；
 * - 发送时只需读取 `filename`（服务端据此把图片转成 Dify 的文件 id）。
 */

/** 一张已选中、等待后续处理的图片。 */
export interface PendingImage {
  /** 原始文件，上传时直接复用 */
  file: File;
  /** 预览用 object URL；移除时必须 revoke，否则图片数据不会被释放 */
  previewUrl: string;
  /** 上传到本服务后的文件名；有值即表示可用于发送 */
  filename?: string;
  /** 正在上传到本服务 */
  uploading?: boolean;
  /** 上传失败原因（面向用户展示） */
  error?: string;
}

/**
 * 单次对话允许的图片数量上限（默认值）。
 *
 * 这个数字存在 chat setting 里（键名 `maxImages`），没有前端 UI，改的是数据。
 * 这里只作为缺省/非法值的兜底，实际生效值由调用方从 setting 读出后传进来。
 *
 * 注意：它还必须不大于 Dify 应用「文件上传」的 `number_limits`（当前 3），
 * 否则服务端会以 400 拒绝整条消息。本地只是提前拦一次、给出更快的反馈。
 */
export const DEFAULT_MAX_PENDING_IMAGES = 3;

/** 解析 setting 里的图片上限：只接受 >=1 的整数，其余一律回落到默认值。 */
export function normalizeMaxImages(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return DEFAULT_MAX_PENDING_IMAGES;
  const int = Math.floor(n);
  return int >= 1 ? int : DEFAULT_MAX_PENDING_IMAGES;
}

/** addPendingImages 的逐张统计，供调用方提示用户。 */
export interface AddPendingImagesResult {
  /** 成功加入列表的数量 */
  added: number;
  /** 因不是图片被忽略的数量 */
  rejected: number;
  /** 因超出数量上限被忽略的数量 */
  overflow: number;
}

export type CreatePreviewUrl = (file: File) => string;
export type RevokePreviewUrl = (url: string) => void;

function defaultCreatePreviewUrl(file: File): string {
  return URL.createObjectURL(file);
}

function defaultRevokePreviewUrl(url: string): void {
  URL.revokeObjectURL(url);
}

/**
 * 是否为可预览的图片。
 *
 * 少部分安卓 WebView（拍照/相机直出）会给出空 MIME，因此 type 为空时按扩展名兜底。
 */
export function isImageFile(file: File): boolean {
  const type = (file.type || "").toLowerCase();
  if (type) return type.startsWith("image/");
  return /\.(jpe?g|png|gif|webp|bmp|heic|heif)$/i.test(file.name || "");
}

/**
 * 把用户选中的文件并入待处理列表（保持选择顺序），跳过非图片与超出上限的文件。
 *
 * 直接在传入的数组上追加，便于组件把 `ref([])` 里的数组直接传进来。
 *
 * @param maxImages 本次允许的数量上限，由调用方从 chat setting 读出
 *                  （缺省则用 `DEFAULT_MAX_PENDING_IMAGES`）
 */
export function addPendingImages(
  images: PendingImage[],
  files: readonly File[],
  createPreviewUrl: CreatePreviewUrl = defaultCreatePreviewUrl,
  maxImages: number = DEFAULT_MAX_PENDING_IMAGES
): AddPendingImagesResult {
  const limit = normalizeMaxImages(maxImages);
  const result: AddPendingImagesResult = { added: 0, rejected: 0, overflow: 0 };
  for (const file of files) {
    if (!isImageFile(file)) {
      result.rejected += 1;
      continue;
    }
    if (images.length >= limit) {
      result.overflow += 1;
      continue;
    }
    images.push({ file, previewUrl: createPreviewUrl(file) });
    result.added += 1;
  }
  return result;
}

/**
 * 移除第 index 张图片并释放其预览 URL。
 *
 * 返回被移除的那一项（越界时返回 undefined）——调用方需要用它的 `filename` 去
 * 删服务器上的副本，所以这里把结果交出去而不是只返回布尔值。
 */
export function removePendingImage(
  images: PendingImage[],
  index: number,
  revokePreviewUrl: RevokePreviewUrl = defaultRevokePreviewUrl
): PendingImage | undefined {
  const target = images[index];
  if (!target) return undefined;
  images.splice(index, 1);
  if (target.previewUrl) revokePreviewUrl(target.previewUrl);
  return target;
}

/**
 * 清空列表并释放全部预览 URL，返回释放的数量。
 *
 * 只做本地清理，**不会**删除服务器上的文件：发送成功后的图片已经被消息引用，
 * 必须保留。要丢弃「还没发出去」的图片请用 `discardPendingImages`。
 */
export function clearPendingImages(
  images: PendingImage[],
  revokePreviewUrl: RevokePreviewUrl = defaultRevokePreviewUrl
): number {
  let revoked = 0;
  for (const item of images) {
    if (item.previewUrl) {
      revokePreviewUrl(item.previewUrl);
      revoked += 1;
    }
  }
  images.length = 0;
  return revoked;
}

/**
 * 丢弃列表中的待发图片：返回它们各自在服务器上的文件名，供调用方逐个删除。
 *
 * 与 `clearPendingImages` 的区别就在这里——这些图片从未被发送，服务器上那份是
 * 多余的，必须删掉，否则会一直留在 pic 目录里变成孤儿文件。
 */
export function discardPendingImages(
  images: PendingImage[],
  revokePreviewUrl: RevokePreviewUrl = defaultRevokePreviewUrl
): string[] {
  const filenames: string[] = [];
  for (const item of images) {
    if (item.filename) filenames.push(item.filename);
  }
  clearPendingImages(images, revokePreviewUrl);
  return filenames;
}

/** 收集可以发送的文件名（上传成功且未失败），顺序与预览一致。 */
export function readyImageFilenames(images: readonly PendingImage[]): string[] {
  const names: string[] = [];
  for (const item of images) {
    if (item.filename && !item.error) names.push(item.filename);
  }
  return names;
}

/** MIME -> 扩展名。按实际内容取后缀，避免出现「.bmp 里装着 jpeg」这类名不符实。 */
const MIME_EXTENSIONS: Record<string, string> = {
  "image/png": "png",
  "image/jpeg": "jpg",
  "image/webp": "webp",
  "image/gif": "gif",
  "image/bmp": "bmp",
};

/**
 * 生成上传到 pic 目录时使用的文件名：`chat-<userId>-<时间戳>.<ext>`。
 *
 * 不用用户原始文件名：原始名可能重复、无意义或含特殊字符，而这个名称会一路带到
 * pic 目录、Dify 的历史消息，并被前端用来拼 `/pic/view?name=`，需要稳定可控。
 */
export function buildChatImageName(
  userId: string | number,
  file: File,
  timestamp: number = Date.now()
): string {
  const safeUser = String(userId ?? "").replace(/[^\w-]/g, "") || "anon";
  const ext =
    MIME_EXTENSIONS[(file.type || "").toLowerCase()] ||
    (file.name.match(/\.([^.]+)$/)?.[1] || "jpg").toLowerCase();
  return `chat-${safeUser}-${timestamp}.${ext}`;
}

/** 是否仍有图片在上传中（发送前需要等它完成）。 */
export function hasUploadingImages(images: readonly PendingImage[]): boolean {
  return images.some((item) => item.uploading);
}

/** 是否存在上传失败的图片（发送前需要提示用户先移除）。 */
export function hasFailedImages(images: readonly PendingImage[]): boolean {
  return images.some((item) => Boolean(item.error));
}
