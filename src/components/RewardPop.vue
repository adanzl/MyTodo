<template>
  <ion-modal id="main" class="backdrop" :is-open="!!current" @didDismiss="onDismiss">
    <div class="p-4 flex border-b border-gray-400 mx-6">
      <span class="text-center w-full">获得</span>
    </div>
    <div
      class="flex flex-col h-full items-center justify-center"
      v-if="current?.rewardType === 'points'">
      <Icon icon="mdi:gift-outline" class="text-red-500 mt-0 w-16 h-16" />
      <div class="font-bold text-[30px] flex mt-4 items-center">
        <Icon icon="mdi:star" class="text-red-500" />
        <div class="ml-2">{{ current?.value }}</div>
      </div>
    </div>
    <div class="flex flex-col h-full items-center justify-center gap-2" v-else>
      <img :src="rewardImgUrl" class="max-w-[50%] max-h-[50%] object-contain" alt="" />
      <div class="font-bold text-[30px] flex items-center">
        <div class="">{{ current?.value }}</div>
      </div>
    </div>
    <div class="items-center text-xm px-4 py-2" v-if="current?.msg">
      <div class="">{{ current?.msg }}</div>
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
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { getPicDisplayUrl } from "@/api/api-pic";
import { getCachedPicByName, PicDisplaySize } from "@/utils/img-mgr";
import EventBus, { C_EVENT } from "@/types/event-bus";

type RewardItem = {
  value: string;
  rewardType: string;
  img?: string;
  msg?: string;
};

const pending: RewardItem[] = [];
const current = ref<RewardItem | null>(null);

function enqueue(params: any) {
  pending.push({
    value: String(params?.value ?? "0"),
    rewardType: params?.rewardType || "points",
    img: params?.img || "",
    msg: params?.msg || "",
  });
  showNext();
}

function showNext() {
  if (current.value || pending.length === 0) return;
  current.value = pending.shift()!;
}

async function onDismiss() {
  current.value = null;
  if (!pending.length) return;
  // ion-modal 关完才能再开，否则第二次 is-open 会被吞掉
  await new Promise((r) => setTimeout(r, 500));
  showNext();
}

onMounted(() => EventBus.$on(C_EVENT.REWARD, enqueue));
onUnmounted(() => EventBus.$off(C_EVENT.REWARD, enqueue));

const cachedImgUrl = ref("");

function loadCachedImg() {
  const raw = current.value?.img;
  if (!raw) {
    cachedImgUrl.value = "";
    return;
  }
  getCachedPicByName(raw, PicDisplaySize.ITEM, PicDisplaySize.ITEM).then((url) => {
    cachedImgUrl.value = url || "";
  });
}

watch(
  () => current.value?.img,
  () => loadCachedImg(),
  { immediate: true }
);

const rewardImgUrl = computed(() => {
  const raw = current.value?.img;
  if (cachedImgUrl.value) return cachedImgUrl.value;
  return getPicDisplayUrl(raw);
});
</script>
