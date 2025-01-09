<template>
  <ion-page>
    <div v-if="bLogin">
      <ion-menu content-id="main-content" @ionDidClose="onMenuClose" :swipe-gesture="false">
        <ion-header>
          <ion-toolbar color="light">
            <ion-title>筛选</ion-title>
            <ion-buttons slot="end">
              <ion-button @click="btnLogoff">注销</ion-button>
            </ion-buttons>
          </ion-toolbar>
        </ion-header>
        <ion-content>
          <ion-item lines="none">
            <ion-avatar slot="start" class="ml-0 w-8 h-8">
              <ion-img :src="curUser.icon" />
            </ion-avatar>
            <ion-label class="font-bold">{{ curUser.name }}</ion-label>
            <MdiStar class="text-red-500" />
            <div class="text-left flex-1 pl-1 font-bold">{{ getUserScore() }}</div>
          </ion-item>
          <ion-accordion-group :multiple="true" :value="['group', 'color', 'priority']" mode="ios">
            <ion-accordion value="group">
              <ion-item slot="header" color="light" class="schedule-group-item">
                <ion-icon :icon="bookmarksOutline" class="w-5"></ion-icon>
                <ion-label class="mx-2.5">分组</ion-label>
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
                      style="margin: 0 16px 0 5px"></icon-mdi-check-all>
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
                    <span class="mr-3">
                      <component :is="group.icon" :height="'22px'" width="22px" color="#7970ff" />
                    </span>
                    <ion-label>{{ group.label }}</ion-label>
                  </ion-item>
                </ion-checkbox>
              </ion-list>
            </ion-accordion>
            <!-- <ion-accordion value="color">
            <ion-item slot="header" color="light" class="schedule-group-item">
              <ion-icon :icon="colorPaletteOutline" class="w-5"></ion-icon>
              <ion-label class="mx-2.5">颜色</ion-label>
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
                    style="margin: 0 16px 0 5px"></icon-mdi-check-all>
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
                  <ion-label
                    :style="{ color: color.tag, 'text-shadow': '1px 1px 1px #FF0000' }">
                    {{ color.label }}
                  </ion-label>
                </ion-item>
              </ion-checkbox>
            </ion-list>
          </ion-accordion> -->
            <ion-accordion value="priority">
              <ion-item slot="header" color="light" class="schedule-group-item">
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
                      style="margin: 0 16px 0 5px"></icon-mdi-check-all>
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
                      class="mr-1" />
                    <ion-label class="ml-2" :style="{ color: priority.color }">
                      {{ priority.label }}
                    </ion-label>
                  </ion-item>
                </ion-checkbox>
              </ion-list>
            </ion-accordion>
          </ion-accordion-group>
        </ion-content>
        <ion-footer>
          <ion-toolbar class="flex">
            <ion-button fill="clear" class="w-[48%]" @click="btnFilterResetClick()">
              重置筛选
            </ion-button>
            <ion-button fill="clear" class="w-[48%]" color="warning" id="btnColor">
              <ion-icon :icon="colorPaletteOutline" />
              编辑颜色
            </ion-button>
          </ion-toolbar>
        </ion-footer>
      </ion-menu>
      <ion-tabs>
        <ion-router-outlet></ion-router-outlet>
        <ion-tab-bar slot="bottom">
          <ion-tab-button tab="tabHome" href="/tabs/tab1">
            <ion-icon :icon="shieldCheckmarkOutline" />
            <ion-label>日程浏览</ion-label>
          </ion-tab-button>

          <ion-tab-button tab="tabCalendar" href="/tabs/tab2">
            <ion-icon :icon="calendarOutline" />
            <ion-label>日历视图</ion-label>
          </ion-tab-button>

          <ion-tab-button tab="tabPic" href="/tabs/tab3">
            <ion-icon :icon="gridOutline" />
            <ion-label>图片列表</ion-label>
          </ion-tab-button>

          <ion-tab-button tab="tabMy" href="/tabs/tab4">
            <ion-icon :icon="squareOutline" />
            <ion-label>存档信息</ion-label>
          </ion-tab-button>
        </ion-tab-bar>
      </ion-tabs>
      <ColorMgr trigger="btnColor" />
    </div>
    <div v-else class="bg-white h-full flex justify-center items-center">
      <ion-card class="max-w-96 max-h-96 w-full">
        <ion-card-header>
          <ion-card-title>用户登录</ion-card-title>
        </ion-card-header>
        <ion-card-content class="p-10">
          <ion-item id="btnUser">
            <ion-avatar slot="start" class="w-16 h-16">
              <ion-img :src="curUser.icon" />
            </ion-avatar>
            <ion-label class="text-2xl font-bold">{{ curUser.name }}</ion-label>
          </ion-item>
          <ion-item>
            <ion-input type="password" label="Password" @ionChange="onPwdChange" class="mt-4">
              <ion-input-password-toggle slot="end"></ion-input-password-toggle>
            </ion-input>
          </ion-item>
          <div class="text-center h-6 text-red-500">{{ errMsg }}</div>
          <ion-popover trigger="btnUser" alignment="center" size="cover" ref="userPopover">
            <ion-list>
              <ion-radio-group @ionChange="onUserSelect($event)" :value="curUser.id">
                <ion-item v-for="(u, idx) in userList" :value="u.id" :key="idx">
                  <ion-radio :value="u.id">
                    <ion-item lines="none">
                      <ion-avatar slot="start" class="w-12 h-12">
                        <ion-img :src="u.icon" />
                      </ion-avatar>
                      <div>{{ u.name }}</div>
                    </ion-item>
                  </ion-radio>
                </ion-item>
              </ion-radio-group>
            </ion-list>
          </ion-popover>
          <div class="flex justify-center">
            <ion-button
              strong="true"
              class="h-16 w-2/3 ion-no-margin mt-10 text-lg"
              @click="btnLoginClick"
              :disabled="curUser.id === -1">
              登 录
            </ion-button>
          </div>
        </ion-card-content>
      </ion-card>
    </div>
  </ion-page>
