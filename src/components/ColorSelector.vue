<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    id="colorSelector"
    mode="ios"
    class="bottom-modal"
    @ionModalDidDismiss="onModalDismiss">
    <ion-item>
      <ion-title>选择颜色</ion-title>
    </ion-item>
    <div>
      <ion-item lines="none">
        <ion-radio-group
          :value="valueRef"
          @ionChange="onSelectChange"
          class="w-full flex flex-wrap ion-padding">
          <ion-radio
            v-for="(op, idx) in ColorOptions"
            :key="idx"
            :value="op.id"
            :style="{ '--radio-bg-color': op.tag }"
            label-placement="stacked"
            alignment="center"
            class="option-item w-1/4 max-w-[25%] min-w-[25%]">
            <div class="w-full">
              <ion-label
                class="ml-1 overflow-hidden"
                :style="{ color: op.tag, 'text-shadow': '1px 1px 1px #FF0000' }">
                {{ op.label }}
              </ion-label>
            </div>
          </ion-radio>
        </ion-radio-group>
      </ion-item>
    </div>
    <ion-footer>
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<style scoped>
.option-item::part(label) {
  margin: 0;
  display: flex;
  align-items: center;
  text-align: center;
}

ion-radio.ios::part(container) {
  width: 30px;
  height: 30px;

  border: 2px solid #ddd;
  border-radius: 50%;
  background-color: var(--radio-bg-color);
}

.radio-checked.ios::part(container) {
  border-color: #6815ec;
  border-width: 2px;
  color: transparent;
}
.radio-checked.ios::part(mark) {
  opacity: 0;
}

</style>

<script lang="ts" setup>
import { ColorOptions } from "@/modal/ColorType";
import { createTriggerController } from "@/utils/Overlay";
import { IonRadio, IonRadioGroup } from "@ionic/vue";
import { onMounted, ref, watch } from "vue";

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
        // 当 trigger 属性变化时，添加点击监听器
        triggerController.addClickListener(modal.value!.$el!, newValue);
      }
    },
    { immediate: true } // 立即执行一次 watcher
  );
});
const onModalDismiss = () => {
  valueRef.value = props.value;
};
</script>
