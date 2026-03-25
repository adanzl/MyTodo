<template>
  <ion-modal id="reward-list-modal" class="backdrop">
    <div class="p-3 flex border-b border-gray-400 mx-6">
      <span class="text-center w-full">恭喜获得</span>
    </div>
    <div class="flex flex-col h-full items-center justify-center p-4">
      <!-- 礼物列表容器：单个元素时居中，多个元素时 2 列网格 -->
      <div 
        :class="[
            'w-full max-h-full overflow-y-auto p-4 gap-6',
            rewardList.length === 1 ? 'flex justify-center' : 'grid grid-cols-2'
        ]"
      >
        <div
          v-for="(item, index) in rewardList"
          :key="index"
          :class="[
            'flex flex-col items-center justify-center p-4 bg-linear-to-br from-rose-50 to-rose-100 rounded-xl shadow-md transition-all',
          ]"
        >
          <!-- 积分类型 -->
          <div v-if="item.rewardType === 'points'" class="flex flex-col items-center gap-3">
            <Icon icon="mdi:gift-outline" class="text-red-500 w-12 h-12" />
            <div class="text-xl font-bold text-gray-800 text-center mt-2 flex items-center">
              <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
              <span class="ml-1">{{ item.value }}</span>
            </div>
          </div>
          <!-- 礼品类型 -->
          <div v-else class="flex flex-col items-center gap-2">
            <img
              :src="getRewardImageUrl(item.img)"
              class="max-w-20 max-h-20 object-contain"
              alt=""
            />
            <div class="text-xl font-bold text-gray-800 text-center mt-2 whitespace-nowrap overflow-hidden text-ellipsis max-w-full">
                {{ item.value }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </ion-modal>
</template>

<style lang="css" scoped>
ion-modal {
    --height: 60%;
    --width: 90%;
}
</style>

<script setup lang="ts">
import { ref, watch } from "vue";
import { getPicDisplayUrl } from "@/api/api-pic";
import { getCachedPicByName, PicDisplaySize } from "@/utils/img-mgr";

interface RewardItem {
    value: string;
    rewardType: string; // 'points' or 'gift'
    img?: string;
}

const props = defineProps({
    rewardList: {
        type: Array as () => RewardItem[],
        default: () => [],
    },
});

const placeholder =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Crect fill='%23e5e7eb' width='80' height='80'/%3E%3C/svg%3E";

/** 缓存的礼品图 data URL 映射表 */
const cachedImgMap = ref<Record<string, string>>({});

function loadCachedImgs() {
    props.rewardList.forEach((item) => {
        if (item.rewardType === "gift" && item.img) {
            const raw = item.img;
            getCachedPicByName(raw, PicDisplaySize.ITEM, PicDisplaySize.ITEM).then(
                (url) => {
                    if (url) {
                        cachedImgMap.value[raw] = url;
                    }
                }
            );
        }
    });
}

watch(
    () => props.rewardList,
    () => {
        cachedImgMap.value = {};
        loadCachedImgs();
    },
    { immediate: true }
);

/** 优先使用缓存，无缓存时用接口 URL，无图时用占位 */
function getRewardImageUrl(img?: string): string {
    if (!img) return placeholder;
    if (cachedImgMap.value[img]) return cachedImgMap.value[img];
    return getPicDisplayUrl(img);
}
</script>
