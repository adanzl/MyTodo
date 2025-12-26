/**
 * 用户数据模型
 */
import { ScheduleData } from "./ScheduleData";
import type { ScheduleSave } from "./ScheduleSave";

// 用户数据
export class UserData {
  id: number = -1; // 存档id
  name: string = ""; // 存档名称
  userId: number = -1; // 用户id
  schedules: ScheduleData[] = []; // 日程计划列表
  // 计划完成情况  日期->对应日期完成情况(任务id->完成情况)
  save: Record<string, Record<number, ScheduleSave>> = {};

  constructor() {
    this.id = -1;
    this.name = "";
    this.userId = -1;
    this.schedules = [];
    this.save = {};
  }

  static Copy(o: UserData): UserData {
    const ret = new UserData();
    ret.id = o.id;
    ret.name = o.name;
    ret.schedules = [];
    for (const schedule of o.schedules) {
      ret.schedules.push(ScheduleData.Copy(schedule));
    }
    ret.save = JSON.parse(JSON.stringify(o.save));
    return ret;
  }
}


