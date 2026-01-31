<template>
  <ion-page id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-menu-button></ion-menu-button>
        </ion-buttons>
        <ion-title>
          <div v-if="selectedDate">{{ selectedDate.dt.format("YY年MM月") }}</div>
          <div v-else>日历</div>
        </ion-title>
        <ion-buttons slot="end">
          <ServerRemoteBadge />
          <ion-button
            class="!mr-1"
            @click="btnTodayClk"
            :disabled="selectedDate?.dt.isToday()">
            今
          </ion-button>
          <ion-button id="btnSort" @click="btnSortClk">
            <ion-icon :icon="swapVertical" class="button-native"></ion-icon>
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <div class="h-fit pt-1" style="background-color: var(--color-main-bg)">
      <!-- https://blog.csdn.net/weixin_41863239/article/details/82490886 -->
      <swiper
        @slideNextTransitionEnd="onSlideChangeNext"
        @slidePrevTransitionEnd="onSlideChangePre"
        @swiper="setSwiperInstance"
        :centered-slides="true"
        :autoHeight="true"
        :modules="[Keyboard, IonicSlides]"
        :keyboard="true">
        <swiper-slide v-for="(slide, idx) in slideArr" :key="idx">
          <CalenderTab
            :slide="slide"
            :daySelectCallback="onDaySelected"
            :selectedDate="selectedDate"
            :swiperRef="swiperRef">
          </CalenderTab>
        </swiper-slide>
      </swiper>
      <ion-button
        color="light"
        expand="full"
        fill="clear"
        class="ion-no-margin ion-no-padding"
        style="min-height: auto"
        @click="btnCalendarFoldClk()">
        <ion-icon :icon="bFold ? chevronDown : chevronUp" color="primary"> </ion-icon>
      </ion-button>
    </div>
    <ion-content ref="scheduleList" scrollEvents @ionScroll="onScheduleListScroll">
      <!-- 日程列表 -->
      <div
        class="flex-1 h-full"
        @touchmove="onScheduleListTouchMove"
        @touchstart="onScheduleListTouchStart">
        <ion-accordion-group :multiple="true" :value="['schedule']">
          <ion-accordion value="schedule">
            <ion-item slot="header" color="light" class="schedule-group-item">
              <div class="mr-3">{{ selectedDate?.dt.format("MM-DD") }}</div>
              <span class="mr-1 text-sm">当前有</span>
              <Icon icon="mdi:star" class="text-red-500 w-4 h-4 mr-1" />
              <span> {{ user?.score ?? 0 }}</span>
              <p style="margin-right: 8px" class="gray" slot="end">
                {{ selectedDate?.events.length }}
              </p>
            </ion-item>
            <div slot="content">
              <ion-reorder-group
                :disabled="bReorderDisabled"
                ref="curScheduleList"
                @ionItemReorder="onReorder($event)"
                mode="ios"
                class="my-0">
                <!-- 日程条目 -->
                <ion-item-sliding
                  v-for="schedule in selectedDate?.events.filter(bShowScheduleItem)"
                  :key="schedule.id">
                  <ion-item lines="none">
                    <ion-checkbox
                      style="--size: 26px; padding-right: 5px"
                      slot="start"
                      :checked="scheduleChecked(schedule.id)"
                      @ionChange="onScheduleCheckboxChange($event, selectedDate, schedule)">
                    </ion-checkbox>
                    <div @click="btnScheduleClk($event, schedule)" class="flex w-full items-center">
                      <ion-label
                        :class="{
                          'line-through':
                            selectedDate?.save && selectedDate?.save[schedule.id]?.state === 1,
                        }"
                        class="pt-2.5 flex-1">
                        <h2 class="truncate">
                          {{ schedule.title }}
                        </h2>
                        <div class="flex text-gray-400">
                          <span class="mr-1 flex items-center text-base">
                            <component
                              :is="getGroupOptions(schedule.groupId).icon"
                              height="18px"
                              width="18px" />
                          </span>
                          <span class="w-14 mr-1 flex items-center text-xs">
                            {{ getGroupOptions(schedule.groupId).label }}
                          </span>
                          <span class="mr-3 flex items-center text-xs">
                            {{ schedule.allDay ? "全天" : schedule.startTs?.format("HH:mm") }}
                          </span>
                          <span class="mr-1 flex items-center">
                            <Icon icon="mdi:star" class="text-red-500 w-4 h-4 mr-1" />
                            <p class="w-5 text-sm">
                              {{ countAllReward(schedule) }}
                            </p>
                          </span>
                        </div>
                      </ion-label>
                      <span
                        class="v-dot"
                        :style="{
                          'background-color': getColorOptions(schedule.color).tag,
                          'margin-left': '10px',
                        }">
                      </span>
                      <component
                        :is="getPriorityOptions(schedule.priority).icon"
                        :height="'36px'"
                        :width="'36px'"
                        :color="getPriorityOptions(schedule.priority).color">
                      </component>
                    </div>
                    <ion-reorder slot="end"></ion-reorder>
                  </ion-item>
                  <div
                    class="pl-[60px] flex items-center text-gray-400"
                    v-for="(sub, idx) in schedule.subtasks"
                    :key="idx"
                    @click="btnScheduleClk($event, schedule)">
                    <ion-checkbox
                      disabled
                      class="sub-checkbox"
                      :checked="
                        selectedDate &&
                        selectedDate.save &&
                        selectedDate.save[schedule.id]?.subtasks[sub.id] === 1
                      " />
                    <span class="pl-2 text-base flex-1">{{ sub.name }}</span>
                    <Icon icon="mdi:star" class="text-red-500" />
                    <span class="w-5 text-right mr-6">{{ sub.score ?? 0 }}</span>
                  </div>
                  <ion-item-options side="end">
                    <ion-item-option @click="btnScheduleAlarmClk">
                      <ion-icon :icon="alarmOutline"></ion-icon>
                    </ion-item-option>
                    <ion-item-option color="danger" @click="btnScheduleRemoveClk($event, schedule)">
                      <ion-icon :icon="trashOutline"></ion-icon>
                    </ion-item-option>
                  </ion-item-options>
                  <div style="height: 1px; box-shadow: 0 0 0 0.1px #f00 inset;" class="mt-2"></div>
                </ion-item-sliding>
              </ion-reorder-group>
            </div>
          </ion-accordion>
        </ion-accordion-group>
      </div>
      <SchedulePop
        ref="scheduleModal"
        :is-open="isScheduleModalOpen"
        :modal="scheduleModal"
        :schedule="scheduleModalData"
        :save="scheduleSave"
        @willDismiss="onScheduleModalDismiss">
      </SchedulePop>
      <ion-alert
        :is-open="scheduleDelConfirm.isOpen"
        header="Confirm!"
        :buttons="[
          { text: 'Cancel', role: 'cancel' },
          { text: 'OK', role: 'confirm' },
        ]"
        :sub-header="scheduleDelConfirm.text"
        @didDismiss="onDelSchedulerConfirm($event)">
      </ion-alert>
      <ion-toast
        :is-open="toastData.isOpen"
        :message="toastData.text"
        :duration="toastData.duration"
        @didDismiss="() => (toastData.isOpen = false)">
      </ion-toast>
    </ion-content>
    <FabButton @click="btnAddScheduleClk" hasBar>
      <ion-icon :icon="add" style="font-size: 36px"></ion-icon>
    </FabButton>
  </ion-page>
</template>
<script lang="ts" src="@/views/TabSchedulePage.ts"></script>
<style lang="css" scoped>
.schedule-group-item::part(native) {
  height: 35px !important;
  min-height: 0 !important;
}
.sub-checkbox {
  --size: 18px;
  --border-radius: 4px;
}
</style>
