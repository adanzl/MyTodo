/**
 * 一个月的数据模型
 */
import dayjs, { type Dayjs } from "dayjs";

// 一个月的数据
export class MonthData {
  vid: number = 0;
  month: number = 0;
  year: number = 0;
  firstDayOfMonth: Dayjs = dayjs().startOf("day");
  weekArr: any[] = [];

  constructor() {
    this.vid = 0;
    this.month = 0;
    this.year = 0;
    this.firstDayOfMonth = dayjs().startOf("day");
    this.weekArr = [];
  }
}


