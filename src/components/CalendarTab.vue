<template>
  <ion-grid v-if="slide">
    <ion-row>
      <ion-col class="ion-text-center" v-for="head in weekHead" :key="head">
        {{ head }}
      </ion-col>
    </ion-row>

    <ion-row class="calendar-row" v-for="week in slide.weekArr" :key="week">
      <ion-col
        class="calendar-col ion-text-center ion-no-padding"
        @click="daySelectCallback ? daySelectCallback(slide, day) : undefined"
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
defineProps({
  name: String,
  slide: Object,
  daySelectCallback: Function,
  selectedDate: Object,
});

const weekHead = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
</script>
