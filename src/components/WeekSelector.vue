<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    id="repeatSelector"
    class="backdrop"
    @ionModalDidDismiss="onModalDismiss">
    <ion-item>
      <ion-title>自定义日期</ion-title>
    </ion-item>
    <div class="w-full h-full px-6 mb-1">
      <ion-list>
        <ion-item v-for="(w, idx) in WEEK" :value="idx" :key="idx" lines="none">
          <ion-checkbox @ionChange="onCheckboxChange($event, idx)" :checked="valueRef.has(idx)">
            {{ w }}
          </ion-checkbox>
        </ion-item>
      </ion-list>
    </div>
    <ion-footer class="flex">
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()"> 取消 </ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()"> 确定 </ion-button>
    </ion-footer>
  </ion-modal>
</template>
<style lang="css" scoped>
ion-modal {
  --width: 80%;
  --height: fit-content;
}
ion-footer {
  border-top-width: 1px;
}
</style>
<script setup lang="ts">
import { IonCheckbox } from "@ionic/vue";
import { WEEK } from "@/types/ScheduleType";
import { ref } from "vue";
const modal = ref();
const props = defineProps({
  value: {
    type: Object,
    default: null,
  },
});
const valueRef = ref<Set<number>>(
  props.value && props.value.week ? new Set(props.value.week) : new Set()
);
const emits = defineEmits(["update:value"]);

function onCheckboxChange(e: CustomEvent, idx: number) {
  if (e.detail.checked) {
    valueRef.value.add(idx);
  } else {
    valueRef.value.delete(idx);
  }
}
function onModalDismiss() {}
function cancel() {
  modal.value.$el!.dismiss();
}
function confirm() {
  emits("update:value", [...valueRef.value]);
  modal.value.$el!.dismiss();
}
</script>
