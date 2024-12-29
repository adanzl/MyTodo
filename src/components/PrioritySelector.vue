<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    id="prioritySelector"
    mode="ios"
    class="bottom-modal"
    @ionModalDidDismiss="onModalDismiss">
    <ion-item>
      <ion-title>优先级</ion-title>
    </ion-item>
    <div class="ion-padding-horizontal">
      <ion-item>
        <ion-radio-group :value="valueRef" @ionChange="onSelectChange" class="width-100">
          <ion-radio
            v-for="(op, idx) in PriorityOptions"
            :key="idx"
            :value="op.id"
            class="option-item">
            <ion-item lines="none" style="flex: 1">
              <span>
                <!-- <Icon :icon="op.icon" :height="'36'" :color="op.color"></Icon> -->
                <component :is="op.icon" :height="'36px'" width="36px" :color="op.color" />
              </span>
              <ion-label style="margin-left: 8px">{{ op.label }}</ion-label>
            </ion-item>
          </ion-radio>
        </ion-radio-group>
      </ion-item>
    </div>
    <ion-footer>
      <ion-button style="width: 40%" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button style="width: 40%" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import { onMounted, ref, watch } from "vue";
import { createTriggerController } from "@/utils/Overlay";
import { IonRadioGroup, IonRadio } from "@ionic/vue";
import { PriorityOptions } from "@/modal/ScheduleType";

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

<style scoped>
.option-item {
  display: block;
  overflow: hidden;
}
.option-item::part(label) {
  margin: 0;
  width: 100%;
}
</style>
