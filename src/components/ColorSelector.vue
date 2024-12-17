<template>
  <ion-modal ref="modal" aria-hidden="true">
    <ion-item>
      <ion-title>Color</ion-title>
    </ion-item>
    <ion-content class="ion-padding">
      <ion-item>
        <ion-radio-group :value="valueRef" @ionChange="onSelectChange">
          <ion-radio
            v-for="(op, idx) in ColorOptions"
            :key="idx"
            :value="op.id">
            <span :style="{ 'background-color': op.tag }" class="v-dot"></span>
            {{ op.label }}
          </ion-radio>
        </ion-radio-group>
      </ion-item>
    </ion-content>
    <ion-footer mode="ios">
      <ion-button style="width: 40%" fill="clear" @click="cancel()">Cancel</ion-button>
      <ion-button style="width: 40%" fill="clear" @click="confirm()">OK</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import { onMounted, ref, watch } from "vue";
import { createTriggerController } from "@/modal/Overlay.ts";
import { IonRadioGroup, IonRadio } from "@ionic/vue";
import { ColorOptions } from "@/modal/ScheduleType";

const props = defineProps({
  trigger: {
    type: String,
    default: "",
  },
  value: {
    type: Number,
    default: 0,
  },
});
const triggerController = createTriggerController();
const modal = ref();
const valueRef = ref(props.value);

const cancel = () => {
  modal.value.$el!.dismiss();
};
const confirm = () => {
  emits("update:value", valueRef.value);
  modal.value.$el!.dismiss();
};
const onSelectChange = (e: any) => {
  console.log("onSelectChange", e.detail.value);
  valueRef.value = e.detail.value;
};

const emits = defineEmits(["update:value"]);
onMounted(() => {
  watch(
    () => props.value,
    (v) => {
      valueRef.value = v;
    }
  );
  watch(
    () => props.trigger,
    (newValue) => {
      if (newValue) {
        console.log("add trigger", newValue);
        // 当 trigger 属性变化时，添加点击监听器
        triggerController.addClickListener(modal.value!.$el!, newValue);
      }
    },
    { immediate: true } // 立即执行一次 watcher
  );
});
</script>

<style scoped>
ion-modal {
  --height: 50%;
  --width: 95%;
  --border-radius: 16px;
  --box-shadow: 0 28px 48px rgba(0, 0, 0, 0.4);
  align-items: end;
  bottom: var(--ion-safe-area-bottom);
}
ion-footer {
  display: flex;
  justify-content: space-around;
}
ion-radio {
  --border-radius: 4px;
  --inner-border-radius: 4px;

  --color: #ddd;
  --color-checked: #6815ec;
}
</style>
