<script lang="ts">
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
  startTs?: dayjs.Dayjs; // 开始时间
  endTs?: dayjs.Dayjs; // 结束时间
  allDay: boolean = false; // 是否全天
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
  // save: Map<string, Map<number, ScheduleSave>>;
  save: Record<string, Record<number, ScheduleSave>> = {};
}

export const SAVE_TS = (dt?: dayjs.Dayjs): string => {
  if(dt ===undefined) return '';
  return dt.format("YYYY-MM-DD");
};
</script>
