<template>
  <ion-grid v-if="slide" @resize="onResize">
    <ion-row>
      <ion-col class="ion-text-center" v-for="head in weekHead" :key="head">
        {{ head }}
      </ion-col>
    </ion-row>

    <ion-row
      class="calendar-row"
      v-for="week in minimal ? minSlide.weekArr : slide.weekArr"
      :key="week"
    >
      <ion-col
        class="calendar-col ion-text-center ion-no-padding"
        @click="daySelectCallback(slide, day)"
        v-for="day in week"
        :key="day"
      >
        <ion-chip
          :class="{
            vertical: true,
            transparent:
              selectedDate && day.dt.unix() !== selectedDate.dt.unix(),
            selected: selectedDate && day.dt.unix() === selectedDate.dt.unix(),
            gray: day.dt.month() !== slide.month,
          }"
        >
          <span>
            <strong> {{ day.dt.date() }}</strong>
          </span>
          <span class="dot" v-if="day.events.length > 0"></span>
        </ion-chip>
      </ion-col>
    </ion-row>
  </ion-grid>
</template>

<script setup lang="ts">
import { IonCol, IonGrid, IonRow } from "@ionic/vue";
import { defineProps, nextTick, ref, watch } from "vue";
const props = defineProps({
  name: String,
  slide: Object,
  daySelectCallback: {
    type: Function,
    default: () => {},
  },
  selectedDate: Object,
  swiperRef: Object,
  minimal: {
    type: Boolean,
    default: false,
  },
});
const minSlide = ref<any>(null);
const updateMinSlide = () => {
  if (props.selectedDate && props.slide) {
    const dt = props.selectedDate.dt;
    const firstDayOfMonth = dt.startOf("month");
    const diff = dt.date() - firstDayOfMonth.date();
    const idx = Math.ceil((diff + firstDayOfMonth.day()) / 7);

    minSlide.value = {
      vid: dt.year(),
      month: dt.month(),
      year: dt.year(),
      weekArr: props.slide.weekArr.slice(idx - 1, idx),
    };
  }
};
const onMinimalChange = () => {
  nextTick(() => {});
};
watch(() => props.slide, updateMinSlide, { deep: true });
watch(() => props.selectedDate, updateMinSlide, { deep: true });
watch(() => props.minimal, onMinimalChange, { deep: true });

const weekHead = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const onResize = () => {
  console.log("onResize");
  // props.swiperRef?.value?.update();
};
</script>
