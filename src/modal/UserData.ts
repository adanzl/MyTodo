import dayjs from "dayjs";

export class Subtask {
  id: number = -1;
  name?: string = "";
  imgIds: number[] = []; // 图片id列表
  static Copy(o: Subtask): Subtask {
    return {
      id: o.id,
      name: o.name,
      imgIds: o.imgIds?.concat(),
    };
  }
}

// 日程计划数据
export class ScheduleData {
  // ===== 日程数据 =====
  id: number = -1; // 任务id
  startTs?: dayjs.Dayjs; // 开始时间
  endTs?: dayjs.Dayjs; // 结束时间
  allDay?: boolean = true; // 是否全天
  reminder?: number = 0; // 提醒类型
  repeat?: number = 0; // 重复类型
  repeatEndTs?: dayjs.Dayjs; // 重复结束类型
  // 以下字段为覆盖字段，用于覆盖默认值
  title?: string; // 任务标题
  color? = 0; // 颜色id
  priority? = -1; // 优先级
  groupId? = -1; // 分组id
  subtasks: Subtask[] = []; // 子任务列表
  static Copy(o: ScheduleData): ScheduleData {
    const ret = JSON.parse(JSON.stringify(o));
    ret.startTs = o.startTs?.clone();
    ret.endTs = o.endTs?.clone();
    ret.repeatEndTs = o.repeatEndTs?.clone();
    ret.subtasks = [];
    if (o.subtasks) {
      for (const subtask of o.subtasks) {
        ret.subtasks.push(Subtask.Copy(subtask));
      }
    }
    return ret;
  }
  constructor() {
    this.startTs = dayjs().startOf("day");
    this.endTs = dayjs().startOf("day");
  }
}

// 日程存档【每天】
export class ScheduleSave {
  state: number = -1;
  subtasks: Record<number, number> = {}; // <number, number>;
  // 覆盖字段
  scheduleOverride?: ScheduleData;
  static Copy(o: ScheduleSave): ScheduleSave {
    const ret = new ScheduleSave();
    ret.state = o.state;
    ret.subtasks = JSON.parse(JSON.stringify(o.subtasks));
    return ret;
  }
}

// 用户数据
export class UserData {
  id: number = -1; // 用户id
  name: string = ""; // 用户名称
  schedules: ScheduleData[] = []; // 日程计划列表
  // 计划完成情况  日期->对应日期完成情况(任务id->完成情况)
  save: Record<string, Record<number, ScheduleSave>> = {};
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
  if (ret.schedules === undefined) {
    ret.schedules = [];
  }
  for (let i = 0; i < ret.schedules.length; i++) {
    const schedule = ret.schedules[i];
    schedule.startTs = dayjs(schedule.startTs);
    schedule.endTs = dayjs(schedule.endTs);
    schedule.repeatEndTs = schedule.repeatEndTs && dayjs(schedule.repeatEndTs);
    if (schedule.subtasks === undefined) {
      schedule.subtasks = [];
    }
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
