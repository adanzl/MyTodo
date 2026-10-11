/**
 * 「点缩略图看大图」的共用状态与开启函数。
 *
 * 视觉与交互由公共组件 `@/components/ImagePreview.vue` 负责，这里只做
 * 「文件名 → 可渲染的预览项」这一步转换，供 TabAiChat 与 TabChatRoom 共用
 * （原先两处各复制了一份逐字相同的实现）。
 *
 * 注意 PageChat 的待发区图片是**本地 blob URL**（`item.previewUrl`，发送前的本地预览，
 * 不是服务器文件名），且列表来自 computed，数据来源不同，故未纳入本 composable。
 */

import { ref } from "vue";
import { getPicDisplayUrl } from "@/api/api-pic";
import type { PreviewImage } from "@/components/ImagePreview.vue";

export type { PreviewImage };

export interface ImagePreviewState {
  open: boolean;
  index: number;
  images: PreviewImage[];
}

export function useImagePreview() {
  const imagePreview = ref<ImagePreviewState>({ open: false, index: 0, images: [] });

  /** 用 pic 查看接口的原始尺寸（不传 w/h）打开第 index 张 */
  function openImagePreview(names: string[], index = 0) {
    imagePreview.value = {
      open: true,
      index,
      images: names.map((name) => ({ src: getPicDisplayUrl(name), alt: name })),
    };
  }

  return { imagePreview, openImagePreview };
}
