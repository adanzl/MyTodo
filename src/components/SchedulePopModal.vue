<template>
  <ion-modal show-backdrop="false" id="main" mode="ios">
    <ion-header>
      <ion-toolbar class="ion-padding">
        <ion-icon
          slot="start"
          :icon="chevronBackOutline"
          style="width: 30px; height: 25px; position: absolute; top: 15px"
          @click="btnCancelClk"></ion-icon>
        <ion-title>
          <h1>{{ (curScheduleData?.id === -1 ? "Add" : "Edit") + " Schedule" }}</h1>
        </ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="main_content ion-padding" ref="scheduleTab">
      <ion-list :inset="true">
        <ion-item>
          <ion-checkbox slot="start" @ionChange="onTaskCheckboxChange" :checked="curSave?.state === 1"> </ion-checkbox>
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
          <ion-item id="btnPriority" lines="none">
            <ion-label>Pri</ion-label>
            <ion-icon
              :icon="icons.mdiRomanNums[getPriorityOptions(curScheduleData.priority).icon]"
              :style="{ color: getPriorityOptions(curScheduleData.priority).color }"
              size="large"></ion-icon>
          </ion-item>
          <PrioritySelector trigger="btnPriority" @update:value="onPriorityChange" :value="curScheduleData.priority">
          </PrioritySelector>
          <ion-item id="btnColor">
            <ion-icon slot="start" :icon="colorPalette" aria-hidden="true"> </ion-icon>
            <span :style="{ 'background-color': getColorOptions(curScheduleData.color).tag }" class="v-dot"></span>
          </ion-item>
          <ColorSelector trigger="btnColor" @update:value="onColorChange" :value="curScheduleData.color">
          </ColorSelector>
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
            <ion-buttons class="ion-justify-content-around">
              <ion-button @click="btnScheduleDateClearClk"> Clear </ion-button>
              <ion-segment v-model="scheduleType" style="width: 130px" @ionChange="onDtTabChange">
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
                class="start-time-modal"
                :isOpen="datetimeShowFlag"
                :keep-contents-mounted="true"
                @willDismiss="
                  () => {
                    datetimeShowFlag = false;
                  }
                ">
                <ion-item>
                  <ion-title><h2>Start time</h2></ion-title>
                </ion-item>
                <ion-datetime
                  id="dts"
                  presentation="time"
                  size="cover"
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
            <ion-select-option v-for="(op, idx) in RepeatOptions" :key="idx" :value="op.id">
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
          <ion-modal :keep-contents-mounted="true" ref="repeatEndTsModal">
            <ion-datetime
              id="idRepeatEndTs"
              ref="repeatEndTsComponent"
              :value="curScheduleData?.repeatEndTs?.format('YYYY-MM-DD')"
              presentation="date"
              @ionChange="onRepeatEndDtChange">
              <ion-buttons slot="buttons" class="ion-justify-content-around">
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
          <ion-checkbox slot="start" :checked="subTaskChecked(task)" @ionChange="onSubtaskCheckboxChange($event, task)">
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
    <ion-footer>
      <ion-toolbar class="transparent">
        <ion-button expand="block" color="warning" @click="btnSaveClk"> Save </ion-button>
      </ion-toolbar>
    </ion-footer>
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
  </ion-modal>
</template>
<script lang="ts" src="../controller/SchedulePopModal.ts"></script>
<style scoped src="../theme/SchedulePopModal.css"></style>
