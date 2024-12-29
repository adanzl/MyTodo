<template>
  <ion-page id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Save</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-list>
        <ion-item>
          <ion-label>Id: {{ userData.id }}</ion-label>
          <ion-label>Name: {{ userData.name }}</ion-label>
          <div class="text-3xl font-bold underline"> hello world</div>
        </ion-item>
      </ion-list>
      <ion-list>
        <ion-item>
          <ion-label>Schedule</ion-label>
          <component :is="MdiStore24Hour" :height="'36px'" :width="'36px'" color="#1a65eb" />
          <icon-mdi-account :height="'36px'" :width="'36px'" color="#1a65eb" />
          <icon-mdi-roman-numeral-7 :height="'36px'" :width="'36px'" color="#1a65eb" />
        </ion-item>
        <ion-item v-for="(schedule, idx) in userData.schedules" :key="idx">
          <ion-label>
            <div style="display: flex; align-items: center">
              <span
                class="v-dot"
                :style="{
                  'background-color': getColorOptions(schedule.color).tag,
                  'margin-inline': '2px',
                }">
              </span>
              <component
                :is="getPriorityOptions(schedule.priority).icon"
                :height="'36px'"
                width="36px"
                :color="getPriorityOptions(schedule.priority).color" />
              <ion-label>{{ "{" + getGroupOptions(schedule.groupId).label + "}" }}</ion-label>
              <!-- <ion-icon
                :icon="icons.mdiRomanNums[getPriorityOptions(schedule.priority).icon]"
                :style="{ color: getPriorityOptions(schedule.priority).color }"
                style="font-size: 1.5rem">
              </ion-icon> -->
              <h2>[{{ schedule.id }}] {{ schedule.title }}</h2>
            </div>
            <p>
              range:
              {{ schedule?.startTs?.format("YYYY-MM-DD") }} -
              {{ schedule?.endTs?.format("YYYY-MM-DD") }} AllDay:
              {{ schedule.allDay }}
            </p>
            <p>
              Remind: {{ schedule.reminder }} | Repeat: {{ schedule.repeat }} | RepeatEnd:
              {{ S_TS(schedule.repeatEndTs) }}
            </p>
            <p v-for="(task, idx) in schedule.subtasks" :key="idx">
              {{ task.name }}
            </p>
          </ion-label>
        </ion-item>
      </ion-list>
      <ion-list>
        <ion-item>
          <ion-label>Save</ion-label>
        </ion-item>
        <ion-item v-for="(v, k) in userData.save" :key="k">
          <ion-label>
            <h6>{{ k }}</h6>
            <p>{{ v }}</p>
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
        ">
      </ion-toast>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { getSave } from "@/utils/NetUtil";
import { getColorOptions, getGroupOptions, getPriorityOptions } from "@/modal/ScheduleType";
import { S_TS, UserData, UData } from "@/modal/UserData";
import { IonRefresher, IonRefresherContent } from "@ionic/vue";
import dayjs from "dayjs";
import { onMounted, ref } from "vue";
import MdiStore24Hour from "virtual:icons/mdi/store-24-hour";

const userData = ref<UserData>(new UserData());
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
onMounted(() => {
  // 获取数据
  getSave(1)
    .then((res: any) => {
      userData.value = UData.parseUserData(res);
    })
    .catch((err) => {
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
});
function handleRefresh(event: any) {
  getSave(1)
    .then((res: any) => {
      userData.value = UData.parseUserData(res);
      for (let i = 0; i < userData.value.schedules.length; i++) {
        const schedule = userData.value.schedules[i];
        schedule.startTs = dayjs(schedule.startTs);
        schedule.endTs = dayjs(schedule.endTs);
        if (schedule.repeatEndTs) {
          schedule.repeatEndTs = dayjs(schedule.repeatEndTs);
        }
      }
      event.target.complete();
    })
    .catch((err) => {
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
      event.target.complete();
    });
}
</script>
