<template>
  <ion-modal id="main" class="backdrop">
    <div class="p-4 flex border-b border-gray-400 mx-6">
      <span class="text-center w-full">恭喜获得</span>
    </div>
    <div class="flex flex-col h-full items-center justify-center" v-if="props.rewardType === 'points'">
      <Icon icon="mdi:gift-outline" class="text-red-500 mt-0 w-16 h-16" />
      <div class="font-bold text-[30px] flex mt-4 items-center">
        <Icon icon="mdi:star" class="text-red-500" />
        <div class="ml-2">{{ props.value }}</div>
      </div>
    </div>
    <div class="flex flex-col h-full items-center" v-else>
      <img :src="rewardImgUrl" class="max-w-[50%] max-h-[50%] mt-5 object-contain" alt="" />
      <div class="font-bold text-[30px] flex mt-4 items-center">
        <div class="">{{ props.value }}</div>
      </div>
    </div>
  </ion-modal>
</template>
<style lang="css" scoped>
ion-modal {
  --height: 50%;
  --width: 80%;
}
</style>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { getPicDisplayUrl } from "@/api/pic";
import { getCachedPicByName, PicDisplaySize } from "@/utils/ImgMgr";

const props = defineProps({
  value: {
    type: String,
    default: "0",
  },
  rewardType: {
    type: String,
    default: "points", // points or gift
  },
  img: {
    type: String,
    default: "",
  },
});

const placeholder =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Crect fill='%23e5e7eb' width='80' height='80'/%3E%3C/svg%3E";

/** 缓存的礼品图 data URL，弹窗内展示用 */
const cachedImgUrl = ref("");

function loadCachedImg() {
  const raw = props.img;
  if (!raw) {
    cachedImgUrl.value = "";
    return;
  }
  getCachedPicByName(raw, PicDisplaySize.ITEM, PicDisplaySize.ITEM).then(
    (url) => {
      cachedImgUrl.value = url || "";
    }
  );
}

watch(
  () => props.img,
  () => loadCachedImg(),
  { immediate: true }
);

/** 优先使用缓存，无缓存时用接口 URL，无图时用占位 */
const rewardImgUrl = computed(() => {
  const raw = props.img;
  if (!raw) return placeholder;
  if (cachedImgUrl.value) return cachedImgUrl.value;
  return getPicDisplayUrl(raw);
});
</script>
