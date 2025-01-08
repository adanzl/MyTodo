<template>
  <ion-modal id="main" @ion-modal-will-dismiss="onModalDismiss">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button @click="btnCancelClk">
            <ion-icon :icon="chevronBackOutline" />
          </ion-button>
        </ion-buttons>
        <ion-title>
          <h3>{{ (curScheduleData?.id === -1 ? "新增" : "编辑") + "日程" }}</h3>
        </ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="" ref="scheduleTab" mode="ios">
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
            class="font-bold"
            @ionChange="onTitleChange">
          </ion-input>
        </ion-item>
        <!-- 分组信息 -->
        <ion-item class="group">
          <ion-button id="btnGroup" class="flex-1 text-base" fill="none">
            <!-- <ion-icon :icon="bookmarksOutline" class="mr-1"></ion-icon> -->
            <span class="mr-3">
              <component
                :is="getGroupOptions(curScheduleData.groupId).icon"
                height="24px"
                width="24px"
                color="#7970ff" />
            </span>
            <ion-label>{{ getGroupOptions(curScheduleData.groupId).label }}</ion-label>
          </ion-button>
          <GroupSelector
            trigger="btnGroup"
            @update:value="onGroupChange"
            :value="curScheduleData.groupId" />
          <ion-button id="btnPriority" class="flex-1 text-base" fill="none">
            <ion-label><strong>Pri</strong></ion-label>
            <component
              :is="getPriorityOptions(curScheduleData.priority).icon"
              :height="'36px'"
              width="36px"
              :color="getPriorityOptions(curScheduleData.priority).color" />
          </ion-button>
          <ion-button id="btnColorSelect" class="flex-1 text-base" fill="none">
            <ion-icon slot="start" :icon="colorPaletteOutline" />
            <span
              :style="{ 'background-color': getColorOptions(curScheduleData.color).tag }"
              class="v-dot"></span>
          </ion-button>
          <ColorSelector
            trigger="btnColorSelect"
            @update:value="onColorChange"
            :value="curScheduleData.color" />
        </ion-item>
      </ion-list>
      <ion-list :inset="true">
        <!-- 开始日期 -->
        <ion-item
          key="0"
          class="ion-text-center"
          :button="true"
          size="large"
          @click="btnScheduleDTClk">
          <ion-icon :icon="calendarOutline" slot="start"></ion-icon>
          <div class="flex ion-justify-content-around ion-padding w-full">
            <div class="ion-text-center" v-if="curScheduleData.startTs">
              <div class="flex items-baseline font-bold text-red-500">
                {{ curScheduleData.startTs.format("MM-DD") + "," }}
                <p class="text-xs">{{ WEEK[curScheduleData.startTs.day()] }}</p>
              </div>
              <ion-label color="tertiary" class="text-xs/4">
                {{ curScheduleData.allDay ? "全天" : curScheduleData?.startTs?.format("HH:mm") }}
              </ion-label>
            </div>
            <div v-else>暂无开始时间</div>
            <div>
              <MdiChevronDoubleRight height="100%" preserveAspectRatio="none" />
            </div>
            <div class="ion-text-center" v-if="curScheduleData.endTs">
              <div class="flex items-baseline font-bold text-red-500">
                {{ curScheduleData.endTs.format("MM-DD") + "," }}
                <p class="text-xs">{{ WEEK[curScheduleData.endTs.day()] }}</p>
              </div>
              <ion-label color="tertiary" class="text-xs/4">
                {{ curScheduleData.allDay ? "全天" : curScheduleData?.endTs?.format("HH:mm") }}
              </ion-label>
            </div>
            <div v-else>暂无结束时间</div>
          </div>
        </ion-item>
        <ion-item ref="dtComponentItem" class="height-0-block flex">
          <div ref="scheduleDTComponent" class="w-full">
            <ion-buttons class="ion-justify-content-around">
              <ion-button @click="btnScheduleDateClearClk">清除</ion-button>
              <ion-segment v-model="scheduleType" style="width: 130px" @ionChange="onDtTabChange">
                <ion-segment-button value="0" class="w-15 min-w-0">开始</ion-segment-button>
                <!-- <ion-segment-button value="1" class="w-15 min-w-0">结束</ion-segment-button> -->
              </ion-segment>
              <ion-button @click="btnDatetimeOkClk">确定</ion-button>
            </ion-buttons>
            <ion-datetime
              presentation="date"
              max="2099-01-01"
              locale="zh-cn"
              @ionChange="onDtChange"
              size="cover">
            </ion-datetime>
            <ion-item class="ion-no-padding" @click="() => (datetimeShowFlag = true)" lines="none">
              <!-- 开始时间 -->
              <ion-icon :icon="timeOutline" slot="start"> </ion-icon>
              <ion-label>开始时间</ion-label>
              <label class="mr-[6px]">
                {{ curScheduleData.allDay ? "全天" : curScheduleData.startTs?.format("HH:mm") }}
              </label>
            </ion-item>
          </div>
        </ion-item>
        <!-- 提醒 -->
        <!-- <ion-item :button="true" :detail="true">
          <ion-icon :icon="notifications" slot="start"> </ion-icon>
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
        <!-- 重复 -->
        <ion-item detail="true" id="btnRepeat" lines="none">
          <ion-icon :icon="repeat" slot="start"> </ion-icon>
          <ion-label>重复</ion-label>
          <ion-label class="text-right mr-0">
            <div>
              <p class="inline-block mr-2 gray">
                {{
                  getNextRepeatDate(
                    curScheduleData.startTs,
                    curScheduleData.repeat,
                    curScheduleData.repeatData
                  )
                }}
              </p>
              <div class="inline-block">{{ getRepeatOptions(curScheduleData.repeat).label }}</div>
            </div>
          </ion-label>
        </ion-item>
        <div class="border-b ml-14">
          <div
            v-if="curScheduleData.repeat === CUSTOM_REPEAT_ID"
            class="text-gray-400 text-wrap ion-no-padding">
            <p
              class="text-xs text-right pr-8 pb-1"
              v-if="
                curScheduleData &&
                curScheduleData.repeatData &&
                curScheduleData.repeatData?.week?.length
              ">
              {{ buildCustomRepeatLabel(curScheduleData.repeatData) }}
            </p>
          </div>
        </div>
        <RepeatSelector
          trigger="btnRepeat"
          @update:value="onRepeatChange"
          :dt="curScheduleData.startTs"
          :value="curScheduleData" />

        <ion-item detail="true" :button="true" id="id-repeat-end">
          <ion-icon :icon="power" slot="start"></ion-icon>
          <ion-label>重复停止</ion-label>
          <ion-label class="text-right mr-0">
            {{
              curScheduleData?.repeatEndTs === undefined
                ? "无"
                : curScheduleData?.repeatEndTs.format("YYYY-MM-DD")
            }}
          </ion-label>
          <ion-modal
            :keep-contents-mounted="true"
            ref="repeatEndTsModal"
            trigger="id-repeat-end"
            class="bottom-modal"
            style="--width: 95%; --height: auto"
            aria-hidden="false">
            <ion-datetime
              locale="zh-cn"
              id="idRepeatEndTs"
              ref="repeatEndTsComponent"
              :value="
                curScheduleData?.repeatEndTs?.format('YYYY-MM-DD') || dayjs().format('YYYY-MM-DD')
              "
              presentation="date"
              size="cover"
              max="2099-01-01"
              @ionChange="onRepeatEndDtChange">
            </ion-datetime>
            <ion-footer class="flex justify-around">
              <ion-button
                class="w-2/5"
                fill="clear"
                size="default"
                color="warning"
                @click="btnRepeatEndClearClk">
                清除
              </ion-button>
              <ion-button class="w-2/5" fill="clear" size="default" @click="btnRepeatEndOkClk">
                确定
              </ion-button>
            </ion-footer>
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
        <ion-item>
          <ion-icon :icon="add" slot="start" style="width: 22px"></ion-icon>
          <ion-button @click="btnSubtaskAddClk" expand="full" class="w-full" color="light">
            添加子任务
          </ion-button>
        </ion-item>
        <SubtaskPopModal
          @update:value="onSubtaskChange"
          :value="curSubtask"
          :is-open="openSubtaskModal"
          @willDismiss="onSubtaskPopDismiss" />
        <ion-item v-for="(task, idx) in curScheduleData?.subtasks" :key="idx" class="subtask-item">
          <ion-checkbox
            slot="start"
            :checked="subTaskChecked(task)"
            class="ion-no-padding"
            @ionChange="onSubtaskCheckboxChange($event, task)">
          </ion-checkbox>
          <div class="flex flex-col w-full h-full" @click="onSubtaskClk($event, task)">
            <ion-label :class="{ 'text-line-through': subTaskChecked(task) }" class="ion-no-margin">
              {{ task.name }}
            </ion-label>
            <div class="pre-img-group" style="margin-top: 5px">
              <div class="pre-img-block" v-for="(img, idx) in task.imgIds" :key="idx">
                <img :src="imgs[img]" />
              </div>
            </div>
          </div>
          <div slot="end" class="w-8 h-full" @click="btnSubtaskRemoveClk($event, task)">
            <ion-icon :icon="removeCircleOutline" size="large" />
          </div>
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
    <!-- 开始时间弹窗 -->
    <ion-modal
      class="bottom-modal"
      :isOpen="datetimeShowFlag"
      :keep-contents-mounted="true"
      @willDismiss="() => (datetimeShowFlag = false)">
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
        @ionChange="(e:any) => (scheduleStartTsComponent = dayjs(e.detail.value))"
        class="schedule-datetime-time">
      </ion-datetime>
      <ion-item>
        <ion-toggle
          class="ion-padding-start"
          :checked="curScheduleData.allDay"
          @ionChange="onScheduleDatetimeAllDayChange">
          <h3>全天</h3>
        </ion-toggle>
      </ion-item>
      <ion-footer>
        <ion-button
          fill="clear"
          class="flex-1 text-gray-400"
          @click="() => (datetimeShowFlag = false)">
          清除
        </ion-button>
        <ion-button fill="clear" class="flex-1 text-orange-400" @click="btnScheduleDatetimeOkClk">
          确定
        </ion-button>
      </ion-footer>
    </ion-modal>
    <PrioritySelector
      trigger="btnPriority"
      @update:value="onPriorityChange"
      :value="curScheduleData.priority" />
  </ion-modal>
</template>
<script lang="ts" src="@/components/SchedulePopModal.ts"></script>
<style scoped>
.schedule-datetime-time::part(wheel-item) {
  min-width: 100px;
  color: rgb(255, 66, 97);
  align-items: center;
  text-align: center;
  font-size: larger;
}
.subtask-item ion-checkbox {
  --size: 18px;
  --border-radius: 4px;
}
.subtask-item::part(native) {
  align-items: flex-start;
  padding: 16px 16px 0 16px;
}
ion-modal#main::part(content) {
  max-width: 500px;
}
ion-modal#main {
  --height: 100%;
}
</style>
