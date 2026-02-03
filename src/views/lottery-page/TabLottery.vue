<template>
  <ion-segment-content id="lotterySpecial">
    <ion-content>
      <ion-item>
        <div class="flex items-center justify-center">
          <span>当前积分：</span>
          <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
          <div class="text-left pl-1 font-bold w-12">{{ userScore }}</div>
        </div>
      </ion-item>
      <ion-radio-group
        :value="selectedCate"
        class="radio-grid"
        @ionChange="onCateChangeFromRadio">
        <ion-radio
          v-for="item in lotteryCatList"
          :key="item.id"
          :value="item"
          label-placement="end"
          justify="start">
          <span class="text-black">{{ item.name }}</span>
        </ion-radio>
      </ion-radio-group>
      <div class="flex items-center justify-center bg-slate-400 h-[calc(100%-300px)]">
        <ion-button
          @click="$emit('lottery')"
          size="default"
          :disabled="userScore < selectedCate.cost">
          <div class="w-20 h-20 flex flex-col items-center justify-center">
            <span>立即抽奖</span>
            <div class="flex items-center justify-center mt-2">
              <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
              {{ selectedCate.cost }}
            </div>
          </div>
        </ion-button>
      </div>
      <!-- 心愿单 -->
      <div class="px-4">
        <div class="flex items-end justify-between h-12 mb-2">
          <div class="w-24 text-2xl text-blue-500 font-bold">心愿单</div>
          <div class="">
            <div class="text-right text-xs text-gray-500 mr-2">
              进度满足时必定获得心愿单内容
              {{ wishList.progress }}%
            </div>
            <progress
              class="progress progress-primary w-56 h-3"
              :value="wishList.progress"
              max="100"></progress>
          </div>
        </div>
        <swiper
          v-if="wishList.data.length > 0"
          class="py-4"
          :modules="[FreeMode]"
          :slidesPerView="'auto'"
          :resistance="true"
          :resistanceRatio="0.5"
          :momentum-ratio="0.5"
          @swiper="setSwiperInstance">
          <swiper-slide v-for="item in wishList.data" :key="item.id" class="!w-auto px-2">
            <div class="w-24 h-24 relative">
              <img :src="item.img" class="w-full h-full object-cover rounded-lg" />
              <div
                class="absolute top-0 right-0 bg-amber-300 w-6 h-6 flex items-center justify-center"
                @click="$emit('remove-wish', item)">
                x
              </div>
              <div
                class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-1 rounded-b-lg truncate">
                {{ item.name }}
              </div>
            </div>
          </swiper-slide>
        </swiper>
        <ion-card v-else class="m-4 ion-padding">
          <ion-card-content>
            <div class="text-center text-gray-500">暂无心愿单内容</div>
          </ion-card-content>
        </ion-card>
      </div>
    </ion-content>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonButton,
  IonCard,
  IonCardContent,
  IonContent,
  IonItem,
  IonRadio,
  IonRadioGroup,
  IonSegmentContent,
} from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import { Icon } from "@iconify/vue";
import "swiper/css";
import "swiper/css/free-mode";
import { FreeMode } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { ref } from "vue";

defineProps<{
  lotteryCatList: any[];
  selectedCate: any;
  wishList: { progress: number; ids: number[]; data: any[] };
  lotteryData: any;
  userScore: number;
}>();

const emit = defineEmits<{
  (e: "cate-change", value: any): void;
  (e: "lottery"): void;
  (e: "remove-wish", item: any): void;
}>();

const swiperRef = ref();

function setSwiperInstance(swiper: any) {
  swiperRef.value = swiper;
  swiper.update();
}

function onCateChangeFromRadio(event: any) {
  emit("cate-change", event.detail.value);
}
</script>

<style scoped>
.radio-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 8px 18px;
}

.radio-grid ion-radio {
  margin: 0;
  --padding-start: 0;
}
</style>
