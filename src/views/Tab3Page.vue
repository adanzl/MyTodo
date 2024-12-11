<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab 3</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content :scroll-y="false">
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
            <h2>{{ schedule.title }}</h2>
            <p>
              {{ schedule?.startTs?.format("YYYY-MM-DD") }} -
              {{ schedule?.endTs?.format("YYYY-MM-DD") }}
            </p>
            <span v-for="(task, idx) in schedule.subTasks" :key="idx">{{
              task.name
            }}</span>
          </ion-label>
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

<script setup lang="ts">
import { getSave } from "@/components/NetUtil.vue";
import { UserData } from "@/type/UserData.vue";
import {
  IonContent,
  IonHeader,
  IonPage,
  IonTitle,
  IonToolbar,
} from "@ionic/vue";
import dayjs from "dayjs";
import { onMounted, ref } from "vue";

const userData = ref<UserData>({ id: 1, name: "leo", schedules: [] });
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
onMounted(() => {
  // 获取数据
  getSave(1)
    .then((res: any) => {
      console.log("getSave", res.data);
      userData.value = JSON.parse(res.data);
      for (let i = 0; i < userData.value.schedules.length; i++) {
        const schedule = userData.value.schedules[i];
        schedule.startTs = dayjs(schedule.startTs);
        schedule.endTs = dayjs(schedule.endTs);
      }
    })
    .catch((err) => {
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
});
</script>
