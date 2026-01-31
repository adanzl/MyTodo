<template>
  <ion-button
    class="absolute rounded-full ion-no-padding"
    :disabled="disabled"
    @touchmove="onTouchMove"
    :style="{ right: posR + ' !important', bottom: posB + ' !important' }">
    <slot></slot>
  </ion-button>
</template>
<style lang="css" scoped>
.rounded-full::part(native) {
  border-radius: 50%;
  padding: 10px;
}
</style>
<script lang="ts" setup>
import { ref } from "vue";
const props = defineProps({
  bottom: String,
  right: String,
  hasBar: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

const posR = ref(props.right ?? "0px");
const posB = ref(props.bottom ?? "0px");
function onTouchMove(event: any) {
  const barHeight = props.hasBar ? document.getElementsByTagName("ion-tab-bar")[0].clientHeight : 0;
  // 获取触摸点相对于屏幕的位置
  const touch = event.touches[0];
  const cX = touch.clientX;
  const cY = touch.clientY;

  // 计算按钮的新位置
  const bWidth = event.target.clientWidth;
  const bHeight = event.target.clientHeight;
  const screenWidth = window.innerWidth;
  const screenHeight = window.innerHeight;

  posR.value = Math.max(0, Math.min(screenWidth - bWidth, screenWidth - cX - bWidth / 2)) + "px";
  posB.value =
    Math.max(0, Math.min(screenHeight / 2 - bHeight, screenHeight - cY - bHeight / 2 - barHeight)) +
    "px";
  //   console.log(posR.value, posB.value);
}
</script>
