/**
 * 一天的数据模型
 */
import dayjs, { type Dayjs } from "dayjs";
import type { ScheduleData } from "./ScheduleData";
import type { ScheduleSave } from "./ScheduleSave";

// 一天的数据
export class DayData {
  dt: Dayjs;
  events: ScheduleData[] = []; // 当天可见日程
  save?: Record<number, ScheduleSave>; // 日程id->日程保存情况

  constructor(_dt?: Dayjs) {
    this.dt = _dt || dayjs().startOf("day");
    this.events = [];
    this.save = undefined;
  }
}
