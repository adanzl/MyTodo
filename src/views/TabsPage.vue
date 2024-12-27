<template>
  <ion-page>
    <ion-menu content-id="main-content" @ionDidClose="onMenuClose">
      <ion-header>
        <ion-toolbar color="light">
          <ion-title>筛选</ion-title>
        </ion-toolbar>
      </ion-header>
      <ion-content>
        <ion-accordion-group :multiple="true" :value="['group', 'color', 'priority']" mode="ios">
          <ion-accordion value="group">
            <ion-item slot="header" color="light">
              <ion-icon :icon="bookmark" aria-hidden="true" style="font-size: 20px"></ion-icon>
              <ion-label style="margin-left: 10px">分组</ion-label>
            </ion-item>
            <ion-list class="ion-padding-horizontal" slot="content">
              <ion-checkbox
                label-placement="start"
                justify="space-between"
                class="option-item"
                @ionChange="onCheckChange($event, groupRef, -1)"
                :checked="bChecked(groupRef, -1)">
                <ion-item lines="none" style="left: -6px">
                  <icon-mdi-check-all
                    :height="'28'"
                    style="margin: 0 10px 0 5px"></icon-mdi-check-all>
                  <ion-label lines="none">全部</ion-label>
                </ion-item>
              </ion-checkbox>
              <ion-checkbox
                label-placement="start"
                v-for="(group, idx) in GroupOptions"
                :key="idx"
                justify="space-between"
                class="option-item"
                @ionChange="onCheckChange($event, groupRef, group.id)"
                :checked="bChecked(groupRef, group.id)">
                <ion-item lines="none">
                  <icon-mdi-tag
                    :height="'20'"
                    style="margin-right: 15px"
                    color="#7970ff"></icon-mdi-tag>
                  <ion-label>{{ group.label }}</ion-label>
                </ion-item>
              </ion-checkbox>
            </ion-list>
          </ion-accordion>
          <ion-accordion value="color">
            <ion-item slot="header" color="light">
              <ion-icon :icon="colorPalette" aria-hidden="true" style="font-size: 20px"></ion-icon>
              <ion-label style="margin-left: 10px">颜色</ion-label>
            </ion-item>
            <ion-list class="ion-padding-horizontal" slot="content">
              <ion-checkbox
                label-placement="start"
                justify="space-between"
                class="option-item"
                @ionChange="onCheckChange($event, colorRef, -1)"
                :checked="bChecked(colorRef, -1)">
                <ion-item lines="none" style="left: -6px">
                  <icon-mdi-check-all
                    :height="'28'"
                    style="margin: 0 10px 0 5px"></icon-mdi-check-all>
                  <ion-label lines="none">全部</ion-label>
                </ion-item>
              </ion-checkbox>
              <ion-checkbox
                label-placement="start"
                v-for="(color, idx) in ColorOptions"
                :key="idx"
                justify="space-between"
                class="option-item"
                @ionChange="onCheckChange($event, colorRef, color.id)"
                :checked="bChecked(colorRef, color.id)">
                <ion-item lines="none">
                  <span :style="{ 'background-color': color.tag }" class="v-dot" slot="start">
                  </span>
                  <ion-label>{{ color.label }}</ion-label>
                </ion-item>
              </ion-checkbox>
            </ion-list>
          </ion-accordion>
          <ion-accordion value="priority">
            <ion-item slot="header" color="light">
              <ion-label style="margin-left: 2px"><strong>Pri</strong></ion-label>
              <ion-label> </ion-label>
            </ion-item>
            <ion-list class="ion-padding-horizontal" slot="content">
              <ion-checkbox
                label-placement="start"
                justify="space-between"
                class="option-item"
                @ionChange="onCheckChange($event, priorityRef, -1)"
                :checked="bChecked(priorityRef, -1)">
                <ion-item lines="none" style="left: -6px">
                  <icon-mdi-check-all
                    :height="'28'"
                    style="margin: 0 10px 0 5px"></icon-mdi-check-all>
                  <ion-label lines="none">全部</ion-label>
                </ion-item>
              </ion-checkbox>
              <ion-checkbox
                label-placement="start"
                v-for="(priority, idx) in PriorityOptions"
                :key="idx"
                justify="space-between"
                class="option-item"
                @ionChange="onCheckChange($event, priorityRef, priority.id)"
                :checked="bChecked(priorityRef, priority.id)">
                <ion-item lines="none" style="left: -6px">
                  <component
                    :is="priority.icon"
                    :height="'36px'"
                    width="36px"
                    :color="priority.color"
                    style="margin-right: 8px" />
                  <ion-label>{{ priority.label }}</ion-label>
                </ion-item>
              </ion-checkbox>
            </ion-list>
          </ion-accordion>
        </ion-accordion-group>
      </ion-content>
      <ion-footer>
        <ion-toolbar>
          <ion-button fill="clear" expand="full" @click="btnFilterResetClick()"> Reset </ion-button>
        </ion-toolbar>
      </ion-footer>
    </ion-menu>
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
import { bookmark, colorPalette } from "ionicons/icons";

import { GroupOptions, ColorOptions, PriorityOptions } from "@/modal/ScheduleType";
import {
  IonAccordion,
  IonAccordionGroup,
  IonMenu,
  IonCheckbox,
  IonRouterOutlet,
  IonTabBar,
  IonTabButton,
  IonTabs,
} from "@ionic/vue";
import {
  calendarOutline,
  gridOutline,
  shieldCheckmarkOutline,
  squareOutline,
} from "ionicons/icons";
import { inject, ref } from "vue";

const groupRef = ref(new Map(GroupOptions.map((option) => [option.id, true])));
const colorRef = ref(new Map(ColorOptions.map((option) => [option.id, true])));
const priorityRef = ref(new Map(PriorityOptions.map((option) => [option.id, true])));
// console.log(groupRef, colorRef, priorityRef);
const eventBus: any = inject("eventBus");
function onMenuClose() {
  eventBus.$emit("menuClose", {
    group: groupRef.value,
    color: colorRef.value,
    priority: priorityRef.value,
  });
}
function bChecked(rRef: any, id: number): boolean {
  if (id === -1) {
    return Array.from(rRef.values()).every((value) => value === true);
  }
  // console.log(rRef, id, rRef.get(id));
  return rRef.get(id) === true;
}
function btnFilterResetClick() {
  groupRef.value = new Map(GroupOptions.map((option) => [option.id, true]));
  colorRef.value = new Map(ColorOptions.map((option) => [option.id, true]));
  priorityRef.value = new Map(PriorityOptions.map((option) => [option.id, true]));
}
function onCheckChange(event: any, rRef: any, id: number) {
  // console.log(event, rRef, id);
  if (id === -1) {
    if (event.detail.checked) {
      for (const [k] of rRef) {
        rRef.set(k, true);
      }
    }
  } else {
    rRef.set(id, event.detail.checked);
  }
}
</script>

<style scoped>
ion-menu::part(container) {
  height: 100%;
}

.option-item::part(label) {
  width: 100%;
}
.option-item ion-label {
  margin: 0px 0px 0px 10px;
}
</style>
