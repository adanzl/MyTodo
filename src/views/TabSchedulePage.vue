<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start" class="ion-padding">
          <ion-icon :icon="list"></ion-icon>
        </ion-buttons>
        <ion-title class="ion-text-center">
          <span v-if="selectedDate">{{ selectedDate.dt.format("YY年MM月") }}</span>
          <div v-else>日历</div>
        </ion-title>
        <ion-buttons slot="end" class="ion-padding">
          <ion-icon :icon="ellipseOutline" @click="btnTodayClk" style="margin-right: 16px"></ion-icon>
          <ion-icon :icon="swapVertical" @click="btnSortClk"></ion-icon>
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
            :minimal="bFold"
            :swiperRef="swiperRef">
          </CalenderTab>
        </swiper-slide>
      </swiper>
      <ion-button color="light" expand="full" fill="clear" size="small" @click="btnCalendarFoldClk()">
        <ion-icon :icon="bFold ? chevronDown : chevronUp" size="medium" color="primary"> </ion-icon>
      </ion-button>
      <!-- 日程列表 -->
      <ion-content color="light" @touchmove="onScheduleListTouchMove" @touchstart="onScheduleListTouchStart">
        <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
          <ion-refresher-content></ion-refresher-content>
        </ion-refresher>
        <ion-accordion-group :multiple="true" :value="['schedule', 'goals']">
          <ion-accordion value="schedule">
            <ion-item slot="header" color="light">
              <ion-label>{{ selectedDate?.dt.format("MM-DD") }}</ion-label>
            </ion-item>
            <div class="" slot="content">
              <ion-list :inset="true" lines="full" mode="ios" ref="curScheduleList">
                <!-- 日程条目 -->
                <ion-item-sliding v-for="(schedule, idx) in selectedDate?.events" :key="idx">
                  <ion-item :detail="true">
                    <ion-checkbox
                      style="--size: 26px; padding-right: 5px"
                      slot="start"
                      :checked="scheduleChecked(schedule.id)"
                      @ionChange="onScheduleCheckboxChange($event, selectedDate, schedule.id)">
                    </ion-checkbox>
                    <ion-label
                      :class="{
                        'text-line-through': selectedDate?.save[schedule.id]?.state === 1,
                      }"
                      @click="btnScheduleClk($event, schedule)">
                      <h2>{{ schedule.title }}</h2>
                      <p>
                        {{ selectedDate?.dt.format("ddd") }}
                        <ion-icon :icon="listOutline" style="position: relative; top: 3px"></ion-icon>
                        {{
                          schedule?.subTasks?.filter(
                            (t) => (selectedDate?.save[schedule.id]?.subTasks[t.id] || 0) === 1
                          ).length
                        }}/{{ schedule?.subTasks?.length }}
                      </p>
                    </ion-label>
                    <span
                      class="v-dot"
                      :style="{ 'background-color': getColorOptions(schedule.color).tag, 'margin-left': '10px' }">
                    </span>
                  </ion-item>
                  <ion-item-options side="end">
                    <ion-item-option @click="btnScheduleAlarmClk">
                      <ion-icon :icon="alarmOutline"></ion-icon>
                    </ion-item-option>
                    <ion-item-option color="danger" @click="btnScheduleRemoveClk($event, schedule)">
                      <ion-icon :icon="trashOutline"></ion-icon>
                    </ion-item-option>
                  </ion-item-options>
                </ion-item-sliding>
              </ion-list>
            </div>
          </ion-accordion>
          <ion-accordion value="goals">
            <ion-item slot="header" color="light">
              <ion-label>Goals</ion-label>
            </ion-item>
            <div class="ion-padding" slot="content">Content</div>
          </ion-accordion>
        </ion-accordion-group>
      </ion-content>
      <SchedulePop
        id="pop-modal"
        ref="scheduleModal"
        :is-open="isScheduleModalOpen"
        :modal="scheduleModal"
        :schedule="scheduleModalData"
        :save="scheduleSave"
        @willDismiss="onScheduleModalDismiss"
        @update:save="onUpdateScheduleSave"
        @update:schedule="onUpdateScheduleData">
      </SchedulePop>
      <ion-alert
        :is-open="scheduleDelConfirm.isOpen"
        header="Confirm!"
        :buttons="alertButtons"
        :sub-header="scheduleDelConfirm.text"
        @didDismiss="onDelSchedulerConfirm($event)"></ion-alert>
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
    <ion-fab slot="fixed" vertical="bottom" horizontal="end">
      <ion-fab-button @click="btnAddScheduleClk">
        <ion-icon :icon="addCircleOutline" size="large"></ion-icon>
      </ion-fab-button>
    </ion-fab>
  </ion-page>
</template>
<script lang="ts" src="../controller/TabSchedulePage.ts"></script>
<style lang="css" scoped src="../theme/TabSchedulePage.css"></style>
