<template>
  <ion-grid>
    <ion-row>
      <ion-col class="ion-text-center" v-for="head in weekHead" :key="head">
        {{ head }}
      </ion-col>
    </ion-row>
    <ion-row v-for="week in slide.weekArr" :key="week">
      <ion-col
        class="ion-text-center ion-no-padding"
        @click="daySelectCallback(slide, day)"
        v-for="day in week"
        :key="day">
        <ion-chip
          :class="{
            vertical: true,
            transparent:
              day.dt.unix() !== selectedDate.dt.unix() &&
              day.dt.unix() !== dayjs().startOf('day').unix(),
            selected: selectedDate && day.dt.unix() === selectedDate.dt.unix(),
            today:
              day.dt.unix() === dayjs().startOf('day').unix() &&
              selectedDate &&
              day.dt.unix() !== selectedDate.dt.unix(),
            gray: day.dt.month() !== slide.month,
          }">
          <span>
            <strong> {{ day.dt.date() }}</strong>
          </span>
          <span
            class="dot"
            :class="{ 'gray-bg': day.dt.month() !== slide.month }"
            v-if="day.events.length > 0"></span>
        </ion-chip>
      </ion-col>
    </ion-row>
  </ion-grid>
</template>

<script setup lang="ts">
import { IonCol, IonGrid, IonRow } from "@ionic/vue";
import dayjs from "dayjs";
import { watch } from "vue";
const props = defineProps({
  name: String,
  slide: {
    type: Object,
    default: null,
  },
  daySelectCallback: {
    type: Function,
    default: () => {},
  },
  selectedDate: {
    type: Object,
    default: null,
  },
  swiperRef: Object,
});
const updateMinSlide = () => {
  props.swiperRef?.emit("update");
};
watch(() => props.slide, updateMinSlide, { deep: true });
watch(() => props.selectedDate, updateMinSlide, { deep: true });

const weekHead = ["日", "一", "二", "三", "四", "五", "六"];
</script>
<style escaped lang="css">
ion-chip {
  margin: 0;
}
ion-chip.selected {
  --color: #fff !important;
  --background: #ff3609 !important;
}
ion-chip.today {
  --background: yellow !important;
}
.dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: #007bff;
  margin-top: 5px;
}
</style>