</template>

<script setup lang="ts">
import CryptoJS from "crypto-js";

import { bookmarksOutline } from "ionicons/icons";
import MdiStar from "~icons/mdi/star";

import { ColorOptions } from "@/modal/ColorType";
import { GroupOptions, PriorityOptions } from "@/modal/ScheduleType";
import { getUserList } from "@/utils/NetUtil";
import {
  IonAccordion,
  IonAccordionGroup,
  IonAvatar,
  IonCard,
  IonCardContent,
  IonCardHeader,
  IonCardTitle,
  IonCheckbox,
  IonImg,
  IonInputPasswordToggle,
  IonMenu,
  IonPopover,
  IonRadio,
  IonRadioGroup,
  IonRouterOutlet,
  IonTabBar,
  IonTabButton,
  IonTabs,
} from "@ionic/vue";
import {
  calendarOutline,
  colorPaletteOutline,
  gridOutline,
  shieldCheckmarkOutline,
  squareOutline,
} from "ionicons/icons";
import _ from "lodash";
import { inject, onMounted, ref } from "vue";
import { User } from "@/modal/UserData";

const bLogin = ref(false);
const userList = ref<any[]>([]);
const errMsg = ref("");
const curUser = ref(new User());
curUser.value.name = "点击选择用户";
const userPopover = ref<any>(null);
const textPwd = ref("");

const groupRef = ref(new Map(GroupOptions.map((option) => [option.id, true])));
const colorRef = ref(new Map(ColorOptions.map((option) => [option.id, true])));
const priorityRef = ref(new Map(PriorityOptions.map((option) => [option.id, true])));
const eventBus: any = inject("eventBus");
const globalVar: any = inject("globalVar");

onMounted(async () => {
  const userData = await getUserList();
  userList.value = userData.data;
  const sUserId = localStorage.getItem("saveUser");
  const sUser = _.find(userData.data, (u) => u.id.toString() === sUserId);
  if (sUser) {
    bLogin.value = true;
    curUser.value = sUser;
    globalVar.user = sUser;
  }
});
function getUserScore () {
  let score = 0;
  if (globalVar.userSave && globalVar.userSave.score){
    score = globalVar.userSave.score;
  }
  return score;
}
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
function onUserSelect(event: any) {
  const uu = _.find(userList.value, (u) => u.id === event.detail.value);
  if (uu) {
    curUser.value = uu;
  }
  userPopover.value?.$el.dismiss();
}
function onPwdChange(event: any) {
  textPwd.value = event.detail.value;
  errMsg.value = "";
}
function btnLoginClick() {
  if (curUser.value.pwd === null || curUser.value.pwd === CryptoJS.MD5(textPwd.value).toString()) {
    errMsg.value = "";
    bLogin.value = true;
    globalVar.user = curUser.value;
    localStorage.setItem("saveUser", curUser.value.id.toString());
  } else {
    errMsg.value = "密码错误";
  }
}
function btnLogoff() {
  bLogin.value = false;
  localStorage.removeItem("saveUser");
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
.schedule-group-item::part(native) {
  height: 35px !important;
  min-height: 0 !important;
}
</style>
