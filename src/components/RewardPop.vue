<template>
  <ion-modal id="main" class="backdrop">
    <ion-item class="light">
      <span class="text-center w-full">恭喜获得</span>
    </ion-item>
    <div class="flex flex-col h-full items-center">
      <MdiGiftOutline class="text-red-500 mt-10 w-16 h-16" />
      <div class="font-bold text-[30px] flex mt-4 items-center">
        <MdiStar class="text-red-500" />
        <div class="ml-2">{{ props.value }}</div>
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
import MdiStar from "~icons/mdi/star";
import MdiGiftOutline from "~icons/mdi/gift-outline";
const props = defineProps({
  value: {
    type: Number,
    default: 0,
  },
});
</script>
