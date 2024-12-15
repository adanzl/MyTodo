<template>
  <div class="ion-padding" id="main">
    <ion-toolbar class="transparent">
      <ion-title>{{ (curScheduleData?.id === -1 ? "Add" : "Editor") + " Schedule" }} </ion-title>
    </ion-toolbar>
    <ion-segment value="sType" @ionChange="onTypeChange">
      <ion-segment-button value="sType" content-id="sType">
        <ion-label>Schedule</ion-label>
      </ion-segment-button>
      <ion-segment-button value="tType" content-id="tType">
        <ion-label>Todo</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view class="main_content">
      <ion-segment-content id="sType" style="height: 100%; background-color: gray !important">
        <ion-content id="main_bg" class="ion-margin-top" ref="scheduleTab">
          <ion-list :inset="true">
            <ion-item>
              <ion-checkbox slot="start" @ionChange="onTaskCheckboxChange" :checked="curSave?.state === 1">
              </ion-checkbox>
              <ion-input
                placeholder="输入日程标题"
                :value="curScheduleData?.title"
                :required="true"
                @ionChange="
                  ($event: any) => {
                    curScheduleData.title = $event.detail.value;
                  }
                ">
              </ion-input>
            </ion-item>
            <!-- 分组信息 -->
            <ion-item>
              <ion-select label-placement="floating" label="Group" value="work">
                <ion-icon slot="start" :icon="bookmark" aria-hidden="true"> </ion-icon>
                <ion-select-option value="none">None</ion-select-option>
                <ion-select-option value="work">Work</ion-select-option>
                <ion-select-option value="other">Other</ion-select-option>
              </ion-select>
              <ion-select label-placement="stacked" label="Priority" value="0">
                <ion-icon slot="start" :icon="airplane" aria-hidden="true"> </ion-icon>
                <ion-select-option value="0">I</ion-select-option>
                <ion-select-option value="1">II</ion-select-option>
                <ion-select-option value="2">III</ion-select-option>
                <ion-select-option value="3">IV</ion-select-option>
              </ion-select>
              <ion-select label-placement="stacked" label="Color" value="0">
                <ion-icon slot="start" :icon="colorPalette" aria-hidden="true"> </ion-icon>
                <ion-select-option value="0">Red</ion-select-option>
                <ion-select-option value="1">Yellow</ion-select-option>
                <ion-select-option value="2">Blue</ion-select-option>
                <ion-select-option value="3">White</ion-select-option>
              </ion-select>
            </ion-item>
          </ion-list>
          <ion-list :inset="true">
            <!-- 开始日期 -->
            <ion-item class="ion-text-center" :button="true" size="large" @click="btnScheduleDTClk">
              <ion-icon :icon="calendar" slot="start"></ion-icon>
              <div class="flex ion-justify-content-around ion-padding width-100">
                <div class="ion-text-center">
                  <ion-label>{{ curScheduleData.startTs?.format("MM-DD,ddd") }}</ion-label>
                  <ion-label color="tertiary" class="font-size-mini">
                    {{ curScheduleData.allDay ? "All Day" : curScheduleData?.startTs?.format("HH:mm") }}
                  </ion-label>
                </div>
                <div>
                  <ion-label> >></ion-label>
                </div>
                <div class="ion-text-center">
                  <ion-label>{{ curScheduleData.endTs?.format("MM-DD,ddd") }}</ion-label>
                  <ion-label color="tertiary" class="font-size-mini">
                    {{ curScheduleData.allDay ? "All Day" : curScheduleData?.endTs?.format("HH:mm") }}
                  </ion-label>
                </div>
              </div>
            </ion-item>
            <ion-item ref="dtComponentItem" class="height-0-block flex">
              <div ref="scheduleDTComponent" style="width: 100%">
                <ion-buttons mode="ios" class="ion-justify-content-around">
                  <ion-button @click="btnScheduleDateClearClk"> Clear </ion-button>
                  <ion-segment v-model="scheduleType" mode="ios" style="width: 130px" @ionChange="onDtTabChange">
                    <ion-segment-button value="0" id="dtStart"> Start </ion-segment-button>
                    <ion-segment-button value="1" id="dtEnd"> End </ion-segment-button>
                  </ion-segment>
                  <ion-button @click="btnDatetimeOkClk">OK </ion-button>
                </ion-buttons>
                <ion-datetime presentation="date" @ionChange="onDtChange" size="cover" class="schedule-datetime-date">
                </ion-datetime>
                <ion-item
                  class="ion-no-padding"
                  @click="
                    () => {
                      datetimeShowFlag = true;
                    }
                  ">
                  <!-- 开始时间 -->
                  <ion-icon :icon="timeOutline" aria-hidden="true" slot="start"> </ion-icon>
                  <ion-label>Start time </ion-label>
                  <label>{{ curScheduleData.allDay ? "All day" : curScheduleData.startTs?.format("HH:mm") }}</label>
                  <ion-modal
                    class="m-ion-modal"
                    mode="ios"
                    :isOpen="datetimeShowFlag"
                    :keep-contents-mounted="true"
                    @willDismiss="
                      () => {
                        datetimeShowFlag = false;
                      }
                    ">
                    <div class="wrapper">
                      <ion-item>
                        <ion-title><h2>Start time</h2></ion-title>
                      </ion-item>
                      <ion-datetime
                        id="dts"
                        presentation="time"
                        size="cover"
                        mode="ios"
                        :value="curScheduleData?.startTs?.format('YYYY-MM-DDTHH:mm')"
                        hourCycle="h23"
                        :disabled="curScheduleData?.allDay"
                        @ionChange="
                          (e:any) => {
                            scheduleStartTsComponent = dayjs(e.detail.value);
                          }
                        "
                        class="schedule-datetime-time">
                      </ion-datetime>
                      <ion-item>
                        <ion-toggle :checked="curScheduleData.allDay" @ionChange="onScheduleDatetimeAllDayChange">
                          <h3>All day</h3>
                        </ion-toggle>
                      </ion-item>
                      <ion-item>
                        <ion-button
                          size="large"
                          fill="clear"
                          style="width: 50%"
                          @click="
                            () => {
                              datetimeShowFlag = false;
                            }
                          ">
                          Cancel
                        </ion-button>
                        <ion-button size="large" fill="clear" style="width: 50%" @click="btnScheduleDatetimeOkClk">
                          Done
                        </ion-button>
                      </ion-item>
                    </div>
                  </ion-modal>
                </ion-item>
              </div>
            </ion-item>
            <ion-item :button="true" :detail="true">
              <ion-icon :icon="notifications" aria-hidden="true" slot="start"> </ion-icon>
              <ion-select
                id="selectReminder"
                aria-label="Reminder"
                :value="curScheduleData?.reminder"
                @ionChange="onReminderChange">
                <div slot="label">
                  <ion-label>Reminder</ion-label>
                </div>
                <ion-select-option v-for="(op, idx) in reminderOptions" :key="idx" :value="op.id">
                  {{ op.label }}
                </ion-select-option>
              </ion-select>
            </ion-item>
            <ion-item detail="true">
              <ion-icon :icon="repeat" aria-hidden="true" slot="start"> </ion-icon>
              <ion-select :value="curScheduleData?.repeat" @ion-change="onRepeatChange">
                <div slot="label">
                  <ion-label>Repeat</ion-label>
                </div>
                <ion-select-option v-for="(op, idx) in repeatOptions" :key="idx" :value="op.id">
                  {{ op.label }}
                </ion-select-option>
              </ion-select>
            </ion-item>
            <ion-item detail="true" :button="true">
              <ion-icon :icon="power" slot="start"></ion-icon>
              <ion-label>Repeat End</ion-label>
              <ion-datetime-button datetime="idRepeatEndTs">
                <ion-label slot="date-target" v-if="curScheduleData?.repeatEndTs === undefined">None</ion-label>
              </ion-datetime-button>
              <ion-modal :keep-contents-mounted="true" ref="repeatEndTsModal" mode="ios">
                <ion-datetime
                  id="idRepeatEndTs"
                  ref="repeatEndTsComponent"
                  :value="curScheduleData?.repeatEndTs?.format('YYYY-MM-DD')"
                  presentation="date"
                  @ionChange="onRepeatEndDtChange">
                  <ion-buttons slot="buttons" mode="ios" class="ion-justify-content-around">
                    <ion-button color="warning" @click="btnRepeatEndClearClk"> Clear </ion-button>
                    <ion-button @click="btnRepeatEndOkClk">OK</ion-button>
                  </ion-buttons>
                </ion-datetime>
              </ion-modal>
            </ion-item>
          </ion-list>
          <ion-list :inset="true">
            <ion-item lines="none">
              <ion-icon :icon="listOutline" slot="start"></ion-icon>
              <ion-label>Sub-task</ion-label>
              <span>
                {{ curScheduleData?.subTasks?.filter((t: any) => subTaskChecked(t)).length }}/{{
                  curScheduleData?.subTasks?.length
                }}
              </span>
            </ion-item>
            <!-- 子任务 -->
            <ion-item lines="none">
              <ion-icon :icon="add" slot="start" style="width: 22px"></ion-icon>
              <ion-input
                v-model="addSubtaskInput"
                placeholder="Add a subtask"
                @ionChange="onSubtaskInputChange($event, undefined)">
              </ion-input>
            </ion-item>
            <ion-item v-for="task in curScheduleData?.subTasks" :key="task">
              <ion-checkbox
                slot="start"
                :checked="subTaskChecked(task)"
                @ionChange="onSubtaskCheckboxChange($event, task)">
              </ion-checkbox>
              <ion-input
                :value="task.name"
                @ionChange="onSubtaskInputChange($event, task)"
                :class="{ 'text-line-through': subTaskChecked(task) }">
              </ion-input>
              <ion-icon :icon="removeCircleOutline" slot="end" @click="btnSubtaskRemoveClk($event, task)"> </ion-icon>
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
      <ion-button expand="block" mode="ios" color="warning" @click="btnSaveClk"> Save </ion-button>
    </ion-footer>
  </div>
  <ion-toast
    :is-open="toastData.isOpen"
    :message="toastData.text"
    :duration="toastData.duration"
    @didDismiss="
      () => {
        toastData.isOpen = false;
      }
    "></ion-toast>
</template>
<script lang="ts" src="../controller/SchedulePopModal.ts"></script>

<style scoped src="../theme/SchedulePopModal.css"></style>
