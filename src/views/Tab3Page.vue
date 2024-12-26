<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab 3</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content>
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-list>
        <ion-item>
          <ion-label>Id: {{ userData.id }}</ion-label> <ion-label>Name: {{ userData.name }}</ion-label>
        </ion-item>
      </ion-list>
      <ion-list>
        <ion-item>
          <ion-label>Schedule</ion-label>
          <Icon :icon="'mdi:roman-numeral-7'" size="large" :height="'36'" color="#1a65eb" />
        </ion-item>
        <ion-item v-for="(schedule, idx) in userData.schedules" :key="idx">
          <ion-label>
            <div style="display: flex; align-items: center">
              <span
                class="v-dot"
                :style="{ 'background-color': getColorOptions(schedule.color).tag, 'margin-inline': '2px' }">
              </span>
              <Icon
                :icon="getPriorityOptions(schedule.priority).icon"
                :height="'36'"
                :color="getPriorityOptions(schedule.priority).color">
              </Icon>
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
              {{ schedule?.startTs?.format("YYYY-MM-DD") }} - {{ schedule?.endTs?.format("YYYY-MM-DD") }} AllDay:
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

<script lang="ts" src="@/views/Tab3Page.ts"></script>
