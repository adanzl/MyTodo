<template>
  <div class="ion-padding" id="main">
    <ion-toolbar class="transparent">
      <ion-buttons slot="start">
        <ion-button @click="cancel()">Cancel</ion-button>
      </ion-buttons>
      <ion-title>Add Schedule</ion-title>
    </ion-toolbar>
    <ion-segment value="sType">
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
          <ion-list
            :inset="true"
            style="background-color: transparent !important"
          >
            <ion-item style="background-color: transparent !important">
              <ion-label>Title</ion-label>
            </ion-item>
            <ion-item>
              <ion-label>label user priority color</ion-label>
            </ion-item>
          </ion-list>
          <ion-list :inset="true">
            <ion-item>
              <ion-label>Start - End</ion-label>
            </ion-item>
            <ion-item>
              <ion-label>Reminder</ion-label>
            </ion-item>
            <ion-item>
              <ion-label>Repeat</ion-label>
            </ion-item>
            <ion-item>
              <ion-label>Defer</ion-label>
            </ion-item>
          </ion-list>
          <ion-list :inset="true">
            <ion-item v-for="v in [1, 2, 3, 4, 5, 56, 67, 78, 78, 78]" :key="v">
              <ion-label>v</ion-label>
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
} from "@ionic/vue";
const props = defineProps({
  modal: Object,
});
const handleChange = (event: any) => {
  console.log(event.detail.value);
};
const cancel = () => {
  props.modal?.$el.dismiss(null, "cancel");
};
</script>

<style scoped>
.main_content {
  background-color: gray;
  height: 75%;
}
ion-content#main_bg::part(background) {
  background: rgb(244, 245, 231);
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
  /* background-color: transparent !important; */
}
ion-segment-content {
  /* justify-content: center; */
  height: 70%;
}
.transparent {
  --background: transparent !important;
}
</style>
