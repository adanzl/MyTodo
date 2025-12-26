/**
 * 日程计划数据模型
 */
import dayjs, { type Dayjs } from "dayjs";
import { RepeatData } from "./RepeatData";
import { Subtask } from "./Subtask";

// 日程计划数据
export class ScheduleData {
  id: number = -1; // 任务id
  startTs?: Dayjs; // 开始时间
  endTs?: Dayjs; // 结束时间
  allDay: boolean = true; // 是否全天
  reminder: number = 0; // 提醒类型
  repeat: number = 0; // 重复类型
  repeatData: RepeatData = new RepeatData(); // 重复数据
  repeatEndTs?: Dayjs; // 重复结束类型
  // 以下字段为覆盖字段，用于覆盖默认值
  title?: string; // 任务标题
  color: number = 0; // 颜色id
  priority: number = -1; // 优先级
  groupId: number = -1; // 分组id
  order: number = 0; // 排序 数字越大越靠后
  score?: number; // 积分
  subtasks: Subtask[] = []; // 子任务列表

  constructor() {
    this.id = -1;
    this.startTs = undefined;
    this.endTs = undefined;
    this.allDay = true;
    this.reminder = 0;
    this.repeat = 0;
    this.repeatData = new RepeatData();
    this.repeatEndTs = undefined;
    this.title = undefined;
    this.color = 0;
    this.priority = -1;
    this.groupId = -1;
    this.order = 0;
    this.score = undefined;
    this.subtasks = [];
    this.startTs = dayjs().startOf("day");
    this.endTs = dayjs().startOf("day");
  }

  static Copy(o: ScheduleData): ScheduleData {
    const ret = JSON.parse(JSON.stringify(o)) as ScheduleData;
    ret.startTs = ret.startTs ? dayjs(ret.startTs) : undefined;
    ret.endTs = ret.endTs ? dayjs(ret.endTs) : undefined;
    ret.repeatEndTs = ret.repeatEndTs ? dayjs(ret.repeatEndTs) : undefined;
    ret.subtasks = [];
    if (o.subtasks) {
      for (const subtask of o.subtasks) {
        ret.subtasks.push(Subtask.Copy(subtask));
      }
    }
    return ret;
  }
}


