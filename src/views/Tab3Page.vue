<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab 3</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content :scroll-y="false">
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-list>
        <ion-item>
          <ion-label>Id: {{ userData.id }}</ion-label>
        </ion-item>
        <ion-item>
          <ion-label>Name: {{ userData.name }}</ion-label>
        </ion-item>
      </ion-list>
      <ion-list>
        <ion-item>
          <ion-label>Schedule</ion-label>
        </ion-item>
        <ion-item v-for="(schedule, idx) in userData.schedules" :key="idx">
          <ion-label>
            <h2>[{{ schedule.id }}] {{ schedule.title }}</h2>
            <p>
              range:
              {{ schedule?.startTs?.format("YYYY-MM-DD") }} -
              {{ schedule?.endTs?.format("YYYY-MM-DD") }}
            </p>
            <p>
              Remind: {{ schedule.reminder }} | Repeat: {{ schedule.repeat }} |
              RepeatEnd: {{ SAVE_TS(schedule.repeatEndTs) }}
            </p>
            <p v-for="(task, idx) in schedule.subTasks" :key="idx">
              {{ task.name }}
            </p>
          </ion-label>
        </ion-item>
      </ion-list>
      <ion-list>
        <ion-item v-for="(v, k) in userData.save" :key="k">
          {{ k }} - {{ v }}
        </ion-item>
      </ion-list>
      <ion-toast
        :is-open="toastData.isOpen"
        :message="toastData.text"
        :duration="toastData.duration"
        @didDismiss="
          () => {
            toastData.isOpen = false;
          }
        "
      >
      </ion-toast>
    </ion-content>
  </ion-page>
</template>

<script lang="ts" src="../controller/Tab3Page.ts"></script>
