/**
 * 日程存档数据模型
 */
import { ScheduleData } from "./ScheduleData";

// 日程存档【每天】
export class ScheduleSave {
  state: number = 0;
  subtasks: Record<number, number> = {}; // <number, number>;
  // 覆盖字段
  scheduleOverride?: ScheduleData;
  score?: number; // 通过这个任务获得的积分

  constructor() {
    this.state = 0;
    this.subtasks = {};
    this.scheduleOverride = undefined;
    this.score = undefined;
  }

  static Copy(o: ScheduleSave): ScheduleSave {
    const ret = new ScheduleSave();
    ret.state = o.state;
    ret.score = o.score;
    if (o.scheduleOverride) ret.scheduleOverride = ScheduleData.Copy(o.scheduleOverride);
    if (o.subtasks) ret.subtasks = JSON.parse(JSON.stringify(o.subtasks));
    return ret;
  }
}

