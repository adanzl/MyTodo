<template>
  <ion-modal
    ref="modal"
    aria-hidden="true"
    id="groupSelector"
    mode="ios"
    @ionModalDidDismiss="onModalDismiss">
    <ion-item>
      <ion-title>分组信息</ion-title>
    </ion-item>
    <ion-content class="ion-padding">
      <ion-item>
        <ion-radio-group :value="valueRef" @ionChange="onSelectChange" class="width-100">
          <ion-radio
            v-for="(op, idx) in GroupOptions"
            :key="idx"
            :value="op.id"
            class="option-item">
            <ion-item lines="none" style="flex: 1">
              <span>
                <!-- <Icon icon="mdi:bookmark" aria-hidden="true" height="28"></Icon> -->
                <ion-icon :icon="bookmark" aria-hidden="true" style="font-size: 20px"></ion-icon>
              </span>
              <ion-label style="margin-left: 8px">{{ op.label }}</ion-label>
            </ion-item>
          </ion-radio>
        </ion-radio-group>
      </ion-item>
    </ion-content>
    <ion-footer>
      <ion-button style="width: 40%" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button style="width: 40%" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import { createTriggerController } from "@/modal/Overlay.ts";
import { GroupOptions } from "@/modal/ScheduleType";
import { IonRadio, IonRadioGroup } from "@ionic/vue";
// import { Icon } from "@iconify/vue";
import { bookmark } from "ionicons/icons";
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

<style scoped>
ion-modal {
  --height: 50%;
  --width: 95%;
  /* --border-radius: 16px; */
  /* --box-shadow: 0 28px 48px rgba(0, 0, 0, 0.4); */
  align-items: end;
}
ion-modal {
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
ion-modal::part(backdrop) {
  background-color: var(--ion-color-dark) !important;
  opacity: 0.3 !important;
}
.option-item::part(label) {
  margin: 0;
  width: 100%;
}
</style>
