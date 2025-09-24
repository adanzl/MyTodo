<template>
  <ion-modal id="main" class="backdrop">
    <ion-item class="light">
      <span class="text-center w-full">恭喜获得</span>
    </ion-item>
    <div class="flex flex-col h-full items-center" v-if="props.rewardType === 'points'">
      <Icon icon="mdi:gift-outline" class="text-red-500 mt-10 w-16 h-16" />
      <div class="font-bold text-[30px] flex mt-4 items-center">
        <Icon icon="mdi:star" class="text-red-500" />
        <div class="ml-2">{{ props.value }}</div>
      </div>
    </div>
    <div class="flex flex-col h-full items-center" v-else>
      <img :src="props.img" class="w-20 h-20 mt-5" />
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
</script>
