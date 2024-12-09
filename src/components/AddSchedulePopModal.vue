<template>
  <div class="ion-padding" id="main">
    <ion-toolbar class="transparent">
      <ion-buttons slot="start">
        <ion-button @click="cancel()">Cancel</ion-button>
      </ion-buttons>
      <ion-title>Add Schedule</ion-title>
    </ion-toolbar>
    <ion-segment value="sType" @ionChange="handleChange">
      <ion-segment-button value="sType" content-id="sType">
        <ion-label>Schedule</ion-label>
      </ion-segment-button>
      <ion-segment-button value="tType" content-id="tType">
        <ion-label>Todo</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view class="main_content">
      <ion-segment-content
        id="sType"
        style="height: 100%; background-color: gray !important"
      >
        <ion-content id="main_bg" class="ion-margin-top">
          <ion-list :inset="true">
            <ion-item>
              <ion-input placeholder="输入日程标题" :value="scheduleTitle">
              </ion-input>
            </ion-item>
            <ion-item>
              <ion-select label-placement="floating" label="Group" value="work">
                <ion-icon slot="start" :icon="bookmark" aria-hidden="true">
                </ion-icon>
                <ion-select-option value="none">None</ion-select-option>
                <ion-select-option value="work">Work</ion-select-option>
                <ion-select-option value="other">Other</ion-select-option>
              </ion-select>
              <ion-select label-placement="stacked" label="Priority" value="0">
                <ion-icon slot="start" :icon="airplane" aria-hidden="true">
                </ion-icon>
                <ion-select-option value="0">I</ion-select-option>
                <ion-select-option value="1">II</ion-select-option>
                <ion-select-option value="2">III</ion-select-option>
                <ion-select-option value="3">IV</ion-select-option>
              </ion-select>
              <ion-select label-placement="stacked" label="Color" value="0">
                <ion-icon slot="start" :icon="colorPalette" aria-hidden="true">
                </ion-icon>
                <ion-select-option value="0">Red</ion-select-option>
                <ion-select-option value="1">Yellow</ion-select-option>
                <ion-select-option value="2">Blue</ion-select-option>
                <ion-select-option value="3">White</ion-select-option>
              </ion-select>
            </ion-item>
          </ion-list>
          <ion-list :inset="true">
            <ion-item class="ion-text-center">
              <ion-icon :icon="calendar"></ion-icon>
              <ion-button size="medium" fill="full" @click="btnScheduleDTClk">
                <ion-label>Start:</ion-label> <ion-label> No time</ion-label>
                <ion-label> >></ion-label>
                <ion-label>End:</ion-label>
                <ion-label> no time</ion-label>
              </ion-button>
            </ion-item>
            <ion-item v-if="bShowScheduleDT">
              <ion-datetime ref="scheduleDT">
                <ion-buttons slot="buttons">
                  <ion-button color="primary">Clear</ion-button>
                  <ion-segment value="start" mode="ios" style="width: 130px">
                    <ion-segment-button value="start" id="dtStart">
                      Start
                    </ion-segment-button>
                    <ion-segment-button value="end" id="dtEnd">
                      End
                    </ion-segment-button>
                  </ion-segment>
                  <ion-button color="primary">OK</ion-button>
                </ion-buttons>
              </ion-datetime>
            </ion-item>
            <ion-item>
              <ion-icon :icon="notifications"></ion-icon>
              <ion-label>Reminder</ion-label>
            </ion-item>
            <ion-item>
              <ion-icon
                :icon="repeat"
                aria-hidden="true"
                class="ion-margin-right"
              >
              </ion-icon>
              <ion-select value="0">
                <div slot="label">
                  <ion-label>Repeat</ion-label>
                </div>
                <ion-select-option value="0">Every day</ion-select-option>
                <ion-select-option value="1">Workday</ion-select-option>
                <ion-select-option value="2">Every week</ion-select-option>
                <ion-select-option value="3">Every Month</ion-select-option>
                <ion-select-option value="4">Every Year</ion-select-option>
              </ion-select>
            </ion-item>
            <ion-item>
              <ion-icon :icon="power"></ion-icon>
              <ion-label>End</ion-label>
            </ion-item>
          </ion-list>
        </ion-content>
      </ion-segment-content>
      <ion-segment-content id="tType">
        <ion-label>Second</ion-label>
        <ion-content color="primary"></ion-content>
      </ion-segment-content>
    </ion-segment-view>
    <ion-footer>
      <ion-button expand="block" mode="ios" color="warning">Save</ion-button>
    </ion-footer>
  </div>
</template>
<script setup lang="ts">
import {
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonSelect,
  IonSelectOption,
  IonDatetime,
} from "@ionic/vue";
import {
  bookmark,
  colorPalette,
  airplane,
  calendar,
  notifications,
  repeat,
  power,
} from "ionicons/icons";
import { ref } from "vue";
const props = defineProps({
  modal: Object,
});
const handleChange = (event: any) => {
  console.log(event.detail.value);
};
const cancel = () => {
  props.modal?.$el.dismiss(null, "cancel");
};

const btnScheduleDTClk = () => {
  console.log("btnScheduleDTClk");
  bShowScheduleDT.value = !bShowScheduleDT.value;
};

const scheduleTitle = ref("");
const scheduleDT = ref();
const bShowScheduleDT = ref(false);
</script>

<style scoped>
.main_content {
  /* background-color: gray; */
  height: 75%;
}
ion-content#main_bg::part(background) {
  background: rgb(244, 245, 231);
}
ion-content#main_bg::part(scroll) {
  color: transparent;
}
#main {
  /* background-color: rgb(253, 254, 244); */
  background: rgb(244, 245, 231);
  height: 100%;
}
ion-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: fit-content;
  padding: 16px;
}
ion-list {
  /* background-color: rgb(253, 254, 244); */
  background-color: transparent !important;
}
ion-segment-content {
  /* justify-content: center; */
  height: 70%;
}
.transparent {
  --background: transparent !important;
}
#dtStart,
#dtEnd {
  font-size: min(0.8125rem, 39px);
  height: 32px;
  width: 64px;
  min-height: 10px;
  min-width: 10px;
  --margin-top: 0px;
}
</style>
