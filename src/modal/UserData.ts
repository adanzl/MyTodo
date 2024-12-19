import dayjs from "dayjs";

export interface SubTask {
  id: number;
  name: string;
}

// 日程计划数据
export class ScheduleData {
  // ===== 日程数据 =====
  id: number = -1; // 任务id
  title?: string; // 任务标题
  color = 0; // 颜色id
  priority = -1; // 优先级
  groupId = -1; // 分组id
  startTs?: dayjs.Dayjs; // 开始时间
  endTs?: dayjs.Dayjs; // 结束时间
  allDay: boolean = true; // 是否全天
  reminder: number = 0; // 提醒类型
  repeat: number = 0; // 重复类型
  repeatEndTs?: dayjs.Dayjs; // 重复结束类型
  subTasks: SubTask[] = []; // 子任务列表
  constructor() {
    this.startTs = dayjs().startOf("day");
    this.endTs = dayjs().startOf("day");
  }
}

// 日程存档
export class ScheduleSave {
  state: number = -1;
  subTasks: Record<number, number> = {}; // <number, number>;
}

// 用户数据
export class UserData {
  id: number = -1; // 用户id
  name: string = ""; // 用户名称
  schedules: ScheduleData[] = []; // 日程计划列表
  // 计划完成情况  日期->对应日期完成情况(任务id->完成情况)
  save: Record<string, Record<number, ScheduleSave>> = {};
}

export const S_TS = (dt?: dayjs.Dayjs): string => {
  if (dt === undefined) return "";
  return dt.format("YYYY-MM-DD");
};

export const parseScheduleData = (jsonStr: string): ScheduleData => {
  const ret = JSON.parse(jsonStr) as ScheduleData;
  ret.startTs = dayjs(ret.startTs);
  ret.endTs = dayjs(ret.endTs);
  ret.repeatEndTs = ret.repeatEndTs && dayjs(ret.repeatEndTs);
  return ret;
};

export const parseUserData = (jsonStr: string): UserData => {
  const ret = JSON.parse(jsonStr) as UserData;
  for (let i = 0; i < ret.schedules.length; i++) {
    const schedule = ret.schedules[i];
    schedule.startTs = dayjs(schedule.startTs);
    schedule.endTs = dayjs(schedule.endTs);
    schedule.repeatEndTs = schedule.repeatEndTs && dayjs(schedule.repeatEndTs);
  }
  return ret;
};

export default {
  ScheduleData,
  ScheduleSave,
  UserData,
  S_TS,
  parseUserData,
  parseScheduleData,
};
