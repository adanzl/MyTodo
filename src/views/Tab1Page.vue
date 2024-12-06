<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab 1</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content :fullscreen="true" color="light">
      <ion-header collapse="condense">
        <ion-toolbar>
          <ion-title size="large">Tab 1</ion-title>
        </ion-toolbar>
      </ion-header>
      <!-- <ion-datetime
        ref="datetime"
        hour-cycle="h23"
        min="2024-12-01"
        max="2024-12-07"
        :show-default-title="true"
      >
        <ion-buttons slot="buttons">
          <ion-button color="danger" @click="reset()">Reset</ion-button>
        </ion-buttons>
        <ion-label slot="title">ion-label</ion-label>
      </ion-datetime> -->
      <CalendarC name="calendar"></CalendarC>
      <ion-button @click="scrollToBottom()">
        <ion-icon slot="start" :icon="star"></ion-icon>Scroll
        <ion-icon slot="end" :icon="heart"></ion-icon>
      </ion-button>
      <ion-list :inset="true" lines="full" mode="ios">
        <ion-item>
          <ion-label>
            Multi-line text that should wrap when it is too long to fit on one
            line.
          </ion-label>
        </ion-item>

        <ion-item>
          <ion-label class="ion-text-nowrap">
            Multi-line text that should ellipsis when it is too long to fit on
            one line.
          </ion-label>
        </ion-item>

        <ion-item>
          <ion-label>
            <h1>H1 Heading</h1>
            <p>Paragraph</p>
          </ion-label>
        </ion-item>
      </ion-list>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { star, heart } from "ionicons/icons";
import { ref } from "vue";
import GConfig from "@/components/GConfig.vue";
import CalendarC from "@/components/CalendarC.vue"
const datetime = ref(null);
const scrollToBottom = () => {
  console.log("scroll to bottom", GConfig);
  GConfig.init();
};
const reset = () => {
  datetime.value.$el.reset();
};
</script>
