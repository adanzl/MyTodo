<template>
  <div id="container">
    <ion-grid>
      <ion-row justify-content-center>
        <ion-col col-auto @click="back()">
          <ion-icon ios="ios-arrow-back" md="md-arrow-back"></ion-icon>
        </ion-col>
        <ion-col col-auto>
          <div>{{ displayYear }} 年 {{ displayMonth + 1 }} 月</div>
        </ion-col>
        <ion-col col-auto @click="forward()">
          <ion-icon ios="ios-arrow-forward" md="md-arrow-forward"></ion-icon>
        </ion-col>
      </ion-row>

      <!-- <ion-row>
        <ion-col
          class="center calendar-header-col"
          *ngFor="let head of weekHead"
          >{{ head }}</ion-col        >
      </ion-row> -->

      <!-- <ion-row
        class="calendar-row"
        *ngFor="let week of weekArray;let i = index"
      >
        <ion-col
          class="center calendar-col"
          (click)="daySelect(day,i,j)"
          *ngFor="let day of week;let j = index"
          [ngClass]="[day.isThisMonth?'this-month':'not-this-month',day.isToday?'today':'',day.isSelect?'select':'']"
        >
          {{ day.date }}
        </ion-col>
      </ion-row> -->
    </ion-grid>
  </div>
</template>
<!-- https://www.npmjs.com/package/ionic3-calendar?activeTab=code -->
<script setup lang="ts">
import { IonGrid, IonRow, IonCol } from "@ionic/vue";
import { ref } from "vue";
defineProps({
  name: String,
});
const dt = new Date();
let currentYear = dt.getFullYear();
let displayYear = ref(dt.getFullYear());
let currentMonth = dt.getMonth();
let currentDate = dt.getDate();
let currentDay = dt.getDay();
const forward = () => {
  // 处理跨年的问题
  if (displayMonth === 11) {
    displayYear++;
    displayMonth = 0;
  } else {
    this.displayMonth++;
  }
  this.createMonth(this.displayYear, this.displayMonth);
};
const back = () => {
  // 处理跨年的问题
  if (this.displayMonth === 0) {
    this.displayYear--;
    this.displayMonth = 11;
  } else {
    this.displayMonth--;
  }
  this.createMonth(this.displayYear, this.displayMonth);
};
const today = () => {
  this.displayYear = this.currentYear;
  this.displayMonth = this.currentMonth;
  this.createMonth(this.currentYear, this.currentMonth);

  // 将今天标记为选择状态
  let todayIndex = _.findIndex(this.dateArray, {
    year: this.currentYear,
    month: this.currentMonth,
    date: this.currentDate,
    isThisMonth: true,
  });
  this.lastSelect = todayIndex;
  this.dateArray[todayIndex].isSelect = true;

  this.onDaySelect.emit(this.dateArray[todayIndex]);
};
</script>
<style>
ion-calendar {
  font-family: "Microsoft YaHei";
  .center {
    text-align: center;
  }
  .calendar-header-col {
    font-size: 1rem;
    color: #666;
  }
  .calendar-row {
    &:last-child {
      border-bottom: 1px solid #eee;
    }
    .calendar-col {
      display: flex;
      justify-content: center;
      padding: 0.8rem;
      font-size: 1.2rem;
      border-left: 1px solid #eee;
      border-top: 1px solid #eee;
      &:last-child {
        border-right: 1px solid #eee;
      }
    }
    .not-this-month {
      color: #fff;
      background: linear-gradient(#e5e5e5, #dfdfdf);
    }
    .today {
      color: #fff;
      box-shadow: inset 0 0 10px #aaa;
      background: radial-gradient(#c5c5c5, #c8c8c8, #ccc);
    }
    .select {
      box-shadow: none;
      color: #fff;
      background: radial-gradient(#5c7eda, #5e89ec, #5e89ec);
    }
  }
}
</style>
