<template>
  <ion-page id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Save</ion-title>
        <ion-button slot="end" fill="clear" @click="btnLogOffClk">SignOut</ion-button>
      </ion-toolbar>
    </ion-header>
    <ion-content v-if="bAuth">
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-item>
        <ion-label>当前积分: [{{ userData.score }}]</ion-label>
      </ion-item>
      <ion-list>
        <ion-item>
          <ion-label>Schedule</ion-label>
          <component :is="MdiStore24Hour" :height="'36px'" :width="'36px'" color="#1a65eb" />
          <icon-mdi-account :height="'36px'" :width="'36px'" color="#1a65eb" />
          <icon-mdi-roman-numeral-7 :height="'36px'" :width="'36px'" color="#1a65eb" />
        </ion-item>
        <ion-item v-for="(schedule, idx) in userData.schedules" :key="idx">
          <ion-label>
            <div class="flex items-center w-full">
              <span
                class="v-dot"
                :style="{
                  'background-color': getColorOptions(schedule.color).tag,
                  'margin-inline': '2px',
                }">
              </span>
              <h2 class="flex-1">[{{ schedule.id }}] {{ schedule.title }}</h2>
              <component
                :is="getPriorityOptions(schedule.priority).icon"
                :height="'36px'"
                width="36px"
                :color="getPriorityOptions(schedule.priority).color" />
              <h2 class="w-16">{{ "{" + getGroupOptions(schedule.groupId).label + "}" }}</h2>
            </div>
            <p>
              range:
              {{ schedule?.startTs?.format("YYYY-MM-DD") }} -
              {{ schedule?.endTs?.format("YYYY-MM-DD") }}
              allDay:{{ schedule.allDay }} order:{{ schedule.order }}
            </p>
            <p>
              Remind: {{ schedule.reminder }} | Repeat: {{ schedule.repeat }} | RepeatEnd:
              {{ S_TS(schedule.repeatEndTs) }}
            </p>
            <p v-for="(task, idx) in schedule.subtasks" :key="idx">
              [{{ task.id }}]{{ task.name }}
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
    </ion-content>
    <div v-else class="w-full h-full items-stretch bg-white text-center ion-padding">
      <ion-input
        type="password"
        label="Password"
        value=""
        @ionChange="onPassChange"
        class="text-blue-500 mt-[50%]">
        <ion-input-password-toggle slot="end"></ion-input-password-toggle>
      </ion-input>
      <ion-button class="w-3/5 mt-[20%]" @click="btnLoginClk">Login</ion-button>
    </div>
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
  </ion-page>
</template>

<script setup lang="ts">
import { getSave } from "@/utils/NetUtil";
import { getGroupOptions, getPriorityOptions } from "@/modal/ScheduleType";
import { getColorOptions } from "@/modal/ColorType";
import { S_TS, UserData, UData } from "@/modal/UserData";
import { IonRefresher, IonRefresherContent, IonInputPasswordToggle } from "@ionic/vue";
import dayjs from "dayjs";
import { onMounted, ref } from "vue";
import MdiStore24Hour from "virtual:icons/mdi/store-24-hour";

const userData = ref<UserData>(new UserData());
const bAuth = ref(false);
const pass = ref("");
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
onMounted(() => {
  const data = localStorage.getItem("bAuth");
  if (data) {
    bAuth.value = data === "true";
  }

  // 获取数据
  getSave(1)
    .then((res: any) => {
      userData.value = UData.parseUserData(res);
      // console.log(userData.value);
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
function btnLoginClk() {
  console.log(pass.value);
  if (pass.value === "NeverGonnaGiveYouUp") {
    localStorage.setItem("bAuth", "true");
    bAuth.value = true;
  }
}
function onPassChange(event: any) {
  pass.value = event.detail.value;
}
function btnLogOffClk() {
  localStorage.setItem("bAuth", "false");
  bAuth.value = false;
}
</script>
