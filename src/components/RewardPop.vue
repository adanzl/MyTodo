<template>
  <ion-modal id="main" class="backdrop">
    <div class="p-4 flex border-b border-gray-400 mx-6">
      <span class="text-center w-full">恭喜获得</span>
    </div>
    <div class="flex flex-col h-full items-center" v-if="props.rewardType === 'points'">
      <Icon icon="mdi:gift-outline" class="text-red-500 mt-10 w-16 h-16" />
      <div class="font-bold text-[30px] flex mt-4 items-center">
        <Icon icon="mdi:star" class="text-red-500" />
        <div class="ml-2">{{ props.value }}</div>
      </div>
    </div>
    <div class="flex flex-col h-full items-center" v-else>
      <img :src="rewardImgUrl" class="w-20 h-20 mt-5 object-contain" alt="" />
      <div class="font-bold text-[30px] flex mt-4 items-center">
        <div class="">{{ props.value }}</div>
      </div>
    </div>
  </ion-modal>
</template>
<style lang="css" scoped>
ion-modal {
  --height: 30%;
  --width: 80%;
}
</style>

<script setup lang="ts">
import { computed } from "vue";
import { getPicDisplayUrl } from "@/api/pic";

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

/** 详情用原始图片 */
const rewardImgUrl = computed(() => {
  const raw = props.img;
  if (!raw) return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Crect fill='%23e5e7eb' width='80' height='80'/%3E%3C/svg%3E";
  return getPicDisplayUrl(raw);
});
</script>
