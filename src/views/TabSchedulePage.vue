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
          <ion-button
            style="position: absolute; right: 50px"
            @click="btnTodayClk"
            v-if="!selectedDate?.dt.isToday()">
            今
          </ion-button>
          <ion-button id="btnSort" @click="btnSortClk">
            <ion-icon :icon="swapVertical" class="button-native"></ion-icon>
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content :scroll-y="false">
      <!-- https://blog.csdn.net/weixin_41863239/article/details/82490886 -->
      <swiper
        @slideNextTransitionEnd="onSlideChangeNext"
        @slidePrevTransitionEnd="onSlideChangePre"
        @swiper="setSwiperInstance"
        :centered-slides="true"
        :autoHeight="true"
        :modules="[IonicSlides, Keyboard]"
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
      <!-- 日程列表 -->
      <ion-content
        color="light"
        @touchmove="onScheduleListTouchMove"
        @touchstart="onScheduleListTouchStart">
        <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
          <ion-refresher-content></ion-refresher-content>
        </ion-refresher>
        <ion-accordion-group :multiple="true" :value="['schedule']">
          <ion-accordion value="schedule">
            <ion-item slot="header" color="light" class="schedule-group-item">
              <ion-label>{{ selectedDate?.dt.format("MM-DD") }}</ion-label>
              <p style="margin-right: 8px" class="gray">{{ selectedDate?.events.length }}</p>
            </ion-item>
            <div slot="content" >
              <ion-reorder-group
                :disabled="bReorderDisabled"
                @ionItemReorder="onReorder($event)"
                mode="ios"
                ref="curScheduleList"
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
                      @ionChange="onScheduleCheckboxChange($event, selectedDate, schedule.id)">
                    </ion-checkbox>
                    <div @click="btnScheduleClk($event, schedule)" class="flex w-full items-center">
                      <ion-label
                        :class="{
                          'text-line-through':
                            selectedDate?.save && selectedDate?.save[schedule.id]?.state === 1,
                        }"
                        class="pt-2.5 flex-1">
                        <h2 class="truncate">{{ schedule.title }}</h2>
                        <div class="flex text-gray-400">
                          <p class="w-14 mb-0">
                            <ion-icon :icon="listOutline" class="top-1 relative" />
                            {{ countFinishedSubtask(schedule) }}
                            /
                            {{ schedule?.subtasks?.length }}
                          </p>
                          <span class="mr-1">
                            <component
                              :is="getGroupOptions(schedule.groupId).icon"
                              height="18px"
                              width="18px" />
                          </span>
                          <p class="w-14">
                            {{ getGroupOptions(schedule.groupId).label }}
                          </p>
                          <p>{{ schedule.allDay ? "全天" : schedule.startTs?.format("HH:mm") }}</p>
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
                    class="pl-[60px] flex items-center"
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
                    <span class="pl-2 text-gray-500 text-base">{{ sub.name }}</span>
                  </div>
                  <ion-item-options side="end">
                    <ion-item-option @click="btnScheduleAlarmClk">
                      <ion-icon :icon="alarmOutline"></ion-icon>
                    </ion-item-option>
                    <ion-item-option color="danger" @click="btnScheduleRemoveClk($event, schedule)">
                      <ion-icon :icon="trashOutline"></ion-icon>
                    </ion-item-option>
                  </ion-item-options>
                  <div style="border-bottom-width: 1px" class="mt-2"></div>
                </ion-item-sliding>
              </ion-reorder-group>
            </div>
          </ion-accordion>
        </ion-accordion-group>
      </ion-content>
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
        :buttons="alertButtons"
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
    <ion-fab slot="fixed" vertical="bottom" horizontal="end">
      <ion-fab-button @click="btnAddScheduleClk">
        <ion-icon :icon="add" style="font-size: 36px"></ion-icon>
      </ion-fab-button>
    </ion-fab>
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
