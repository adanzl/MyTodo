<template>
  <ion-page>
    <ion-tabs>
      <ion-router-outlet></ion-router-outlet>
      <ion-tab-bar slot="bottom">
        <ion-tab-button tab="tabHome" href="/tabs/tab1">
          <ion-icon aria-hidden="true" :icon="shieldCheckmarkOutline" />
          <ion-label>日程</ion-label>
        </ion-tab-button>

        <ion-tab-button tab="tabCalendar" href="/tabs/tab2">
          <ion-icon aria-hidden="true" :icon="calendarOutline" />
          <ion-label>日历</ion-label>
        </ion-tab-button>

        <ion-tab-button tab="tabPic" href="/tabs/tab3">
          <ion-icon aria-hidden="true" :icon="gridOutline" />
          <ion-label>图片</ion-label>
        </ion-tab-button>

        <ion-tab-button tab="tabMy" href="/tabs/tab4">
          <ion-icon aria-hidden="true" :icon="squareOutline" />
          <ion-label>存档</ion-label>
        </ion-tab-button>
      </ion-tab-bar>
    </ion-tabs>
  </ion-page>
</template>

<script setup lang="ts">
import { IonTabBar, IonTabButton, IonTabs, IonLabel, IonPage, IonRouterOutlet } from "@ionic/vue";
import {
  gridOutline,
  squareOutline,
  shieldCheckmarkOutline,
  calendarOutline,
} from "ionicons/icons";
</script>
