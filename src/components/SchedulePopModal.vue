<template>
  <ion-modal show-backdrop="false" id="main" mode="ios" aria-hidden="false">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start" class="ion-padding">
          <ion-button @click="btnCancelClk">
            <ion-icon :icon="chevronBackOutline"> </ion-icon>
          </ion-button>
        </ion-buttons>
        <ion-title>
          <h3>{{ (curScheduleData?.id === -1 ? "新增" : "编辑") + "日程" }}</h3>
        </ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="main_content ion-padding" ref="scheduleTab">
      <ion-list :inset="true">
        <ion-item>
          <ion-checkbox
            slot="start"
            @ionChange="onTaskCheckboxChange"
            :checked="curSave?.state === 1">
          </ion-checkbox>
          <ion-input
            placeholder="输入日程标题"
            :value="curScheduleData?.title"
            :required="true"
            @ionChange="onTitleChange">
          </ion-input>
        </ion-item>
        <!-- 分组信息 -->
        <ion-item class="group">
          <ion-button id="btnGroup" class="group-tab" fill="none">
            <ion-icon :icon="bookmark" aria-hidden="true"></ion-icon>
            <ion-label>{{ getGroupOptions(curScheduleData.groupId).label }}</ion-label>
          </ion-button>
          <GroupSelector
            trigger="btnGroup"
            @update:value="onGroupChange"
            :value="curScheduleData.groupId"></GroupSelector>
          <ion-button id="btnPriority" class="group-tab" fill="none">
            <ion-label><strong>Pri</strong></ion-label>
            <Icon
              :icon="getPriorityOptions(curScheduleData.priority).icon"
              :height="'36'"
              :color="getPriorityOptions(curScheduleData.priority).color">
            </Icon>
          </ion-button>
          <PrioritySelector
            trigger="btnPriority"
            @update:value="onPriorityChange"
            :value="curScheduleData.priority">
          </PrioritySelector>
          <ion-button id="btnColor" class="group-tab" fill="none">
            <ion-icon slot="start" :icon="colorPalette" aria-hidden="true"> </ion-icon>
            <span
              :style="{ 'background-color': getColorOptions(curScheduleData.color).tag }"
              class="v-dot"></span>
          </ion-button>
          <ColorSelector
            trigger="btnColor"
            @update:value="onColorChange"
            :value="curScheduleData.color">
          </ColorSelector>
        </ion-item>
      </ion-list>
      <ion-list :inset="true">
        <!-- 开始日期 -->
        <ion-item class="ion-text-center" :button="true" size="large" @click="btnScheduleDTClk">
          <ion-icon :icon="calendar" slot="start"></ion-icon>
          <div class="flex ion-justify-content-around ion-padding width-100">
            <div class="ion-text-center">
              <ion-label>{{ curScheduleData.startTs?.format("MM-DD") }}</ion-label>
              <ion-label color="tertiary" class="font-size-mini">
                {{ curScheduleData.allDay ? "全天" : curScheduleData?.startTs?.format("HH:mm") }}
              </ion-label>
            </div>
            <div>
              <ion-label> >></ion-label>
            </div>
            <div class="ion-text-center">
              <ion-label>{{ curScheduleData.endTs?.format("MM-DD") }}</ion-label>
              <ion-label color="tertiary" class="font-size-mini">
                {{ curScheduleData.allDay ? "全天" : curScheduleData?.endTs?.format("HH:mm") }}
              </ion-label>
            </div>
          </div>
        </ion-item>
        <ion-item ref="dtComponentItem" class="height-0-block flex">
          <div ref="scheduleDTComponent" style="width: 100%">
            <ion-buttons class="ion-justify-content-around">
              <ion-button @click="btnScheduleDateClearClk">清除</ion-button>
              <ion-segment v-model="scheduleType" style="width: 130px" @ionChange="onDtTabChange">
                <ion-segment-button value="0" id="dtStart">开始</ion-segment-button>
                <ion-segment-button value="1" id="dtEnd">结束</ion-segment-button>
              </ion-segment>
              <ion-button @click="btnDatetimeOkClk">确定</ion-button>
            </ion-buttons>
            <ion-datetime
              presentation="date"
              locale="zh-cn"
              @ionChange="onDtChange"
              size="cover"
              class="schedule-datetime-date">
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
              <ion-label>开始时间</ion-label>
              <label>
                {{ curScheduleData.allDay ? "全天" : curScheduleData.startTs?.format("HH:mm") }}
              </label>
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
                  <ion-title><h2>开始时间</h2></ion-title>
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
                  <ion-toggle
                    :checked="curScheduleData.allDay"
                    @ionChange="onScheduleDatetimeAllDayChange">
                    <h3>全天</h3>
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
                    清除
                  </ion-button>
                  <ion-button
                    size="large"
                    fill="clear"
                    style="width: 50%"
                    @click="btnScheduleDatetimeOkClk">
                    确定
                  </ion-button>
                </ion-item>
              </ion-modal>
            </ion-item>
          </div>
        </ion-item>
        <!-- <ion-item :button="true" :detail="true">
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
        </ion-item> -->
        <ion-item detail="true">
          <ion-icon :icon="repeat" aria-hidden="true" slot="start"> </ion-icon>
          <ion-select :value="curScheduleData?.repeat" @ion-change="onRepeatChange">
            <div slot="label">
              <ion-label>重复</ion-label>
            </div>
            <ion-select-option v-for="(op, idx) in RepeatOptions" :key="idx" :value="op.id">
              {{ op.label }}
            </ion-select-option>
          </ion-select>
        </ion-item>
        <ion-item detail="true" :button="true">
          <ion-icon :icon="power" slot="start"></ion-icon>
          <ion-label>重复停止</ion-label>
          <ion-datetime-button datetime="idRepeatEndTs">
            <ion-label slot="date-target" v-if="curScheduleData?.repeatEndTs === undefined">
              无
            </ion-label>
          </ion-datetime-button>
          <ion-modal :keep-contents-mounted="true" ref="repeatEndTsModal">
            <ion-datetime
              locale="zh-cn"
              id="idRepeatEndTs"
              ref="repeatEndTsComponent"
              :value="curScheduleData?.repeatEndTs?.format('YYYY-MM-DD')"
              presentation="date"
              @ionChange="onRepeatEndDtChange">
              <ion-buttons slot="buttons" class="ion-justify-content-around">
                <ion-button color="warning" @click="btnRepeatEndClearClk"> 清除 </ion-button>
                <ion-button @click="btnRepeatEndOkClk">确定</ion-button>
              </ion-buttons>
            </ion-datetime>
          </ion-modal>
        </ion-item>
      </ion-list>
      <ion-list :inset="true">
        <ion-item lines="none">
          <ion-icon :icon="listOutline" slot="start"></ion-icon>
          <ion-label>子任务</ion-label>
          <span>
            {{ curScheduleData?.subtasks?.filter((t: any) => subTaskChecked(t)).length }}/{{
              curScheduleData?.subtasks?.length
            }}
          </span>
        </ion-item>
        <!-- 子任务 -->
        <ion-item lines="none">
          <ion-icon :icon="add" slot="start" style="width: 22px"></ion-icon>
          <ion-button @click="btnSubtaskAddClk" expand="full" class="width-100" color="light">
            添加子任务
          </ion-button>
        </ion-item>
        <SubtaskPopModal
          @update:value="onSubtaskChange"
          :value="curSubtask"
          :is-open="openSubtaskModal"
          @ion-modal-will-dismiss="
            () => {
              openSubtaskModal = false;
            }
          ">
        </SubtaskPopModal>
        <ion-item v-for="(task, idx) in curScheduleData?.subtasks" :key="idx">
          <ion-checkbox
            slot="start"
            :checked="subTaskChecked(task)"
            @ionChange="onSubtaskCheckboxChange($event, task)">
          </ion-checkbox>
          <div class="subtask-content" @click="onSubtaskClk($event, task)">
            <ion-label :class="{ 'text-line-through': subTaskChecked(task) }" class="ion-no-margin">
              {{ task.name }}
            </ion-label>
            <div class="pre-img-group" style="margin-top: 5px">
              <div class="pre-img-block" v-for="(img, idx) in task.imgIds" :key="idx">
                <img :src="imgs[img]" />
              </div>
            </div>
          </div>
          <ion-icon
            :icon="removeCircleOutline"
            slot="end"
            @click="btnSubtaskRemoveClk($event, task)">
          </ion-icon>
        </ion-item>
      </ion-list>
    </ion-content>
    <ion-footer>
      <ion-toolbar>
        <ion-button expand="block" color="warning" @click="btnSaveClk"> 保存 </ion-button>
      </ion-toolbar>
    </ion-footer>
    <ion-toast
      :is-open="toastData.isOpen"
      :message="toastData.text"
      :duration="toastData.duration"
      @didDismiss="onToastDismiss">
    </ion-toast>
    <ion-action-sheet :is-open="openSaveSheet" :buttons="saveActionButtons"> </ion-action-sheet>
  </ion-modal>
</template>
<script lang="ts" src="../controller/SchedulePopModal.ts"></script>
<style scoped src="../theme/SchedulePopModal.css"></style>
