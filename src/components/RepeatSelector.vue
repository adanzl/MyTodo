<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    id="repeatSelector"
    class="bottom-modal"
    @ionModalDidDismiss="onModalDismiss">
    <ion-item>
      <ion-title>选择重复方式</ion-title>
    </ion-item>
    <div class="ion-padding">
      <ion-item lines="none">
        <ion-radio-group :value="valueRef" @ionChange="onSelectChange" class="w-full" mode="ios">
          <ion-radio
            v-for="(op, idx) in RepeatOptions"
            :key="idx"
            :value="op.id"
            @click="onItemClk($event, op)"
            class="option-item">
            <ion-item lines="none">
              <div class="flex w-full items-center">
                <span>
                  <component :is="op.icon" :height="'25px'" width="36px" color="#7970ff" />
                </span>
                <ion-label class="flex-1 ml-2">{{ op.label }} </ion-label>
                <ion-label class="text-gray-400 text-xs font-mono" v-if="op.tag">
                  （下次 {{ getNextRepeatDate(dt as dayjs.Dayjs, op.id, repeatData) }}）
                </ion-label>
              </div>
            </ion-item>
            <div
              id="btnCustom"
              v-if="op.id === CUSTOM_REPEAT_ID"
              class="pr-6 text-gray-400 text-wrap text-sm text-right ">
              <p v-if="repeatData.week?.length">{{ buildCustomRepeatLabel(repeatData) }}</p>
              <p v-else>自定义重复的日期</p>
            </div>
          </ion-radio>
        </ion-radio-group>
        <WeekSelector
          ref="weekSelector"
          trigger="btnCustom"
          side="top"
          alignment="center"
          @update:value="onRepeatDataChange"
          :value="repeatData" />
      </ion-item>
    </div>
    <ion-footer>
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import {
  RepeatOptions,
  getNextRepeatDate,
  buildCustomRepeatLabel,
  RepeatData,
  CUSTOM_REPEAT_ID,
  RepeatType,
} from "@/modal/ScheduleType";
import { createTriggerController } from "@/utils/Overlay";
import { IonRadio, IonRadioGroup } from "@ionic/vue";
import { onMounted, ref, watch } from "vue";
import dayjs from "dayjs";
import WeekSelector from "@/components/WeekSelector.vue";
const props = defineProps({
  trigger: {
    type: String,
    default: "",
  },
  value: {
    type: Object,
    default: null,
  },
  dt: {
    type: Object,
    default: dayjs(),
  },
});
const triggerController = createTriggerController();
const modal = ref();
const weekSelector = ref();
const valueRef = ref(props.value.repeat ?? 0);
const repeatData = ref(props.value.repeatData ?? new RepeatData());

const cancel = () => {
  modal.value.$el!.dismiss();
};
const confirm = () => {
  emits("update:value", valueRef.value, repeatData.value);
  modal.value.$el!.dismiss();
};
const onSelectChange = (e: any) => {
  console.log("onSelectChange", e.detail.value);
  valueRef.value = e.detail.value;
};
function onItemClk(_e: any, o: RepeatType) {
  if (o.id === CUSTOM_REPEAT_ID) {
    weekSelector.value?.$el.present();
  }
}

const emits = defineEmits(["update:value"]);
onMounted(() => {
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
  // valueRef.value = props.value;
};

function onRepeatDataChange(v: number[]) {
  console.log("onRepeatDataChange", v);
  repeatData.value.week = v;
}
</script>

<style scoped>
.option-item::part(label) {
  margin: 0;
  width: 100%;
}
</style>
